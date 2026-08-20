# Nova AI Agent Employee｜简历与面试材料

> 项目定位：基于 RAG、LLM Tool Calling 与 Playwright RPA 的企业 AI 数字员工 Demo。本文严格以当前仓库已经实现和验收的能力为准，不把 Docker、会话持久化、知识上传、正式 ERP API 或数字人 Avatar 描述为已完成功能。

## 可量化事实速查

以下数字可在面试中使用，但应说明它们是项目工程规模和测试结果，不是虚构的商业收益：

- 1 条可解释的 Agent 主链路，接入 3 个白名单工具：知识库检索、ERP 订单查询、安全计算。
- 3 个本地服务端口：Streamlit `8501`、FastAPI Backend `8000`、Mock ERP `8001`。
- 4 份企业知识 PDF、4 个当前索引向量；默认切块大小 `500`、重叠 `80`、Top-K `3`、相似度阈值 `0.45`。
- 20 条确定性模拟订单，覆盖已发货、处理中、已完成、已退款、待付款和已取消等状态。
- Agent 最大执行步数为 5，默认禁止并行工具调用，以保证条件式问题先查订单事实再决定是否查政策。
- 18 个测试文件、80 个显式测试函数；默认回归结果为 `109 passed, 4 skipped`，完整本地集成回归为 `113 passed`。
- TTS 文本上限 2,000 字符，默认超时 30 秒，生成音频默认保留 24 小时。
- 覆盖 3 个固定面试场景：RAG、RPA、订单与政策的多工具综合问题。

---

## 1. 简历描述参考

### 1.1 较详细版本（中文）

**Nova AI Agent Employee｜企业 AI 数字员工**

技术栈：Python 3.11、FastAPI、OpenRouter、OpenAI SDK、Pydantic、Playwright、BGE、FAISS、Streamlit、SQLite、Edge TTS、pytest

- 基于 FastAPI 与 OpenRouter Tool Calling 自研可解释的 Agent Loop，通过 Pydantic Schema 注册并二次校验 `search_company_docs`、`query_order`、`calculate` 3 个白名单工具，支持单工具及多轮组合调用；设置最多 5 步、重复调用检测、有限重试和统一错误码，降低死循环、错误参数及工具失败时的编造风险。
- 使用 pypdf、`BAAI/bge-small-zh-v1.5` 与 FAISS CPU 构建本地企业 RAG，完成 4 份 PDF 的离线解析、切块、向量索引、Top-K 检索、阈值过滤和来源去重；回答可回传文件名、页码、Chunk ID 与相似度，实现可追踪的知识问答。
- 使用 Playwright Async API 实现浏览器 RPA，自动登录 FastAPI/Jinja2/SQLite 构建的 Mock ERP，并从 20 条确定性订单中查询状态、金额和物流；采用 `data-testid` 稳定选择器、15 秒超时、登录失败/订单不存在/页面异常映射，确保 Agent 不直接绕过网页读取数据库。
- 设计 FastAPI `/api/chat`、`/api/tts` 和 `/health` 契约，统一返回回答、Agent Trace、Sources、Audio URL 与 Request ID；使用 Streamlit 展示 3 个固定演示问题、工具执行步骤、耗时、引用来源和按需中文 TTS，语音失败时不影响文字主链路。
- 建立 Fake LLM 单元测试、API 测试、真实 BGE/FAISS 集成测试、临时 Mock ERP 与项目内 Chromium RPA 回归，以及演示前 Preflight；18 个测试文件的默认回归达到 `109 passed, 4 skipped`，完整本地集成回归达到 `113 passed`，并对 API Key、密码、完整 Prompt 和文档正文实施日志脱敏。

### 1.2 Detailed version (English)

**Nova AI Agent Employee | Enterprise AI Employee**

Tech stack: Python 3.11, FastAPI, OpenRouter, OpenAI SDK, Pydantic, Playwright, BGE, FAISS, Streamlit, SQLite, Edge TTS, pytest

- Built an explainable agent loop with FastAPI and OpenRouter tool calling. Registered and revalidated 3 allowlisted tools—document search, ERP order lookup, and safe calculation—through Pydantic schemas, with multi-round execution, a 5-step cap, duplicate-call detection, bounded retries, and structured error handling.
- Developed a local enterprise RAG pipeline with pypdf, `BAAI/bge-small-zh-v1.5`, and FAISS CPU, indexing 4 PDFs with chunking, Top-K retrieval, score filtering, source deduplication, and traceable file/page/chunk citations.
- Implemented asynchronous browser RPA with Playwright to log into a FastAPI/Jinja2/SQLite Mock ERP and query 20 deterministic orders for status, amount, and shipment data; added stable `data-testid` selectors, a 15-second timeout, and explicit login/not-found/page-error mappings.
- Designed typed `/api/chat`, `/api/tts`, and `/health` contracts that return answers, agent traces, sources, audio URLs, and request IDs. Built a Streamlit interface for 3 interview scenarios with tool-step visualization and optional Chinese TTS that degrades safely to text.
- Established Fake-LLM unit tests, API tests, real BGE/FAISS integration tests, temporary Mock ERP and project-local Chromium RPA tests, plus demo preflight checks. The suite contains 18 test files and records `109 passed, 4 skipped` by default and `113 passed` in the full local integration run.

