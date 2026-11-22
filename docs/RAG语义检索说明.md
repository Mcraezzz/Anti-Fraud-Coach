# RAG 语义检索实现说明

## 已实现能力

- 接入知识库版本管理：`backend/app/data/knowledge_versions.json`
- 接入案例引用库：`backend/app/data/fraud_cases.json`
- `/api/ask` 返回：
  - `answer`：基于检索结果生成的回答
  - `references`：知识条目与案例来源
  - `case_citations`：相似案例引用
  - `knowledge_version`：当前知识库版本与校验值
  - `retrieval_method`：实际使用的检索链路
- 新增接口：
  - `GET /api/rag/status`：查看 RAG 模型、索引、版本和案例数量
  - `POST /api/rag/rebuild`：清空缓存并重建 RAG 引擎

## 检索链路

系统优先使用以下链路：

```text
用户问题
  -> BGE-M3 生成 query embedding
  -> FAISS 或 Chroma 向量检索
  -> BGE reranker 重排候选条目
  -> 组合知识条目和相似案例
  -> 生成可追溯反诈回答
```

如果当前 Python 环境没有安装 `sentence-transformers`、`faiss-cpu` 或 `chromadb`，后端会自动退回到关键词检索，保证小程序演示不中断。

## 启用语义检索依赖

在后端目录执行：

```powershell
cd C:\Users\22672\Desktop\反诈系统\backend
python -m pip install -r requirements-models.txt
```

本地模型默认读取：

```text
D:\CARIC模型&数据集\models\BAAI_bge-m3
D:\CARIC模型&数据集\models\BAAI_bge-reranker-v2-m3
```

## 可选环境变量

```powershell
$env:ANTI_FRAUD_RAG_INDEX_BACKEND="auto"   # auto / faiss / chroma
$env:ANTI_FRAUD_SEMANTIC_RAG="1"           # 1 启用，0 关闭
$env:ANTI_FRAUD_RAG_TOP_K="4"
$env:ANTI_FRAUD_RAG_CANDIDATE_K="8"
```

查看状态：

```powershell
curl http://127.0.0.1:8000/api/rag/status
```
