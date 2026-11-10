# 项目二：校园反诈 RAG 识别与训练系统

[中文](rag-project.md) | [English](rag-project.en.md)

[返回仓库总览](../README.md)

## 定位与实现范围

本项目用于验证面向大学生的中英文反诈媒体内容分析流程。Python 核心实现预处理、风险特征与实体提取、混合检索、证据融合与重排序，并可调用 Qwen 生成分析。`app.py` 是 Streamlit 应用入口，支持文本输入和图片 OCR；`run_demo.py` 是命令行入口。

`webdesign/` 是本项目配套的 React 网页设计原型，当前读取 `mockData.ts`，尚未调用 Python 引擎。它与可运行的 Streamlit 界面需要区分。仓库中的微信小程序也是独立原型，尚未与本引擎集成。

## 运行条件与边界

以下命令均在**仓库根目录**执行。先安装依赖，按根目录 `.env.example` 配置实际数据集、模型路径及 API 密钥；可将示例复制为 `.env` 后编辑。示例中的 D 盘路径属于原开发环境，不是仓库自带资源。

外部数据集、模型权重与 `storage/rag_index` 不包含在此次上传中，需要自行准备相应资源并构建索引。`--mock` 只跳过 Qwen 调用，仍会执行检索流程，因此不等于完全无需本地依赖。缺少 API 密钥时使用规则模拟分析；API 调用失败时也会回退，并通过 `api_error` 和 `raw_model_output` 标识。看到报告不代表本次调用一定来自在线模型。

目前代码实现不等同于经过真实场景准确率验证或已经上线的服务。前端展示、检索证据与模型输出应分别评估。

## 技术与运行说明

课程主题：**基于 LLM-RAG 的大学生反诈媒体内容识别与训练系统**。系统接受中文、英文、混合文本或截图/图片，提供风险等级、诈骗类型、独立风险特征、OCR 文字、关键信号、检索证据、融合与重排序得分、反诈建议、训练问题、合规提醒和用于评估的结构化 JSON。

### 数据来源

默认数据集根目录为 `D:\CARIC模型&数据集\datasets`。索引构建器使用的主要来源包括：

- `campus_anti_fraud_bilingual_rules`
- `ChiFraud`
- `hf_notd5a_malicious-benign-sms-mms-dataset`
- `hf_wangyuancheng_discord-phishing-scam-clean`
- `hf_weijianzhg_email-safety-triage-10k`
- `github_Phishing-Database_Phishing.Database`
- `hf_phishdestroy_destroylist`
- `github_scamsniffer_scam-database`

### 安装与配置

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

通过环境变量设置 Qwen API 密钥：

```powershell
$env:DASHSCOPE_API_KEY="sk-your-api-key-here"
```

可选配置：

```powershell
$env:DASHSCOPE_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
$env:QWEN_MODEL="qwen3.7-plus"
```

### 检索架构

当前实现结合 Qwen `qwen3.7-plus`、PaddleOCR 图片文字提取、独立文本预处理、风险特征与实体提取、BGE-M3 稠密向量、FAISS 向量检索、BM25 词法检索、URL/域名精确指标匹配、证据融合、去重和 BGE reranker 重排序。

BM25 索引全部知识条目；FAISS 默认索引全部条目的 BGE-M3 向量，也可限制数量以控制 CPU 构建时间。原开发环境中的模型路径为：

- `D:\CARIC模型&数据集\models\BAAI_bge-m3`
- `D:\CARIC模型&数据集\models\BAAI_bge-reranker-v2-m3`

证据融合得分可配置：

```text
final_score = alpha * bm25_score
            + beta  * dense_score
            + gamma * url_match_score
            + delta * risk_keyword_score
```

当 `USE_RERANKER=true` 时，融合后的候选证据会使用 `BAAI/bge-reranker-v2-m3` 重排序。输出最终 top-k 前，依据条目 ID 和归一化标题/文本指纹去重。

默认权重：

```text
alpha = 0.35
beta = 0.35
gamma = 0.15
delta = 0.15
reranker_weight = 0.30
```

### 结构化输出

返回 JSON 包含预处理、实体和风险特征等信息，分析结果包含风险、解释与建议。用于后续评估的相关字段包括：

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

这些字段可能位于返回对象的不同层级；请以引擎返回结构为准。

### 构建 RAG 索引

```powershell
python build_index.py
```

生成的索引保存在 `storage/rag_index`。仅使用 CPU 时，BGE-M3 编码可能耗时较长，可限制稠密索引数量或跳过稠密索引：

```powershell
python build_index.py --dense-limit 500
python build_index.py --skip-dense
```

`--dense-limit 0` 表示对全部知识条目构建稠密 FAISS 索引。原开发机的 GPU 环境示例（其他机器请替换为实际 Python 路径）：

```powershell
D:\conda\envs\pytorch\python.exe build_index.py
D:\conda\envs\pytorch\python.exe -m streamlit run app.py --server.port 8501
```

### 命令行演示

模拟模式，不调用 Qwen API：

```powershell
python run_demo.py --mock
```

调用真实 Qwen API（需有效配置）：

```powershell
python run_demo.py
```

### 启动网页应用

```powershell
streamlit run app.py --server.port 8501
```

浏览器打开 `http://localhost:8501`。界面支持文本输入和图片上传；聊天/短信截图、海报或钓鱼图片先经过 OCR，提取文字与输入文本合并后进入同一 RAG 分析流程。主报告以可读文本展示，完整 JSON 在原始输出/调试区域查看。

### 补充说明

- API 密钥不硬编码。
- URL/域名黑名单用于精确指标匹配，不会全部向量化。
- 混合检索由 BM25 词法匹配与 BGE-M3 + FAISS 多语言语义匹配组成。