### 1.3 STAR 短版（中文，可直接放入简历）

**S/T（背景与任务）**：针对企业知识分散、旧 ERP 缺少标准接口且通用大模型无法获取实时业务数据的问题，独立设计可现场演示、可解释并具备失败保护的 AI 数字员工。

**A（行动）**：使用 FastAPI + OpenRouter 自研最多 5 步的 Tool Calling Agent，编排 RAG、Playwright ERP RPA 和安全计算 3 个工具；使用 BGE + FAISS 索引 4 份 PDF，构建含来源引用、执行轨迹、统一错误码、Request ID 和按需 TTS 的 Streamlit 交互链路。

**R（结果）**：完成 RAG、订单查询及双工具综合问题 3 类端到端场景，覆盖 20 条模拟订单；建立 18 个测试文件，默认回归 `109 passed, 4 skipped`，完整本地集成回归 `113 passed`，实现从 Agent 决策到浏览器执行、来源引用和故障降级的可复现实验闭环。

### 1.4 STAR short version (English)

**S/T:** Designed an explainable AI employee for fragmented enterprise knowledge and legacy ERP workflows where a general-purpose LLM cannot access real-time business data.

**A:** Built a FastAPI/OpenRouter agent with a 5-step execution cap and 3 tools for local RAG, Playwright ERP automation, and safe calculation; indexed 4 PDFs with BGE/FAISS and exposed citations, traces, structured errors, request IDs, and optional TTS in Streamlit.

**R:** Delivered 3 reproducible end-to-end interview scenarios across 20 deterministic orders, with 18 test files and verified results of `109 passed, 4 skipped` by default and `113 passed` in the full local integration suite.

### 1.5 投递时的压缩建议

- 简历版优先使用 3 条 STAR 要点，项目介绍或作品集再使用详细版。
- 如果岗位偏后端，突出 API 契约、错误映射、异步 RPA、测试和日志安全。
- 如果岗位偏 AI 应用，突出 Agent Loop、Tool Calling 协议、RAG 来源、评测与幻觉控制。
- 如果岗位偏自动化，突出 API 优先原则、Playwright 页面状态等待、稳定选择器与故障恢复。
- 不要声称“生产落地”“提升业务效率 80%”“支持高并发”或“完全消除幻觉”，因为当前项目没有对应生产数据或压测证据。

---

## 2. 三到五分钟项目介绍

### 2.1 可直接口述的版本

大家好，我介绍的项目叫 **Nova AI Agent Employee**，它是一个基于 RAG、LLM Agent 和 RPA 的企业 AI 数字员工 Demo。这个项目解决的是两个典型问题：第一，企业制度和产品资料分散在 PDF 中，普通大模型不知道公司的私有知识；第二，订单状态属于实时业务数据，通用模型既不知道，也不能凭空回答，而一些旧 ERP 又不一定提供标准 API。

整个系统由三个本地服务组成。用户在 `8501` 端口的 Streamlit 页面提问，请求发送到 `8000` 端口的 FastAPI Backend。Backend 内部是我自己实现的 Agent Loop，它通过 OpenRouter 调用支持 Tool Calling 的模型。模型只负责判断应该使用哪个工具，真正的工具执行、参数校验、超时和错误处理都由 Python 程序控制。系统目前有三个白名单工具：企业知识库检索、ERP 订单查询和安全计算。

知识库部分使用 pypdf 读取 4 份企业 PDF，按照 500 字符和 80 字符重叠进行切块，再使用本地中文模型 `BAAI/bge-small-zh-v1.5` 生成向量并保存到 FAISS。检索时默认取 Top 3，并通过 0.45 的阈值过滤低相关内容。每个 Chunk 从索引阶段就保留文件名、页码和 Chunk ID，因此回答不只是给结论，还能展示来源。这里 RAG 的价值不是保证模型永远不幻觉，而是把回答约束在可检索资料内，并让用户能够核对证据。

订单查询部分使用 Playwright 操作 `8001` 端口的 Mock ERP。RPA 会打开登录页、输入账号密码、搜索订单、进入详情页，再读取订单状态、金额和物流。Mock ERP 内置 20 条不同状态的订单，方便稳定复现已发货、处理中、已退款和不存在订单等场景。我特意没有让 Agent 直接读取 SQLite，因为项目想展示的是旧系统只有网页、没有 API 时如何自动化；如果真实系统有稳定 API，我会优先使用 API，因为它更快、更稳定，也更容易监控。

最有代表性的演示问题是：“查询订单 10001，如果已经发货，告诉我物流信息，同时根据公司的退款政策告诉我是否还能申请退款。”在这个问题中，模型先调用 `query_order`，Python 使用 RPA 得到订单已发货和物流信息；然后模型再调用 `search_company_docs` 查询退款政策；最后将两个工具结果交给模型生成综合回答。前端会同时展示两个工具的执行轨迹、耗时、来源和 Request ID，所以面试官可以看到 Agent 为什么得到这个结论，而不是只看到一段黑盒文本。

在安全和稳定性方面，我做了几层约束。Tool 参数由 Pydantic Schema 描述，并在执行前再次校验；Calculator 使用 AST 白名单而不是 `eval`；Agent 最大执行 5 步，并检测相同工具和参数的重复调用；LLM、RPA、RAG 和 TTS 都有清晰错误码和降级路径。TTS 是按需调用的，即使语音服务失败，文字回答、来源和轨迹仍然保留。日志包含轮次、工具名、状态、耗时和 Request ID，但不记录 API Key、密码、完整 Prompt 或大段文档内容。

