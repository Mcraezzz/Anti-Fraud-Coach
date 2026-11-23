# Anti-Fraud Coach · 校园反诈教练

简体中文 · [English](README.en.md)

学生可以在微信小程序里粘贴可疑短信、聊天记录或链接，查看哪些话术触发了风险提示，再进入相关情景练习如何回应。例如，遇到“先交保证金才能入职”的招聘消息，可以查看识别依据和处置建议，然后在虚假兼职训练中选择下一步行动。

## 功能

- **风险识别**支持文本、短信、链接和聊天截图。截图通过本地 OCR 提取文字。结果页展示风险等级、命中的原文片段和行动建议。
- **反诈问答**从校园反诈知识库检索资料，随回答列出参考依据。每个问题独立检索。
- **情景训练**覆盖虚假兼职、刷单返利、冒充客服、游戏交易诈骗、校园贷和冒充熟人。后端根据所选回答评分，能力报告汇总六个维度的表现，并标出尚未评估的维度。
- **记录与管理**按设备会话保存识别历史、训练进度和隐私偏好。管理员可查看汇总的识别活动和训练完成情况。

## 在微信开发者工具中运行

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

## 数据与模型

小程序通过 `/api/coach` 访问后端。服务默认将设备会话和活动保存在 `backend/app/data/coach.sqlite3`，可通过 `ANTI_FRAUD_COACH_DB` 指定数据库位置。清除小程序本地存储后，原设备会话将无法恢复。

截图识别需要本地 OCR 运行环境和模型。要启用语义检索，可安装模型依赖，将 `ANTI_FRAUD_RESOURCE_ROOT` 指向包含 `models` 子目录的资源目录，并将 `ANTI_FRAUD_SEMANTIC_RAG` 设为 `1` 后重启服务。[模型依赖](backend/requirements-models.txt) · [检索配置](docs/RAG语义检索说明.md) · [小程序接入与测试](docs/新版小程序接入说明.md)
