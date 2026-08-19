# AI 数字员工项目实施计划

> 本文基于现有 `Readme.md` 制定，只规划、不实现代码。  
> 项目定位：用于简历和面试演示的可运行 Demo，而不是生产级企业系统。  
> 核心原则：可运行、可演示、可解释、易修改，功能数量服从于演示稳定性。

## 1. 结论先行

原方案的业务故事、核心技术链路和面试展示点已经比较完整，整体可行。最有价值的不是“数字人”概念本身，而是下面这条能被现场演示和清楚讲解的链路：

```text
自然语言问题
  -> LLM 判断并调用工具
  -> Playwright 查询模拟 ERP
  -> RAG 检索公司政策
  -> LLM 汇总多个工具结果
  -> 展示答案、来源和执行记录
```

原方案的问题主要不是缺少功能，而是范围偏大，并且把一些加分项写成了最低要求。如果一次完成 RAG、RPA、Agent、TTS、Docker、知识上传、数字人接口和大量测试，初学时很容易陷入依赖、部署和异步调试，反而无法解释核心代码。

因此，本计划做以下收缩：

1. 保留四个核心亮点：RAG、Tool Calling、Playwright RPA、多工具调用。
2. 使用简单的自写 Agent Loop，不引入 LangChain、LangGraph 或多 Agent 框架。
3. 使用 OpenRouter 的 OpenAI 兼容接口统一调用 LLM，并将具体模型保留为可配置项。
4. Embedding 默认在本地运行，避免额外 API 费用。
5. Mock ERP 使用 FastAPI + Jinja2 + Python 内置 `sqlite3`，第一版不引入 SQLAlchemy。
6. 前后端只采用普通 HTTP 请求，不做 WebSocket、SSE 和流式输出。
7. TTS、Docker、知识库上传都放到核心链路稳定之后。
8. 不实现语音输入、真正数字人、用户系统、权限系统和生产级部署。

最终建议把项目分为三个等级：

- **P0 核心必做**：能完成三个固定面试场景，且失败时能给出清楚错误。
- **P1 简历加分**：TTS、执行轨迹 UI、Docker、更多测试和更好的 README。
- **P2 后续扩展**：上传 PDF、会话持久化、切换其他模型、数字人接口。

只要 P0 完成并稳定，项目已经足够写进简历；P1 应按剩余时间选择，不应阻塞 P0。

---

## 2. 原方案完整度分析

### 2.1 已经设计得较完整的部分

| 方面 | 评价 | 原因 |
| --- | --- | --- |
| 项目目标 | 完整 | 明确是面试 Demo，不追求商业产品 |
| 演示场景 | 很完整 | RAG、RPA、计算、多工具综合问题都有示例 |
| 总体架构 | 基本完整 | 前端、API、Agent、Tool、RAG、RPA、TTS 边界明确 |
| Tool 定义 | 完整 | 三个工具职责清楚，输入也较简单 |
| RAG 流程 | 基本完整 | 包含加载、切块、Embedding、检索和来源 |
| RPA 流程 | 完整 | 登录、搜索、详情读取、错误场景均可落地 |
| 工程要求 | 较完整 | 包含配置、日志、异常、测试和 Docker |
| 面试准备 | 很完整 | 已列出演示问题、简历描述和知识问答 |

### 2.2 需要补充或修正的地方

#### 2.2.1 “用户文字 / 语音”与实际范围不一致

架构图写了语音输入，但后文只设计了 TTS，没有 ASR（语音识别）。第一版应明确：

- 输入仅支持文字；
- 输出可选 TTS；
- 不开发麦克风录音和语音转文字。

#### 2.2.2 模型供应商被写死

原文大量使用 `GPT-4o` 和 `OPENAI_API_KEY`，后续方案又一度写死为 DeepSeek。当前决策是统一通过 OpenRouter 调用 LLM，配置改为：

```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openai/gpt-5-mini
LLM_TEMPERATURE=0
LLM_PARALLEL_TOOL_CALLS=false
OPENROUTER_HTTP_REFERER=http://localhost:8501
OPENROUTER_APP_TITLE=AI Digital Employee Demo
```

业务代码只依赖 `LLMClient`，不直接依赖某个具体模型名称。`OPENROUTER_API_KEY` 是必需的秘密配置；`HTTP-Referer` 和 `X-OpenRouter-Title` 对本地调用不是鉴权必需项，但建议配置，便于 OpenRouter 归因和识别应用。以后切换模型时只修改 `LLM_MODEL`，不修改 Agent 业务代码。

#### 2.2.3 OpenRouter 模型需要单独选定并验证

OpenRouter 是统一路由层，不等于某个固定模型。本项目初始 Demo 已选定 `openai/gpt-5-mini`，但应用代码仍必须从 `LLM_MODEL` 读取，不能硬编码。该模型配置必须满足：

- 支持 `tools` / Tool Calling；
- 能稳定返回 OpenAI 兼容的 assistant tool-call message；
- 支持项目所需的上下文长度；
- 价格、延迟和可用性符合演示要求；
- 首选非推理或低推理配置，并使用 `temperature=0` 或模型允许的最低值。

初始 Demo 允许 OpenRouter 在上游 Provider 间自动路由，不固定某个上游 Provider；不主动启用 prompt logging，暂不强制 ZDR。架构应预留后续传入 Provider 与隐私路由选项的位置，但 Phase 5 第一版不增加这些配置的复杂逻辑。不要把 `auto` 模型或免费模型作为唯一方案；固定 `openai/gpt-5-mini` 完整模型 ID，并用三个核心问题做真实冒烟测试。可通过 OpenRouter Models API 的 `supported_parameters=tools` 核对能力；模型名、价格和能力可能变化，演示前应再次核对。

#### 2.2.4 RAG 缺少索引生命周期设计

原文描述了建库流程，但没有明确：

