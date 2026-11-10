# Campus Anti-Fraud RAG: Companion Website Design Prototype

[中文](README.md) | [English](README.en.md)

[Repository overview](../README.en.md) · [Python RAG project](../docs/rag-project.en.md)

This directory uses React, TypeScript, Vite, and Tailwind CSS to display recognition, evidence, training, history, and debugging views. `src/App.tsx` reads mock results from `src/mockData.ts`; the recognition button and screenshot upload area are not connected to a real analysis workflow.

This is the RAG project's website design prototype. It is separate from the WeChat Mini Program under the root `pages/` directory and from the functional Streamlit interface provided by `app.py`. Previewing it currently requires no Gemini or Qwen API key. AI Studio template entries in the dependency list and `.env.example` do not mean a model service is connected.

## Local Preview

Run in this directory, with Node.js and npm installed:

```powershell
npm install
npm run dev
```

The development server uses port 3000 by default. Build and type-check commands:

```powershell
npm run build
npm run lint
```

To run Python retrieval and analysis, follow the [RAG project guide](../docs/rag-project.en.md) and start Streamlit from the repository root.
