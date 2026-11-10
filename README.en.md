# Anti-Fraud Coach: Two Projects and Their Comparison

[中文](README.md) | [English](README.en.md)

This repository contains two independent projects: a **WeChat Mini Program product prototype** and a **Python campus anti-fraud RAG system**. They address the same anti-fraud theme but are not currently connected. The Mini Program interface should not be interpreted as already invoking the RAG engine.

## Project 1: WeChat Mini Program Prototype

A mobile anti-fraud coach for university students, demonstrating recognition, risk explanations, Q&A, scenario training, ability reports, and administration screens.

- **Technology:** WeChat Mini Program JavaScript / WXML / WXSS, Skyline, and glass-easel.
- **Entry points and directories:** `app.js`, `app.json`, `app.wxss`, `pages/`, `components/`, `assets/`, `styles/`, `utils/`, and `project.config.json`.
- **Current status:** UI and navigation prototype. Recognition uses a simulated page transition; results and training content are predefined. No real OCR, RAG, or model API is connected.
- **Preview:** Import the repository root into WeChat DevTools, configure an AppID as needed, and use an environment supporting Skyline.

Details: [Mini Program project](docs/mini-program.en.md).

## Project 2: Campus Anti-Fraud RAG Recognition and Training System

A coursework and technical research project that processes Chinese, English, or mixed text, including text extracted from images through OCR. Outputs include risk analysis, retrieved evidence, recommended actions, and training questions.

- **Technology:** Python, Streamlit, Qwen, PaddleOCR, BGE-M3, FAISS, BM25, and BGE reranker.
- **Entry points and directories:** `app.py`, `build_index.py`, `run_demo.py`, `anti_fraud_rag/`, `tests/`, and `requirements.txt`.
- **Current status:** Actual retrieval and model-call implementations exist. Execution requires the relevant dependencies, data, and model configuration. Missing API credentials or failed API calls trigger rule-based simulated analysis.
- **Companion website:** `webdesign/` is a React / TypeScript / Vite design prototype using mock data. It is not connected to the Python engine. The functional Python web interface is Streamlit `app.py`.
- **Research materials:** `N&D Report.docx`, `PROJECT_ANALYSIS_REPORT.md`, `参考文献/`, and `outputs/`.

Installation, index building, and startup: [RAG project](docs/rag-project.en.md). Website preview: [webdesign guide](webdesign/README.en.md).

## Similarities

- Both address anti-fraud recognition and safety education for university students, focusing on suspicious messages, chats, and links.
- Both follow the design direction of identifying risks, explaining them, recommending actions, and supporting training.
- Both emphasize risk signals and readable explanations and could be developed into different parts of one anti-fraud product.

These similarities concern goals and design; they do not imply shared algorithms, data, or services in the current implementation.

## Differences

| Aspect | WeChat Mini Program | Python RAG project |
| --- | --- | --- |
| Primary purpose | Mobile product experience and interaction demonstration | Anti-fraud retrieval, analysis, and technical validation |
| Runtime | WeChat DevTools / Mini Program environment | Python CLI / Streamlit browser interface |
| Main languages | JavaScript, WXML, WXSS | Python; TypeScript / React for the companion UI prototype |
| Recognition workflow | Predefined UI and timed navigation | Preprocessing, risk features, entity extraction, hybrid retrieval, and analysis generation |
| OCR | UI entry point without actual recognition integration | PaddleOCR integration in the Streamlit flow, requiring dependencies and models |
| Evidence and results | Predefined page content | Local knowledge base, rules, and optional Qwen calls, with simulated fallback |
| Q&A and training | UI demonstrations of Q&A, scenarios, and ability reports | Analysis may include training questions; not a complete online learning platform |
| Data and dependencies | UI preview needs no Python models or indexes | Full functionality requires local data, models, indexes, and optional API credentials |
| Validation focus | Layout, navigation, and interaction flow | Retrieved evidence, analysis output, OCR, and model-call behavior |
| Integration status | Does not call the Python RAG engine | No connected business API for the Mini Program; React prototype is also unconnected |

## Repository Layout and Runtime Boundaries

The projects share the repository root but run independently: `app.js` belongs to the Mini Program, while `app.py` belongs to the Python application. `webdesign/` is a companion UI prototype for the RAG project, not Mini Program code or a third deployed backend service.

Uploaded materials include source code, example configuration, reports, and figures. Secret files, dependency directories, runtime logs, local indexes under `storage/`, and third-party installers under `downloads/` are excluded from version control. External datasets and model weights are not bundled either.

## Future Integration (Not Implemented)

The Python engine could be exposed through a service API so the Mini Program or React website can submit text/images and display analysis results. This would require API contracts, upload and OCR workflows, error handling, access control, and data persistence. For now, the two projects should be run, demonstrated, and evaluated separately.