测试方面，我把不稳定的外部依赖与核心逻辑分开：使用 Fake LLM 测 Agent 消息循环和多工具行为，使用真实 BGE/FAISS 测检索，使用临时 Mock ERP 和项目内 Chromium 测 RPA。当前共有 18 个测试文件，默认回归是 `109 passed, 4 skipped`，完整本地集成回归是 `113 passed`。另外还有 Preflight 脚本，在演示前检查配置、模型 tools 能力、余额、索引、订单 seed、Chromium 和端口，并让三个固定问题各运行一次。

我没有在第一版引入 LangChain、多 Agent、Redis、Celery 或复杂前端，因为这个项目的目标是用最小且可解释的架构证明 Agent、RAG、RPA、API 设计和测试能力。当前限制是没有服务端会话记忆、知识上传、权限系统和生产部署，免费模型的综合 Tool Calling 也可能波动。下一步我会优先增加稳定模型评测、混合检索和重排、会话与权限、正式 ERP API 适配、可观测性和 Human-in-the-loop，而不是单纯继续堆叠框架。

### 2.2 时间控制提示

- **0:00–0:30**：业务问题和项目目标。
- **0:30–1:20**：三服务架构、Agent 与 3 个工具。
- **1:20–2:10**：RAG 与来源追踪。
- **2:10–2:50**：Playwright RPA 与 API 优先原则。
- **2:50–3:40**：综合问题的多轮 Tool Calling。
- **3:40–4:30**：安全、测试、Preflight 与量化结果。
- **4:30–5:00**：技术取舍、当前限制和下一步。

如果面试时间只有 3 分钟，可删去具体切块参数、TTS 和测试分层细节，只保留业务问题、架构、综合场景、安全边界与结果。

---

## 3. 面试时需要能够解释的问题

下面不只列问题，也给出回答时应覆盖的关键点和面试官可能继续追问的方向。

### 3.1 项目定位与架构

#### 1. 为什么选择“企业 AI 数字员工”，而不是普通聊天机器人？

回答要点：普通聊天只生成文本；数字员工需要访问企业私有知识和实时业务系统，并执行受控动作。本项目通过 RAG 获取静态私有知识，通过 RPA 获取动态订单事实，通过 Calculator 执行确定性运算，再通过 Agent 编排。核心价值是“有依据地回答并执行”，不是换一个聊天 UI。

可能追问：如果只做固定的三个意图，为什么不用规则路由？

应答：固定 Demo 可以用规则路由，且确定性更高；选择 Tool Calling 是为了展示自然语言扩展和多步组合能力，但关键业务条件仍应使用代码工作流或策略约束，而不能完全交给模型。

#### 2. Agent、ChatBot 和固定 Workflow 有什么区别？

回答要点：ChatBot 主要生成回复；Workflow 的步骤和分支由代码预先确定；Agent 由模型根据上下文选择下一步工具。Agent 灵活但不确定，Workflow 稳定但扩展自然语言意图成本更高。真实生产系统通常采用混合方案：模型负责意图理解，关键流程由确定性状态机执行。

#### 3. 为什么拆成 Streamlit、Backend 和 Mock ERP 三个服务？

回答要点：UI 只展示，Backend 负责 Agent/API，ERP 模拟外部遗留系统；边界清楚后可以独立替换、测试和故障隔离。前端不持有 LLM Key，也不直接访问数据库。

#### 4. 为什么当前不是“生产级系统”？

回答要点：缺少鉴权/RBAC、多租户、会话持久化、在线索引、审计审批、高可用、压测、正式 Secret Manager、生产监控和部署方案；当前定位是可复现的面试 Demo，不能用测试数量代替生产 SLA。

### 3.2 Agent 与 Tool Calling

#### 5. 什么是 Function Calling / Tool Calling？到底是谁执行工具？

回答要点：模型返回结构化的工具名和 JSON 参数，它不会执行 Python 函数。应用读取 Tool Call，按白名单找到工具，用 Pydantic 校验参数后执行，再把结构化结果连同 `tool_call_id` 发回模型。

#### 6. 为什么工具执行完还要把结果发送给 LLM？

回答要点：模型只提出调用意图，并不知道真实执行结果。回传后它才能基于订单状态、政策片段或错误信息形成最终自然语言回答，并决定是否继续调用下一个工具。

#### 7. 为什么要自己实现 Agent Loop，而没有使用 LangChain/LangGraph？

回答要点：当前只有 3 个工具和最多 5 步，手写循环代码量有限，更容易解释 OpenAI Tool Calling 消息协议、错误边界和轨迹。缺点是以后增加持久化、分支、暂停恢复和人工审批时需要自行维护；复杂工作流届时可迁移到 LangGraph 或其他状态机框架。

#### 8. 综合条件问题如何保证先查订单、再查退款政策？

回答要点：默认 `parallel_tool_calls=false`，System Prompt 明确先确认条件，并将工具结果逐轮放回 messages。当前属于“提示词 + 顺序 Agent Loop”的软约束；如果业务规则要求绝对保证，应把条件分支写成确定性 Workflow，而不是依赖模型遵循提示词。

