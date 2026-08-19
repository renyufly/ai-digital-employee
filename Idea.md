# AI Digital Employee / AI Office Assistant Demo

## 1. 项目目标

本项目是一个用于面试展示的 **AI 数字员工 / AI 办公助手 Demo**。

目标不是开发完整商业产品，而是在较短时间内完成一个可运行、可演示、结构清晰的 AI 应用，用于证明以下技术能力：

- Python
- FastAPI
- GPT-4o / OpenAI API
- LLM Tool Calling / Function Calling
- Agent
- RAG
- Embedding
- Vector Database
- Playwright RPA
- TTS
- Streamlit
- SQLite
- 基础 Docker 化
- 基础工程化与模块化设计

核心演示场景：

> 用户通过自然语言向 AI 数字员工提出业务问题，Agent 自动判断应该查询企业知识库、操作 ERP 系统还是调用计算工具，并在获得结果后综合回答，最后通过 TTS 将回答转换为语音。

------

# 2. Demo 核心场景

重点实现以下三个 Tool。

## 2.1 企业知识库查询

用户：

> 公司的退款政策是什么？

Agent 自动调用：

```python
search_company_docs(query="退款政策")
```

系统：

```text
问题
↓
Embedding
↓
Vector Search
↓
获取 Top-K 文档 Chunk
↓
GPT-4o
↓
生成回答
↓
返回引用来源
```

示例输出：

```text
根据公司的退款政策：

1. 退款申请提交后需要经过审核；
2. 审核时间通常为 1-2 个工作日；
3. 审核通过后，退款会在 3-5 个工作日内原路返回。

来源：
refund_policy.pdf
```

------

## 2.2 RPA 查询订单

用户：

> 帮我查询订单 10001。

Agent 自动调用：

```python
query_order(order_no="10001")
```

该 Tool 不直接查询数据库，而是使用 Playwright 操作 Mock ERP：

```text
打开浏览器
↓
访问 ERP 登录页
↓
填写用户名密码
↓
登录
↓
进入订单管理
↓
输入订单号
↓
点击查询
↓
读取订单状态与物流信息
↓
返回给 Agent
```

最终回答：

```text
订单 10001 已经发货。

物流公司：顺丰
物流单号：SF123456789
发货时间：2026-08-18 13:20
```

------

## 2.3 Calculator

用户：

> 订单金额 1280 元，如果退款 80%，需要退款多少钱？

Agent 自动调用：

```python
calculate(expression="1280 * 0.8")
```

Tool 返回：

```text
1024
```

LLM 最终生成自然语言回答：

```text
该订单按照 80% 的退款比例计算，需要退款 1024 元。
```

------

# 3. 最终综合演示场景

项目最终必须支持一个能够体现 Agent 多工具调用能力的问题：

> 查询订单 10001，如果已经发货，告诉我物流信息，同时根据公司的退款政策告诉我是否还能申请退款。

理想执行流程：

```text
用户
↓
GPT-4o Agent
↓
识别需要订单信息
↓
调用 query_order
↓
Playwright 操作 Mock ERP
↓
获得订单状态和物流信息
↓
Agent 判断还需要退款政策
↓
调用 search_company_docs
↓
RAG 检索退款政策
↓
获得相关文档 Chunk
↓
GPT-4o 综合两个 Tool 的结果
↓
生成最终回答
↓
TTS
↓
语音播放
```

示例：

```text
订单 10001 当前已经发货。

物流公司为顺丰，物流单号为 SF123456789。

根据公司的退款政策，已发货订单仍然可以申请退款，
但需要先完成退货流程，商品退回并审核通过后，
退款会在 3-5 个工作日内原路返回。
```

------

# 4. 系统整体架构

