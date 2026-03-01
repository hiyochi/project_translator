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
        print("\n\n🛑 接收到中断信号，等待当前文件保存完毕后安全停止...")
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
        """生成 Prompt"""
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

            translated_text = None
            for attempt in range(max_retries):
                if self.is_exiting:
                    return False
                try:
                    response = self.client.chat.completions.create(
                        model=self.model_config["model"],
                        messages=self._get_translate_prompt(source_text, is_code),
                        temperature=self.model_config.get("temperature", 0.3),
                        timeout=60.0,
                    )
                    translated_text = response.choices[0].message.content
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(2)
                    else:
                        raise e

            if translated_text:
                # 原子写入：先写入临时文件，再替换，防止强退导致损坏
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

        # 1. 读取断点记录
        processed_files = set()
        if self.status_file.exists():
            processed_files = {
                line.strip()
                for line in self.status_file.read_text(encoding="utf-8").splitlines()
                if line.strip()
            }

        print(f"🔍 正在扫描目录: {self.root_path} ...")

        # 2. 预扫描并过滤文件
        files_to_process = []
        for file_path in self.root_path.rglob("*"):
            if (
                not file_path.is_file()
                or file_path.name == self.config["log_file_name"]
            ):
                continue

            rel_path = str(file_path.relative_to(self.root_path))
            rel_parts = Path(rel_path).parts

            # 过滤忽略的目录或隐藏目录
            if any(
                part in self.config.get("ignore_dirs", []) or part.startswith(".")
                for part in rel_parts
            ):
                continue

            # 过滤已处理过的文件
            if rel_path in processed_files:
                continue

            # 判断文件类型
            ext = file_path.suffix.lower()
            is_doc = ext in self.config.get("doc_exts", [])
            is_code = ext in self.config.get("code_exts", [])

            if is_doc or is_code:
                # 把符合条件的文件加入待处理队列
                files_to_process.append((file_path, rel_path, is_code))

        total_files = len(files_to_process)

        # 3. 打印统计信息
        print(f"📌 扫描完毕！已跳过 {len(processed_files)} 个历史完成项。")
        if total_files == 0:
            print("🎉 当前目录下所有支持的文件均已翻译完毕！")
            return

        print(f"🚀 开始翻译，共有 {total_files} 个文件需要处理。\n")

        # 为了让如 [ 1/15] [10/15] 对齐更美观，计算总数的位数
        pad_len = len(str(total_files))

        # 4. 遍历处理队列
        with open(self.status_file, "a", encoding="utf-8") as status_f:
            for i, (file_path, rel_path, is_code) in enumerate(files_to_process, 1):
                if self.is_exiting:
                    print("\n🛑 运行已安全中止。")
                    break

                # 打印进度，例如：[ 1/10] 📝 正在翻译: xxx ...
                progress_prefix = f"[{i:>{pad_len}}/{total_files}]"
                print(
                    f"{progress_prefix} 📝 正在翻译: {rel_path} ... ",
                    end="",
                    flush=True,
                )

                if self._process_file(file_path, is_code):
                    status_f.write(f"{rel_path}\n")
                    status_f.flush()
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
