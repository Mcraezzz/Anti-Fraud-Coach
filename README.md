# Anti-Fraud Coach：两个项目说明与对比

[中文](README.md) | [English](README.en.md)

本仓库保留两个独立实现：**新版微信小程序 + FastAPI 后端**和 **coursework 校园反诈 RAG 课程项目**。新版小程序已经调用自己的后端；它没有调用 `coursework/anti_fraud_rag/`。两者分别安装、启动和管理数据。

## 项目导航

- **项目一：小程序应用** — `miniprogram/`、`backend/`、`web-preview/`；下方提供功能和启动说明。
- **项目二：课程 RAG 系统** — [coursework 中文说明](coursework/README.md) / [English](coursework/README.en.md)，包含 Python 核心、Streamlit、React 网页原型、测试、报告和参考文献。

## 项目一：新版微信小程序与 FastAPI 后端

学生可以在微信小程序里粘贴可疑短信、聊天记录或链接，查看哪些话术触发了风险提示，再进入相关情景练习如何回应。例如，遇到“先交保证金才能入职”的招聘消息，可以查看识别依据和处置建议，然后在虚假兼职训练中选择下一步行动。

### 功能

- **风险识别**支持文本、短信、链接和聊天截图。截图通过本地 OCR 提取文字。结果页展示风险等级、命中的原文片段和行动建议。
- **反诈问答**从校园反诈知识库检索资料，随回答列出参考依据。每个问题独立检索。
- **情景训练**覆盖虚假兼职、刷单返利、冒充客服、游戏交易诈骗、校园贷和冒充熟人。后端根据所选回答评分，能力报告汇总六个维度的表现，并标出尚未评估的维度。
- **记录与管理**按设备会话保存识别历史、训练进度和隐私偏好。管理员可查看汇总的识别活动和训练完成情况。

### 在微信开发者工具中运行

在仓库根目录打开 PowerShell。以下命令启动 FastAPI 后端，问答使用词法检索，OCR 在需要时加载。

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
$env:ANTI_FRAUD_SEMANTIC_RAG = "0"
$env:ANTI_FRAUD_OCR_PRELOAD = "0"
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

打开[健康检查](http://127.0.0.1:8000/api/coach/health)，确认返回的 `ok` 为 `true`。保持后端运行，在微信开发者工具中导入 [miniprogram](miniprogram/) 目录并点击「编译」。进入「识别」，选择一个内置样本并点击「开始智能识别」，即可验证小程序与后端的连接。[本地 API 文档](http://127.0.0.1:8000/docs)

真机调试时，将启动命令中的监听地址改为 `0.0.0.0`，让手机和电脑连接同一局域网。在「我的 → 系统偏好设置 → 个人资料与后端连接设置」填写电脑的局域网地址及端口，例如 `http://192.168.1.20:8000`。

### 数据与模型

小程序通过 `/api/coach` 访问后端。服务默认将设备会话和活动保存在 `backend/app/data/coach.sqlite3`，可通过 `ANTI_FRAUD_COACH_DB` 指定数据库位置。清除小程序本地存储后，原设备会话将无法恢复。

截图识别需要本地 OCR 运行环境和模型。要启用语义检索，可安装模型依赖，将 `ANTI_FRAUD_RESOURCE_ROOT` 指向包含 `models` 子目录的资源目录，并将 `ANTI_FRAUD_SEMANTIC_RAG` 设为 `1` 后重启服务。[模型依赖](backend/requirements-models.txt) · [检索配置](docs/RAG语义检索说明.md) · [小程序接入与测试](docs/新版小程序接入说明.md)

## 项目二：课程 RAG 系统

面向中英文反诈内容分析与课程实验，采用 Python、Streamlit、BM25、BGE-M3、FAISS、BGE 重排序、PaddleOCR 和可选 Qwen API。支持文本与图片文字分析，输出风险特征、证据、建议和训练问题。`coursework/webdesign/` 是使用模拟数据的 React 设计原型，尚未连接 Python 引擎。

从仓库根目录执行 `cd coursework`，按[技术与运行说明](coursework/docs/rag-project.md)安装依赖、配置数据/模型路径、构建索引，再执行 `streamlit run app.py`。API 密钥缺失或调用失败时，分析可回退为规则模拟；`--mock` 仍需本地检索依赖。

## 共同点与差异

两者都面向大学生反诈识别与教育，围绕风险信号、证据解释、处置建议和训练学习展开，并包含 OCR 与知识检索相关实现。相同技术名称不代表共享实现、索引或数据。

| 对比项 | 项目一：新版小程序应用 | 项目二：coursework RAG |
| --- | --- | --- |
| 定位 | 面向用户的识别、问答、训练和记录流程 | 课程研究、检索与生成流程验证 |
| 主要入口 | 微信小程序调用 FastAPI `/api/coach` | Streamlit `app.py` 与命令行 `run_demo.py` |
| 代码位置 | `miniprogram/`、`backend/` | `coursework/` |
| 前后端连接 | 小程序已实现自身后端调用 | Streamlit 直接使用课程引擎；React 原型未接通 |
| 检索 | 自有知识库、词法检索及可选语义检索配置 | BM25 + BGE-M3/FAISS、IOC 匹配、融合与重排序 |
| 模型配置 | `ANTI_FRAUD_*` 环境变量及本地模型资源 | `.env.example` 中的数据/模型路径和 Qwen API 配置 |
| 训练与历史 | 后端评分、设备会话、训练进度和 SQLite 活动记录 | 分析中生成训练问题，侧重结构化输出与实验材料 |
| 数据存储 | 默认 `backend/app/data/coach.sqlite3` | 默认 `coursework/storage/rag_index`，不共享前者数据库 |
| 预览页面 | `web-preview/` | `coursework/webdesign/`，使用模拟数据 |
| 相互关系 | 不依赖课程项目启动 | 不连接新版小程序服务；可独立运行 |

源码、配置示例、测试、报告、图表和参考文献纳入仓库。依赖目录、密钥、运行数据库、日志、本地索引、第三方安装包以及外部模型/数据集不随上传提供。