#### 9. 如何防止 Agent 死循环或重复调用？

回答要点：最多 5 步；记录规范化后的 `tool_name + arguments`，拒绝相同调用重复出现；工具不无限重试；未知工具、参数 JSON 错误和最终空回答都有明确错误。

#### 10. 为什么 Tool Schema 还不够，执行前仍要再次校验？

回答要点：Schema 是给模型的约束描述，不是可信安全边界；模型或 Provider 仍可能返回缺字段、额外字段或错误类型。应用必须把模型输出视为不可信输入并重新校验。

#### 11. Agent 与多 Agent 的边界是什么？为什么没有做多 Agent？

回答要点：当前工具职责明确，一个协调 Agent 足够。多 Agent 会引入路由、共享状态、通信、冲突解决、成本和调试复杂度；只有当不同角色需要独立上下文、长期任务或并行专业推理时才值得引入。

### 3.3 RAG 与知识库

#### 12. 什么是 RAG？它怎样降低幻觉？

回答要点：先从外部知识库检索相关片段，再把片段提供给模型生成答案。它让回答有企业资料和来源，但检索可能漏召回、资料可能过期、模型也可能误读，因此只能降低而不能完全消除幻觉。

#### 13. 为什么需要 Embedding 和向量检索？

回答要点：Embedding 把文本映射为语义向量，使不同措辞但含义相近的问题也能匹配；关键词检索精确但不擅长同义表达。生产中可以采用 BM25 + 向量的混合检索，而不是二选一。

#### 14. 为什么选择 `BAAI/bge-small-zh-v1.5`？

回答要点：中文能力较好、模型较小、可本地运行、没有每次调用费用和外部数据传输。缺点是效果上限、CPU 延迟和领域适配可能不如更大或商业 Embedding；选择它是因为当前只有 4 份中文 PDF，演示规模不需要昂贵服务。

#### 15. Chunk Size、Overlap、Top-K 和阈值分别有什么作用？

回答要点：Chunk 太小会丢上下文，太大则混入噪声并占用 Token；Overlap 防止信息在边界被截断，但会带来重复；Top-K 平衡召回和上下文噪声；阈值拒绝低相关结果。当前 `500/80/3/0.45` 是 Demo 初始值，不是通用最优值，应该通过标注问答集调参。

#### 16. 为什么从切块阶段就保存文件名、页码和 Chunk ID？

回答要点：来源元数据必须与向量一一对应，才能在检索、去重、UI 展示和审计时追溯证据；生成回答后再猜页码是不可靠的。

#### 17. 为什么只用 FAISS，不用 Chroma、Qdrant、Milvus 或 pgvector？

回答要点：FAISS 对 4 份文档的本地单机 Demo 最轻量，没有额外服务和运维。缺点是缺少原生多用户、权限、在线更新、过滤、备份和服务化能力；规模扩大或需要 metadata filter 时会考虑 Qdrant/pgvector，超大规模再评估 Milvus。

#### 18. 当前 RAG 最大的问题是什么？

回答要点：语料和评测集太小，当前 4 份 PDF 只形成 4 个向量，不能证明复杂切块或检索质量；没有 BM25 混合检索、Reranker、Query Rewrite、增量索引和文档权限。下一步应先建立带正确来源的评测集，再优化算法。

#### 19. 如何处理扫描 PDF、表格和图片？

回答要点：当前 pypdf 只适合文本型 PDF。扫描件需要 OCR，复杂版面可用 PyMuPDF、Unstructured、Docling 或云文档理解服务；表格应保留结构并按表格语义切块，而不是简单按字符截断。

#### 20. 如何防御知识库 Prompt Injection？

回答要点：把检索内容视为数据而非指令；System Prompt 明确忽略文档中的越权指令；工具权限与数据访问在代码层限制；对敏感操作增加人工确认；建立恶意文档测试。当前项目主要做了工具白名单和参数校验，文档级注入防御仍需增强。

### 3.4 RPA 与 ERP

#### 21. 为什么有 API 时应优先 API，而不是 RPA？

回答要点：API 更快、更稳定、结构化、易做权限、幂等和监控；RPA 依赖页面、选择器和浏览器资源。RPA 适合没有 API、改造成本高或需要快速连接遗留系统的场景。

#### 22. Playwright 和 Selenium 怎么选？

回答要点：Playwright 有更好的自动等待、浏览器上下文、网络拦截和现代异步 API，减少显式 sleep；Selenium 生态成熟、语言和浏览器覆盖广、企业存量更多。本项目选择 Playwright 是因为页面交互简单且使用 Python 异步栈。

#### 23. 为什么 Mock ERP 仍有价值？

回答要点：真实 ERP 不适合放进公开项目，也不便于稳定复现。Mock ERP 提供登录、列表、搜索、详情和 20 条固定订单，使 RPA 成功与失败场景可重复测试，同时模拟“只能通过网页访问”的遗留系统边界。

#### 24. 如何让 RPA 更稳定？

回答要点：使用 `data-testid`，等待元素状态而不是固定 sleep；页面阶段分别记录日志；设置超时；区分登录失败、订单不存在和页面结构变化；失败时关闭浏览器；正式系统还应加入截图/Trace、重试幂等、页面版本监控和告警。

#### 25. RPA 可以并发跑很多订单吗？

