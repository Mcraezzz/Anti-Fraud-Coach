import argparse

from anti_fraud_rag.config import AppConfig
from anti_fraud_rag.data_loader import load_knowledge_corpus
from anti_fraud_rag.retriever import LocalRagIndex


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-dense", action="store_true", help="Build BM25 only and skip BGE-M3/FAISS.")
    parser.add_argument(
        "--dense-limit",
        type=int,
        default=None,
        help="Number of documents to embed with BGE-M3. 0 means all documents.",
    )
    args = parser.parse_args()

    config = AppConfig.from_env()
    items, iocs = load_knowledge_corpus(config)
    index = LocalRagIndex.build(
        items,
        iocs,
        config,
        build_dense=not args.skip_dense,
        dense_limit=args.dense_limit,
    )
    index.save(config.index_dir)
    print(f"Built index: {len(items)} knowledge items")
    print(f"Stored at: {config.index_dir}")
    print(f"IOC domains: {len(iocs.domains)}")
    print(f"IOC urls: {len(iocs.urls)}")
    print(f"BM25 documents: {len(items)}")
    print(f"FAISS dense documents: {len(index.dense_item_indices)}")


if __name__ == "__main__":
    main()
