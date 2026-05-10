# 依赖注入（Dependency Injection） 模块，是整个服务层的 实例管理中心，统一管理服务实例获取
# 单例模式+懒加载
# - @lru_cache 装饰器确保函数只执行一次，返回的实例全局复用
# - 第一次调用时创建实例，后续调用直接返回缓存
from functools import lru_cache

from app.services.agents.orchestrator import SimpleAgentOrchestrator
from app.services.diagnosis_service import DiagnosisService
from app.services.eval.evaluator import DemoEvaluator
from app.services.indexing.repo_registry import RepoRegistry
from app.services.indexing.repository_index import RepositoryIndex
from app.services.mcp.gateway import StaticMcpGateway
from app.services.memory.store import InMemoryMemoryStore
from app.services.rag.retriever import SampleRagRetriever
from app.services.tools.code_search import CodeSearchTool
from app.services.tools.registry import ToolRegistry


@lru_cache
def get_repo_registry() -> RepoRegistry:
    return RepoRegistry()

# → RepositoryIndex 单例
@lru_cache
def get_repository_index() -> RepositoryIndex:
    return RepositoryIndex(repo_registry=get_repo_registry())


@lru_cache
def get_code_search_tool() -> CodeSearchTool:
    return CodeSearchTool(repo_registry=get_repo_registry())

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
        code_search_tool=get_code_search_tool(),
    )

# → DiagnosisService 单例，核心走编排器
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
        "orchestrator": "SimpleAgentOrchestrator with read-only code evidence flow",
        "repo_source": "Registered repos from apps/api/app/data/repos.json",
        "code_search": "Python grep demo; replace with ripgrep in production",
        "vector_db": "Milvus placeholder for docs/cases/module cards",
        "cache": "Redis placeholder",
        "memory": {
            "short_term": "InMemoryMemoryStore for demo",
            "long_term": "Extensible via Postgres + Milvus",
        },
        "tool_use": "ToolRegistry + CodeSearchTool",
        "mcp": "StaticMcpGateway placeholder",
        "eval": "DemoEvaluator placeholder for RAG/business metrics",
    }

