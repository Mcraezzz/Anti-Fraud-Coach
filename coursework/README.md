# 项目二：校园反诈 RAG 课程系统

[中文](README.md) | [English](README.en.md) · [两个项目的总览与对比](../README.md)

本目录独立保留原课程项目的源码、测试、配置示例、报告、图表和参考文献，包含此前修复的 IOC 匹配、OCR 解析及异常评分处理。

- **Python 核心**：`anti_fraud_rag/`，实现预处理、混合检索、证据融合与可选 Qwen 调用。
- **实际界面与命令行**：`app.py`（Streamlit）、`run_demo.py`；`build_index.py` 构建本地索引。
- **React 设计原型**：[webdesign](webdesign/README.md)，使用模拟数据，尚未接通 Python 引擎。
- **研究材料**：`N&D Report.docx`、`PROJECT_ANALYSIS_REPORT.md`、`参考文献/`、`outputs/`。

[完整技术、配置与运行说明](docs/rag-project.md)。所有 Python 启动、建索引及测试命令应在本目录执行：先从仓库根目录 `cd coursework`。运行时数据、模型与依赖需另外准备；配置示例为 `.env.example`。

新版微信小程序与它自己的 FastAPI 服务位于仓库 `miniprogram/` 和 `backend/`，不属于本目录，也未与本课程引擎共享接口或数据库。
