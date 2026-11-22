# Anti-Fraud Coach

新版小程序已接入下载版本的视觉样式与六类情景训练，真实实现位于本目录。启动、数据说明及验证方式见 [新版小程序接入说明](docs/新版小程序接入说明.md)。`Documents/CRAIC` 仅为界面原型。

面向大学生的 AI 反诈情景识别与智能训练系统 MVP。

本项目采用“小程序前端 + FastAPI 后端”的结构。后端优先使用规则引擎完成稳定演示，并预留本地模型、OCR、RAG 检索接口；当 `D:\CARIC模型&数据集` 下的模型可用且依赖安装完成后，可以逐步启用更强的 embedding、reranker 和生成模型。

## 目录结构

```text
反诈系统/
  backend/        FastAPI 后端
  miniprogram/    微信小程序前端
  docs/           说明文档
```

## 快速启动后端

```powershell
cd C:\Users\22672\Desktop\反诈系统\backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

启动后访问：

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

运行后端测试：

```powershell
cd C:\Users\22672\Desktop\反诈系统\backend
python -m pytest -q
```

## 小程序使用

用微信开发者工具导入：

```text
C:\Users\22672\Desktop\反诈系统\miniprogram
```

本地调试时请在微信开发者工具中关闭“校验合法域名”，后端地址默认为 `http://127.0.0.1:8000`。

## 本地模型目录

默认读取：

```text
D:\CARIC模型&数据集
```

当前后端已预留以下模型路径：

- `models\hfl_chinese-macbert-base`
- `models\BAAI_bge-m3`
- `models\BAAI_bge-reranker-v2-m3`
- `models\Qwen_Qwen3-Embedding-0.6B`
- `models\Qwen_Qwen3-4B-Instruct-2507`

MVP 默认不开启大模型生成，避免普通电脑首次运行卡顿。后续可以在 `backend/app/services/model_service.py` 中接入本地推理或远程 API。

## 当前能力

- 规则引擎支持关键词风险、链接风险、金额风险和组合话术识别。
- 组合话术包括冒充客服链路、刷单返利链路、贷款陷阱链路。
- 小程序端展示风险等级、风险分、可信度、风险概览、风险解释和建议。
- 情景训练包含 10 道题，并输出得分、薄弱类型和能力维度。