- 何时建立索引；
- 如何知道文档变了；
- 服务启动时是否重复建库；
- 索引和元数据如何对应；
- 没有达到相关度时如何拒答。

第一版采用最简单方案：通过独立脚本手动重建索引；后端启动时只加载已有索引；索引目录同时保存向量索引和 `metadata.json`；文档更新后重新运行脚本。

#### 2.2.5 Agent 输出契约还不够明确

Tool 的结果不能只返回随意的 `dict`，否则 Agent、API 和 UI 很快互相耦合。应统一为：

```text
ToolResult
├── success: bool
├── data: object | null
├── error_code: string | null
├── message: string
└── sources: Source[]
```

Chat API 再统一返回：

```text
ChatResponse
├── answer: string
├── traces: AgentTrace[]
├── sources: Source[]
└── audio_url: string | null
```

这样前端不需要理解每个工具内部实现。

#### 2.2.6 条件问题未定义执行策略

综合问题中有“如果已经发货”。模型可能一次同时调用两个工具，也可能先查订单再查政策。为了展示 Agent 能力，应允许多轮 Tool Calling，但在 system prompt 中明确：

- 先获取条件判断所需的事实；
- 再决定是否调用后续工具；
- 最多执行 5 轮；
- 同一个工具和相同参数不重复执行；
- 工具失败后停止依赖该结果的推断。

#### 2.2.7 RPA 与 Docker 存在复杂度冲突

本地 `headless=False` 最适合面试展示；容器中的有头 Chromium 则需要额外显示环境。第一版应把“本地演示”作为标准路径：

- 面试演示：本地运行，`RPA_HEADLESS=false`；
- 自动测试：本地或 CI，`RPA_HEADLESS=true`；
- Docker：只作为后置加分项，默认 `headless=true`。

不需要为容器中的可视浏览器投入时间。

#### 2.2.8 测试不能过度依赖真实 LLM

真实模型的 Tool 选择有概率波动，而且会产生费用。测试应分层：

- 纯函数和工具测试不调用 LLM；
- Agent Loop 使用假的 LLM 响应测试；
- 真实 OpenRouter 调用只保留少量手工冒烟测试；
- Playwright 完整浏览器测试可以标记为 integration。

#### 2.2.9 成本和密钥管理需要更明确

项目只使用模拟数据，但仍应做到：

- `.env` 不提交；
- `.env.example` 只放空值；
- 日志不打印 API Key 和完整请求头；
- 限制 Agent 步数和单次输出长度；
- TTS 默认按按钮生成，不对每条回答自动生成；
- 演示前准备少量 API 余额并完成真实联调。

---

## 3. 可行度评估

### 3.1 总体判断

在缩减范围后，方案可行度高。各模块都使用成熟 Python 库，模拟数据规模很小，不需要高性能基础设施。真正的难点有三个：

1. 正确实现 Tool Calling 消息循环；
2. 让 Playwright 选择器和等待逻辑稳定；
3. 让 RAG 返回可追踪来源，并在资料不足时拒绝编造。

这三个难点恰好也是最适合面试讲解的内容，因此值得保留。

### 3.2 复杂度与风险

| 模块 | 难度 | 主要风险 | 控制方法 |
| --- | --- | --- | --- |
| Mock ERP | 低 | 页面字段和 RPA 选择器不一致 | 给关键元素固定 `data-testid` |
| Calculator | 低 | 不安全执行表达式 | AST 白名单，不使用 `eval` |
| RAG | 中 | 中文检索效果、来源丢失 | 本地中文 Embedding、保留 metadata、固定测试题 |
| RPA | 中 | 页面等待、登录状态、浏览器环境 | 显式等待、清楚超时、每次关闭浏览器 |
| Tool Calling | 中 | 消息格式错误、死循环、重复调用 | 自写小循环、最大轮数、调用去重 |
| FastAPI | 低 | 错误直接变成 500 | 业务错误统一转响应模型 |
| Streamlit | 低到中 | 状态刷新、超时无反馈 | `session_state`、spinner、简单同步请求 |
| TTS | 低到中 | 外部服务不稳定 | 点击后生成、失败不影响文字回答 |
| Docker | 中 | Playwright 浏览器依赖 | 最后做，容器默认 headless |

### 3.3 推荐的完成边界

#### P0：必须完成

- Mock ERP 可登录、搜索和查看订单；
- Playwright 能查询存在和不存在的订单；
- 本地 PDF 能构建索引并检索来源；
- Calculator 安全计算四则运算和括号；
- 通过 OpenRouter 选定的模型能稳定选择三种工具；
- Agent 能完成 RPA + RAG 的多步调用；
- FastAPI 提供 `/health` 和 `/api/chat`；
- Streamlit 展示聊天、工具轨迹和来源；
- 核心单元测试通过；
- README 能让别人从零运行。

#### P1：建议完成

- 点击按钮后生成 TTS；
- Docker Compose 启动三个服务；
- Playwright 集成测试；
- 模型调用耗时和工具耗时日志；
- 一键初始化脚本；
- 演示截图或 GIF。

#### P2：有余力再做

- PDF 上传并重建索引；
- 保存聊天历史到数据库；
- 支持多个 LLM Provider；
- RAG 评测集和指标；
- Avatar 接口或视频生成；
- 流式回答。

明确不做：用户注册、RBAC、真实 ERP、真实支付、微服务治理、Redis、消息队列、Kubernetes、模型训练、多 Agent。

---

## 4. 最终推荐架构

### 4.1 运行时架构

