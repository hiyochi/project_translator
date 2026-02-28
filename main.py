# import os
import argparse
import signal
import sys
import tomllib
from pathlib import Path
from openai import OpenAI

# 全局变量
is_exiting = False
client = None
config = {}
model_config = {}


def signal_handler(sig, frame):
    """拦截 Ctrl+C 并立即退出"""
    global is_exiting
    print("\n\n🛑 接收到中断信号，正在立即停止...")
    is_exiting = True
    sys.exit(0)


# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)


def load_config(profile_name):
    """加载指定的配置文件段落"""
    config_path = Path(__file__).parent / "config.toml"
    if not config_path.exists():
        print(f"❌ 错误：找不到配置文件 {config_path}")
        sys.exit(1)

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    if "model" not in data or profile_name not in data["model"]:
        print(f"❌ 错误：配置文件中找不到 [{profile_name}] 配置节")
        sys.exit(1)

    return data


def get_translate_prompt(content, is_code):
    if not is_code:
        return [
            {
                "role": "system",
                "content": config["prompts"]["non_code"],
            },
            {"role": "user", "content": content},
        ]
    else:
        return [
            {
                "role": "system",
                "content": config["prompts"]["code"],
            },
            {"role": "user", "content": content},
        ]


def process_file(file_path, is_code):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source_text = f.read()

        if not source_text.strip():
            return True

        # 设置较短的超时或在此检查退出标志
        response = client.chat.completions.create(
            model=model_config["model"],
            messages=get_translate_prompt(source_text, is_code),
            temperature=model_config["temperature"],
            # timeout=60.0 # 可选：设置超时防止无限等待
        )

        translated_text = response.choices[0].message.content

        if translated_text:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(translated_text)
            return True
        return False

    except Exception as e:
        if not is_exiting:
            print(f"\n   ❌ 处理出错 {file_path.name}: {e}")
        return False


def main():
    global client, config, model_config

    parser = argparse.ArgumentParser(description="多配置全能项目翻译工具")
    parser.add_argument("dir", help="目标文件夹路径")
    parser.add_argument(
        "--profile",
        "-p",
        default="default",
        help="使用 config.toml 中的配置段 (默认: default)",
    )
    args = parser.parse_args()

    config = load_config(args.profile)
    model_config = config["model"][args.profile]
    client = OpenAI(api_key=model_config["api_key"], base_url=model_config["base_url"])

    if not args.dir:
        parser.print_help()
        return

    root_path = Path(args.dir).resolve()
    status_file = root_path / config["log_file_name"]

    if not root_path.exists() or not root_path.is_dir():
        print(f"❌ 错误：路径 '{args.dir}' 不存在")
        return

    processed_files = set()
    if status_file.exists():
        with open(status_file, "r", encoding="utf-8") as f:
            processed_files = {line.strip() for line in f if line.strip()}

    print(f"🚀 开始处理: {root_path}")
    print(f"📌 已跳过 {len(processed_files)} 个记录\n")

    for file_path in root_path.rglob("*"):
        if is_exiting:
            break  # 检查退出标志

        if not file_path.is_file() or file_path.name == config["log_file_name"]:
            continue
        if any(
            part in config["ignore_dirs"] or part.startswith(".")
            for part in file_path.parts
        ):
            continue

        rel_path = str(file_path.relative_to(root_path))
        if rel_path in processed_files:
            continue

        ext = file_path.suffix.lower()
        is_doc = ext in config["doc_exts"]
        is_code = ext in config["code_exts"]

        if is_doc or is_code:
            print(f"📝 正在翻译: {rel_path} ... ", end="", flush=True)

            if process_file(file_path, is_code):
                with open(status_file, "a", encoding="utf-8") as f:
                    f.write(f"{rel_path}\n")
                print("✅")
            else:
                print("⏩")


if __name__ == "__main__":
    main()
