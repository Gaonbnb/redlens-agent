# 核心引擎，负责协调不同组件之间的交互
# 诊断主链路编排
# 问题描述 → 问题解析 → 模块召回 → 相关文件 → 提交记录 → 案例检索 → 排查建议
from app.schemas.diagnosis import (
    CandidateModule,
    DiagnosisRequest,
    DiagnosisResponse,
    ProblemUnderstanding,
    RelatedCommit,
)
from app.services.indexing.repository_index import RepositoryIndex
from app.services.mcp.gateway import StaticMcpGateway
from app.services.memory.store import InMemoryMemoryStore
from app.services.rag.retriever import SampleRagRetriever
from app.services.tools.registry import ToolRegistry


class SimpleAgentOrchestrator:
    """Minimal orchestrator that preserves extension points for LangGraph/multi-agent."""

    def __init__(
        self,
        repository_index: RepositoryIndex,
        rag_retriever: SampleRagRetriever,
        memory_store: InMemoryMemoryStore,
        tool_registry: ToolRegistry,
        mcp_gateway: StaticMcpGateway,
    ) -> None:
        self.repository_index = repository_index
        self.rag_retriever = rag_retriever
        self.memory_store = memory_store
        self.tool_registry = tool_registry
        self.mcp_gateway = mcp_gateway

    def run(self, request: DiagnosisRequest) -> DiagnosisResponse:
        understanding = self._parse_problem(request)
        # rank_modules 基于关键词打分排序模块
        modules = self.repository_index.rank_modules(understanding.keywords)
        top_modules = modules[:3]
        # related_files 基于模块ID召回相关文件
        related_files = self.repository_index.related_files([item["id"] for item in top_modules])
        # related_commits 基于关键词召回相关提交
        related_commits = self.repository_index.related_commits(understanding.keywords)
        # rag_retriever 基于关键词检索相关案例
        retrieved_cases = self.rag_retriever.retrieve(understanding.keywords)
        # _build_suggestions 基于模块、提交、案例生成排查建议
        suggestions = self._build_suggestions(understanding, top_modules, related_commits, retrieved_cases)
        debug_context = {
            "tool_registry": self.tool_registry.list_tools(),
            "mcp_servers": self.mcp_gateway.list_servers(),
            "retrieved_cases": retrieved_cases,
            "memory_snapshot": self.memory_store.short_term_snapshot(),
        }

        return DiagnosisResponse(
            problem_understanding=understanding,
            candidate_modules=[
                CandidateModule(name=item["name"], score=item["score"], reason=item["reason"]) for item in top_modules
            ],
            related_files=related_files,
            related_commits=[
                RelatedCommit(hash=item["hash"], message=item["message"]) for item in related_commits
            ],
            suggestions=suggestions,
            debug_context=debug_context,
        )
    # 关键词匹配识别领域
    def _parse_problem(self, request: DiagnosisRequest) -> ProblemUnderstanding:
        text = f"{request.title} {request.description} {request.framework or ''} {request.chip or ''}".lower()
        keyword_map = {
            "runtime_init": ["init", "initialize", "loader", "device", "runtime", "初始化", "加载"],
            "framework_adaptation": ["torch", "pytorch", "framework", "适配", "算子", "operator"],
            "performance": ["performance", "slow", "latency", "bandwidth", "性能", "吞吐"],
        }

        domain = "general"
        keywords: list[str] = []
        for candidate, terms in keyword_map.items():
            hits = [term for term in terms if term in text]
            if hits:
                domain = candidate
                keywords.extend(hits)

        if not keywords:
            keywords = [word for word in ["runtime", "device", "driver"] if word in text] or ["runtime"]

        symptoms = []
        if "失败" in text or "fail" in text:
            symptoms.append("操作失败")
        if "初始化" in text or "init" in text:
            symptoms.append("初始化异常")
        if "device" in text or "设备" in text:
            symptoms.append("设备相关异常")

        missing_info = []
        if request.version is None:
            missing_info.append("软件版本")
        if "错误码" not in request.description and "error code" not in text:
            missing_info.append("错误码")
        if "日志" not in request.description and "log" not in text:
            missing_info.append("关键日志")

        return ProblemUnderstanding(
            domain=domain,
            symptoms=symptoms or ["待补充现象"],
            missing_info=missing_info,
            keywords=sorted(set(keywords)),
        )

    def _build_suggestions(
        self,
        understanding: ProblemUnderstanding,
        modules: list[dict],
        commits: list[dict],
        retrieved_cases: list[dict],
    ) -> list[str]:
        suggestions = []
        if modules:
            suggestions.append(f"优先排查模块 `{modules[0]['name']}` 的入口文件和初始化返回路径。")
        if understanding.domain == "runtime_init":
            suggestions.append("补充驱动版本、错误码和初始化阶段日志，优先核对 runtime 与 device loader 的版本匹配。")
        if commits:
            suggestions.append(f"对比近期提交 `{commits[0]['hash']}` 前后的初始化链路差异。")
        if retrieved_cases:
            suggestions.append("参考相似案例中的排查顺序，先确认环境，再确认入口调用，再确认资源初始化。")
        if not suggestions:
            suggestions.append("先补充更完整的现象描述、版本、日志和复现路径。")
        return suggestions