```text
┌────────────────────────────────────────────────────────────┐
│ Streamlit :8501                                           │
│ 聊天记录 / 输入框 / 执行轨迹 / 来源 / TTS 按钮             │
└──────────────────────────┬─────────────────────────────────┘
                           │ HTTP JSON
                           v
┌────────────────────────────────────────────────────────────┐
│ FastAPI Backend :8000                                     │
│                                                            │
│ Chat API -> AgentService -> LLMClient (OpenRouter)         │
│                   │                                        │
│                   ├── search_company_docs                  │
│                   │      -> Retriever -> FAISS + metadata  │
│                   ├── query_order                           │
│                   │      -> Playwright                     │
│                   └── calculate -> safe AST evaluator      │
│                                                            │
│ Optional: TTSService -> audio file                         │
└──────────────────────────┬─────────────────────────────────┘
                           │ Browser automation
                           v
┌────────────────────────────────────────────────────────────┐
│ Mock ERP :8001                                            │
│ FastAPI + Jinja2 + sqlite3                                │
│ 登录 / 订单列表 / 搜索 / 详情                              │
└────────────────────────────────────────────────────────────┘
```

### 4.2 离线索引流程

```text
knowledge/*.pdf
  -> pypdf 提取每页文本
  -> 按字符递归切块
  -> 本地 BGE 中文模型生成向量
  -> FAISS 写入 data/vector_store/index.faiss
  -> 来源信息写入 data/vector_store/metadata.json
```

该流程通过命令手动执行，不放进每次后端启动过程，避免启动慢和重复下载模型。

### 4.3 模块职责

| 模块 | 只负责什么 | 不负责什么 |
| --- | --- | --- |
| `api` | HTTP 入参校验和响应转换 | Tool 选择、页面抓取 |
| `agent` | 维护消息、调用 LLM、分发工具、汇总轨迹 | 具体 RAG/RPA 实现 |
| `tools` | 校验参数并把内部服务包装成 Tool | HTTP 和 UI |
| `rag` | 文档、切块、向量、检索、来源 | Agent 消息循环 |
| `rpa` | 浏览器登录和订单查询 | 直接访问数据库 |
| `mock_erp` | 模拟遗留网页系统 | 给 Agent 提供捷径 API |
| `tts` | 文本生成音频 | 决定回答内容 |
| `frontend` | 展示和发请求 | 直接调用 LLM 或数据库 |

---

## 5. 技术选型

### 5.1 固定选型

| 类别 | 选择 | 选择理由 |
| --- | --- | --- |
| Python | 3.11 | 生态成熟，依赖兼容性好 |
| 后端 | FastAPI + Uvicorn | 类型清楚，易做 API 文档 |
| 数据校验 | Pydantic | 与 FastAPI 原生配合 |
| 配置 | pydantic-settings + `.env` | 配置集中且易解释 |
| Mock ERP | FastAPI + Jinja2 + sqlite3 | 依赖少、实现直观 |
| RPA | Playwright async API | 等待机制和现代浏览器支持好 |
| LLM 网关 | OpenRouter | 用一个 API Key 和统一端点访问多个模型 |
| LLM SDK | `openai` Python SDK | 指向 OpenRouter 的 OpenAI 兼容接口，代码简单且易替换 |
| 默认 LLM | 由 `LLM_MODEL` 指定 | 必须使用支持 Tool Calling 的完整 OpenRouter 模型 ID |
| PDF | pypdf | 足够处理自制的文本型 PDF |
| Embedding | `BAAI/bge-small-zh-v1.5` | 本地、中文、体积较小、无需按次付费 |
| 向量检索 | FAISS CPU | 小型本地项目简单直接 |
| 前端 | Streamlit | 快速展示 AI 交互和执行轨迹 |
| 测试 | pytest + pytest-asyncio | 适合 Python 和异步工具 |
| HTTP 客户端 | httpx | 测试 FastAPI、前端调用均方便 |

### 5.2 刻意不使用的技术

- 不用 LangChain/LangGraph：三个 Tool 的循环自己写更容易理解和讲解。
- 不用 SQLAlchemy：只有一张订单表，`sqlite3` 足够；以后需要复杂关系时再换。
- 不用 Chroma 服务：本地 FAISS 文件足够，减少一个服务和一层抽象。
- 不用 Celery/Redis：所有任务在 Demo 内可同步等待。
- 不用 React/Vue：Streamlit 足够展示项目价值。

### 5.3 成本方案

默认只有 LLM 对话产生 API 费用：

- LLM：OpenRouter 按所选模型计费；模型价格与路由策略在演示前确认；
- Embedding：本地模型，零调用费用；
- 向量库：本地 FAISS，零服务费用；
- ERP：本地模拟系统；
- 数据库：SQLite；
- TTS：P1 可先用 `edge-tts` 进行个人 Demo，或换成正式付费 TTS Provider。

`edge-tts` 是第三方 Python 客户端，并非正式 Azure 商业 API。它适合低成本个人演示，但服务端接口变化可能导致不稳定；如果简历演示要求更稳，应使用正式 TTS API，并仍通过 `TTSService` 接口隔离。

---

## 6. 建议目录结构

目录只保留真正会用到的文件，避免为了“看起来工程化”创建空模块：

```text
RAGAgent/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── chat.py
│   │   └── tts.py                 # P1
│   ├── agent/
│   │   ├── service.py             # Agent Loop
│   │   ├── prompts.py
│   │   ├── schemas.py
│   │   └── tool_registry.py
│   ├── tools/
│   │   ├── calculator.py
│   │   ├── knowledge.py
│   │   └── order.py
│   ├── rag/
│   │   ├── loader.py
│   │   ├── splitter.py
│   │   ├── embeddings.py
│   │   ├── vector_store.py
│   │   └── retriever.py
│   ├── rpa/
│   │   └── order_query.py
│   ├── llm/
│   │   └── client.py
│   ├── tts/
│   │   └── service.py             # P1
│   └── core/
│       ├── config.py
│       ├── errors.py
│       └── logging.py
├── mock_erp/
│   ├── app.py
│   ├── database.py
│   ├── seed.py
│   ├── templates/
│   │   ├── login.html
│   │   ├── orders.html
│   │   └── order_detail.html
│   └── static/
├── frontend/
│   └── streamlit_app.py
├── knowledge/
│   ├── company_intro.pdf
│   ├── refund_policy.pdf
│   ├── shipping_policy.pdf
│   └── product_manual.pdf
├── data/
│   ├── orders.db
│   ├── vector_store/
│   └── audio/                     # P1，生成文件不提交
├── scripts/
│   ├── seed_erp.py
│   └── build_index.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── .env.example
├── .gitignore
├── requirements.txt
├── docker-compose.yml            # P1
├── Dockerfile                    # P1
├── Readme.md
└── plan.md
```