回答要点：当前每次请求启动浏览器流程，不适合高并发。生产方案需要浏览器池、队列、并发上限、任务状态、超时取消和目标系统限流；批量查询更应推动 ERP API 或数据同步，而不是无限横向扩展 RPA。

### 3.5 安全、错误处理和可靠性

#### 26. 为什么 Calculator 不能直接使用 `eval`？

回答要点：模型参数和用户输入均不可信，`eval` 可能执行导入、文件、网络或系统命令。当前解析 AST，只允许数字、括号和有限算术节点，并限制表达式长度、幂和异常情况。

#### 27. Tool 失败时系统怎么处理？

回答要点：工具统一返回 `ToolResult`，包含 `success`、`data`、`error_code`、`message`、`sources`；Agent 将安全结果回传模型，同时 API 将错误映射为 4xx/5xx。模型被要求不编造，前端显示安全提示和 Trace。

#### 28. 为什么同时需要 Request ID、Trace 和日志？

回答要点：Request ID 关联一次 HTTP 请求；Trace 面向用户展示安全、简短的执行过程；日志面向开发排障，记录轮次、耗时和状态。三者受众和敏感度不同，不能直接把完整内部日志暴露给用户。

#### 29. 哪些数据不应该进入日志？

回答要点：API Key、Authorization Header、ERP 密码、完整用户问题、完整 Prompt、工具敏感参数和大段文档内容。当前日志用长度、模型名、工具名、状态、耗时、文件名和分数替代原文。

#### 30. 最大步数为什么设为 5？

回答要点：三个演示场景最多需要约 3 轮模型交互，5 步提供余量，又能限制成本和失控范围。这不是固定真理，应根据任务复杂度、成本预算和离线轨迹统计调整。

#### 31. 如何处理 LLM 限流、超时、余额不足和模型不支持 tools？

回答要点：配置固定模型 ID；Preflight 调 Models/Credits API 检查；客户端只对限流、临时上游错误和网络错误有限重试；鉴权、余额、模型不存在和 tools 不支持映射为明确错误，不盲目重试。

### 3.6 API、前端、TTS 与状态

#### 32. 为什么使用 FastAPI？

回答要点：Pydantic 类型校验、异步支持和自动 OpenAPI 文档适合 Agent API；相较 Flask 约定更完整，相较 Django 更轻。当前没有复杂后台管理、ORM 或大型业务域，因此 FastAPI 成本更低。

#### 33. Streamlit 中有聊天历史，为什么仍然说 Agent 无会话记忆？

回答要点：页面把消息保存在当前 UI Session 只用于显示；Backend 每次只处理当前问题，`session_id` 是预留字段，不读取历史。UI 历史不等于模型上下文或服务端持久化。

#### 34. 为什么 TTS 做成按需调用，而不是每次自动生成？

回答要点：减少延迟、网络依赖和无用音频；让文本主链路先成功；Provider 失败时只提示语音不可用。TTS 不参与答案推理，属于表现层增强。

#### 35. `edge-tts` 有什么风险？

回答要点：它适合低成本个人 Demo，但不是正式 Azure 商业 API，接口变化和可用性不受项目控制。生产环境应通过现有 `TTSService` 抽象替换 Azure Speech、ElevenLabs 或其他有 SLA 的 Provider。

### 3.7 测试、评估与工程权衡

#### 36. 为什么多数自动测试不直接调用真实 LLM？

回答要点：真实模型有成本、网络波动和非确定性，会造成慢且不稳定的 CI。Fake LLM 用确定输出覆盖直接回答、单工具、多工具、错误参数、重复和超限；真实模型只用于受控冒烟与演示前验收。

#### 37. `109 passed` 是否代表系统质量足够高？

回答要点：不代表。它说明已定义的代码路径没有回归，但不能证明真实模型稳定性、检索质量、安全性、高并发或生产 SLA。需要场景评测集、线上指标、对抗测试、压测和故障演练补充。

#### 38. Preflight 解决什么问题？

回答要点：把演示前容易遗漏的依赖变成可执行检查，包括 `.env`、固定模型、余额、tools 能力、ERP seed、向量索引、Chromium、端口和三个真实问题，减少“代码没变但环境导致 Demo 失败”的风险。

#### 39. 为什么没有使用 Redis、Celery、SQLAlchemy、React 或 Docker？

回答要点：当前是单机、小数据、短任务的面试 Demo，增加这些组件会提高部署与讲解成本，却不直接增强 Agent 主链路。缺点是当前不适合多实例、高并发和长任务；当真实需求出现时再按瓶颈引入。Docker 已按当前项目计划明确忽略，本地运行是正式演示路径。

#### 40. 如果让你把项目上线，第一周先做什么？

回答要点：先定义用户、数据敏感度、SLA 和验收指标；接入鉴权/RBAC和 Secret Manager；建立稳定模型与 RAG 评测集；将关键业务分支改为确定性 Workflow；接正式 API 或加 RPA 队列；补监控、审计、限流、压测和部署流水线，而不是先做 Avatar。

---

## 4. 技术选择及主流方案对比

### 4.1 语言与后端

