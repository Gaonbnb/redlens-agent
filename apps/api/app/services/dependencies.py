# 依赖注入，统一管理服务实例获取
from functools import lru_cache

from app.services.agents.orchestrator import SimpleAgentOrchestrator
from app.services.diagnosis_service import DiagnosisService
from app.services.eval.evaluator import DemoEvaluator
from app.services.indexing.repository_index import RepositoryIndex
from app.services.mcp.gateway import StaticMcpGateway
from app.services.memory.store import InMemoryMemoryStore
from app.services.rag.retriever import SampleRagRetriever
from app.services.tools.registry import ToolRegistry

# → RepositoryIndex 单例
@lru_cache
def get_repository_index() -> RepositoryIndex:
    return RepositoryIndex()

# → InMemoryMemoryStore 单例
@lru_cache
def get_memory_store() -> InMemoryMemoryStore:
    return InMemoryMemoryStore()


@lru_cache
def get_rag_retriever() -> SampleRagRetriever:
    return SampleRagRetriever()


@lru_cache
def get_tool_registry() -> ToolRegistry:
    return ToolRegistry()


@lru_cache
def get_mcp_gateway() -> StaticMcpGateway:
    return StaticMcpGateway()


@lru_cache
def get_orchestrator() -> SimpleAgentOrchestrator:
    return SimpleAgentOrchestrator(
        repository_index=get_repository_index(),
        rag_retriever=get_rag_retriever(),
        memory_store=get_memory_store(),
        tool_registry=get_tool_registry(),
        mcp_gateway=get_mcp_gateway(),
    )

# → DiagnosisService 单例
@lru_cache
def get_diagnosis_service() -> DiagnosisService:
    return DiagnosisService(orchestrator=get_orchestrator(), memory_store=get_memory_store())

# → DemoEvaluator 单例
@lru_cache
def get_evaluator() -> DemoEvaluator:
    return DemoEvaluator()


def get_architecture_summary() -> dict:
    return {
        "api": "FastAPI",
        "orchestrator": "SimpleAgentOrchestrator (replaceable with LangGraph)",
        "vector_db": "Milvus placeholder enabled by configuration",
        "cache": "Redis placeholder enabled by configuration",
        "memory": {
            "short_term": "InMemoryMemoryStore for demo",
            "long_term": "Extensible via Postgres + Milvus",
        },
        "tool_use": "ToolRegistry",
        "mcp": "StaticMcpGateway placeholder",
        "multi_agent": [
            "planner",
            "retriever",
            "code_investigator",
            "report_writer",
        ],
        "eval": "DemoEvaluator placeholder for RAG/business metrics",
    }