不需要给每个目录都预先创建大量文件。进入对应阶段时再创建，保持每一步都能运行。

---

## 7. 核心数据契约

在开始业务实现前先确定这些契约，后续模块按契约连接。

### 7.1 Source

```text
file: str          # refund_policy.pdf
page: int | null   # PDF 页码，从 1 开始
chunk_id: str      # refund_policy-p1-c2
content: str       # 命中的原文片段
score: float       # 相似度，只用于调试或 UI 展示
```

### 7.2 ToolResult

```text
success: bool
data: dict | null
error_code: str | null
message: str
sources: list[Source]
```

错误码至少包括：

- `INVALID_ARGUMENT`
- `ORDER_NOT_FOUND`
- `ERP_LOGIN_FAILED`
- `RPA_TIMEOUT`
- `RAG_NOT_READY`
- `NO_RELEVANT_DOCUMENT`
- `CALCULATION_ERROR`
- `TOOL_INTERNAL_ERROR`

### 7.3 AgentTrace

```text
step: int
type: agent | tool_start | tool_result | error
name: str | null
summary: str
duration_ms: int | null
```

不要把完整 prompt、API Key、浏览器密码或大段文档写进 trace。

### 7.4 ChatResponse

```text
answer: str
traces: list[AgentTrace]
sources: list[Source]
audio_url: str | null
request_id: str
```

第一版不返回 token 流。`audio_url` 默认是 `null`，用户点击 TTS 后再单独调用接口。

---

## 8. 分阶段实施步骤

每个阶段都遵守同一规则：先写最小实现，再写对应测试，再手工验收，最后记录自己能否解释。上一阶段未通过，不进入下一阶段。

### Phase 0：项目骨架与运行环境

#### 目标

建立最小可运行工程，不实现业务功能。

#### 具体步骤

1. 确认使用 Python 3.11，并创建虚拟环境。
2. 创建最小目录：`app/`、`mock_erp/`、`frontend/`、`tests/`、`scripts/`、`knowledge/`、`data/`。
3. 创建 `requirements.txt`，初期只加入当前阶段依赖；不要一次加入所有可选库。
4. 创建 `.gitignore`，忽略 `.env`、`.venv`、`__pycache__`、SQLite 数据库、向量索引、音频和测试缓存。
5. 创建 `.env.example`，只放配置名和安全默认值。
6. 实现配置对象，启动时校验必要配置；只有实际调用 LLM 时才强制要求 API Key，使 ERP 和本地测试可独立运行。
7. 实现基础日志格式：时间、级别、模块、request_id、消息。
8. 建立最小 FastAPI 应用和 `GET /health`。
9. 写第一个健康检查测试。

#### 验收

- `uvicorn app.main:app --reload --port 8000` 可启动；
- `/health` 返回 `{"status": "ok"}`；
- 缺少 `.env` 时，非 LLM 功能仍可启动；
- 测试可以独立运行。

#### 需要理解

- 虚拟环境解决什么问题；
- FastAPI 路由、Pydantic 模型和 Uvicorn 的关系；
- 为什么配置不应该散落在业务代码中。

### Phase 1：Mock ERP

#### 目标

人工能通过网页登录并查询订单，为 RPA 提供稳定目标。

#### 具体步骤

1. 定义单张 `orders` 表，采用原 README 的字段；时间用 ISO 格式字符串即可。
2. 使用 `sqlite3` 封装三个最小函数：初始化表、按订单号查询、列出订单。
3. Seed 固定的 20 条数据，不使用完全随机数据，保证重复初始化结果一致。
4. 重点准备以下订单：
   - `10001`：已发货，包含物流公司、单号和发货时间；
   - `10002`：处理中，没有物流；
   - `10003`：已完成且超过 30 天；
   - `10004`：已退款；
   - 其余数据覆盖其他状态。
5. Seed 采用“存在则更新或先清表再插入”的明确策略，保证可重复执行。
6. 实现登录页，凭证从环境变量读取；登录成功后写入简单 session cookie。
7. 实现订单列表、订单号搜索和详情页。
8. 给 RPA 会操作的元素加稳定属性，例如：
   - `data-testid="username"`
   - `data-testid="password"`
   - `data-testid="login-submit"`
   - `data-testid="order-search"`
   - `data-testid="order-row-10001"`
9. 详情字段使用固定 `data-testid`，不要让 RPA 解析整页自然语言。
10. 页面只做简单 CSS，保证清楚、整齐和适合录屏，不做复杂前端框架。
11. 对错误登录、空搜索和不存在订单给出可见提示。

#### 验收

- 可使用配置中的账号密码登录；
- 可搜索 `10001` 并看到完整物流信息；
- 可搜索不存在的订单并看到“未找到”；
- 未登录直接访问订单页会回到登录页；
- 重复运行 seed 不会制造重复订单。

#### 需要理解

- 为什么模拟 ERP 仍然有业务价值；
- 为什么真实项目有 API 时应优先 API；
- 为什么 RPA 需要稳定选择器而不是依赖页面文字或 CSS 层级。

### Phase 2：Playwright RPA

#### 目标

通过真实浏览器页面完成查询，不直接读取 SQLite。

#### 具体步骤