| 当前选择 | 常见替代 | 当前方案优点 | 当前方案缺点 | 为什么仍选择当前方案 |
| --- | --- | --- | --- | --- |
| Python 3.11 | TypeScript/Node.js、Java/Spring Boot | AI/RAG/RPA 生态完整，原型快，异步库够用 | CPU 密集、高并发和静态约束弱于部分替代方案 | 主要依赖 sentence-transformers、FAISS、Playwright 和 AI SDK，Python 集成成本最低 |
| FastAPI + Uvicorn | Flask、Django/DRF、Spring Boot、NestJS | Pydantic 校验、Async、OpenAPI 开箱即用 | 大型业务治理、后台管理和成熟企业规范不如 Django/Spring | 项目 API 少、类型契约重要，FastAPI 在轻量与工程化之间平衡最好 |
| Pydantic / pydantic-settings | dataclass、Marshmallow、手写校验 | 请求、配置、Tool 参数统一类型约束 | 运行时校验有成本，复杂版本升级需注意兼容 | 模型输出不可信，清晰的二次校验比少量性能开销更重要 |

### 4.2 Agent 与模型接入

| 当前选择 | 常见替代 | 当前方案优点 | 当前方案缺点 | 为什么仍选择当前方案 |
| --- | --- | --- | --- | --- |
| 手写 Agent Loop | LangChain Agent、LangGraph、Semantic Kernel、AutoGen | 消息协议、工具执行、去重、步数和 Trace 全部透明，面试可解释 | 状态持久化、分支、恢复、人工审批需自行开发 | 只有 3 个工具和最多 5 步，引入框架收益小于抽象与调试成本 |
| OpenRouter + OpenAI SDK | 直接调用 OpenAI/Anthropic/Gemini、LiteLLM、自部署 vLLM/Ollama | 一个兼容端点可切换多模型，代码简单 | 多一层网关依赖；模型质量、路由、价格和能力可能变化 | Demo 需要低成本试验不同 Tool Calling 模型，并保留替换能力 |
| 顺序 Tool Calling | 并行 Tool Calling、固定 DAG | 条件问题可先查订单再决定下一步，轨迹容易理解 | 延迟更高，仍不能完全保证模型遵循业务条件 | 当前综合问题存在条件依赖；绝对关键流程以后应迁移为代码 Workflow |

### 4.3 RAG

| 当前选择 | 常见替代 | 当前方案优点 | 当前方案缺点 | 为什么仍选择当前方案 |
| --- | --- | --- | --- | --- |
| pypdf | PyMuPDF、pdfplumber、Unstructured、Docling、OCR 服务 | 轻量，文本型 PDF 足够 | 扫描件、复杂表格和版面能力有限 | 当前 4 份资料是自制文本 PDF，不需要复杂解析管线 |
| `bge-small-zh-v1.5` 本地 Embedding | OpenAI/Cohere Embedding、BGE-M3、更大本地模型 | 中文、本地、零按次费用、数据不出本机 | CPU 延迟和效果上限有限，需要下载模型 | Demo 数据小，隐私、成本和离线复现优先于极致指标 |
| FAISS CPU | Chroma、Qdrant、Milvus、Weaviate、Elasticsearch、pgvector | 快、简单、无服务依赖 | 缺少服务化、权限、在线更新、复杂过滤和分布式能力 | 当前仅 4 个向量，部署向量数据库属于过度工程 |
| Dense Top-K + 阈值 | BM25、Hybrid Search、Reranker、Query Rewrite | 实现直观，链路容易解释 | 关键词精确匹配、复杂查询和排序能力有限 | 先建立最小 RAG 基线，后续应以评测数据决定是否增加混合检索与重排 |

### 4.4 RPA 与数据层

| 当前选择 | 常见替代 | 当前方案优点 | 当前方案缺点 | 为什么仍选择当前方案 |
| --- | --- | --- | --- | --- |
| Playwright Async API | Selenium、Puppeteer、UiPath/Power Automate、直接 ERP API | 自动等待、现代浏览器支持、异步 Python、Trace/网络能力好 | 页面变化易破坏，资源和延迟高于 API | 项目要演示无 API 遗留系统的浏览器自动化；真实有 API 时仍优先 API |
| FastAPI + Jinja2 Mock ERP | 接真实 SaaS、静态 HTML、前端 SPA | 登录/搜索/详情完整，数据可复现且安全 | 不能代表真实 ERP 的复杂权限、验证码和页面变化 | 公开项目不能依赖真实企业系统，Mock 能稳定测试端到端 RPA |
| sqlite3 | PostgreSQL/MySQL、SQLAlchemy | 零服务、单文件、20 条订单足够 | 并发、迁移、连接管理和复杂关系能力有限 | 当前只有 1 张表，ORM 和数据库服务不会增加核心展示价值 |

### 4.5 前端、语音和工程化

| 当前选择 | 常见替代 | 当前方案优点 | 当前方案缺点 | 为什么仍选择当前方案 |
| --- | --- | --- | --- | --- |
| Streamlit | React/Vue + 独立 API、Gradio | 最快完成聊天、Trace、来源和音频展示 | UI 定制、状态管理、性能和大型前端工程能力有限 | 面试价值在 Agent 轨迹，不在复杂视觉设计 |
| Edge TTS | Azure Speech、ElevenLabs、OpenAI TTS、本地模型 | 接入快、成本低、中文声音可用 | 非正式商业 API，稳定性和 SLA 不可控 | 作为可选 P1 展示能力，并通过 `TTSService` 隔离，便于替换 |
| pytest + Fake LLM + 分层集成测试 | 全部真实端到端、仅手工测试 | 快、确定、便宜，同时保留真实 BGE/RPA 回归 | Fake 不能证明真实模型表现；完整集成仍依赖本地资源 | 单元测试保障逻辑，真实冒烟保障 Provider 能力，二者职责分离 |
| 同进程请求执行 | Celery/RQ + Redis、消息队列、工作流引擎 | 架构简单，Demo 可同步看到完整结果 | 长任务阻塞、无法水平扩展或恢复任务 | 当前请求量小、任务短；生产化后 RPA 和索引应进入队列 |

