# 核心引擎，负责协调不同组件之间的交互
# 诊断主链路编排
# 问题描述 → 问题解析 → 模块召回 → 相关文件 → 提交记录 → 案例检索 → 排查建议
from app.schemas.diagnosis import (
    CandidateModule,
    CodeMatch,
    DiagnosisRequest,
    DiagnosisResponse,
    ProblemUnderstanding,
    RelatedCommit,
)
from app.services.indexing.repository_index import RepositoryIndex
from app.services.mcp.gateway import StaticMcpGateway
from app.services.memory.store import InMemoryMemoryStore
from app.services.rag.retriever import SampleRagRetriever
from app.services.tools.code_search import CodeSearchTool
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
        code_search_tool: CodeSearchTool,
    ) -> None:
        self.repository_index = repository_index
        self.rag_retriever = rag_retriever
        self.memory_store = memory_store
        self.tool_registry = tool_registry
        self.mcp_gateway = mcp_gateway
        self.code_search_tool = code_search_tool

    def run(self, request: DiagnosisRequest) -> DiagnosisResponse:
        understanding = self._parse_problem(request)
        search_queries = self._build_search_queries(request, understanding)
        code_matches = self.code_search_tool.search_code(search_queries, max_results=12)
        # rank_modules 基于关键词打分排序模块
        modules = self.repository_index.rank_modules(understanding.keywords)
        top_modules = modules[:3]
        # related_files 基于模块ID召回相关文件
        related_files = self._merge_related_files(top_modules, code_matches)
        # related_commits 基于关键词召回相关提交
        related_commits = self.repository_index.related_commits(understanding.keywords + search_queries)
        # rag_retriever 基于关键词检索相关案例
        retrieved_cases = self.rag_retriever.retrieve(understanding.keywords)
        # _build_suggestions 基于模块、提交、案例生成排查建议
        suggestions = self._build_suggestions(understanding, top_modules, code_matches, related_commits, retrieved_cases)

        debug_context = {
            "search_queries": search_queries,
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
            code_matches=[
                CodeMatch(
                    repo=item["repo"],
                    file_path=item["file_path"],
                    line=item["line"],
                    text=item["text"],
                    hit_terms=item["hit_terms"],
                    context=item["context"],
                )
                for item in code_matches
            ],
            related_commits=[RelatedCommit(hash=item["hash"], message=item["message"]) for item in related_commits],
            suggestions=suggestions,
            debug_context=debug_context,
        )

    # 关键词匹配识别领域
    def _parse_problem(self, request: DiagnosisRequest) -> ProblemUnderstanding:
        text = f"{request.title} {request.description} {request.framework or ''} {request.chip or ''}".lower()
        keyword_map = {
            "runtime_init": ["runtime", "init", "initialize", "loader", "device", "hipinit", "driver"],
            "framework_adaptation": ["torch", "pytorch", "framework", "operator", "adapter"],
            "performance": ["performance", "slow", "latency", "bandwidth", "scheduler"],
        }

        domain = "general"
        keywords: list[str] = []
        for candidate_domain, terms in keyword_map.items():
            hits = [term for term in terms if term in text]
            if hits and domain == "general":
                domain = candidate_domain
            keywords.extend(hits)

        if "device init failed" in text:
            keywords.extend(["device", "init", "failed"])
        if not keywords:
            keywords = ["runtime", "device"]

        symptoms = []
        if "fail" in text or "failed" in text:
            symptoms.append("operation failed")
        if "init" in text or "initialize" in text:
            symptoms.append("initialization failure")
        if "device" in text:
            symptoms.append("device related issue")

        missing_info = []
        if not request.version:
            missing_info.append("software version")
        if "error code" not in text and "failed" not in text:
            missing_info.append("error code or exact error text")
        if "log" not in text:
            missing_info.append("key runtime log")

        return ProblemUnderstanding(
            domain=domain,
            symptoms=symptoms or ["needs more symptoms"],
            missing_info=missing_info,
            keywords=sorted(set(keywords)),
        )

    def _build_search_queries(self, request: DiagnosisRequest, understanding: ProblemUnderstanding) -> list[str]:
        queries = list(understanding.keywords)
        text = f"{request.title} {request.description}".lower()
        if "device init failed" in text:
            queries.insert(0, "device init failed")
        if request.framework and request.framework.lower() == "pytorch":
            queries.extend(["pytorch", "hipInit"])
        return list(dict.fromkeys(query for query in queries if len(query) >= 3))[:10]

    def _merge_related_files(self, modules: list[dict], code_matches: list[dict]) -> list[str]:
        files = self.repository_index.related_files([item["id"] for item in modules])
        for match in code_matches:
            files.append(f"{match['repo']}:{match['file_path']}:{match['line']}")
        return list(dict.fromkeys(files))[:10]

    def _build_suggestions(
        self,
        understanding: ProblemUnderstanding,
        modules: list[dict],
        code_matches: list[dict],
        commits: list[dict],
        retrieved_cases: list[dict],
    ) -> list[str]:
        suggestions = []
        if modules:
            suggestions.append(f"Start with module `{modules[0]['name']}` because it has the highest tag/path match.")
        if code_matches:
            first = code_matches[0]
            suggestions.append(
                f"Inspect `{first['repo']}:{first['file_path']}:{first['line']}`; it directly matched `{', '.join(first['hit_terms'])}`."
            )
        if understanding.domain == "runtime_init":
            suggestions.append("Check driver/runtime compatibility and collect the initialization-stage runtime log.")
        if commits:
            suggestions.append(f"Compare behavior around commit `{commits[0]['hash']}`: {commits[0]['message']}.")
        if retrieved_cases:
            suggestions.append("Use similar historical cases as SOP references, but validate against current repo evidence.")
        return suggestions or ["Add exact logs, version details, and reproduction steps before deeper investigation."]
