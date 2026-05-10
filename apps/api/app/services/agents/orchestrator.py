# SimpleAgentOrchestrator: 诊断主链路编排器
# 核心引擎，负责协调不同组件之间的交互
# 诊断流程：问题描述 → 问题解析 → 代码搜索 → 模块召回 → 相关文件 → 提交记录 → 案例检索 → 证据构建 → 排查建议
from app.schemas.diagnosis import (
    CandidateModule,
    CodeMatch,
    DiagnosisRequest,
    DiagnosisResponse,
    EvidenceItem,
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
        # repository_index: 代码索引服务，用于模块召回、文件关联、提交查询
        # rag_retriever: RAG 检索器，用于相似历史案例检索
        # memory_store: 记忆存储，记录诊断历史
        # tool_registry: 工具注册表，管理可用工具
        # mcp_gateway: MCP 网关，管理 MCP 服务
        # code_search_tool: 代码搜索工具，基于 ripgrep 搜索代码
        self.repository_index = repository_index
        self.rag_retriever = rag_retriever
        self.memory_store = memory_store
        self.tool_registry = tool_registry
        self.mcp_gateway = mcp_gateway
        self.code_search_tool = code_search_tool

    # run: 执行完整诊断流程
    # 输入: DiagnosisRequest (问题描述)
    # 输出: DiagnosisResponse (诊断结果)
    def run(self, request: DiagnosisRequest) -> DiagnosisResponse:
        # 1. 问题解析：识别领域、症状、缺失信息、关键词
        understanding = self._parse_problem(request)

        # 2. 构建搜索关键词：基于问题描述和问题理解构建代码搜索查询
        search_queries = self._build_search_queries(request, understanding)

        # 3. 代码搜索：使用 ripgrep 在仓库中搜索代码匹配
        code_matches = self.code_search_tool.search_code(search_queries, max_results=12)

        # 4. 模块召回：基于关键词对模块打分排序
        modules = self.repository_index.rank_modules(understanding.keywords)
        top_modules = modules[:3]  # 取分数最高的3个模块

        # 5. 相关文件：合并模块关联文件和代码匹配文件
        related_files = self._merge_related_files(top_modules, code_matches)

        # 6. 提交记录：基于关键词召回相关提交
        related_commits = self.repository_index.related_commits(understanding.keywords + search_queries)

        # 7. 案例检索：RAG 检索相似历史案例
        retrieved_cases = self.rag_retriever.retrieve(understanding.keywords)

        # 8. 构建证据项：统一证据来源（模块、代码、提交、案例）
        evidence_items = self._build_evidence_items(top_modules, code_matches, related_commits, retrieved_cases)

        # 9. 生成排查建议：基于模块、代码匹配、提交、案例生成建议
        suggestions = self._build_suggestions(understanding, top_modules, code_matches, related_commits, retrieved_cases)

        # 10. 构建调试上下文
        debug_context = {
            "search_queries": search_queries,
            "tool_registry": self.tool_registry.list_tools(),
            "mcp_servers": self.mcp_gateway.list_servers(),
            "retrieved_cases": retrieved_cases,
            "memory_snapshot": self.memory_store.short_term_snapshot(),
        }

        # 返回完整诊断结果
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
            evidence_items=evidence_items,
            suggestions=suggestions,
            debug_context=debug_context,
        )

    # _parse_problem: 问题解析
    # 识别领域（runtime_init/framework_adaptation/performance）、症状、缺失信息、关键词
    def _parse_problem(self, request: DiagnosisRequest) -> ProblemUnderstanding:
        text = f"{request.title} {request.description} {request.framework or ''} {request.chip or ''}".lower()

        # 领域关键词映射
        keyword_map = {
            "runtime_init": ["runtime", "init", "initialize", "loader", "device", "hipinit", "driver"],
            "framework_adaptation": ["torch", "pytorch", "framework", "operator", "adapter"],
            "performance": ["performance", "slow", "latency", "bandwidth", "scheduler"],
        }

        domain = "general"
        keywords: list[str] = []
        # 遍历关键词映射，找到匹配的领域
        for candidate_domain, terms in keyword_map.items():
            hits = [term for term in terms if term in text]
            if hits and domain == "general":
                domain = candidate_domain
            keywords.extend(hits)

        # 特殊处理 "device init failed"
        if "device init failed" in text:
            keywords.extend(["device", "init", "failed"])
        if not keywords:
            keywords = ["runtime", "device"]

        # 症状识别
        symptoms = []
        if "fail" in text or "failed" in text:
            symptoms.append("操作失败")
        if "init" in text or "initialize" in text:
            symptoms.append("初始化异常")
        if "device" in text:
            symptoms.append("设备相关异常")

        # 缺失信息识别
        missing_info = []
        if not request.version:
            missing_info.append("软件版本")
        if "error code" not in text and "failed" not in text:
            missing_info.append("错误码或完整错误文本")
        if "log" not in text:
            missing_info.append("关键 runtime 日志")

        return ProblemUnderstanding(
            domain=domain,
            symptoms=symptoms or ["待补充现象"],
            missing_info=missing_info,
            keywords=sorted(set(keywords)),
        )

    # _build_search_queries: 构建代码搜索关键词
    # 基于问题理解和问题描述构建最适合搜索的关键词列表
    def _build_search_queries(self, request: DiagnosisRequest, understanding: ProblemUnderstanding) -> list[str]:
        queries = list(understanding.keywords)
        text = f"{request.title} {request.description}".lower()

        # 特殊处理 "device init failed"
        if "device init failed" in text:
            queries.insert(0, "device init failed")
        # 如果是 PyTorch 框架，添加相关关键词
        if request.framework and request.framework.lower() == "pytorch":
            queries.extend(["pytorch", "hipInit"])

        # 去重并过滤短关键词（长度<3），最多返回10个
        return list(dict.fromkeys(query for query in queries if len(query) >= 3))[:10]

    # _merge_related_files: 合并相关文件
    # 合并模块关联的文件和代码搜索匹配的文件
    def _merge_related_files(self, modules: list[dict], code_matches: list[dict]) -> list[str]:
        files = self.repository_index.related_files([item["id"] for item in modules])
        # 添加代码匹配的文件（格式：repo:file_path:line）
        for match in code_matches:
            files.append(f"{match['repo']}:{match['file_path']}:{match['line']}")
        # 去重，最多返回10个
        return list(dict.fromkeys(files))[:10]

    # _build_suggestions: 生成排查建议
    # 基于问题理解、模块、代码匹配、提交、案例生成针对性建议
    def _build_suggestions(
        self,
        understanding: ProblemUnderstanding,
        modules: list[dict],
        code_matches: list[dict],
        commits: list[dict],
        retrieved_cases: list[dict],
    ) -> list[str]:
        suggestions = []

        # 建议1：基于最高分模块
        if modules:
            suggestions.append(f"优先排查模块 `{modules[0]['name']}`，它的标签、路径或典型问题命中度最高。")

        # 建议2：基于代码匹配结果
        if code_matches:
            first = code_matches[0]
            suggestions.append(
                f"检查 `{first['repo']}:{first['file_path']}:{first['line']}`，"
                f"这里直接命中了 `{', '.join(first['hit_terms'])}`。"
            )

        # 建议3：基于领域特定建议
        if understanding.domain == "runtime_init":
            suggestions.append("补充驱动/runtime 版本匹配关系，并收集初始化阶段 runtime 日志。")

        # 建议4：基于提交历史
        if commits:
            suggestions.append(f"对比提交 `{commits[0]['hash']}` 前后的行为变化：{commits[0]['message']}。")

        # 建议5：基于历史案例
        if retrieved_cases:
            suggestions.append("参考相似历史案例的排查顺序，但最终结论要以当前仓库证据为准。")

        # 默认建议
        return suggestions or ["先补充完整日志、版本信息和复现路径，再继续深入排查。"]

    # _build_evidence_items: 构建统一证据项
    # 将模块、代码、提交、案例等不同来源的证据统一为 EvidenceItem 格式
    def _build_evidence_items(
        self,
        modules: list[dict],
        code_matches: list[dict],
        commits: list[dict],
        retrieved_cases: list[dict],
    ) -> list[EvidenceItem]:
        evidence: list[EvidenceItem] = []

        # 模块证据
        for module in modules:
            evidence.append(
                EvidenceItem(
                    source_type="module",
                    repo=module.get("repo"),
                    module_name=module["name"],
                    score=module["score"],
                    reason=module["reason"],
                    preview=module.get("description") or module["name"],
                    metadata={"module_id": module["id"]},
                )
            )

        # 代码证据
        for item in code_matches:
            evidence.append(
                EvidenceItem(
                    source_type="code",
                    repo=item["repo"],
                    file_path=item["file_path"],
                    line=item["line"],
                    score=0.86,  # 代码匹配固定分数
                    reason=f"Matched code terms: {', '.join(item['hit_terms'])}",
                    preview=item["text"],
                    metadata={"context": item["context"]},
                )
            )

        # 提交证据
        for item in commits:
            evidence.append(
                EvidenceItem(
                    source_type="commit",
                    repo=item.get("repo"),
                    commit_hash=item["hash"],
                    score=0.72,  # 提交匹配固定分数
                    reason="Commit message or keywords matched the problem terms.",
                    preview=item["message"],
                    metadata={"keywords": item.get("keywords", []), "summary": item.get("summary")},
                )
            )

        # 案例证据
        for item in retrieved_cases:
            evidence.append(
                EvidenceItem(
                    source_type="case",
                    case_id=item["id"],
                    score=0.68,  # 案例匹配固定分数
                    reason="Historical case keywords matched the problem terms.",
                    preview=item["title"],
                    metadata={"keywords": item.get("keywords", [])},
                )
            )

        # 最多返回30个证据项
        return evidence[:30]