### 4.6 技术选择的总原则

当前方案不是“每项技术都最强”，而是在 **可解释、可复现、低成本、最少运维和面试展示价值** 之间取平衡。替代方案只有在出现相应需求时才值得引入：

- 出现复杂分支、暂停恢复和人工审批时，再引入 LangGraph/工作流引擎。
- 出现多用户、在线更新和权限过滤时，再引入 Qdrant/pgvector 等服务化向量库。
- 出现高并发和长任务时，再引入 Redis、队列、Worker 和任务状态机。
- 出现复杂 UI 和产品化需求时，再迁移 React/Vue。
- 接入真实 ERP 时优先标准 API，RPA 只覆盖 API 缺口。

---

## 5. 后续会增加或可扩展的功能

### 5.1 Agent 与业务流程

- 服务端会话持久化、上下文摘要、Token 预算和跨轮订单指代解析。
- 将退款、审批等关键条件从 Prompt 软约束升级为确定性状态机或 LangGraph Workflow。
- Human-in-the-loop：高风险操作在执行前展示计划、参数和影响，由用户确认。
- 工具级权限、幂等键、审计记录、补偿动作和长任务恢复。
- 增加邮件、日历、CRM、工单等连接器，但保持白名单与最小权限。

### 5.2 RAG 与知识治理

- PDF/Word/网页上传、增量索引、删除同步、索引版本和原子切换。
- BM25 + Dense Hybrid Search、Cross-Encoder Reranker、Query Rewrite 和多查询召回。
- 建立包含正确答案、正确来源、拒答样本和恶意文档的 RAG 评测集。
- 文档级 ACL、多租户隔离、敏感字段脱敏、有效期与版本管理。
- OCR、表格解析、图片理解，以及对扫描件和复杂版面的支持。

### 5.3 RPA 与企业集成

- 正式 ERP API Adapter，采用 API 优先、RPA 补位的统一工具接口。
- 浏览器池、任务队列、并发限制、失败截图/Trace、断点续跑和页面变更告警。
- 操作类工具的确认、幂等、审批、回滚与完整审计。
- 为不同 ERP 页面提供版本化 Selector 和契约测试。

### 5.4 模型、语音与数字人

- 多模型路由、Fallback、成本/延迟预算、Provider 隐私路由与 ZDR 选项。
- 流式输出和流式 TTS，缩短首字与首音频延迟。
- 将 Edge TTS 替换为有 SLA 的正式 Provider，并增加声音、语速和缓存策略。
- 在现有 `LLM → TTS` 后接 Avatar API、Lip Sync、视频生成和播放；Avatar 仅属于表现层，不应侵入 Agent 核心。

### 5.5 产品化与平台能力

- 用户登录、RBAC、租户隔离、配额和管理后台。
- Redis/队列/Worker、PostgreSQL、对象存储和可恢复任务状态。
- OpenTelemetry Trace、指标、日志聚合、成本统计、告警和 Prompt/模型版本对比。
- CI/CD、容器化或其他部署打包、Secret Manager、依赖漏洞扫描、压测和灾难恢复。
- 面向业务的反馈、引用纠错、人工标注和持续评测闭环。

---

## 6. 当前项目中可优化的技术点或功能

### 6.1 优先级清单

