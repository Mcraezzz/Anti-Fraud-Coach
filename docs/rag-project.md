# 项目二：校园反诈 RAG 识别与训练系统

[返回仓库总览](../README.md)

## 定位与实现范围

本项目用于验证面向大学生的中英文反诈媒体内容分析流程。Python 核心实现预处理、风险特征与实体提取、混合检索、证据融合与重排序，并可调用 Qwen 生成分析。`app.py` 是 Streamlit 应用入口，支持文本输入和图片 OCR；`run_demo.py` 是命令行入口。

`webdesign/` 是本项目配套的 React 网页设计原型，当前读取 `mockData.ts`，尚未调用 Python 引擎。它与可运行的 Streamlit 界面需要区分。仓库中的微信小程序也是独立原型，尚未与本引擎集成。

## 运行条件与边界

以下命令均在**仓库根目录**执行。先安装依赖，按根目录 `.env.example` 配置实际数据集、模型路径及 API 密钥；可将示例复制为 `.env` 后编辑。示例中的 D 盘路径属于原开发环境，不是仓库自带资源。

外部数据集、模型权重与 `storage/rag_index` 不包含在此次上传中，需要自行准备相应资源并构建索引。`--mock` 只跳过 Qwen 调用，仍会执行检索流程，因此不等于完全无需本地依赖。缺少 API 密钥时使用规则模拟分析；API 调用失败时也会回退，并通过 `api_error` 和 `raw_model_output` 标识。看到报告不代表本次调用一定来自在线模型。

目前代码实现不等同于经过真实场景准确率验证或已经上线的服务。前端展示、检索证据与模型输出应分别评估。

## 原有技术与运行说明

# Campus Anti-Fraud RAG System

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

The engine returns a JSON object with stable fields for later evaluation:

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
D:\conda\envs\pytorch\python.exe build_index.py --dense-limit 500
D:\conda\envs\pytorch\python.exe build_index.py --skip-dense
```

`--dense-limit 0` means dense FAISS embeddings for all knowledge items.

For GPU acceleration, use the `pytorch` conda environment on this machine:

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