```text
                      ┌──────────────────┐
                      │      用户         │
                      │   文字 / 语音     │
                      └────────┬─────────┘
                               │
                               ↓
                      ┌──────────────────┐
                      │    Streamlit      │
                      │     Frontend      │
                      └────────┬─────────┘
                               │
                               ↓
                      ┌──────────────────┐
                      │     FastAPI       │
                      │      Backend      │
                      └────────┬─────────┘
                               │
                               ↓
                      ┌──────────────────┐
                      │   GPT-4o Agent    │
                      │ Tool Selection    │
                      └────────┬─────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ↓                    ↓                    ↓
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│       RAG       │  │       RPA       │  │    Calculator   │
│ Knowledge Base  │  │   Playwright    │  │      Tool       │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
                              ↓
                     ┌─────────────────┐
                     │     GPT-4o      │
                     │ Final Response  │
                     └────────┬────────┘
                              │
                              ↓
                     ┌─────────────────┐
                     │       TTS       │
                     │ Text → Speech   │
                     └────────┬────────┘
                              │
                              ↓
                          用户播放
```

------

# 5. 推荐技术栈

后端：

```text
Python 3.11+
FastAPI
Pydantic
Uvicorn
```

LLM：

```text
OpenAI API
GPT-4o
Tool Calling / Function Calling
```

RAG：

```text
OpenAI Embeddings
FAISS 或 Chroma
PyPDF / pypdf
可选 LangChain
```

建议：

第一版可以使用 LangChain 辅助文档加载和向量库管理，但是尽量保留自己实现的核心逻辑，包括：

```text
Chunk
Embedding
Retriever
Prompt Construction
Tool Calling Loop
```

不要完全隐藏在高级框架内部。

RPA：

```text
Playwright
```

Mock ERP：

```text
FastAPI
Jinja2
SQLite
SQLAlchemy（可选）
```

前端：

```text
Streamlit
```

TTS：

```text
OpenAI TTS 或其他 TTS API
```

部署：

```text
Docker
Docker Compose
```

------

# 6. 项目目录

建议严格按照模块化方式组织：

```text
ai-digital-employee/

├── app/
│   ├── main.py
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── prompts.py
│   │   ├── tools.py
│   │   └── schemas.py
│   │
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   ├── splitter.py
│   │   ├── embedding.py
│   │   ├── vector_store.py
│   │   └── retriever.py
│   │
│   ├── rpa/
│   │   ├── __init__.py
│   │   ├── browser.py
│   │   ├── login.py
│   │   └── order_query.py
│   │
│   ├── tts/
│   │   ├── __init__.py
│   │   └── tts_service.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── chat.py
│   │   ├── knowledge.py
│   │   └── tts.py
│   │
│   └── core/
│       ├── config.py
│       └── logging.py
│
├── mock_erp/
│   ├── app.py
│   ├── database.py
│   ├── models.py
│   ├── seed.py
│   │
│   ├── templates/
│   │   ├── login.html
│   │   ├── orders.html
│   │   └── order_detail.html
│   │
│   └── static/
│
├── frontend/
│   └── streamlit_app.py
│
├── knowledge/
│   ├── company_intro.pdf
│   ├── refund_policy.pdf
│   ├── shipping_policy.pdf
│   └── product_manual.pdf
│
├── data/
│   ├── orders.db
│   └── vector_store/
│
├── tests/
│   ├── test_agent.py
│   ├── test_rag.py
│   ├── test_rpa.py
│   └── test_tools.py
│
├── scripts/
│   ├── init_vector_db.py
│   └── seed_erp.py
│
├── .env.example
├── .gitignore
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
└── README.md
```

------

# 7. Mock ERP

需要开发一个简单的模拟企业订单管理系统。

地址：

```text
http://localhost:8001
```

登录页：

```text
用户名：admin
密码：admin123
```

订单列表至少包含：

```text
订单号
客户名称
金额
订单状态
物流公司
物流单号
创建时间
发货时间
```

SQLite 表：

```sql
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no TEXT UNIQUE NOT NULL,
    customer_name TEXT NOT NULL,
    amount REAL NOT NULL,
    status TEXT NOT NULL,
    shipping_company TEXT,
    tracking_number TEXT,
    created_at TEXT,
    shipped_at TEXT
);
```

