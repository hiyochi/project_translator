import argparse
import signal
import sys
import tomllib
import time
from pathlib import Path
from typing import Dict, Any, List
from openai import OpenAI


class ProjectTranslator:
    def __init__(self, target_dir: str, profile_name: str = "default"):
        self.is_exiting = False
        self.root_path = Path(target_dir).resolve()

        # 加载配置
        self.config = self._load_config(profile_name)
        self.model_config = self.config["model"][profile_name]

        # 初始化客户端 (使用 .get() 防止配置文件缺少 base_url 报错)
        self.client = OpenAI(
            base_url=self.model_config.get("base_url"),
            api_key=self.model_config["api_key"],
        )

        self.status_file = self.root_path / self.config["log_file_name"]

        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, sig, frame):
        """拦截 Ctrl+C 并优雅退出"""
        print("\n\n🛑 接收到中断信号，等待当前文件处理完毕后停止...")
        self.is_exiting = True

    def _load_config(self, profile_name: str) -> Dict[str, Any]:
        """加载配置文件"""
        config_path = Path(__file__).parent / "config.toml"
        if not config_path.exists():
            sys.exit(f"❌ 错误：找不到配置文件 {config_path}")

        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        if "model" not in data or profile_name not in data["model"]:
            sys.exit(f"❌ 错误：配置文件中找不到 [{profile_name}] 配置节")

        return data

    def _get_translate_prompt(
        self, content: str, is_code: bool
    ) -> List[Dict[str, str]]:
        """生成 Prompt (消除重复代码)"""
        prompt_type = "code" if is_code else "non_code"
        return [
            {"role": "system", "content": self.config["prompts"][prompt_type]},
            {"role": "user", "content": content},
        ]

    def _process_file(
        self, file_path: Path, is_code: bool, max_retries: int = 3
    ) -> bool:
        """处理单个文件，包含重试机制和原子写入"""
        try:
            source_text = file_path.read_text(encoding="utf-8")
            if not source_text.strip():
                return True

            # 重试机制
            translated_text = None
            for attempt in range(max_retries):
                if self.is_exiting:
                    return False
                try:
                    response = self.client.chat.completions.create(
                        model=self.model_config["model"],
                        messages=self._get_translate_prompt(source_text, is_code),
                        temperature=self.model_config.get("temperature", 0.3),
                        timeout=60.0,  # 设置超时，防止死等
                    )
                    translated_text = response.choices[0].message.content
                    break  # 成功则跳出重试循环
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(2)  # 失败后稍作等待
                    else:
                        raise e  # 抛出最后一次异常

            if translated_text:
                # 【关键优化】原子写入：先写入临时文件，再替换原文件，防止强退导致文件损坏
                temp_file = file_path.with_suffix(".tmp.trans")
                temp_file.write_text(translated_text, encoding="utf-8")
                temp_file.replace(file_path)
                return True

        except UnicodeDecodeError:
            print(f"\n   ⚠️ 跳过二进制或非 UTF-8 文件: {file_path.name}")
        except Exception as e:
            if not self.is_exiting:
                print(f"\n   ❌ 处理出错 {file_path.name}: {e}")

        return False

    def run(self):
        """执行主逻辑"""
        if not self.root_path.exists() or not self.root_path.is_dir():
            print(f"❌ 错误：路径 '{self.root_path}' 不存在")
            return

        processed_files = set()
        if self.status_file.exists():
            processed_files = {
                line.strip()
                for line in self.status_file.read_text(encoding="utf-8").splitlines()
                if line.strip()
            }

        print(f"🚀 开始处理: {self.root_path}")
        print(f"📌 已跳过 {len(processed_files)} 个记录\n")

        # 以追加模式打开日志文件，保持句柄打开，提高性能
        with open(self.status_file, "a", encoding="utf-8") as status_f:
            for file_path in self.root_path.rglob("*"):
                if self.is_exiting:
                    print("\n🛑 运行已安全中止。")
                    break

                if (
                    not file_path.is_file()
                    or file_path.name == self.config["log_file_name"]
                ):
                    continue

                # 【优化】只检查相对路径的 parts，避免被父级目录的命名误导
                rel_path = str(file_path.relative_to(self.root_path))
                rel_parts = Path(rel_path).parts
                if any(
                    part in self.config["ignore_dirs"] or part.startswith(".")
                    for part in rel_parts
                ):
                    continue

                if rel_path in processed_files:
                    continue

                ext = file_path.suffix.lower()
                is_doc = ext in self.config.get("doc_exts", [])
                is_code = ext in self.config.get("code_exts", [])

                if is_doc or is_code:
                    print(f"📝 正在翻译: {rel_path} ... ", end="", flush=True)

                    if self._process_file(file_path, is_code):
                        status_f.write(f"{rel_path}\n")
                        status_f.flush()  # 确保立刻写入硬盘
                        print("✅")
                    else:
                        print("⏩ (跳过或失败)")


def main():
    parser = argparse.ArgumentParser(description="多配置全能项目翻译工具")
    parser.add_argument("dir", help="目标文件夹路径")
    parser.add_argument(
        "--profile",
        "-p",
        default="default",
        help="使用 config.toml 中的配置段 (默认: default)",
    )
    args = parser.parse_args()

    translator = ProjectTranslator(args.dir, args.profile)
    translator.run()


if __name__ == "__main__":
    main()