1. 安装 Playwright 和 Chromium。
2. 只创建一个公开函数 `async query_order(order_no: str) -> ToolResult`。
3. 先校验订单号：去除空格、不能为空、限制合理长度，不接受任意脚本内容。
4. 启动浏览器时从配置读取 `RPA_HEADLESS` 和超时时间。
5. 每次查询创建 browser/context/page；第一版不做浏览器池和登录复用。
6. 按顺序完成：打开登录页、填写凭证、提交、确认登录成功、搜索订单、打开详情、读取字段。
7. 使用 `data-testid` 定位，并使用 Playwright 的显式等待，不使用固定 `sleep`。
8. 将页面文本转换为统一订单字典；金额转换为数值，空物流字段转换为 `null`。
9. 在 `finally` 中关闭浏览器，避免异常后残留进程。
10. 将超时、登录失败、不存在订单和页面结构变化分别映射为错误码。
11. 日志记录关键动作和耗时，但不记录密码。
12. 开发演示默认 `headless=false`，自动测试默认 `true`。

#### 验收

- 查询 `10001` 返回正确状态和物流；
- 查询 `10002` 返回处理中且物流为空；
- 查询不存在订单返回 `ORDER_NOT_FOUND`；
- 密码错误返回 `ERP_LOGIN_FAILED`；
- ERP 未启动时返回明确错误而不是未处理堆栈；
- 执行完成后浏览器进程正常关闭。

#### 测试

- 参数校验单元测试；
- 针对正在运行的 Mock ERP 写 2 至 3 个集成测试；
- 集成测试加 marker，默认单元测试不强制启动浏览器。

#### 需要理解

- Playwright 自动执行的是代码，不是 LLM；
- Agent 只决定何时调用工具；
- RPA 为何比数据库/API 查询慢且更脆弱。

### Phase 3：安全 Calculator 与工具统一层

#### 目标

建立第一个无外部依赖的 Tool，并确定所有 Tool 的调用规范。

#### 具体步骤

1. 使用 Python `ast.parse(..., mode="eval")` 解析表达式。
2. 白名单只允许数字、括号、加减乘除、取模和有限的幂运算。
3. 禁止名称、属性访问、函数调用、列表、字典和字符串。
4. 限制表达式长度、数字大小和幂指数，避免超大计算。
5. 除零和非法语法转换为 `CALCULATION_ERROR`。
6. 创建 Tool Registry：工具名映射到输入模型、说明和执行函数。
7. 工具分发时再次用 Pydantic 校验 LLM 给出的参数。
8. 未知工具返回明确错误，不动态导入或执行任意函数。

#### 验收

- `1280 * 0.8` 返回 `1024`；
- 括号和基础四则运算正确；
- `__import__`、函数调用和属性访问被拒绝；
- 未知工具和错误参数不会导致 Agent 崩溃。

#### 需要理解

- `eval` 的安全风险；
- JSON Schema/Pydantic 如何约束模型输出；
- 模型提出 Tool Call 与程序执行 Tool 的区别。

### Phase 4：RAG 离线索引

#### 目标

从本地 PDF 建立可持久化、可追踪来源的中文向量索引。

#### 具体步骤

1. 编写四份短而明确的企业文档，每份 1 至 3 页；所有内容均为模拟信息。
2. 确保 PDF 是文本型 PDF，而不是扫描图片；第一版不做 OCR。
3. 每份政策包含可区分的规则和边界，例如已发货、已完成超过 30 天、处理时间。
4. Loader 按页提取文本，保留文件名和页码；空页跳过并记录 warning。
5. Splitter 使用简单的递归字符切块：优先按段落、句号再按字符截断。
6. 初始参数建议：`chunk_size=500`、`chunk_overlap=80`；这些值放配置中。
7. 为每个 chunk 生成稳定 ID，并保存：文件、页码、chunk_id、content。
8. 使用 `BAAI/bge-small-zh-v1.5` 本地生成向量并做归一化。
9. 使用 FAISS 保存向量；用 JSON 保存顺序完全对应的 metadata。
10. 保存一份 `manifest.json`，记录 embedding 模型名、维度、切块参数、文档清单和构建时间。
11. 后端加载索引时校验向量数量和 metadata 数量一致。
12. 索引缺失时返回 `RAG_NOT_READY`，提示先运行构建脚本。

#### 检索策略

1. 用户查询先转成同一模型的向量；
2. 检索 `top_k=3`；
3. 返回相似度最高的 chunks；
4. 第一版阈值不要凭感觉写死，先用固定测试问题观察分数；
5. 根据相关与无关问题的分数分布设置配置阈值；
6. 低于阈值时返回 `NO_RELEVANT_DOCUMENT`；
7. RAG Tool 只返回检索上下文和来源，最终自然语言由 Agent 生成，避免额外调用一次 LLM。

#### 验收问题

- “退款多久到账？”命中退款政策；
- “已发货还能退款吗？”命中退货与退款条款；
- “默认有哪些物流公司？”命中物流政策；
- “公司创立于什么时候？”命中公司介绍；
- “公司的年假有几天？”在资料不存在时明确无法确认。

#### 测试

- PDF 能提取文本；
- chunk 不为空且 metadata 完整；
- 构建后可重新加载；
- 固定问题的 Top-3 中出现预期文件；
- 无关问题不会伪装成确定答案。

#### 需要理解

- Embedding、向量相似度、Chunk 和 Top-K 的含义；
- 为什么来源 metadata 必须从切块开始保留；
- RAG 为什么只能降低幻觉，不能彻底消除幻觉。

### Phase 5：LLM Client 与 Agent Loop

#### 目标

让 LLM 在三个工具之间选择，并可靠执行多轮调用。

#### 具体步骤