初始化 20-30 条模拟数据。

订单状态建议包含：

```text
待付款
处理中
已发货
已完成
已退款
已取消
```

------

# 8. Playwright RPA

实现：

```python
async def query_order(order_no: str) -> dict:
    ...
```

执行逻辑：

```text
1. 启动 Chromium
2. 打开 Mock ERP
3. 登录
4. 进入订单页面
5. 搜索订单号
6. 点击订单
7. 抓取订单详情
8. 返回 dict
9. 关闭浏览器
```

返回格式：

```json
{
  "order_no": "10001",
  "customer_name": "张三",
  "amount": 1280,
  "status": "已发货",
  "shipping_company": "顺丰",
  "tracking_number": "SF123456789",
  "shipped_at": "2026-08-18 13:20"
}
```

开发阶段：

```python
headless=False
```

这样面试 Demo 时可以看到浏览器被自动操作。

同时支持：

```python
headless=True
```

用于自动测试或部署。

注意：

如果系统本身提供 API，则业务上应该优先使用 API。

RPA 的定位是：

> 用于模拟没有开放 API 的旧 ERP / 企业遗留系统。

------

# 9. RAG

## 文档准备

在：

```text
knowledge/
```

中创建以下文档：

```text
company_intro.pdf
refund_policy.pdf
shipping_policy.pdf
product_manual.pdf
```

退款政策示例：

```text
退款政策

1. 用户提交退款申请后，需要经过审核。
2. 审核通常需要 1-2 个工作日。
3. 审核通过后，退款将在 3-5 个工作日内原路返回。
4. 已发货订单需要先完成退货。
5. 商品退回并验收成功后才进入退款流程。
6. 已完成超过 30 天的订单原则上不支持无理由退款。
```

物流政策：

```text
物流政策

1. 普通订单通常会在付款完成后 24 小时内发货。
2. 默认物流公司包括顺丰、中通和京东物流。
3. 发货后用户可以通过物流单号查询运输状态。
```

------

# 10. RAG Pipeline

实现完整流程：

```text
PDF
↓
Text Extraction
↓
Chunk
↓
Embedding
↓
Vector Database
```

查询：

```text
Question
↓
Embedding
↓
Similarity Search
↓
Top-K Chunks
↓
Prompt
↓
GPT-4o
↓
Answer
```

推荐默认参数：

```text
chunk_size = 500-800
chunk_overlap = 80-150
top_k = 3-5
```

这些参数需要写入配置，而不是硬编码到业务逻辑中。

------

# 11. RAG 返回格式

建议：

```python
{
    "answer": "...",
    "sources": [
        {
            "file": "refund_policy.pdf",
            "chunk_id": 3,
            "content": "..."
        }
    ]
}
```

前端必须显示来源。

例如：

```text
根据公司的退款政策，审核通常需要 1-2 个工作日，
审核完成后退款会在 3-5 个工作日原路返回。

Sources:
- refund_policy.pdf
```

------

# 12. Agent Tools

第一版实现三个 Tool。

## Tool 1

```python
search_company_docs(query: str)
```

描述：

```text
搜索企业内部知识库，用于回答公司政策、
产品说明、物流政策、退款政策等问题。
```

------

## Tool 2

```python
query_order(order_no: str)
```

描述：

```text
通过企业 ERP 查询指定订单的信息，包括订单状态、
客户、金额、物流公司和物流单号。
```

内部调用 Playwright RPA。

------

## Tool 3

```python
calculate(expression: str)
```

描述：

```text
进行数学计算。
```

不要直接执行用户输入的 Python `eval`。

使用安全表达式解析器或者自己限制支持的运算符。

------

# 13. Agent 执行逻辑

核心 Agent Loop：

```text
User Message
↓
Send message + tools to GPT-4o
↓
模型判断是否调用 Tool
↓
如果调用：
    执行 Tool
    ↓
    获取结果
    ↓
    将 Tool Result 返回 GPT-4o
    ↓
    再次判断是否需要 Tool
↓
直到模型返回最终文本
```

