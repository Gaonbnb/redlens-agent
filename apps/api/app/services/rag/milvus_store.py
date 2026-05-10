import hashlib

from app.core.config import get_settings

try:
    from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility
except ImportError:  # pragma: no cover - optional production dependency
    Collection = None
    CollectionSchema = None
    DataType = None
    FieldSchema = None
    connections = None
    utility = None


class MilvusKnowledgeStore:
    """Milvus store for docs/cases/module cards/commit summaries, not raw code."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.collection_name = "redlens_knowledge"
        self.dim = 64

    @property
    def enabled(self) -> bool:
        return bool(self.settings.enable_milvus and Collection)

    def ensure_collection(self) -> None:
        if not self.enabled:
            return
        connections.connect(host=self.settings.milvus_host, port=str(self.settings.milvus_port))
        if utility.has_collection(self.collection_name):
            return
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=256),
            FieldSchema(name="source_type", dtype=DataType.VARCHAR, max_length=32),
            FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=8192),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dim),
        ]
        schema = CollectionSchema(fields=fields, description="Docs, cases, module cards, and commit summaries")
        collection = Collection(self.collection_name, schema=schema)
        collection.create_index("embedding", {"index_type": "AUTOINDEX", "metric_type": "COSINE"})

    def upsert_texts(self, items: list[dict]) -> int:
        if not self.enabled:
            return 0
        self.ensure_collection()
        collection = Collection(self.collection_name)
        rows = [
            [
                item["id"],
                item["source_type"],
                item["title"][:512],
                item["text"][:8192],
                self._hash_embedding(item["text"]),
            ]
            for item in items
        ]
        if not rows:
            return 0
        collection.upsert(list(map(list, zip(*rows))))
        collection.flush()
        return len(rows)

    def summary(self) -> dict:
        if not self.enabled:
            return {"enabled": False, "collection": self.collection_name}
        self.ensure_collection()
        collection = Collection(self.collection_name)
        collection.load()
        return {"enabled": True, "collection": self.collection_name, "entities": collection.num_entities}

    def _hash_embedding(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).digest()
        values = []
        for index in range(self.dim):
            byte = digest[index % len(digest)]
            values.append((byte / 127.5) - 1.0)
        return values