1. 创建 `LLMClient`，配置 API Key、base URL、model、timeout 和最大重试次数。
2. 使用 OpenAI SDK 调用 OpenRouter 的 OpenAI 兼容接口，业务层不直接初始化 SDK Client。
3. 启动或首次调用时校验 `OPENROUTER_API_KEY` 和 `LLM_MODEL` 非空；模型 ID 不合法或不支持 Tool Calling 时给出明确配置错误。
4. 将 Tool Registry 转换为 API 需要的工具 JSON Schema。综合条件问题默认设置 `parallel_tool_calls=false`，引导模型先查订单事实，再决定是否查政策；若所选模型不支持该参数，则依靠 prompt 和 Agent Loop 保证顺序。
5. 编写简洁 system prompt，说明：
   - 政策问题调用知识库；
   - 订单事实必须调用 ERP；
   - 数学问题调用 calculator；
   - 工具失败不得编造；
   - 来源不足要说明无法确认；
   - 条件问题先查条件再决定下一步；
   - 回答用中文并保持简洁。
6. Agent Loop 的单轮流程：发送 messages 和 tools，读取 assistant message。
7. 若无 tool calls，返回最终答案。
8. 若有 tool calls，先把完整 assistant tool-call message 加入历史。
9. 对每个 Tool Call：解析 JSON、校验输入、执行工具、序列化 ToolResult，并以对应 `tool_call_id` 回传。
10. 将工具来源累积到最终 `sources`，按 `file + page + chunk_id` 去重。
11. 将每一步转换为安全、简短的 AgentTrace。
12. 最多执行 `MAX_AGENT_STEPS=5`；超限时返回可理解错误。
13. 记录已经执行的 `tool_name + normalized_arguments`；相同调用重复出现时阻止死循环。
14. LLM 网络错误只做 1 至 2 次短重试；Tool 本身不要被 Agent 无限制重试。
15. 分别映射 OpenRouter 的鉴权失败、余额不足、限流、上游 Provider 错误和超时；只对限流、临时上游错误和网络错误做有限重试。
16. 对最终答案为空、返回未知工具或参数 JSON 错误分别处理。
17. 记录请求耗时、响应中的模型名和 token usage；不得记录 API Key、Authorization header 或完整业务 prompt。

#### 多工具场景的预期流程

```text
用户：查询订单 10001，如果已经发货，告诉我物流信息，
      同时根据退款政策告诉我是否还能申请退款。

第 1 轮：LLM -> query_order(10001)
工具结果：已发货 + 物流信息

第 2 轮：LLM -> search_company_docs(已发货订单退款政策)
工具结果：政策 chunks + sources

第 3 轮：LLM -> 最终中文答案
```

如果模型偶尔在第一轮同时调用两个独立工具，也可以正确执行；但条件分支的 prompt 应引导它优先查询订单。

#### 验收

- 订单问题只调用 `query_order`；
- 政策问题只调用 `search_company_docs`；
- 计算问题调用 `calculate`；
- 综合问题能完成至少两个工具并给出来源；
- 不存在订单时不编造物流；
- 知识库无答案时明确说明无法从资料确认；
- 重复调用和超过最大轮数都有可理解错误。

#### 测试

- 用 Fake LLM 构造“直接回答、单工具、多工具、错误参数、重复工具、超限”响应；
- Tool Registry 使用假的工具函数，测试消息循环而不是外部系统；
- 真实 OpenRouter 只做手工或可选 integration test，避免每次测试付费和波动。

#### 需要理解

- Tool schema 为什么只是描述，不会自动执行函数；
- 为什么工具结果必须再次发给 LLM；
- Agent 与固定 Workflow 的差异；
- 最大步数和去重如何防止死循环。

### Phase 6：FastAPI Chat API

#### 目标

通过稳定 HTTP 契约暴露 Agent 能力。

#### 具体步骤

1. 实现 `POST /api/chat`，请求体只需要 `message`，可选 `session_id` 暂不持久化。
2. 限制空消息和过长消息。
3. 为每个请求生成 `request_id`，贯穿日志、trace 和响应。
4. 调用 AgentService，转换为 `ChatResponse`。
5. 业务可预期错误返回正常结构和合适状态码；真正未知异常记录堆栈但不给前端暴露内部信息。
6. 第一版每个请求独立，不保留多轮聊天上下文；UI 可以显示历史，但 Agent 只处理当前问题。
7. OpenAPI 文档中提供三个核心问题示例。
8. 设置明确超时预期：RPA 会比普通问答慢，前端 HTTP timeout 应高于 RPA timeout。

#### 为什么第一版不做会话记忆

三个核心演示都是单次完整问题。会话记忆会引入 token 增长、上下文裁剪、session 存储和“上一轮订单号”解析，不是核心简历价值。后续可以在 P2 添加。

#### 验收

- `/docs` 可调用接口；
- 三个核心问题返回统一结构；
- sources 和 traces 能被 JSON 正确序列化；
- Tool 失败时 API 不返回无信息的 500；
- 日志能用 request_id 找到一次完整调用。

### Phase 7：Streamlit 前端

#### 目标

把核心技术过程直观展示给面试官。

#### 页面布局

```text
顶部：项目标题 + 服务状态
左侧主区：聊天历史、输入框、示例问题按钮
右侧边栏：本次 Agent 执行轨迹
回答下方：来源折叠面板、TTS 按钮（P1）
```

#### 具体步骤

1. 前端只通过 HTTP 调 FastAPI，不导入 Agent、RAG 或 RPA 模块。
2. 使用 `st.session_state` 保存界面聊天历史。
3. 提供三个示例问题按钮，确保面试时无需手打长问题。
4. 请求过程中显示 spinner，例如“Agent 正在查询 ERP…”；第一版无需实时更新步骤。
5. 回答完成后展示 traces：步骤号、工具名、成功/失败、耗时。
6. sources 默认折叠，显示文件、页码和命中片段，避免页面过长。
7. 订单、知识库和模型错误转成面向用户的短提示。
8. 页面明确标注“所有订单和公司资料均为模拟数据”。
9. 不做登录、不做复杂 CSS、不做动态图表。
10. 检查窄屏和常用笔记本分辨率下是否仍清楚。

#### 验收

- 三个示例按钮都能完成调用；
- 多工具问题能看见两个工具步骤；
- RAG 回答能展开来源；
- 后端关闭时前端显示连接错误；
- 重复提问不会丢失之前的 UI 历史。