伪代码：

```python
messages = [
    system_prompt,
    user_message,
]

while True:
    response = call_llm(
        messages=messages,
        tools=TOOLS
    )

    if not response.tool_calls:
        return response.text

    for tool_call in response.tool_calls:
        result = execute_tool(tool_call)

        messages.append(tool_call)
        messages.append(result)
```

需要设置最大 Tool 调用次数，例如：

```text
MAX_AGENT_STEPS = 5
```

避免死循环。

------

# 14. Agent System Prompt

Agent 应遵循以下原则：

```text
你是一个企业 AI 数字员工。

你的职责是帮助员工查询公司资料、订单信息和完成简单计算。

规则：

1. 对于公司政策、产品文档、退款、物流等知识问题，
   优先调用 search_company_docs。

2. 对于真实订单状态、物流、订单金额等业务数据，
   必须调用 query_order，不得凭空猜测。

3. 对于数学问题使用 calculate。

4. 如果 Tool 返回错误，不得伪造结果。

5. 企业知识库中没有答案时，明确说明无法从现有资料确认。

6. 不得编造订单信息。

7. 回答应简洁、准确，并尽可能说明信息来源。

8. 如果问题需要多个 Tool，可以按顺序调用多个 Tool。
```

------

# 15. 多步 Agent 示例

用户：

```text
查询订单 10001，如果已经发货，
告诉我物流信息，同时根据公司的退款政策告诉我还能不能退款。
```

预期：

```text
Step 1
query_order(order_no="10001")

Step 2
获得：
status = 已发货

Step 3
search_company_docs(
    query="已发货订单退款政策"
)

Step 4
GPT-4o 综合结果

Step 5
输出最终回答
```

这个场景是项目最重要的 Demo。

必须保证稳定执行。

------

# 16. FastAPI API

主服务运行：

```text
http://localhost:8000
```

需要实现以下 API。

## Health Check

```http
GET /health
```

返回：

```json
{
  "status": "ok"
}
```

------

## Chat

```http
POST /api/chat
```

Request：

```json
{
  "message": "帮我查一下订单10001"
}
```

Response：

```json
{
  "answer": "订单10001已经发货。",
  "tool_calls": [
    {
      "name": "query_order",
      "arguments": {
        "order_no": "10001"
      }
    }
  ],
  "sources": [],
  "audio_url": null
}
```

------

## Knowledge Upload

可选：

```http
POST /api/knowledge/upload
```

用于上传新 PDF 并重新建立索引。

如果时间不足，MVP 可以只读取本地 `knowledge/`。

------

## TTS

```http
POST /api/tts
```

Request：

```json
{
  "text": "订单10001已经发货。"
}
```

Response：

```json
{
  "audio_url": "/audio/xxx.mp3"
}
```

------

# 17. Streamlit Frontend

页面应包含：

```text
AI 数字员工头像

聊天历史

输入框

发送按钮

Agent Tool 调用记录

RAG Sources

TTS 播放按钮
```

推荐布局：

```text
┌────────────────────────────────────────────────────┐
│             Enterprise AI Employee                 │
├───────────────────────────────┬────────────────────┤
│                               │ Agent Execution    │
│ 🤖 AI Digital Employee        │                    │
│                               │ Tool: query_order  │
│ 用户：查询订单10001           │ Status: success    │
│                               │                    │
│ AI：订单10001已经发货...      │ Tool: RAG          │
│                               │ Source: refund...  │
│ 🔊 Play Voice                 │                    │
│                               │                    │
├───────────────────────────────┴────────────────────┤
│ [ 输入问题............................... ] [发送] │
└────────────────────────────────────────────────────┘
```

UI 不需要复杂。

重点是功能和执行过程可视化。

------

# 18. Agent Execution Log

必须记录 Agent 执行过程。

例如：

