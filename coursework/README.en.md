# Project 2: Campus Anti-Fraud RAG Coursework System

[中文](README.md) | [English](README.en.md) · [Two-project overview and comparison](../README.en.md)

This directory independently preserves the original coursework source, tests, example configuration, reports, figures, and references, including the previous IOC matching, OCR parsing, and non-finite score fixes.

- **Python core:** `anti_fraud_rag/` implements preprocessing, hybrid retrieval, evidence fusion, and optional Qwen calls.
- **Functional UI and CLI:** `app.py` (Streamlit), `run_demo.py`, and `build_index.py` for local indexes.
- **React design prototype:** [webdesign](webdesign/README.en.md), using mock data without a connection to the Python engine.
- **Research materials:** `N&D Report.docx`, `PROJECT_ANALYSIS_REPORT.md`, `参考文献/`, and `outputs/`.

[Complete technical, configuration, and operating guide](docs/rag-project.en.md). Run all Python startup, indexing, and testing commands in this directory: first run `cd coursework` from the repository root. Runtime data, models, and dependencies must be prepared separately; see `.env.example` for configuration.

The updated WeChat Mini Program and its own FastAPI service live in the repository `miniprogram/` and `backend/` directories. They are separate from this coursework engine and do not share its API or database.