#### 需要理解

- Streamlit 刷新模型和 `session_state`；
- 为什么 UI 历史不等于 LLM 会话记忆；
- 为什么执行轨迹比复杂视觉设计更能体现项目价值。

### Phase 8：TTS（P1）

#### 目标

按需把已生成回答转换为音频，失败不影响核心回答。

#### 具体步骤

1. 定义最小 `TTSService.synthesize(text) -> audio_path` 接口。
2. 第一版选择一个 Provider，不做多 Provider 管理后台。
3. 添加 `POST /api/tts`，限制文本长度，只接受已有回答的合理长度。
4. 文件名使用 UUID，保存在 `data/audio/`。
5. FastAPI 安全暴露音频静态路径。
6. Streamlit 在每条 AI 回答下提供“生成语音”按钮，而不是自动生成。
7. 成功后使用 `st.audio`；失败仅显示提示，不改变文字答案。
8. 提供简单清理策略，例如启动时删除过旧音频；不要无限增长。

#### 验收

- 中文回答可生成并播放；
- 同一按钮重复点击行为明确；
- TTS 超时或失败不影响聊天；
- 空文本和超长文本被拒绝。

#### 后续 Avatar

README 中只需说明 TTS 输出可作为数字人服务输入。不要为了一个未使用的接口创建大量抽象类或假实现。

### Phase 9：测试、日志与演示稳定性

#### 目标

把“偶尔能跑”提升为“面试时稳定能跑”。

#### 测试分层

1. 单元测试：Calculator、切块、配置、Tool Registry、Agent Loop。
2. RAG 集成测试：真实小索引和固定问题，不调用 LLM。
3. RPA 集成测试：真实 Mock ERP + headless Chromium。
4. API 测试：依赖注入 Fake Agent，验证请求响应。
5. 手工端到端测试：真实 OpenRouter 模型 + ERP + RAG + Streamlit。

#### 必测清单

- 正常订单 `10001`；
- 未发货订单 `10002`；
- 不存在订单；
- 退款政策命中；
- 无关政策拒答；
- 正常计算、除零、恶意表达式；
- Tool 参数错误；
- LLM 超时；
- RPA 超时；
- 最大 Agent 步数；
- 综合问题完成两个工具；
- 来源去重。

#### 日志要求

- 每个 chat 请求有 request_id；
- 记录 LLM 调用轮数和耗时；
- 记录工具名、成功状态和耗时；
- RPA 记录页面阶段，不记录密码；
- RAG 记录 top_k、命中文件和分数；
- 错误日志保留堆栈；
- 不记录 API Key、Authorization header 和全部 prompt。

#### 演示前检查脚本/清单

1. API 余额可用；
2. 网络可访问模型服务；
3. Chromium 已安装；
4. ERP 数据已 seed；
5. 向量索引已构建；
6. 端口 8000、8001、8501 未被占用；
7. `.env` 配置正确；
8. 三个示例问题各运行一次；
9. 准备一段录屏，现场网络异常时仍能说明项目；
10. 准备纯文字回答路径，TTS 故障时跳过即可。

### Phase 10：Docker 与交付（P1）

#### 目标

展示基础容器化，不追求生产级镜像和编排。

#### 具体步骤

1. 核心功能本地稳定后再创建 Dockerfile。
2. Compose 包含 backend、mock-erp、frontend 三个服务。
3. 通过服务名访问，例如 backend 使用 `http://mock-erp:8001`。
4. 向量索引、SQLite 和 audio 使用挂载目录。
5. API Key 通过环境变量注入，不写进镜像。
6. Playwright 容器使用官方兼容镜像或完整安装浏览器依赖。
7. 容器模式固定 `RPA_HEADLESS=true`。
8. 为 ERP 和 backend 添加 healthcheck，frontend 等待 backend 可用。
9. README 同时保留本地运行和 Docker 运行两种方式。

#### 验收

- `docker compose up --build` 能启动三个服务；
- 容器中 RPA 可访问 mock-erp；
- 重启后 seed 和索引行为明确；
- 密钥未进入镜像层和仓库；
- 明确说明有头浏览器演示仍推荐本地运行。

如果 Docker 中的 Playwright 花费过多时间，可以只提交经过说明的 Dockerfile/Compose，并把本地运行作为正式演示路径；不要让 Docker 阻塞项目完成。

### Phase 11：README、简历和面试材料

#### README 最终结构

1. 一句话项目介绍；
2. 演示 GIF/截图；
3. 核心功能；
4. 架构图；
5. 技术选型及取舍；
6. 三个演示问题；
7. 本地安装与运行；
8. Docker 运行（若完成）；
9. 配置说明；
10. 测试命令；
11. 已知限制；
12. 后续扩展。

#### 简历描述必须与实际实现一致

建议完成 P0 后使用如下表述：

```text
基于 FastAPI 与 OpenRouter Tool Calling 实现企业 AI 助手，
设计可解释的 Agent Loop，支持知识库检索、ERP 查询和安全计算工具的动态选择与多步调用。

使用 pypdf、中文 Embedding 与 FAISS 构建本地 RAG，
支持 PDF 切块、语义检索、相关性过滤及文件/页码来源引用。

使用 Playwright 自动登录模拟 ERP 并查询订单与物流信息，
通过统一 ToolResult、错误码和执行轨迹将 RPA 结果安全返回 Agent。

使用 Streamlit 展示聊天、工具调用轨迹和检索来源，
并通过单元测试与端到端演示覆盖核心多工具场景。
```

只有真正完成 TTS 或 Docker 后，才把它们加入简历描述。

---

## 9. 推荐配置项

