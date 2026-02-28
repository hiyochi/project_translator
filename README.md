# LLM Project Translator

一个基于大语言模型的项目翻译工具，支持翻译文档和代码注释。

## 项目概述

LLM Project Translator 是一个功能强大的批量翻译工具，专门用于将开源项目中的文档和代码注释翻译成中文。它使用 OpenAI 兼容的 API（支持 Gemini、GPT 等多个模型），可以智能处理 Markdown 文档和各种编程语言的代码文件。

## 核心功能

- 📝 **文档翻译**：支持 Markdown (.md) 和纯文本 (.txt) 文件的翻译
- 💻 **代码注释翻译**：仅翻译代码中的注释，保持代码逻辑完整
- 🔄 **多配置支持**：支持多个模型配置（默认、专业版、GPT 等）
- ⚡ **批量处理**：递归扫描目录，自动处理所有符合条件的文件
- 🛡️ **安全机制**：原子写入防止文件损坏，支持中断后继续
- 📊 **进度记录**：自动记录已处理文件，避免重复翻译

## 环境要求

- **Python**: >= 3.14
- **依赖**: openai >= 2.24.0
- **API 密钥**: 需要 OpenAI 兼容 API 的访问密钥（如 Gemini API、OpenAI API 等）

## 安装步骤

### 1. 克隆或下载项目

```bash
git clone https://github.com/hiyochi/project_translator.git
cd project_translator
```

### 2. 安装依赖

使用 uv（推荐）：
```bash
uv sync
```

或使用 pip：
```bash
pip install -e .
```

### 3. 配置环境

复制配置示例文件：
```bash
cp config.example.toml config.toml
```

编辑 `config.toml`，填入你的 API 密钥：
```toml
[model.default]
base_url = "https://generativelanguage.googleapis.com/v1beta/"
api_key = "你的API密钥"  # 填入你的 API 密钥
model = "gemini-2.5-flash"
temperature = 0.1
```

## 使用指南

### 基本用法

翻译指定目录：
```bash
python main.py /path/to/your/project
```

### 使用不同的配置文件

使用 `--profile` 或 `-p` 参数指定配置段：
```bash
# 使用专业版配置（Gemini Pro）
python main.py /path/to/your/project -p pro

# 使用 GPT 配置
python main.py /path/to/your/project -p gpt
```

### 常见操作示例

#### 1. 翻译当前目录
```bash
python main.py .
```

#### 2. 翻译子目录
```bash
python main.py ./docs
```

#### 3. 中断后继续翻译
工具会自动记录已处理的文件到 `processed.txt`，再次运行时会自动跳过已处理的文件。

#### 4. 强制重新翻译
删除 `processed.txt` 文件即可重新翻译所有文件。

### 支持的文件类型

- **文档文件**：.md, .txt
- **代码文件**：.py, .rs, .js, .java, .cpp, .h, .go, .ts, .php

### 忽略的目录

默认会忽略以下目录：
- `.git`, `.venv`, `__pycache__`, `node_modules`
- `.idea`, `.vscode`
- `dist`, `build`
- `test_data`
- 所有以 `.` 开头的隐藏目录

## 配置说明

### 配置文件结构

`config.toml` 包含以下主要部分：

#### 全局配置
```toml
log_file_name = "processed.txt"  # 进度记录文件名
doc_exts = [".md", ".txt"]       # 文档文件扩展名
code_exts = [".py", ".rs", ...]  # 代码文件扩展名
ignore_dirs = [...]               # 忽略的目录列表
```

#### 提示词配置
```toml
[prompts]
non_code = "文档翻译的提示词..."
code = "代码注释翻译的提示词..."
```

#### 模型配置
```toml
[model.default]
base_url = "API 基础 URL"
api_key = "你的 API 密钥"
model = "模型名称"
temperature = 0.1  # 温度参数（越低越稳定）
```

### 支持的模型

- **Gemini 2.5 Flash**（默认，快速且经济）
- **Gemini 2.5 Pro**（更高质量）
- **GPT 系列**（OpenAI API）
- 任何 OpenAI 兼容 API 的模型

## 项目结构

```
project_translator/
├── main.py              # 主程序文件
├── config.example.toml  # 配置文件示例
├── pyproject.toml       # 项目配置和依赖
├── uv.lock              # uv 依赖锁定文件
├── LICENSE-MIT          # MIT 许可证
├── LICENSE-APACHE       # Apache 2.0 许可证
└── README.md            # 项目说明文档
```

## 贡献指南

欢迎贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建你的功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

### 开发规范

- 代码遵循 Python 最佳实践
- 提交信息清晰简洁
- 新增功能请添加相应的注释

## 许可证

本项目采用双重许可证：

- **MIT License** - 详见 [LICENSE-MIT](LICENSE-MIT)
- **Apache License 2.0** - 详见 [LICENSE-APACHE](LICENSE-APACHE)

你可以根据自己的需要选择其中一个许可证。

## 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 Issue：[GitHub Issues]

## 致谢

感谢所有为本项目做出贡献的开发者！

---

**注意**：使用本工具翻译项目时，请确保遵守原项目的许可证要求，尊重原作者的知识产权。