```text
18:21:03 USER
查询订单10001

18:21:04 AGENT
Selected tool: query_order

18:21:04 TOOL
query_order(order_no="10001")

18:21:05 RPA
Opening ERP...

18:21:06 RPA
Login success

18:21:07 RPA
Searching order 10001

18:21:08 TOOL RESULT
status=已发货

18:21:09 AGENT
Generating final response

18:21:10 TTS
Audio generated
```

日志可以同时：

```text
打印到终端
+
显示在 Streamlit UI
```

------

# 19. TTS

实现：

```python
async def text_to_speech(text: str) -> str:
    ...
```

输入：

```text
订单10001已经发货。
```

输出：

```text
data/audio/<uuid>.mp3
```

Streamlit 中：

```python
st.audio(audio_path)
```

第一版不需要复杂流式 TTS。

------

# 20. 数字人

第一版不要求真正实现 3D 或视频数字人。

前端可以显示：

```text
🤖
AI Digital Employee
```

或使用静态 Avatar。

系统架构需要为数字人预留接口：

```python
class AvatarService:
    async def generate_video(
        self,
        audio_path: str
    ) -> str:
        ...
```

第一版可以不实现具体 Provider。

未来可接：

```text
TTS Audio
↓
Avatar API
↓
Lip Sync
↓
Generated Video
```

README 中说明：

> 当前 Demo 已完成 LLM → TTS 链路，数字人 Avatar 层采用接口解耦设计，后续可以接入第三方数字人服务。

------

# 21. 配置

所有配置通过环境变量加载。

`.env.example`：

```env
OPENAI_API_KEY=

OPENAI_MODEL=gpt-4o

EMBEDDING_MODEL=

MOCK_ERP_URL=http://localhost:8001
MOCK_ERP_USERNAME=admin
MOCK_ERP_PASSWORD=admin123

VECTOR_DB_PATH=./data/vector_store

RPA_HEADLESS=false

MAX_AGENT_STEPS=5
```

禁止：

```text
把 API Key 写死在代码中。
```

------

# 22. Logging

使用 Python `logging`。

建议结构：

```text
timestamp
level
module
message
```

例如：

```text
2026-08-19 18:21:05 INFO rpa.login ERP login success
2026-08-19 18:21:07 INFO agent.tool Calling query_order
2026-08-19 18:21:08 INFO rag.retrieve Retrieved 3 chunks
```

------

# 23. Error Handling

项目至少处理以下错误：

```text
OpenAI API 调用失败
Tool 调用失败
订单不存在
ERP 登录失败
Playwright timeout
RAG 无相关文档
TTS 生成失败
```

Agent Tool 不应该抛出未经处理的异常。

Tool 返回统一结构，例如：

```python
{
    "success": False,
    "error": "ORDER_NOT_FOUND",
    "message": "订单不存在"
}
```

------

# 24. 安全要求

Calculator 不允许：

```python
eval(user_input)
```

ERP 凭证必须放 `.env`。

禁止提交：

```text
.env
API Key
真实密码
真实个人数据
```

项目所有订单、用户和业务数据均为模拟数据。

------

# 25. 测试

最低要求：

```text
test_rag.py
test_tools.py
test_agent.py
```

至少覆盖：

```text
知识库可以检索到退款政策

不存在的订单可以正确返回错误

calculator 可以完成基础计算

Agent 可以正确选择 query_order

Agent 可以正确选择 search_company_docs
```

Playwright 的完整浏览器测试可以作为可选项。

------

# 26. Docker

理想情况下使用：

```text
docker-compose up
```

启动：

```text
Backend
Mock ERP
```

Streamlit 可以：

```text
单独运行
```

或者一起加入 Compose。

服务：

```text
backend:
    8000

mock-erp:
    8001

frontend:
    8501
```

------

# 27. 推荐运行命令

安装：

```bash
python -m venv .venv
```

Linux / macOS：

```bash
source .venv/bin/activate
```

Windows：

```bash
.venv\Scripts\activate
```

安装依赖：

```bash
pip install -r requirements.txt
```

安装 Playwright：

```bash
playwright install chromium
```