```env
# LLM
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openai/gpt-5-mini
LLM_TEMPERATURE=0
LLM_PARALLEL_TOOL_CALLS=false
LLM_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=1
LLM_MAX_OUTPUT_TOKENS=1000
OPENROUTER_HTTP_REFERER=http://localhost:8501
OPENROUTER_APP_TITLE=AI Digital Employee Demo
MAX_AGENT_STEPS=5

# RAG
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
KNOWLEDGE_DIR=./knowledge
VECTOR_DB_PATH=./data/vector_store
CHUNK_SIZE=500
CHUNK_OVERLAP=80
RAG_TOP_K=3
RAG_SCORE_THRESHOLD=0.45

# Mock ERP / RPA
MOCK_ERP_URL=http://localhost:8001
MOCK_ERP_USERNAME=admin
MOCK_ERP_PASSWORD=admin123
RPA_HEADLESS=false
RPA_TIMEOUT_MS=15000

# Application
BACKEND_URL=http://localhost:8000
LOG_LEVEL=INFO
AUDIO_DIR=./data/audio
```

`RAG_SCORE_THRESHOLD` 初期留空，通过固定测试集观察分数后再填写，不应复制其他模型的阈值。

---

## 10. 推荐开发顺序与里程碑

| 里程碑 | 包含阶段 | 可展示结果 | 是否可写简历 |
| --- | --- | --- | --- |
| M1 | Phase 0-2 | 浏览器自动登录 ERP 并查询订单 | 可作为 RPA 小 Demo |
| M2 | Phase 3-4 | 安全计算 + PDF 语义检索和来源 | 可作为 RAG 小 Demo |
| M3 | Phase 5-7 | 完整 Agent 多工具链路和 UI | **达到项目核心完成标准** |
| M4 | Phase 8-9 | TTS、测试、日志、稳定性 | 简历内容更完整 |
| M5 | Phase 10-11 | Docker、README、录屏、面试材料 | 项目交付完成 |

建议每次只推进一个里程碑。M3 前不做 TTS 和 Docker，M3 完成后先录制一版可用 Demo，再继续增强。

---

## 11. 最终验收用例

### 用例 A：RAG

输入：

```text
公司的退款政策是什么？
```

必须满足：

- 调用 `search_company_docs`；
- 不调用订单工具；
- 回答只基于命中文档；
- 展示 `refund_policy.pdf` 和页码；
- trace 中能看到检索成功。

### 用例 B：RPA

输入：

```text
帮我查询订单 10001。
```

必须满足：

- 调用 `query_order`；
- 面试模式可看到浏览器操作；
- 返回状态、物流公司、物流单号和发货时间；
- 不编造政策内容。

### 用例 C：Calculator

输入：

```text
订单金额 1280 元，如果退款 80%，需要退款多少钱？
```

必须满足：

- 调用 `calculate`；
- 结果为 1024 元；
- 不执行任何非数学表达式。

### 用例 D：多工具核心场景

输入：

```text
查询订单 10001，如果已经发货，告诉我物流信息，
同时根据公司的退款政策告诉我是否还能申请退款。
```

必须满足：

- 查询 ERP；
- 检索退款政策；
- trace 中至少显示两个工具；
- 最终答案区分“订单事实”和“政策依据”；
- 展示政策来源；
- 任一工具失败时不伪造对应结论。

### 用例 E：失败保护

分别测试：

- 不存在订单；
- ERP 关闭；
- 向量索引缺失；
- 问知识库中没有的内容；
- OpenRouter API Key 无效或账户余额不足；
- Calculator 恶意表达式；
- Agent 重复调用同一工具。

每种情况都必须向用户说明问题，且服务不崩溃。

---

## 12. 面试时应能独立讲清楚的实现主线

建议按下面顺序讲，而不是逐个罗列框架名：

1. 为什么选择“企业数字员工”这个场景；
2. 一个普通聊天模型为什么不能知道实时订单；
3. Tool Calling 中模型只负责选择，Python 程序负责真正执行；
4. 为什么旧 ERP 用 Playwright，而有 API 时会优先 API；
5. RAG 如何从 PDF 变成 chunks、向量和来源；
6. 为什么工具结果要再次发送给模型；
7. 多工具问题如何经过多轮 Agent Loop；
8. 最大步数、参数校验、拒答和错误码如何降低风险；
9. 为什么选择本地 Embedding 和低价 LLM；
10. 为什么没有使用 LangChain、多 Agent、Redis 等复杂组件；
11. 当前限制是什么，未来会如何扩展。

如果不能用自己的话解释某个模块，就优先简化该模块，而不是继续增加功能。

---

## 13. 资料与版本说明

以下选型在真正开始对应阶段前应再次核对版本：

- OpenRouter Quickstart 与 OpenAI SDK 兼容调用：<https://openrouter.ai/docs/quickstart>
- OpenRouter Tool Calling：<https://openrouter.ai/docs/guides/features/tool-calling>
- OpenRouter 模型列表与能力过滤：<https://openrouter.ai/docs/guides/overview/models>
- BGE 中文 Embedding 模型卡：<https://huggingface.co/BAAI/bge-small-zh-v1.5>
- Sentence Transformers 语义检索说明：<https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html>
- edge-tts 项目：<https://github.com/rany2/edge-tts>

模型名称、价格和第三方服务可用性会变化，因此配置必须可替换，README 不应把某个价格写成永久承诺。

---

## 14. 最终决策摘要

本项目的最佳实现路线不是把原 README 的所有条目全部做完，而是先完成一条稳定、可解释的端到端链路：

```text
OpenRouter Tool Calling
  + 本地中文 RAG / FAISS
  + Playwright Mock ERP
  + 安全 Calculator
  + FastAPI
  + Streamlit 执行轨迹
```

这套范围已经能证明 Python 后端、LLM Tool Calling、Agent、RAG、向量检索、RPA、API 设计、错误处理和基础测试能力。TTS 与 Docker是加分项，不应成为核心项目完成的前置条件。整个实现过程中，应优先保证每个阶段能单独运行、测试和讲解，并为后续替换模型、增加文档或增加工具保留清楚接口，而不是提前建设复杂平台。
