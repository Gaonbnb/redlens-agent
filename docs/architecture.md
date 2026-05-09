# Architecture Notes

当前 Demo 采用单服务实现最小诊断链路，但模块边界已经拆开：

- `services/indexing`: 代码索引与样例模块数据
- `services/rag`: RAG 检索接口
- `services/memory`: 长短期记忆接口
- `services/tools`: 工具注册与工具调用
- `services/mcp`: MCP 网关占位
- `services/agents`: 诊断编排、多 Agent 占位
- `services/eval`: 评估接口

后续演进顺序建议：

1. 用真实 repo 索引替换样例 JSON
2. 引入 Milvus 向量检索
3. 引入 Redis 短期记忆与缓存
4. 引入 Postgres 持久化案例和反馈
5. 把编排切换到 LangGraph
6. 再加多 Agent 与 MCP