初始化 ERP：

```bash
python scripts/seed_erp.py
```

初始化向量数据库：

```bash
python scripts/init_vector_db.py
```

启动 Mock ERP：

```bash
uvicorn mock_erp.app:app --port 8001
```

启动 Backend：

```bash
uvicorn app.main:app --reload --port 8000
```

启动 Streamlit：

```bash
streamlit run frontend/streamlit_app.py
```

------

# 28. MVP 开发顺序

Codex 开发时严格按照以下顺序。

## Phase 1：Mock ERP

完成：

```text
SQLite
Seed Data
Login Page
Order List
Order Search
Order Detail
```

验收：

```text
人工可以在网页登录并查询订单。
```

------

## Phase 2：RPA

完成：

```text
Playwright
自动登录
自动搜索订单
获取订单详情
```

验收：

```python
result = await query_order("10001")
```

能够返回正确订单数据。

------

## Phase 3：LLM Tool Calling

完成三个 Tool：

```text
query_order
search_company_docs
calculate
```

先实现 Tool schema 与调用流程。

验收：

用户：

```text
查询订单10001
```

Agent 自动调用：

```text
query_order
```

------

## Phase 4：RAG

完成：

```text
PDF loading
chunk
embedding
vector DB
retrieval
source citation
```

验收：

用户：

```text
退款多久到账？
```

系统能够根据 `refund_policy.pdf` 回答。

------

## Phase 5：Multi-Tool Agent

实现 Agent Loop。

验收问题：

```text
查询订单10001，如果已经发货，
告诉我物流信息，同时根据公司退款政策告诉我还能不能退款。
```

Agent 必须：

```text
query_order
↓
search_company_docs
↓
最终回答
```

------

## Phase 6：Frontend

完成：

```text
Chat UI
Tool Execution
Sources
Error Display
```

------

## Phase 7：TTS

完成：

```text
Answer
↓
TTS
↓
Audio
↓
Streamlit Playback
```

------

## Phase 8：工程化

完成：

```text
.env.example
README
Docker
logging
tests
error handling
type hints
```

------

# 29. 不需要开发的功能

为了控制项目规模，第一版不要开发：

```text
用户注册系统

复杂 RBAC

复杂 Vue / React 前端

真实支付

真实 ERP

真正 3D 数字人

模型训练

Fine-tuning

复杂多 Agent 框架

Kubernetes

Redis Cluster

复杂消息队列

生产级分布式架构
```

这些会浪费面试准备时间。

------

# 30. 开发原则

Codex 生成代码时遵循：

```text
1. 优先简单可运行，而不是过度设计。

2. 每个模块职责单一。

3. 重要函数使用 Type Hint。

4. API 使用 Pydantic Model。

5. 配置统一从 config.py 获取。

6. 不允许在业务代码硬编码 API Key。

7. Agent Tool 必须有明确输入输出 Schema。

8. RPA 和 Agent 解耦。

9. RAG 和 Agent 解耦。

10. TTS 和 Agent 解耦。

11. 每完成一个 Phase 保证系统仍可以运行。

12. 不要为了使用框架而使用框架。

13. 核心 Agent Loop 尽量清晰可读。

14. 代码优先考虑面试讲解可理解性。
```

------

# 31. 面试重点展示

项目完成后需要能够现场演示以下三个问题。

### Demo 1：RAG

```text
公司的退款政策是什么？
```

展示：

```text
Agent
↓
RAG Tool
↓
Vector Search
↓
Answer
↓
Source
```

------

### Demo 2：RPA

```text
帮我查询订单10001。
```

展示：

```text
Agent
↓
query_order
↓
Playwright Browser
↓
自动登录 ERP
↓
自动查询
↓
Answer
```

浏览器建议：

```text
headless=False
```

方便面试官看到自动操作过程。

------

### Demo 3：Multi-Step Agent

```text
查询订单10001，如果已经发货，
告诉我物流信息，同时根据公司的退款政策告诉我是否还能退款。
```

展示：