| 优先级 | 当前问题 | 影响 | 优化方向 | 可验证结果 |
| --- | --- | --- | --- | --- |
| P0 | 当前免费 Tool Calling 模型在综合问题上存在漏调工具或退化输出 | 现场 Demo 不稳定 | 配置稳定模型与可用额度；建立多次重复真实评测；保留模型 Fallback | 3 个固定问题连续多轮达到预设通过率，无空答/重复字符 |
| P0 | RAG 只有 4 份 PDF、4 个向量，数据规模过小 | 无法证明复杂检索质量 | 扩充真实结构的文档和问答评测集；基于 Recall@K、MRR、来源准确率调参 | 形成版本化评测报告，而非凭主观观察选 `500/80/3/0.45` |
| P0 | 条件式工具顺序主要依赖 Prompt | 关键业务分支不具备强确定性 | 把“先查订单再判断退款”改为显式状态机/Workflow；模型只负责意图和总结 | 自动测试证明未发货/不存在订单不会错误进入后续步骤 |
| P0 | 文档 Prompt Injection 与工具越权防护仍不完整 | 恶意文档可能影响模型行为 | 检索内容标记为不可信数据、策略层权限、恶意样本测试、高风险操作确认 | 对抗测试覆盖越权指令、数据外泄和工具滥用 |
| P0 | 当前没有真实用户鉴权和文档权限 | 不能处理真实企业数据 | OIDC/OAuth2、RBAC、文档 ACL、租户隔离与审计 | 不同角色只能检索和执行其授权范围内的资源 |
| P1 | 索引通过手工命令整体重建 | 文档更新后可能出现旧索引或半成品 | 内容 Hash、增量索引、Manifest 校验、临时目录构建后原子切换 | 更新/删除文档后索引一致，失败时仍保留旧可用版本 |
| P1 | Dense-only 检索对订单号、产品代码等精确词不占优 | 可能漏掉关键词强匹配 | BM25 + Dense 混合召回，增加 Reranker 和 Query Rewrite | 在评测集上提升来源 Recall@K 和最终回答正确率 |
| P1 | 每次 RPA 请求的浏览器成本较高 | 延迟和并发能力有限 | 浏览器池、Context 隔离、任务队列、并发上限；优先接正式 API | 记录 P50/P95 延迟、资源占用和最大安全并发 |
| P1 | RPA 页面变化主要依赖运行时报错发现 | 选择器失效发现较晚 | 页面契约测试、失败截图/Playwright Trace、Selector 版本与告警 | 页面变化能在 CI 或预检阶段提前暴露 |
| P1 | Agent 请求未持久化，UI 历史不等于会话记忆 | 不能处理“上一单”“继续”类问题 | 服务端消息存储、摘要、Token 裁剪、会话过期与删除 | 多轮用例可复现，且 Token/隐私生命周期明确 |
| P1 | `edge-tts` 缺少商业 SLA | 语音演示受第三方变化影响 | 保留接口并接正式 TTS Provider；缓存相同文本结果 | Provider 故障可切换，文字主链路始终可用 |
| P1 | 只有日志和请求轨迹，没有统一 Metrics/Tracing | 难以定位跨 LLM、RAG、RPA 的瓶颈 | OpenTelemetry、Token/成本、工具成功率、P95 延迟和错误率 | 单个 Request ID 可串联 API、模型与工具耗时 |
| P2 | Streamlit 状态和 UI 定制能力有限 | 产品化体验和复杂交互受限 | 前后端分离，React/Vue + SSE/WebSocket 流式响应 | 首字延迟、交互状态和可维护性有量化改善 |
| P2 | SQLite 和同步本地文件只适合单机 | 多实例下数据一致性不足 | PostgreSQL、对象存储、Redis/队列和迁移工具 | 多实例部署下会话、任务、音频和索引生命周期一致 |
| P2 | 未做容器与部署交付 | 环境复现依赖本地手册 | 在项目明确恢复部署阶段后增加 CI 和可复现打包 | 新环境自动构建、测试并通过健康检查；当前阶段仍按计划忽略 Docker |

### 6.2 代码层面的具体改进

1. **Agent 状态显式化**：将当前 messages 列表和循环条件封装为状态对象，为持久化、恢复和人工审批预留状态迁移。
2. **策略与执行分离**：Tool Registry 继续负责 Schema/执行器，另加 Policy Layer 负责用户、工具、资源和风险级别授权。
3. **模型输出质量校验**：除空回答和重复字符外，增加必须引用来源、必须包含订单字段、不得声称执行未执行工具等业务断言。
4. **RAG 评测先行**：在增加框架前建立 Golden Dataset，分别评估 Retriever、Reranker 和最终生成，避免只看最终答案无法定位问题。
5. **异步与阻塞审计**：继续把 CPU/同步检索放到线程或 Worker；对 Embedding、索引和批量 RPA 引入队列，避免阻塞 API Event Loop。
6. **统一超时预算**：从 HTTP 总超时向下分配 LLM、RPA、RAG、TTS 子预算，并支持请求取消，避免各层超时相加失控。
7. **配置分环境**：开发、测试和演示使用不同配置，默认示例不应让免费不稳定模型看起来等同正式推荐模型。
8. **Secret 与演示账号治理**：Mock ERP 默认账号只能用于本地；真实环境接 Secret Manager，日志和异常继续保持脱敏。
9. **API 能力增强**：增加 SSE 流式输出、健康检查分级（liveness/readiness）、限流、请求大小限制和幂等键。
10. **测试补强**：增加 Prompt Injection、并发、取消、页面变化、索引损坏、音频清理竞态和多轮会话测试；真实模型测试采用次数与预算上限。

### 6.3 优化顺序建议

如果只有一周时间，建议按以下顺序投入：

1. 先解决稳定模型、真实三题重复评测和演示 Preflight，这是当前最直接的交付风险。
2. 建立 RAG Golden Dataset，再决定混合检索、Reranker 和参数调整。
3. 把关键条件流程确定化，并补 Prompt Injection、权限和高风险操作确认。
4. 增加索引生命周期、RPA Trace 和统一可观测性。
5. 最后再做会话、复杂前端、Avatar 或部署包装；这些不应掩盖核心正确性问题。

---

## 面试表达底线

- 能区分“模型选择工具”和“程序执行工具”。
- 能承认 Agent、RAG 和 RPA 的不确定性与失败边界。
- 能用数据说明工程覆盖，但不把测试数量包装成业务收益。
- 能解释为什么当前没有引入复杂框架，也能说明规模增长后何时应该迁移。
- 能明确指出当前免费模型综合场景仍有波动，稳定模型真实复验尚待可用配置。
- 能把下一步优先级放在正确性、安全、评测和可观测性，而不只是增加炫酷功能。
