# dependencies.py: 依赖注入模块
# 整个服务层的实例管理中心，统一管理服务实例获取
# 使用单例模式 + 懒加载：
#   - @lru_cache 装饰器确保函数只执行一次，返回的实例全局复用
#   - 第一次调用时创建实例，后续调用直接返回缓存
from functools import lru_cache

from app.services.agents.orchestrator import SimpleAgentOrchestrator
from app.services.diagnosis_service import DiagnosisService
from app.services.eval.evaluator import DemoEvaluator
from app.services.feedback.store import FeedbackStore
from app.services.indexing.ingestion import RepoIngestionService
from app.services.indexing.repo_registry import RepoRegistry
from app.services.indexing.repository_index import RepositoryIndex
from app.services.mcp.gateway import StaticMcpGateway
from app.services.memory.store import InMemoryMemoryStore
from app.services.rag.milvus_store import MilvusKnowledgeStore
from app.services.rag.retriever import SampleRagRetriever
from app.services.tools.code_search import CodeSearchTool
from app.services.tools.registry import ToolRegistry
from app.services.storage.postgres import PostgresStore


# ========== 基础服务实例 ==========

# RepoRegistry 单例：仓库注册表，负责加载仓库配置和扫描文件
@lru_cache
def get_repo_registry() -> RepoRegistry:
    return RepoRegistry()


# RepositoryIndex 单例：代码索引服务
# 依赖 RepoRegistry 和 PostgresStore
@lru_cache
def get_repository_index() -> RepositoryIndex:
    return RepositoryIndex(repo_registry=get_repo_registry(), postgres=get_postgres_store())


# CodeSearchTool 单例：代码搜索工具
# 依赖 RepoRegistry，使用 ripgrep 进行代码搜索
@lru_cache
def get_code_search_tool() -> CodeSearchTool:
    return CodeSearchTool(repo_registry=get_repo_registry())


# ========== 存储服务 ==========

# PostgresStore 单例：PostgreSQL 持久化存储
@lru_cache
def get_postgres_store() -> PostgresStore:
    return PostgresStore()


# MilvusKnowledgeStore 单例：Milvus 向量知识库
@lru_cache
def get_milvus_knowledge_store() -> MilvusKnowledgeStore:
    return MilvusKnowledgeStore()


# ========== Ingestion 服务 ==========

# RepoIngestionService 单例：仓库索引构建服务
# 负责扫描仓库文件、加载提交记录、更新数据库
@lru_cache
def get_ingestion_service() -> RepoIngestionService:
    return RepoIngestionService(
        repo_registry=get_repo_registry(),
        postgres=get_postgres_store(),
        milvus=get_milvus_knowledge_store(),
    )


# ========== 反馈服务 ==========

# FeedbackStore 单例：用户反馈存储
# 用于记录用户对诊断结果的反馈（是否命中、正确结论等）
@lru_cache
def get_feedback_store() -> FeedbackStore:
    return FeedbackStore(postgres=get_postgres_store())


# ========== 记忆/检索/工具服务 ==========

# InMemoryMemoryStore 单例：内存记忆存储（短期记忆）
# 记录最近诊断历史
@lru_cache
def get_memory_store() -> InMemoryMemoryStore:
    return InMemoryMemoryStore()


# SampleRagRetriever 单例：RAG 检索器（demo 版本）
# 用于相似历史案例检索
@lru_cache
def get_rag_retriever() -> SampleRagRetriever:
    return SampleRagRetriever()


# ToolRegistry 单例：工具注册表
# 管理可用工具清单
@lru_cache
def get_tool_registry() -> ToolRegistry:
    return ToolRegistry()


# StaticMcpGateway 单例：MCP 网关（占位）
# 管理 MCP 服务连接
@lru_cache
def get_mcp_gateway() -> StaticMcpGateway:
    return StaticMcpGateway()


# ========== 编排器和诊断服务 ==========

# SimpleAgentOrchestrator 单例：诊断主链路编排器
# 依赖所有基础服务，协调诊断流程
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


# DiagnosisService 单例：诊断服务
# 核心服务，调用编排器执行诊断
@lru_cache
def get_diagnosis_service() -> DiagnosisService:
    return DiagnosisService(orchestrator=get_orchestrator(), memory_store=get_memory_store())


# DemoEvaluator 单例：评估服务（占位）
# 支持 hit_at_3, module_recall, context_relevance, suggestion_actionability 等指标
@lru_cache
def get_evaluator() -> DemoEvaluator:
    return DemoEvaluator()


# ========== 架构文档 ==========

# get_architecture_summary: 返回系统架构设计文档
def get_architecture_summary() -> dict:
    return {
        "api": "FastAPI",
        "orchestrator": "SimpleAgentOrchestrator with read-only code evidence flow",
        "repo_source": "Registered repos from apps/api/app/data/repos.json",
        "code_search": "ripgrep (`rg`) over mounted repos; metadata comes from PostgreSQL when enabled",
        "vector_db": "Milvus reserved for docs/cases/module cards/commit summaries, not full raw code",
        "cache": "Redis placeholder",
        "memory": {
            "short_term": "InMemoryMemoryStore for demo",
            "long_term": "Extensible via Postgres + Milvus",
        },
        "tool_use": "ToolRegistry + CodeSearchTool",
        "mcp": "StaticMcpGateway placeholder",
        "eval": "DemoEvaluator placeholder for RAG/business metrics",
    }