```text
GPT-4o
↓
query_order
↓
RPA
↓
search_company_docs
↓
RAG
↓
GPT-4o
↓
Final Answer
↓
TTS
```

这是最重要的演示。

------

# 32. 面试时需要能够解释的问题

开发过程中保证自己能解释：

```text
什么是 Agent？

Agent 和普通 ChatBot 的区别？

Agent 和固定 Workflow 的区别？

什么是 Function Calling / Tool Calling？

到底是谁执行 Tool？

为什么 Tool 执行完还要把结果发送给 LLM？

什么是 RAG？

为什么需要 Embedding？

什么是 Vector Search？

为什么需要 Chunk？

Chunk Size 和 Overlap 有什么作用？

Top-K 如何选择？

RAG 如何降低幻觉？

为什么不能完全避免幻觉？

为什么有 API 时应该优先 API 而不是 RPA？

什么时候适合使用 RPA？

Playwright 和 Selenium 有什么区别？

为什么 Calculator 不能直接 eval？

为什么 Agent 要设置最大 Step？

如果 Tool 失败怎么办？

为什么模块之间需要解耦？

TTS 在整个架构中的位置是什么？

真正数字人还需要增加哪些模块？
```

------

# 33. 简历描述参考

项目名称：

```text
Enterprise AI Digital Employee
基于 RAG + Agent + RPA 的企业 AI 数字员工
```

简历描述：

```text
基于 Python、FastAPI 与 GPT-4o 开发企业 AI 数字员工 Demo，
设计 LLM Tool Calling Agent，实现企业知识库查询、订单系统操作
和计算工具的动态选择与多步骤调用。

基于 Embedding + Vector Database 构建 RAG 企业知识库，
支持 PDF 文档解析、语义检索、上下文增强问答及来源引用。

使用 Playwright 实现 RPA 自动化，通过浏览器自动登录模拟 ERP、
查询订单状态及物流信息，并将结果作为 Agent Tool 返回给大模型。

集成 TTS 实现 AI 回答语音输出，并使用 Streamlit 构建聊天界面
及 Agent Tool 执行过程可视化。
```

------

# 34. 最终验收标准

项目完成的最低标准：

-  Mock ERP 可以正常登录
-  ERP 支持订单查询
-  Playwright 可以自动登录 ERP
-  Playwright 可以查询指定订单
-  GPT-4o 可以正常对话
-  Agent 支持 Tool Calling
-  Agent 支持 query_order
-  Agent 支持 search_company_docs
-  Agent 支持 calculator
-  RAG 可以读取 PDF
-  RAG 可以建立向量索引
-  RAG 可以返回 Source
-  Agent 可以执行多个 Tool
-  Multi-Step Demo 可以稳定运行
-  FastAPI 提供 Chat API
-  Streamlit 可以完成聊天交互
-  UI 可以显示 Tool Call
-  TTS 可以生成语音
-  Streamlit 可以播放语音
-  API Key 使用 `.env`
-  项目有基础日志
-  项目有基础异常处理
-  项目有 README
-  项目可以按照 README 从零启动

------

# 35. Codex 当前任务

请按照本 README 逐步实现项目。

优先实现 MVP，不要一次性生成整个项目的所有复杂代码。

执行顺序：

```text
1. 初始化项目目录和依赖
2. 创建 Mock ERP
3. 创建 SQLite Mock Data
4. 完成 Playwright query_order
5. 创建 GPT-4o Client
6. 实现三个 Agent Tools
7. 实现 RAG
8. 实现 Agent Tool Calling Loop
9. 实现 Multi-Tool Agent
10. 创建 FastAPI API
11. 创建 Streamlit UI
12. 添加 TTS
13. 添加 Logging
14. 添加 Tests
15. 添加 Docker
16. 完善 README
```

每完成一步：

```text
先保证当前代码可以运行和测试，
再进入下一阶段。
```

项目的最高优先级不是功能数量，而是：

```text
可运行
可演示
可解释
结构清晰
面试时稳定
```