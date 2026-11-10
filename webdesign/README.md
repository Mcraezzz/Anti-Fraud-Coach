# 校园反诈 RAG：配套网页设计原型

[中文](README.md) | [English](README.en.md)

[返回仓库总览](../README.md) · [Python RAG 项目](../docs/rag-project.md)

本目录使用 React、TypeScript、Vite 和 Tailwind CSS，展示识别、证据、训练、历史和调试等页面。`src/App.tsx` 读取 `src/mockData.ts` 中的模拟结果；识别按钮与截图上传区域尚未接通真实分析流程。

这是 RAG 项目的网页设计原型，与根目录 `pages/` 下的微信小程序分开，也与 `app.py` 提供的实际 Streamlit 界面分开。当前预览不需要 Gemini 或 Qwen API 密钥；依赖列表与 `.env.example` 中的 AI Studio 模板内容不代表已接入模型服务。

## 本地预览

在本目录执行（需要 Node.js 与 npm）：

```powershell
npm install
npm run dev
```

开发服务器默认端口为 3000。构建和类型检查命令：

```powershell
npm run build
npm run lint
```

如需运行 Python 检索与分析功能，请按 [RAG 项目说明](../docs/rag-project.md) 在仓库根目录启动 Streamlit。
