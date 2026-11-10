# Project 2: Campus Anti-Fraud RAG Recognition and Training System

[中文](rag-project.md) | [English](rag-project.en.md)

[Repository overview](../README.en.md)

## Purpose and Implementation Scope

This project validates a Chinese/English anti-fraud media analysis workflow for university students. The Python core implements preprocessing, risk feature and entity extraction, hybrid retrieval, evidence fusion, and reranking, with optional Qwen-generated analysis. `app.py` is the Streamlit entry point supporting text input and image OCR; `run_demo.py` is the CLI entry point.

`webdesign/` is a companion React UI prototype that currently reads `mockData.ts` without calling the Python engine. It is distinct from the functional Streamlit interface. The WeChat Mini Program is also an independent prototype and has not been integrated with this engine.

## Runtime Requirements and Boundaries

Run all commands below from the **repository root**. Install dependencies and configure actual dataset paths, model paths, and API credentials using the root `.env.example`; you may copy it to `.env` and edit it. The example D-drive paths refer to the original development environment, not bundled repository resources.

External datasets, model weights, and `storage/rag_index` are not included in this upload. Prepare the relevant resources and build the index locally. `--mock` skips only the Qwen call and still performs retrieval, so it does not remove local dependency requirements. Missing API credentials trigger rule-based simulated analysis. Failed API calls also fall back, marked through `api_error` and `raw_model_output`. A displayed report does not necessarily come from an online model call.

Having this implementation does not establish real-world accuracy or mean the service is deployed. UI demonstrations, retrieved evidence, and model output should be evaluated separately.

## Technical and Operating Guide

This project is a bilingual RAG prototype for the coursework topic:

**An LLM-RAG Based Anti-Fraud Media Content Recognition and Training System for College Students**

The system accepts Chinese, English, mixed fraud-related media text, or uploaded screenshots/images and returns:

- fraud risk level
- fraud type
- independent risk feature extraction
- OCR text extracted from uploaded images
- key risk signals
- retrieved evidence
- evidence fusion and reranking scores
- anti-fraud advice
- training question
- compliance reminder
- structured JSON for evaluation

## Data Sources

Default dataset root:

`D:\CARIC模型&数据集\datasets`

Main sources used by the index builder:

- `campus_anti_fraud_bilingual_rules`
- `ChiFraud`
- `hf_notd5a_malicious-benign-sms-mms-dataset`
- `hf_wangyuancheng_discord-phishing-scam-clean`
- `hf_weijianzhg_email-safety-triage-10k`
- `github_Phishing-Database_Phishing.Database`
- `hf_phishdestroy_destroylist`
- `github_scamsniffer_scam-database`

## Setup

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Set the Qwen API key as an environment variable:

```powershell
$env:DASHSCOPE_API_KEY="sk-your-api-key-here"
```

Optional settings:

```powershell
$env:DASHSCOPE_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
$env:QWEN_MODEL="qwen3.7-plus"
```

## Retrieval Architecture

The current system uses:

```text
Qwen qwen3.7-plus
+ PaddleOCR image text extraction
+ Independent text preprocessing
+ Risk Feature Extraction
+ Entity Extraction
+ BAAI/bge-m3 dense embeddings
+ FAISS vector search
+ BM25 lexical retrieval
+ URL/domain exact indicator matching
+ Evidence fusion
+ Evidence deduplication
+ BAAI/bge-reranker-v2-m3 reranking
```

BM25 indexes all knowledge items. FAISS indexes BGE-M3 dense embeddings for all items by default, or a configured subset when CPU build time needs to be controlled.

Local model path:

`D:\CARIC模型&数据集\models\BAAI_bge-m3`

Local reranker path:

`D:\CARIC模型&数据集\models\BAAI_bge-reranker-v2-m3`

The final evidence score is configurable:

```text
final_score = alpha * bm25_score
            + beta  * dense_score
            + gamma * url_match_score
            + delta * risk_keyword_score
```

The top fused candidates are then reranked with `BAAI/bge-reranker-v2-m3` when `USE_RERANKER=true`.
Before final top-k output, retrieved evidence is explicitly deduplicated by item id and a normalized title/text fingerprint.

Default weights:

```text
alpha = 0.35
beta  = 0.35
gamma = 0.15
delta = 0.15
reranker_weight = 0.30
```

## Structured Output

The engine returns a JSON object with fields for later evaluation. These fields can appear at different nesting levels; consult the engine return structure:

- `preprocessing`
- `entity_extraction`
- `risk_features`
- `risk_level`
- `risk_score`
- `fraud_type`
- `risk_signals`
- `evidence_summary`
- `evidence_fusion`
- `natural_language_report`
- `anti_fraud_suggestion`
- `compliance_rewrite`
- `training_question`
- `evaluation_labels`

## Build The RAG Index

```powershell
python build_index.py
```

The generated index is stored in `storage/rag_index`.

On a CPU-only machine, BGE-M3 embedding can take some time. Useful build options:

```powershell
python build_index.py --dense-limit 500
python build_index.py --skip-dense
```

`--dense-limit 0` means dense FAISS embeddings for all knowledge items.

The original development machine used this GPU environment; replace these executable paths with your own Python environment:

```powershell
D:\conda\envs\pytorch\python.exe build_index.py
D:\conda\envs\pytorch\python.exe -m streamlit run app.py --server.port 8501
```

## Run A CLI Demo

Mock mode, no API call:

```powershell
python run_demo.py --mock
```

Real Qwen API mode:

```powershell
python run_demo.py
```

## Run The Web App

```powershell
streamlit run app.py --server.port 8501
```

Open:

`http://localhost:8501`

The web app supports text input and image upload. Uploaded chat screenshots, SMS screenshots, posters, or phishing images are processed by OCR first; the recognized text is then merged with the typed text and sent through the same RAG risk-analysis pipeline. The main user-facing risk report is displayed as normal readable text, while full JSON remains available only in the raw-output/debug section.

## Notes

- The API key is intentionally not hardcoded.
- URL/domain blacklists are used for exact indicator matching and are not fully embedded.
- The RAG index uses hybrid retrieval: BM25 for lexical matching and BGE-M3 + FAISS for multilingual semantic matching.
