# 项目实施记录

## Phase 0 - 已实现

- 阶段：Phase 0（项目骨架与运行环境）
- 状态：已完成
- 完成日期：2026-08-19
- 范围控制：仅完成骨架、环境、配置、日志、健康检查与首个测试，尚未开始 Mock ERP、RPA、RAG、Agent、前端或 TTS 业务功能。

## 实施过程

1. 阅读 `plan.md` 的 Phase 0 方案，并以 `Idea.md` 中的 AI 数字员工演示目标作为背景。
2. 检查初始仓库，确认只有 `plan.md` 与 `Idea.md`，不存在需要保留或兼容的既有代码。
3. 使用本机已有的 `uv 0.9.22` 管理环境，将 CPython 3.11.14 下载到项目内的 `.uv-python/`，并在项目内创建 `.venv/`。
4. 将 uv 缓存固定到项目内的 `.uv-cache/`；`uv.toml` 会让后续依赖缓存继续留在本项目。创建或重建环境时，使用项目内的 `UV_PYTHON_INSTALL_DIR`，避免写入全局 Python 目录。
5. 创建 Phase 0 要求的最小目录：`app/`、`mock_erp/`、`frontend/`、`tests/`、`scripts/`、`knowledge/`、`data/`。
6. 创建 `requirements.txt`，只加入本阶段所需的 FastAPI、Uvicorn、pydantic-settings、httpx 和 pytest，没有提前安装后续阶段依赖。
7. 创建 `.gitignore`，忽略密钥、本地虚拟环境、uv 下载目录、Python/测试缓存、SQLite、向量索引和音频输出。
8. 创建 `.env.example`，按计划集中列出配置名和安全的本地默认值，API Key 保持为空。
9. 在 `app/core/config.py` 实现基于环境变量的统一配置对象：启动时校验数值范围与切块参数关系；`LLM_API_KEY` 保持可选，仅在未来真实调用 LLM 时通过 `require_llm_api_key()` 强制校验。
10. 在 `app/core/logging.py` 实现基础日志配置，格式包含时间、级别、模块、`request_id` 和消息。
11. 在 `app/main.py` 创建最小 FastAPI 应用、请求 ID 中间件和 `GET /health`；响应严格为 `{"status":"ok"}`，并通过响应头回传请求 ID。
12. 在 `tests/test_health.py` 创建首个独立健康检查测试，验证状态码、JSON 响应和请求 ID。

## 项目内环境命令

PowerShell 下创建或重建同样的隔离环境：

```powershell
$env:UV_CACHE_DIR = (Join-Path (Get-Location) '.uv-cache')
$env:UV_PYTHON_INSTALL_DIR = (Join-Path (Get-Location) '.uv-python')
uv venv --python 3.11 --python-preference only-managed .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```

日常运行直接使用项目虚拟环境，不依赖全局 Python：

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

## 验收结果

| 验收项                   | 结果 | 证据                                                        |
| ------------------------ | ---- | ----------------------------------------------------------- |
| Python 3.11 项目虚拟环境 | 通过 | `.venv\Scripts\python.exe --version` 返回 `Python 3.11.14`  |
| Uvicorn 可启动           | 通过 | `app.main:app` 在 `127.0.0.1:8000` 完成启动                 |
| `/health` 响应正确       | 通过 | HTTP 200，响应体为 `{"status":"ok"}`                        |
| 缺少 `.env` 可启动       | 通过 | 未创建 `.env`，应用导入和服务启动均成功，LLM Key 为可选状态 |
| 测试可独立运行           | 通过 | `1 passed`                                                  |
| Python 文件可编译        | 通过 | `python -m compileall -q app tests` 成功                    |
| Git 补丁格式检查         | 通过 | `git diff --check` 无错误                                   |

## Phase 0 产物

- 环境约束：`.python-version`、`uv.toml`、`requirements.txt`
- 安全与配置：`.gitignore`、`.env.example`、`app/core/config.py`
- 基础设施：`app/core/logging.py`
- 最小服务：`app/main.py`
- 自动测试：`tests/test_health.py`
- 后续阶段占位目录：`mock_erp/`、`frontend/`、`scripts/`、`knowledge/`、`data/`

## Phase 1（Mock ERP）- 已实现

- 当前阶段：Phase 1（Mock ERP）
- 状态：已完成
- 完成日期：2026-08-19
- 累计进度：Phase 0、Phase 1 已完成；Phase 2（Playwright RPA）尚未开始。
- 范围控制：本次严格停留在 Mock ERP，没有提前实现 RPA、RAG、Agent、前端或 TTS。

## Phase 1 实施过程

1. 完整核对 `plan.md` 的 Phase 1 步骤与验收项，并参考 `Idea.md` 的订单字段、演示账号及重点订单数据。
2. 延续 Phase 0 的项目内环境方案：Python 3.11.14 位于 `.uv-python/`，虚拟环境位于 `.venv/`，uv 缓存位于 `.uv-cache/`；没有安装或修改全局 Python 和全局包。
3. 在 `requirements.txt` 中仅补充当前阶段需要的 `jinja2`、`python-multipart` 和 `itsdangerous`，并通过本地 `uv` 安装到 `.venv/`。
4. 在统一配置中新增 `MOCK_ERP_DATABASE_PATH` 与 `MOCK_ERP_SESSION_SECRET`；登录账号和密码继续从环境变量读取，`.env.example` 只保存本地演示默认值。
5. 使用 Python 内置 `sqlite3` 实现最小数据层：建表、按订单号查询、列出订单，以及供 seed 使用的原子替换数据操作；没有引入 SQLAlchemy。
6. 创建固定的 20 条订单数据，覆盖待付款、处理中、已发货、已完成、已退款、已取消状态。其中：
   - `10001` 为已发货，物流公司顺丰，物流单号 `SF123456789`，发货时间 `2026-08-18 13:20`；
   - `10002` 为处理中且物流字段为空；
   - `10003` 为已完成且创建时间超过 30 天；
   - `10004` 为已退款。
7. Seed 采用“事务内清空后插入固定数据”的策略，并重置自增序列；重复执行后数据库仍严格保持 20 条且内容一致。
8. 实现 FastAPI + Jinja2 的 Mock ERP：登录页、session cookie、退出登录、订单列表、订单号精确搜索及订单详情页。
9. 为后续 RPA 添加稳定选择器，包括登录输入框、登录按钮、搜索框、搜索按钮、订单行、订单链接和所有详情字段的 `data-testid`。
10. 页面使用简单响应式 CSS，适合人工操作和录屏；错误登录、空搜索、不存在订单均显示明确提示，未登录访问订单页会重定向到登录页。
11. 新增自动测试，覆盖 seed 幂等性、20 条固定数据、重点订单内容、未登录保护、错误登录、成功登录、订单搜索、详情字段、不存在订单与空搜索。
12. 使用真实 Uvicorn 进程在 `127.0.0.1:8001` 启动服务，并通过 HTTP 完成登录和 `10001` 查询，确认页面包含稳定订单行与完整物流单号。

## 项目内环境与运行命令

PowerShell 下安装依赖（缓存和 Python 下载均留在项目目录）：

```powershell
$env:UV_CACHE_DIR = (Join-Path (Get-Location) '.uv-cache')
$env:UV_PYTHON_INSTALL_DIR = (Join-Path (Get-Location) '.uv-python')
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```

初始化固定 ERP 数据：

```powershell
.venv\Scripts\python.exe scripts\seed_erp.py
```

启动 Mock ERP：

```powershell
.venv\Scripts\python.exe -m uvicorn mock_erp.app:app --port 8001
```

浏览器访问 `http://localhost:8001`，默认本地演示账号为 `admin`，密码为 `admin123`。实际值可在项目根目录的 `.env` 中覆盖，不应提交 `.env`。

运行测试：

```powershell
.venv\Scripts\python.exe -m pytest -q
```

## Phase 1 验收结果

| 验收项             | 结果 | 证据                                                                    |
| ------------------ | ---- | ----------------------------------------------------------------------- |
| 配置账号密码可登录 | 通过 | 错误密码返回 401 和可见提示；正确凭证写入 session 并进入 `/orders`      |
| 搜索 `10001`       | 通过 | 列表显示已发货、顺丰、`SF123456789`；详情页各字段具有固定 `data-testid` |
| 搜索不存在订单     | 通过 | 页面显示“未找到订单 99999”                                              |
| 空搜索提示         | 通过 | 页面显示“请输入订单号”                                                  |
| 未登录访问保护     | 通过 | 访问 `/orders` 返回 303 并跳转 `/login`                                 |
| Seed 可重复执行    | 通过 | 连续执行两次后仍为固定 20 条，无重复订单号                              |
| 自动测试           | 通过 | `3 passed`（含原 Phase 0 健康检查）                                     |
| Python 编译检查    | 通过 | `python -m compileall -q app mock_erp scripts tests`                    |
| 真实服务冒烟检查   | 通过 | Uvicorn :8001 启动，HTTP 登录和 `10001` 查询均返回 200                  |
| Git 补丁格式检查   | 通过 | `git diff --check` 无错误                                               |

## Phase 0 回顾

Phase 0 已完成项目目录、项目内 uv/Python 3.11 环境、最小依赖、统一配置、基础日志、FastAPI `/health` 与健康检查测试。其环境隔离规则在 Phase 1 中继续沿用。

## 下一阶段边界

按照 `plan.md`，下一阶段是 Phase 2：Playwright RPA。应在下一阶段安装项目内 Playwright/Chromium，实现自动登录、搜索和详情字段读取；本次未开始该工作。

## Phase 2 - 已实现

- 阶段：Phase 2（Playwright RPA）
- 状态：已完成
- 完成日期：2026-08-19
- 累计进度：Phase 0、Phase 1、Phase 2 已完成；下一阶段为 Phase 3（安全 Calculator 与工具统一层）。
- 范围控制：本次只实现 RPA 及其必要的统一 `ToolResult` 数据契约，没有提前实现 Calculator、RAG、LLM Agent、前端或 TTS。

## Phase 2 实施过程

1. 完整核对 `plan.md` 的 Phase 2 目标、步骤、验收和测试要求，并参考 `Idea.md` 中“通过 Playwright 操作无 API 的旧 ERP”这一项目背景及订单返回字段。
2. 延续项目内环境隔离规则：Python 继续使用 `.uv-python/` 中的 CPython 3.11.14，依赖只通过本地 uv 安装进 `.venv/`，uv 缓存继续固定在 `.uv-cache/`；没有安装或修改全局 Python、全局 Python 包或全局浏览器版本。
3. 在 `requirements.txt` 中仅增加当前阶段需要的 `playwright`，实际安装版本为 1.62.0。
4. 将 Chromium、headless shell、FFmpeg 和 Playwright 辅助文件下载到项目内的 `.playwright-browsers/`，并在 `.env.example`、统一配置与 `.gitignore` 中加入 `PLAYWRIGHT_BROWSERS_PATH`；浏览器二进制没有写入用户级 Playwright 缓存。
5. 按总体数据契约创建 `Source` 与 `ToolResult` Pydantic 模型。RPA 统一返回 `success`、`data`、`error_code`、`message`、`sources`，不向调用方抛出未经处理的浏览器异常。
6. 创建唯一公开 RPA 入口 `async query_order(order_no: str) -> ToolResult`；订单号会先去除首尾空格，并校验非空、最大 32 字符以及仅包含字母、数字、下划线和连字符，避免把任意脚本文本带入页面操作。
7. 每次查询均新建 Playwright、Chromium browser、context 和 page，读取 `RPA_HEADLESS`、`RPA_TIMEOUT_MS`、ERP URL 与凭证；没有实现浏览器池、session 复用或数据库/API 捷径。
8. 浏览器严格按“打开登录页 → 填写凭证 → 提交并确认登录 → 搜索订单 → 打开详情 → 读取字段”的顺序操作，全程使用 Phase 1 的 `data-testid` 和 Playwright 显式等待，没有固定 `sleep`。
9. 将详情文本转换成稳定订单字典：金额转为 `float`，空的物流公司、物流单号和发货时间转为 `None`。测试中发现空文本元素不符合 Playwright 的 `visible` 判定，因此详情字段改为等待 `attached`，既允许合法空值又能检测缺失元素。
10. 通过 `finally` 关闭 browser context 和 browser。日志记录订单号、登录/查询阶段与总耗时，但不记录密码。
11. 分别映射错误：非法参数为 `INVALID_ARGUMENT`，不存在订单为 `ORDER_NOT_FOUND`，错误凭证为 `ERP_LOGIN_FAILED`，操作超时为 `RPA_TIMEOUT`，ERP 未启动为 `ERP_UNAVAILABLE`，页面结构或金额格式变化为 `ERP_PAGE_CHANGED`，其他未预期错误为 `TOOL_INTERNAL_ERROR`。
12. 添加 pytest integration marker 与 `--run-integration` 开关。默认测试只执行单元测试，不启动本地服务和浏览器；显式集成测试会使用临时 SQLite 数据库、临时端口、真实 Uvicorn Mock ERP 和项目内 headless Chromium。

## Phase 2 项目内环境与运行命令

安装 Python 依赖：

```powershell
$env:UV_CACHE_DIR = (Join-Path (Get-Location) '.uv-cache')
$env:UV_PYTHON_INSTALL_DIR = (Join-Path (Get-Location) '.uv-python')
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```

将 Chromium 安装到项目目录：

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = (Join-Path (Get-Location) '.playwright-browsers')
.venv\Scripts\python.exe -m playwright install chromium
```

默认运行单元测试（不启动 Chromium）：

```powershell
.venv\Scripts\python.exe -m pytest -q
```

运行包含真实浏览器的完整测试：

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = (Join-Path (Get-Location) '.playwright-browsers')
.venv\Scripts\python.exe -m pytest -q --run-integration
```

开发演示时先初始化并启动 Mock ERP，然后调用公开函数；默认 `RPA_HEADLESS=false`，可看到浏览器自动操作：

```powershell
.venv\Scripts\python.exe scripts\seed_erp.py
.venv\Scripts\python.exe -m uvicorn mock_erp.app:app --port 8001
```

## Phase 2 验收结果

| 验收项           | 结果 | 证据                                                                            |
| ---------------- | ---- | ------------------------------------------------------------------------------- |
| 查询 `10001`     | 通过 | 真实 Chromium 返回“已发货”、顺丰、`SF123456789` 和发货时间，金额为数值 `1280.0` |
| 查询 `10002`     | 通过 | 返回“处理中”，物流公司、物流单号和发货时间均为 `None`                           |
| 查询不存在订单   | 通过 | `99999` 返回 `success=false` 与 `ORDER_NOT_FOUND`                               |
| 密码错误         | 通过 | 返回 `ERP_LOGIN_FAILED`，日志不包含密码                                         |
| ERP 未启动       | 通过 | 返回 `ERP_UNAVAILABLE` 和明确的服务启动提示，无未处理堆栈                       |
| 参数安全校验     | 通过 | 空白、超长和包含脚本字符的订单号均返回 `INVALID_ARGUMENT`，不会启动浏览器       |
| 超时映射         | 通过 | Playwright 超时统一映射为 `RPA_TIMEOUT`                                         |
| 浏览器资源关闭   | 通过 | context 与 browser 均在 `finally` 中关闭，集成测试连续多次查询可正常完成        |
| 默认自动测试     | 通过 | `8 passed, 3 skipped`，被跳过项均为显式浏览器集成测试                           |
| 完整集成测试     | 通过 | `11 passed`，使用真实 Uvicorn、临时 SQLite 与项目内 headless Chromium           |
| Python 编译检查  | 通过 | `python -m compileall -q app mock_erp scripts tests` 成功                       |
| Git 补丁格式检查 | 通过 | `git diff --check` 无空白错误                                                   |

## Phase 2 产物

- 统一契约：`app/agent/schemas.py`
- RPA 实现：`app/rpa/order_query.py`、`app/rpa/__init__.py`
- 环境配置：`requirements.txt`、`.env.example`、`.gitignore`、`app/core/config.py`
- 测试控制：`pytest.ini`、`tests/conftest.py`
- 单元测试：`tests/test_rpa_validation.py`
- 真实浏览器集成测试：`tests/integration/test_order_query.py`

## 当前进度与下一阶段边界

- 当前进度：Phase 2 已完整验收，浏览器 RPA 小 Demo 已可独立运行和讲解。
- 下一阶段：严格按照 `plan.md` 进入 Phase 3（安全 Calculator 与工具统一层）。
- 尚未开始：Calculator、Tool Registry、RAG、LLM Client、Agent Loop、Chat API、Streamlit、TTS 与 Docker。

## Phase 3 - 已实现

- 阶段：Phase 3（安全 Calculator 与工具统一层）
- 状态：已完成
- 完成日期：2026-08-19
- 累计进度：Phase 0、Phase 1、Phase 2、Phase 3 已完成；下一阶段为 Phase 4（RAG 离线索引）。
- 范围控制：本次只实现安全计算器、Tool Registry、参数二次校验与统一分发，没有提前实现 RAG、LLM Client、Agent Loop、Chat API、前端或 TTS。

## Phase 3 实施过程

1. 完整核对 `plan.md` 的 Phase 3 目标、步骤、验收项与安全边界，并参考 `Idea.md` 中三个 Agent Tool、禁止直接 `eval`、Tool 统一错误结构及后续 Tool Calling 的项目背景。
2. 延续项目内环境隔离规则：验证运行时仍为 `.venv/` 中的 Python 3.11.14、本地 uv 0.9.22，uv 缓存与 Python 下载目录仍固定在 `.uv-cache/` 和 `.uv-python/`；Phase 3 不需要新增第三方依赖，也没有修改任何全局环境或全局包。
3. 创建 `app/tools/calculator.py`，唯一公开计算入口为 `calculate(expression: str) -> ToolResult`；表达式通过 `ast.parse(..., mode="eval")` 解析，代码中没有调用 `eval` 或 `exec`。
4. Calculator 只允许普通整数/小数、括号、二元加减乘除、取模、有限幂运算及一元正负号。名称、布尔值、字符串、函数调用、属性访问、列表、字典和其他 AST 节点全部默认拒绝。
5. 为避免资源滥用，增加多层限制：表达式最多 200 字符、AST 最多 64 个节点、单个数值绝对值最多 `10^12`、中间及最终结果绝对值最多 `10^15`、幂指数绝对值最多 10，并拒绝非有限数值和复数结果。
6. 将非法语法、不允许的节点、除零、对零取模、超限数字、超限结果和超限幂指数统一转换为 `CALCULATION_ERROR`；未预期内部异常转换为 `TOOL_INTERNAL_ERROR`，不向调用方泄漏堆栈。
7. 创建 `app/agent/tool_registry.py`，使用不可变 `ToolDefinition` 将工具名、中文说明、Pydantic 输入模型和异步执行函数绑定在一起；当前只显式注册已经可用的 `calculate` 和 `query_order`，没有为尚未实现的 RAG 注册占位工具。
8. 为 `calculate` 和 `query_order` 分别创建严格输入模型，启用 `strict=True` 与 `extra="forbid"`。Registry 在执行前再次通过 Pydantic 校验模型给出的参数，拒绝缺失字段、错误类型、多余字段和非对象参数。
9. 实现统一异步入口 `dispatch_tool(name, arguments) -> ToolResult`：未知工具返回 `UNKNOWN_TOOL`，错误参数返回 `INVALID_ARGUMENT`，执行器意外失败返回 `TOOL_INTERNAL_ERROR`；分发仅查表调用白名单函数，不动态导入或执行任意名称。
10. 实现 `tool_schemas()`，由 Registry 的 Pydantic 输入模型生成确定的 OpenAI 兼容 Function Tool JSON Schema，供后续 Phase 5 的 LLM Client 直接使用，并保证 Schema 禁止额外字段。
11. 新增 `tests/test_tools.py`，覆盖正常四则运算、括号、取模、有限幂、一元正负号、注入表达式、函数与属性访问、非数值字面量、除零、复杂度/数值边界、Registry 分发、Pydantic 二次校验、未知工具及 Schema 内容。
12. 运行默认测试和包含真实 Chromium 的完整集成回归，确认新增工具层没有破坏健康检查、Mock ERP 和 Phase 2 RPA。

## Phase 3 项目内运行命令

本阶段没有新增依赖。若需要按锁定的项目方式同步现有依赖，仍使用：

```powershell
$env:UV_CACHE_DIR = (Join-Path (Get-Location) '.uv-cache')
$env:UV_PYTHON_INSTALL_DIR = (Join-Path (Get-Location) '.uv-python')
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```

运行不启动浏览器的默认测试：

```powershell
.venv\Scripts\python.exe -m pytest -q
```

运行包含项目内 Chromium 的完整回归：

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = (Join-Path (Get-Location) '.playwright-browsers')
.venv\Scripts\python.exe -m pytest -q --run-integration
```

## Phase 3 验收结果

| 验收项                     | 结果 | 证据                                                                        |
| -------------------------- | ---- | --------------------------------------------------------------------------- |
| `1280 * 0.8`               | 通过 | 返回 `success=true`、`result=1024` 与 `CALCULATION_ERROR` 为空              |
| 括号和基础四则运算         | 通过 | `(2 + 3) * 4 - 6 / 2` 返回 `17`，取模、一元正负号和有限幂测试同时通过       |
| 拒绝代码与对象访问         | 通过 | `__import__`、函数调用、属性访问、列表、字典、字符串和布尔值均被拒绝        |
| 限制高成本计算             | 通过 | 长度、AST 节点、数值、结果和幂指数均有上限，超限返回 `CALCULATION_ERROR`    |
| 除零和非法语法             | 通过 | 除零、对零取模和不完整表达式均返回 `CALCULATION_ERROR`                     |
| Tool 参数二次校验          | 通过 | 缺字段、错误类型、多余字段和非对象参数均返回 `INVALID_ARGUMENT`            |
| 未知工具安全拒绝           | 通过 | 未注册工具返回 `UNKNOWN_TOOL`，不会动态导入、执行或造成未处理异常           |
| Tool Schema                | 通过 | 只输出 `calculate` 与 `query_order`，均包含说明、必填字段和禁止额外字段约束 |
| 默认自动测试               | 通过 | `37 passed, 3 skipped`；跳过项仅为显式浏览器集成测试                        |
| 完整集成回归               | 通过 | `40 passed`，真实 Uvicorn Mock ERP 与项目内 headless Chromium 均正常        |
| Python 编译检查            | 通过 | `python -m compileall -q app mock_erp scripts tests` 成功                   |
| Git 补丁格式检查           | 通过 | `git diff --check` 无空白错误                                               |

## Phase 3 产物

- 安全 Calculator：`app/tools/calculator.py`、`app/tools/__init__.py`
- Tool Registry 与严格输入模型：`app/agent/tool_registry.py`
- 单元与安全边界测试：`tests/test_tools.py`
- 实施与验收记录：`step.md`

## 当前进度与下一阶段边界

- 当前进度：Phase 3 已完整验收；Calculator 与订单 RPA 已能通过统一 Registry 安全分发，并可生成后续 LLM Tool Calling 所需的 JSON Schema。
- 下一阶段：严格按照 `plan.md` 进入 Phase 4（RAG 离线索引），届时才创建模拟企业 PDF、Loader、Splitter、Embedding、FAISS、metadata/manifest 和知识库 Tool。
- 尚未开始：RAG、`search_company_docs`、LLM Client、Agent Loop、Chat API、Streamlit、TTS 与 Docker。

## Phase 4 - 已实现

- 阶段：Phase 4（RAG 离线索引）
- 状态：已完成
- 完成日期：2026-08-19
- 累计进度：Phase 0、Phase 1、Phase 2、Phase 3、Phase 4 已完成；下一阶段为 Phase 5（LLM Client 与 Agent Loop）。
- 范围控制：本次只实现本地模拟 PDF、文本提取、切块、本地 BGE Embedding、FAISS 持久化、检索与知识库 Tool；没有实现或调用 OpenRouter、LLM Client、Agent Loop、Chat API、前端或 TTS。

## Phase 4 实施过程

1. 完整核对 `plan.md` 的 Phase 4 目标、步骤、检索策略、验收问题和测试要求，并参考 `Idea.md` 中企业知识库、退款政策、物流政策和来源展示的项目背景。
2. 延续项目内环境隔离规则：Python 使用 `.uv-python/` 中的 CPython 3.11.14，依赖只通过本地 uv 安装到 `.venv/`，uv 缓存继续固定在 `.uv-cache/`；没有修改全局 Python 或全局包。
3. 在 `requirements.txt` 中增加本阶段依赖：`pypdf`、`reportlab`、`sentence-transformers` 和 `faiss-cpu`。实际环境使用 pypdf 5.9.0、reportlab 4.5.1、sentence-transformers 5.7.0、faiss-cpu 1.15.0 和 CPU 版 torch 2.13.0。
4. 将 BGE 模型缓存固定在项目内 `.model-cache/` 并加入 `.gitignore`。首次下载的 `BAAI/bge-small-zh-v1.5` 缓存约 96.4 MB；后续加载优先使用 `local_files_only=True`，缓存完整时不会向 Hugging Face 发网络请求。
5. 创建四份 1 页、可提取中文文本的模拟 PDF：`company_intro.pdf`、`refund_policy.pdf`、`shipping_policy.pdf` 和 `product_manual.pdf`。内容明确标记为 Demo 模拟数据，覆盖公司成立时间、退款时效、已发货退货条件、超过 30 天边界、默认物流公司和 A100 产品说明。
6. 使用嵌入式 TrueType 中文字体生成 PDF。最初验证发现 CID 字体生成的 PDF 在终端显示存在编码歧义，因此改为嵌入 TrueType 字体，并通过 Unicode code point 和固定中文断言确认 pypdf 实际提取内容正确；第一版未引入 OCR。
7. 创建 PDF Loader，按文件名和页码确定性加载；保留文件、从 1 开始的页码和正文，空页会记录 warning，无 PDF 或所有页面为空时返回明确错误。
8. 创建中文感知的递归字符 Splitter，优先按段落、换行、句号、感叹号、问号、分号、逗号切分，最后才按字符截断；使用配置中的 `CHUNK_SIZE=500` 和 `CHUNK_OVERLAP=80`，并生成稳定的 `<file>-p<page>-c<index>` ID。
9. 创建本地 BGE Embedding 封装：文档与查询都输出 float32 归一化向量；查询加入 BGE 检索指令。模型按需加载，非 RAG 命令不会提前加载 torch 或模型权重。
10. 创建 FAISS `IndexFlatIP` 向量索引，归一化后使用内积表示余弦相似度。索引写入 `data/vector_store/index.faiss`，顺序完全对应的来源写入 `metadata.json`。
11. 创建 `manifest.json`，记录格式版本、UTC 构建时间、Embedding 模型名、512 维向量、向量数量、切块参数，以及四份 PDF 的文件名、SHA-256 和大小。加载时严格校验 FAISS 数量、metadata 数量、manifest 数量和维度一致。
12. 创建 `scripts/build_index.py` 作为手动离线构建入口；索引不在后端启动时自动重建。缺少完整索引时返回 `RAG_NOT_READY` 并提示先运行构建脚本，索引损坏或模型不一致时也拒绝继续检索。
13. 创建 `KnowledgeRetriever` 和 `search_company_docs`。Tool 只返回 query、检索上下文和 `Source`，不额外调用 LLM；来源包含文件、页码、稳定 chunk ID、原文和相似度。默认 Retriever 被进程内复用，避免每次 Tool 调用重新加载本地模型。
14. 将 `search_company_docs` 注册到现有白名单 Tool Registry，新增严格 Pydantic 参数模型；同步检索通过 `asyncio.to_thread` 接入异步 Tool 调度，不阻塞事件循环。
15. 使用真实 BGE 对五个固定问题观察分数：四个相关问题第一名为 0.4676 至 0.7024，无关年假问题第一名为 0.3686。基于当前固定模型和模拟文档，将初始 `RAG_SCORE_THRESHOLD` 设为 0.45，并保留环境变量覆盖能力。
16. 按已确认的 OpenRouter 决策同步配置示例和文档：Provider 为 OpenRouter、示例模型为 `openai/gpt-5-mini`、允许上游自动路由、API Key 字段保持为空、应用代码中的模型默认值保持空字符串并要求未来从 `LLM_MODEL` 加载。本阶段没有创建 `.env`，也没有调用 OpenRouter。
17. 新增单元测试与真实模型集成测试，覆盖 PDF 中文文本、页码、切块边界、稳定 chunk ID、索引重载、manifest、数量不一致、缺失索引、四个相关问题和无关问题拒答；同时完成此前健康检查、ERP、RPA、Calculator 和 Tool Registry 的完整回归。

## Phase 4 项目内环境与运行命令

安装依赖，Python 下载与 uv 缓存都保留在项目目录：

```powershell
$env:UV_CACHE_DIR = (Join-Path (Get-Location) '.uv-cache')
$env:UV_PYTHON_INSTALL_DIR = (Join-Path (Get-Location) '.uv-python')
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```

重新生成四份模拟知识库 PDF：

```powershell
.venv\Scripts\python.exe scripts\create_knowledge_pdfs.py
```

如果当前系统没有脚本支持的中文字体，可通过 `KNOWLEDGE_PDF_FONT` 指定本机 TrueType/OpenType 中文字体；已提交的 PDF 可直接使用，不需要每次重新生成。

首次下载本地 BGE 模型并构建索引，模型缓存与索引都只写入项目目录：

```powershell
.venv\Scripts\python.exe scripts\build_index.py
```

默认运行不加载真实模型和浏览器的快速测试：

```powershell
.venv\Scripts\python.exe -m pytest -q
```

运行包含真实 BGE、FAISS、Mock ERP 和项目内 Chromium 的完整回归：

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = (Join-Path (Get-Location) '.playwright-browsers')
.venv\Scripts\python.exe -m pytest -q --run-integration
```

## Phase 4 验收结果

| 验收项 | 结果 | 证据 |
| --- | --- | --- |
| 四份模拟 PDF | 通过 | 四份 PDF 均为 1 页文本型 PDF，pypdf 可提取完整中文和页码 |
| Loader 与 Splitter | 通过 | 空页保护、语义分隔、500/80 配置、非空 chunk 和稳定 ID 均有测试 |
| 本地 Embedding | 通过 | BAAI/bge-small-zh-v1.5 在项目缓存加载，输出 512 维归一化向量 |
| FAISS 持久化 | 通过 | `index.faiss` 可重载，向量、metadata、manifest 数量和维度一致 |
| 退款到账问题 | 通过 | `refund_policy.pdf` 第一名，score=0.6544 |
| 已发货退款问题 | 通过 | `refund_policy.pdf` 第一名，score=0.7024 |
| 默认物流公司问题 | 通过 | `shipping_policy.pdf` 第一名，score=0.5597 |
| 公司成立时间问题 | 通过 | `company_intro.pdf` 第一名，score=0.4676 |
| 无关年假问题 | 通过 | 第一名原始 score=0.3686，低于 0.45，返回 `NO_RELEVANT_DOCUMENT` |
| Tool Registry | 通过 | Schema 只暴露 `calculate`、`query_order`、`search_company_docs` 三个白名单 Tool |
| 默认自动测试 | 通过 | `47 passed, 4 skipped`；跳过项为显式集成测试 |
| 完整集成回归 | 通过 | `51 passed`，真实 BGE/FAISS 与真实 Mock ERP/Chromium 全部通过 |
| Python 编译检查 | 通过 | `python -m compileall -q app mock_erp scripts tests` 成功 |
| 密钥与环境检查 | 通过 | `.env` 不存在且未被 Git 跟踪，`.env.example` 中 `OPENROUTER_API_KEY` 为空 |
| Git 补丁格式检查 | 通过 | `git diff --check` 无空白错误 |

## Phase 4 产物

- 模拟知识库：`knowledge/company_intro.pdf`、`knowledge/refund_policy.pdf`、`knowledge/shipping_policy.pdf`、`knowledge/product_manual.pdf`
- PDF 生成与索引命令：`scripts/create_knowledge_pdfs.py`、`scripts/build_index.py`
- RAG 实现：`app/rag/models.py`、`loader.py`、`splitter.py`、`embeddings.py`、`indexer.py`、`vector_store.py`、`retriever.py`
- 知识库 Tool：`app/tools/knowledge.py` 与更新后的 `app/agent/tool_registry.py`
- 配置与依赖：`.env.example`、`.gitignore`、`requirements.txt`、`app/core/config.py`
- 自动测试：`tests/test_rag.py`、`tests/integration/test_rag_real.py` 及更新后的 Registry 测试
- 运行时生成但不提交：`.model-cache/`、`data/vector_store/`

## 当前进度与下一阶段边界

- 当前进度：Phase 4 已完整验收；三个 Agent Tool 均已实现并注册，RAG 可以在不调用 LLM 的情况下返回可追踪上下文和来源。
- 下一阶段：严格按照 `plan.md` 进入 Phase 5（LLM Client 与 Agent Loop），届时才使用本机 `.env` 中的 `OPENROUTER_API_KEY` 和 `LLM_MODEL=openai/gpt-5-mini` 调用 OpenRouter。
- Phase 5 的既定路由边界：允许 OpenRouter 自动选择上游 Provider；初始 Demo 不固定上游 Provider、不主动启用 prompt logging、不强制 ZDR，但 LLM Client 应保留未来增加 Provider/隐私路由选项的配置入口。
- 尚未开始：OpenRouter LLM Client、Agent Loop、Chat API、Streamlit、TTS 与 Docker。

## Phase 5 - 已完整验收

- 阶段：Phase 5（LLM Client 与 Agent Loop）
- 状态：已完成，包括真实 OpenRouter、RAG、Calculator、RPA 与条件式多工具场景联调。
- 完成日期：2026-08-19
- 累计进度：Phase 0 至 Phase 5 已完整验收；下一阶段为 Phase 6（FastAPI Chat API）。
- 范围控制：本次只实现 OpenRouter LLM Client、自写 Agent Loop、Prompt、错误映射、Fake LLM 自动测试和手工冒烟脚本；没有提前实现 Chat API、Streamlit、TTS 或 Docker。

## Phase 5 实施过程

1. 完整核对 `plan.md` 的 Phase 5 目标、17 项具体步骤、多工具预期流程、验收项和 Fake LLM 测试要求，并参考 `Idea.md` 中企业政策、ERP、Calculator 和条件式多工具场景的业务背景。
2. 延续项目内环境隔离规则：Python 使用 `.uv-python/` 中的 CPython 3.11.14，依赖只通过本地 uv 安装到 `.venv/`，uv 缓存固定在 `.uv-cache/`；没有修改全局 Python、全局包或系统浏览器版本。
3. 在 `requirements.txt` 中增加 `openai` 1.x SDK，并补齐 `plan.md` 固定测试选型中此前遗漏的 `pytest-asyncio`；实际项目环境安装 `openai==1.109.1`、`pytest-asyncio==1.4.0`，相关传递依赖也只进入项目 `.venv/`。
4. 初次根据 OpenRouter 模型目录选择 `qwen/qwen3-next-80b-a3b-instruct:free`，真实联调时收到 HTTP 404。进一步核对发现该型号已标记弃用并于 2026-07-19 下线，因此改用当前仍活跃、免费且支持 `tools` 的固定模型 `openai/gpt-oss-20b:free`；同时保留 `openai/gpt-5-mini` 作为免费端点波动或限流时的稳定回退提示。
5. 没有使用 `openrouter/free` 或 `openrouter/auto` 随机路由作为模型 ID。`LLMClient` 要求 `LLM_MODEL` 为固定的 `provider/model` 完整 ID，允许固定模型的 `:free` 后缀，并拒绝空值、`auto` 和免费随机路由，符合计划中“模型可配置但不能硬编码随机模型”的边界。
6. 创建 `app/llm/client.py`，业务层只依赖统一的 `LLMClient.complete()`。SDK Client 的 API Key、base URL、model、timeout、最大重试、temperature、最大输出 token、`parallel_tool_calls=false` 及 OpenRouter 可选归因请求头全部来自集中配置。
7. OpenAI SDK 自带重试被关闭，由项目代码只对限流、网络错误、超时和上游 5xx 做 `LLM_MAX_RETRIES` 控制的短重试，避免 SDK 与业务层叠加重试。鉴权失败、余额/免费额度不足、模型或 Tool Calling 不支持、普通 API 错误和空响应均映射为明确且不泄密的错误码与中文消息。
8. `LLMClient` 将 OpenAI SDK 响应归一化为 `LLMResponse` 和 `LLMToolCall`，Agent 业务代码不直接依赖 SDK 的复杂响应类型；成功日志只记录耗时、实际响应模型名和 token usage，不记录 API Key、Authorization Header 或完整 Prompt。
9. 创建独立 `app/agent/prompts.py`，system prompt 明确政策调用知识库、订单事实调用 ERP、数学问题调用 Calculator、工具失败不得编造、资料不足明确无法确认、条件问题先确认条件后调用后续工具，并要求简洁中文回答。
10. 创建不依赖 LangChain/LangGraph 的 `AgentService`：每轮把完整 messages 和 Tool Registry Schema 交给 LLM；有 Tool Call 时先追加完整 assistant tool-call message，再以对应 `tool_call_id` 追加序列化后的 `ToolResult`；无 Tool Call 时返回最终答案。
11. Tool 参数先进行 JSON 对象解析，再交给现有 Tool Registry 的严格 Pydantic 白名单校验；错误 JSON 转为 `INVALID_ARGUMENT` ToolResult，未知工具转为 `UNKNOWN_TOOL`，两者都会回传模型以生成可理解回答，不动态执行任意名称。
12. Agent 记录 `tool_name + 规范化 JSON 参数`，参数字段顺序和空格不同仍视为相同调用；重复调用立即返回 `REPEATED_TOOL_CALL`，避免模型在工具失败后死循环。执行轮数由 `MAX_AGENT_STEPS` 限制，超限返回 `MAX_AGENT_STEPS_EXCEEDED`。
13. 新增 `AgentTrace` 和 Phase 5 内部 `AgentResult` 契约。Trace 只展示轮次、类型、工具名、安全摘要和耗时，不包含完整参数、业务 Prompt、ERP 密码或 API Key；Phase 6 的 HTTP 层可直接据此组装最终 `ChatResponse`。
14. Tool 返回的 RAG 来源按 `file + page + chunk_id` 累积去重。即使同一来源在不同检索结果或 Tool Call 中重复出现，Agent 最终只返回一份可追踪来源。
15. 新增 `tests/test_agent.py`，使用 Fake LLM 和 Fake Dispatcher 覆盖直接回答、单工具消息协议、条件式两工具调用、来源去重、错误 JSON、重复工具调用、最大轮数和未知工具，不依赖真实 OpenRouter、BGE、ERP 或浏览器。
16. 新增 `tests/test_llm_client.py`，覆盖缺失 API Key、随机模型 ID 拒绝、固定免费模型 ID、Tool Call 响应归一化、token usage、模型参数、最大输出 token 和 `parallel_tool_calls=false`。
17. 新增 `scripts/smoke_agent.py`，提供退款政策、Calculator、订单查询和条件式多工具四个真实模型问题。该脚本只读取本机 `.env`，不接受代码内硬编码 Key，也不会将 Key 写入日志。
18. 完成默认快速回归、包含真实本地 BGE/FAISS 与项目内 Chromium 的完整集成回归、Python 编译检查及 Git 补丁格式检查。

## API Key 手动填写位置

在项目根目录从 `.env.example` 复制一份名为 `.env` 的本机文件，只填写下面字段：

```env
OPENROUTER_API_KEY=你的_OpenRouter_API_Key
LLM_MODEL=openai/gpt-oss-20b:free
```

`.env` 已在 `.gitignore` 中，禁止提交。不要把真实 Key 填入 `.env.example`、Python 文件、`step.md` 或终端命令历史。如果固定免费模型当时限流或下线，可只在本机 `.env` 将模型改为：

```env
LLM_MODEL=openai/gpt-5-mini
```

## Phase 5 项目内环境与运行命令

只向项目虚拟环境安装依赖：

```powershell
$env:UV_CACHE_DIR = (Join-Path (Get-Location) '.uv-cache')
$env:UV_PYTHON_INSTALL_DIR = (Join-Path (Get-Location) '.uv-python')
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```

默认运行 Fake LLM 和其他快速测试，不会调用 OpenRouter：

```powershell
.venv\Scripts\python.exe -m pytest -q
```

运行包含真实 BGE、FAISS、Mock ERP 和项目内 Chromium 的完整本地回归，仍不会调用 OpenRouter：

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = (Join-Path (Get-Location) '.playwright-browsers')
$env:HF_HUB_OFFLINE = '1'
.venv\Scripts\python.exe -m pytest -q --run-integration
```

手填 `.env` 后，先启动 Mock ERP，再在另一个终端执行真实 OpenRouter 冒烟测试：

```powershell
.venv\Scripts\python.exe -m uvicorn mock_erp.app:app --port 8001
.venv\Scripts\python.exe scripts\smoke_agent.py
```

## Phase 5 验收结果

| 验收项 | 结果 | 证据 |
| --- | --- | --- |
| LLM 配置隔离 | 通过 | Client 从集中配置读取 Key、base URL、model、timeout 和重试；业务层不初始化 SDK |
| 固定免费模型 | 通过 | 默认 `openai/gpt-oss-20b:free`，完整 ID 且支持 tools；拒绝 `auto`/随机免费路由 |
| 顺序工具调用 | 通过 | 默认 `parallel_tool_calls=false`，Prompt 明确条件问题先查事实再决定后续工具 |
| 单工具消息循环 | 通过 | Fake LLM 验证 assistant tool_calls 与对应 `tool_call_id` ToolResult 完整回传 |
| 条件式多工具 | 通过 | Fake LLM 依次执行 `query_order`、`search_company_docs` 后生成最终回答 |
| Calculator 选择链路 | 通过 | Tool Schema 包含 Calculator，Fake Client 验证 Tool Call 归一化和 Agent 分发协议 |
| 来源累计去重 | 通过 | 相同 `file + page + chunk_id` 来源只保留一份 |
| 错误参数与未知工具 | 通过 | 均转为统一 ToolResult 回传模型，不产生未处理异常或任意执行 |
| 重复调用保护 | 通过 | 规范化参数后识别重复调用，返回 `REPEATED_TOOL_CALL` |
| 最大轮数保护 | 通过 | 达到配置上限返回 `MAX_AGENT_STEPS_EXCEEDED` 和可理解中文提示 |
| LLM 错误映射 | 通过 | 鉴权、余额、限流、超时、网络、模型不支持、上游 5xx 和普通 API 错误均有明确映射 |
| 默认自动测试 | 通过 | `60 passed, 4 skipped`；跳过项仅为显式本地集成测试 |
| 完整本地集成回归 | 通过 | `64 passed`，真实 BGE/FAISS、Uvicorn Mock ERP 和项目内 headless Chromium 全部正常 |
| Python 编译检查 | 通过 | `python -m compileall -q app mock_erp scripts tests` 成功 |
| Git 补丁格式检查 | 通过 | `git diff --check` 无空白错误 |
| 真实 OpenRouter 四场景 | 通过 | RAG、Calculator、订单 RPA 和条件式 RPA + RAG 均由真实模型正确选择工具并生成中文答案 |

## Phase 5 产物

- LLM Client 与归一化响应：`app/llm/client.py`、`app/llm/__init__.py`
- LLM/配置错误：`app/core/errors.py`
- Agent Prompt 与自写循环：`app/agent/prompts.py`、`app/agent/service.py`
- Agent 契约：更新后的 `app/agent/schemas.py`
- 项目内依赖与模型示例：`requirements.txt`、`.env.example`、`pytest.ini`
- Fake LLM 自动测试：`tests/test_agent.py`、`tests/test_llm_client.py`
- 真实模型手工冒烟入口：`scripts/smoke_agent.py`

## 当前进度与下一阶段边界

- 当前进度：Phase 5 已完整验收。真实模型依次正确调用 `search_company_docs`、`calculate`、`query_order`，综合问题按 `query_order -> search_company_docs` 顺序完成，并返回订单物流和退款政策来源答案。
- 联调观察：免费模型曾触发短时 429，现有有限重试与 `LLM_RATE_LIMITED` 提示正常生效；等待约 30 秒后单独重试成功。正式面试演示前应预热验证，必要时在本机 `.env` 切换 `openai/gpt-5-mini`。
- 下一步：严格进入 Phase 6（FastAPI Chat API）。
- 尚未开始：Phase 6 Chat API、Streamlit、TTS 与 Docker。

## Phase 6 - 已完整验收

- 阶段：Phase 6（FastAPI Chat API）
- 状态：已完成，包括稳定 HTTP 契约、请求校验、request_id、错误映射、OpenAPI 示例和 API 自动测试。
- 完成日期：2026-08-19
- 累计进度：Phase 0 至 Phase 6 已完整验收；下一阶段为 Phase 7（Streamlit 前端）。
- 范围控制：本次只实现 Chat API，没有提前实现 Streamlit、会话持久化、TTS、知识上传或 Docker。

## Phase 6 实施过程

1. 完整核对 `plan.md` 的 Phase 6 目标、8 项具体步骤、统一响应契约和验收项，并参考 `Idea.md` 中订单查询、企业退款政策和条件式 RPA + RAG 三个演示场景。
2. 延续项目内环境隔离规则：Python 继续使用 `.uv-python/` 中的 CPython 3.11.14 和 uv 创建的 `.venv/`，uv 缓存固定在 `.uv-cache/`；本阶段没有新增依赖，也没有修改全局 Python、全局包或系统浏览器。
3. 创建 `app/api/chat.py` 与 API 包，提供 `POST /api/chat`。请求只包含必填 `message` 和可选 `session_id`；`session_id` 仅作为 P2 会话能力的预留字段，本阶段不保存、不读取，也不向 Agent 传递历史上下文。
4. 创建严格的 `ChatRequest`：禁止未知字段，自动去除消息首尾空白，拒绝全空白消息，将消息长度限制为 1 至 2000 个字符，并将可选 `session_id` 限制为 1 至 128 个字符。
5. 创建计划规定的 `ChatResponse`：统一返回 `answer`、`traces`、`sources`、`audio_url` 和 `request_id`。Phase 6 不实现 TTS，因此 `audio_url` 固定为 `null`；Pydantic 模型保证 Agent Trace 与 RAG Source 可稳定序列化为 JSON。
6. 通过 FastAPI Dependency 注入并进程内复用无会话状态的 `AgentService`。测试可用 Fake Agent 替换依赖，不会调用真实 OpenRouter、BGE 或浏览器；生产请求仍连接 Phase 5 已验收的真实 Agent 链路。
7. 调整已有 request-id middleware：每个 HTTP 请求生成新的 UUID，写入 `request.state`、响应 `X-Request-ID` Header 和 `ChatResponse.request_id`，并通过 ContextVar 自动进入该请求期间的全部日志。
8. Chat API 逐条记录 Agent Trace 的轮次、类型、工具名、耗时和安全摘要。日志过滤器会为这些记录附加同一 request_id，因此可以从一次 HTTP 响应反查该次 Agent、LLM、RAG 与 RPA 日志；不记录完整用户 Prompt、API Key、Authorization Header 或 ERP 密码。
9. 为预期业务错误建立 HTTP 状态映射，同时保持统一 ChatResponse：参数问题为 400/422，订单或资料不存在为 404，上游工具或模型故障为 502，模型配置、限流或知识库未就绪为 503，LLM/RPA 超时为 504。Tool 或 Agent 失败不会退化成无信息的默认 500。
10. 为请求校验、LLM 配置和未知异常增加全局处理：校验失败返回统一 422 结构；缺少 Key 或模型配置返回清楚的 503；真正未知异常以 `logger.exception` 保留服务端堆栈，但前端只收到脱敏的 500 提示。
11. 在 OpenAPI 的 ChatRequest Schema 中加入退款政策、订单 10001 和“已发货后再查退款政策”三个核心问题示例；`/docs` 同时说明每个请求独立，RPA 比普通问答慢，调用端超时必须高于 `RPA_TIMEOUT_MS`，演示前端建议至少 120 秒。
12. 新增 `tests/test_chat_api.py`，覆盖成功响应、Trace/Source JSON、Header 与 Body request_id 一致、每次请求独立、三个核心问题统一结构、空白/过长消息、预期超时错误、缺少 LLM 配置、未知异常脱敏、OpenAPI 示例和 `/docs` 可访问。
13. API 测试首次执行发现 pytest-asyncio 严格模式不会自动接管普通 `pytest.fixture` 声明的异步 fixture；改为显式 `pytest_asyncio.fixture` 后定向测试全部通过。该修正只涉及测试生命周期，没有改变运行时代码。
14. 完成默认快速回归、真实本地 BGE/FAISS、Mock ERP、项目内 Chromium 的完整集成回归、Python 编译、uv 依赖兼容性和 Git 补丁格式检查。本阶段没有进行新的真实 OpenRouter 付费/限流调用；Phase 5 已完成相同 Agent 的四场景真实联调，Phase 6 使用 Fake Agent 确定性验证 HTTP 包装层。

## Phase 6 项目内环境与运行命令

只检查项目虚拟环境，不修改全局依赖：

```powershell
$env:UV_CACHE_DIR = (Join-Path (Get-Location) '.uv-cache')
$env:UV_PYTHON_INSTALL_DIR = (Join-Path (Get-Location) '.uv-python')
uv pip check --python .venv\Scripts\python.exe
```

启动后端并打开交互式 API 文档：

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
# 浏览器访问 http://localhost:8000/docs
```

调用 Chat API；订单/RPA 或综合问题的客户端超时应高于 `RPA_TIMEOUT_MS`，建议至少 120 秒：

```powershell
$body = @{ message = '退款多久到账？' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/chat -ContentType 'application/json' -Body $body -TimeoutSec 120
```

默认快速回归，不调用 OpenRouter、不加载真实模型和浏览器：

```powershell
.venv\Scripts\python.exe -m pytest -q
```

包含真实 BGE/FAISS、Mock ERP 和项目内 Chromium 的完整本地回归，仍不调用 OpenRouter：

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = (Join-Path (Get-Location) '.playwright-browsers')
$env:HF_HUB_OFFLINE = '1'
.venv\Scripts\python.exe -m pytest -q --run-integration
```

## Phase 6 验收结果

| 验收项 | 结果 | 证据 |
| --- | --- | --- |
| `POST /api/chat` | 通过 | Fake Agent API 测试验证请求进入 Agent，并返回统一 ChatResponse |
| 消息与会话字段校验 | 通过 | 空字符串、全空白、超过 2000 字符、空 session_id 和未知字段由严格模型拒绝 |
| 三个核心问题 | 通过 | 退款、订单和条件式综合问题均返回相同的 5 字段结构 |
| Trace 与 Source JSON | 通过 | 工具 Trace、中文来源内容、页码、chunk ID 和 score 均正确序列化 |
| request_id 贯通 | 通过 | 每次请求生成不同 UUID；响应 Header 与 Body 一致；Trace 日志共享 ContextVar request_id |
| 单轮请求隔离 | 通过 | 相同 session_id 的两个请求只将各自当前 message 交给 Agent，不共享历史 |
| 预期错误结构 | 通过 | Agent 超时返回统一 504 ChatResponse，不返回默认 HTML 或无信息 500 |
| 未知异常脱敏 | 通过 | 服务端保留堆栈，响应不包含测试注入的内部异常细节 |
| OpenAPI 与 `/docs` | 通过 | `/docs`、`/openapi.json` 可访问，Schema 含三个核心问题示例和超时说明 |
| API 定向测试 | 通过 | `13 passed` |
| 默认自动测试 | 通过 | `72 passed, 4 skipped`；跳过项仅为显式本地集成测试 |
| 完整本地集成回归 | 通过 | `76 passed`，真实 BGE/FAISS、Uvicorn Mock ERP 和项目内 headless Chromium 全部正常 |
| uv 环境兼容性 | 通过 | `uv pip check --python .venv\Scripts\python.exe` 检查 71 个包，全部兼容 |
| Python 编译检查 | 通过 | `python -m compileall -q app mock_erp scripts tests` 成功 |
| Git 补丁格式检查 | 通过 | `git diff --check` 无空白错误 |

## Phase 6 产物

- Chat API、请求/响应模型、错误映射和 OpenAPI 示例：`app/api/chat.py`
- API 包：`app/api/__init__.py`
- request_id middleware 与全局异常处理：更新后的 `app/main.py`
- Fake Agent API 自动测试：`tests/test_chat_api.py`

## 当前进度与下一阶段边界

- 当前进度：Phase 6 已完整验收。FastAPI 已通过统一 HTTP 契约暴露 Phase 5 Agent，`/docs` 可直接查看并调用三个核心问题。
- 已确认边界：每次请求独立，`session_id` 暂不持久化；前端需要使用高于 RPA 超时的 HTTP timeout；TTS 尚未实现，所以 `audio_url=null`。
- 下一步：严格按照 `plan.md` 进入 Phase 7（Streamlit 前端），前端只通过 HTTP 调用本阶段 API，并使用自身 `session_state` 展示界面历史。
- 尚未开始：Phase 7 Streamlit、Phase 8 TTS、Docker 与 P2 会话持久化。

## Phase 7 - 已完整验收

- 阶段：Phase 7（Streamlit 前端）
- 状态：已完成，包括 HTTP-only 前端客户端、界面聊天历史、三个示例问题、执行轨迹、折叠来源、用户错误提示、服务状态和响应式布局检查。
- 完成日期：2026-08-20
- 累计进度：Phase 0 至 Phase 7 已完整验收，M3（完整 Agent 多工具链路和 UI）达到核心完成标准；下一阶段为 Phase 8（TTS，P1）。
- 范围控制：本次没有提前实现 TTS 服务、会话持久化、知识上传、复杂 CSS、动态图表、登录或 Docker；语音播放按钮仅作为 Phase 8 的禁用占位。

## Phase 7 实施过程

1. 严格以 `plan.md` 的阶段编号为准，将 Phase 7 定义为 Streamlit 前端；`Idea.md` 中较早版本的 Phase 7（TTS）不覆盖修订计划，TTS 继续留在 Phase 8。参考 `Idea.md` 的核心退款政策、订单查询和条件式 RPA + RAG 场景设计页面内容。
2. 延续项目内环境隔离：Python 使用 uv 管理的项目 `.venv/`，uv 缓存和 Python 下载目录分别固定为 `.uv-cache/` 与 `.uv-python/`。新增 `streamlit>=1.47,<2.0` 后只安装到项目虚拟环境，实际解析版本为 `streamlit==1.62.0`，没有修改全局 Python、全局包或系统浏览器。
3. 创建 `frontend/client.py`，前端只通过 HTTP 调用 FastAPI 的 `GET /health` 和 `POST /api/chat`，没有导入 Agent、RAG 或 RPA 模块。Chat 超时为 120 秒，高于 RPA 超时；健康检查使用 2 秒短超时。
4. 在前端侧复制并校验公开 HTTP 数据契约，包括 answer、traces、sources、audio_url 和 request_id；未知额外字段允许忽略，缺失必要字段或非 JSON 响应会转换为面向用户的“后端返回格式异常”短提示。
5. HTTP 200 响应显示正常答案；后端 4xx/5xx 的统一 ChatResponse 保留 answer、trace、source 和 request_id 并作为错误样式展示。连接拒绝、请求超时和普通 HTTP 通信异常分别映射为可操作的中文提示，不向用户暴露内部异常。
6. 创建 `frontend/streamlit_app.py`，使用 `st.session_state` 保存 UI 聊天历史和一个仅用于请求标识的 UI session_id。后端仍按 Phase 6 契约只处理当前问题，因此界面历史不等于 LLM 会话记忆。
7. 页面顶部显示项目标题、技术链路、后端在线/离线状态和“所有订单和公司资料均为模拟数据”声明；主区显示聊天历史、三个示例按钮和最大 2000 字符输入框；右侧显示最新一次 Agent 执行轨迹。
8. 三个示例按钮分别对应退款政策、订单 10001 和条件式订单 + 退款政策问题。提交期间显示 spinner，明确订单查询可能启动 ERP 浏览器；请求完成后触发 Streamlit rerun，从 session_state 恢复全部历史。
9. Trace 逐项显示步骤号、工具名、成功/失败图标、安全摘要和耗时，并在面板底部显示 request_id。多工具响应可同时看到 `query_order` 和 `search_company_docs`，便于面试时展示 Agent 的决策过程。
10. RAG Source 在每条助手回答下方使用默认收起的 expander，显示文件名、页码、chunk ID、相似度和命中文本；没有来源时不创建空面板，避免页面过长。
11. 回答下方保留禁用的“语音播放（Phase 8）”按钮并明确说明尚未实现，保证阶段边界真实，不伪造可用 TTS 能力。
12. 创建 `tests/test_frontend_client.py`，使用 `httpx.MockTransport` 覆盖 health/chat HTTP 路径、session_id、成功契约、结构化后端错误、连接失败和异常响应契约，不依赖真实 OpenRouter、ERP 或浏览器。
13. 创建 `tests/test_frontend_app.py`，使用 Streamlit 官方 `AppTest` 覆盖初始布局、服务状态、三个示例按钮、单一 UI session_id、六条历史消息、多工具轨迹、默认折叠来源、重复提问历史和后端断连错误显示。
14. 使用真实 Streamlit 进程完成启动冒烟检查：`/_stcore/health` 返回 200/ok，首页返回 200。随后通过本地浏览器分别检查默认桌面、1366×768、768×900 和 430×900 视口；常用笔记本布局保持主区和右侧轨迹，窄屏自动压缩或纵向堆叠，关键控件仍清楚可读。
15. 完成默认快速回归、真实本地 BGE/FAISS、Mock ERP、项目内 Chromium 的完整集成回归、Python 编译、uv 依赖兼容性和 Git 补丁格式检查。Phase 7 自动验收使用 Fake HTTP 保持确定性，没有再次消耗 OpenRouter 额度；Phase 5 已完成同一 Agent 四个真实问题的模型联调。

## Phase 7 项目内环境与运行命令

仅向项目虚拟环境安装或检查依赖：

```powershell
$env:UV_CACHE_DIR = (Join-Path (Get-Location) '.uv-cache')
$env:UV_PYTHON_INSTALL_DIR = (Join-Path (Get-Location) '.uv-python')
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
uv pip check --python .venv\Scripts\python.exe
```

分别启动 Mock ERP、FastAPI 和 Streamlit；每条命令在项目根目录的独立终端执行：

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = (Join-Path (Get-Location) '.playwright-browsers')
.venv\Scripts\python.exe -m uvicorn mock_erp.app:app --port 8001

.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000

.venv\Scripts\python.exe -m streamlit run frontend\streamlit_app.py --server.port 8501
# 浏览器访问 http://localhost:8501
```

前端通过根目录 `.env` 的 `BACKEND_URL` 访问后端，默认值为 `http://localhost:8000`。订单查询需要 Mock ERP；RAG 问题需要已构建向量索引；所有真实 Agent 问题都需要在本机 `.env` 填写有效 `OPENROUTER_API_KEY`。

运行 Phase 7 定向测试和默认回归：

```powershell
.venv\Scripts\python.exe -m pytest -q tests\test_frontend_client.py tests\test_frontend_app.py
.venv\Scripts\python.exe -m pytest -q
```

运行包含真实本地 BGE/FAISS、Mock ERP 和项目内 Chromium 的完整回归，仍不会调用 OpenRouter：

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = (Join-Path (Get-Location) '.playwright-browsers')
$env:HF_HUB_OFFLINE = '1'
.venv\Scripts\python.exe -m pytest -q --run-integration
```

## Phase 7 验收结果

| 验收项 | 结果 | 证据 |
| --- | --- | --- |
| HTTP-only 前端边界 | 通过 | `frontend/` 不导入 Agent、RAG 或 RPA；只调用 `/health` 与 `/api/chat` |
| 三个示例问题按钮 | 通过 | AppTest 依次点击三个按钮，Fake Client 收到计划规定的三个完整问题 |
| UI 聊天历史 | 通过 | 三次示例调用保留 6 条 user/assistant 消息；重复手输同一问题仍保留此前历史 |
| 单轮后端语义 | 通过 | UI 可复用 session_id 便于标识，但每次只向 API 发送当前 message，不发送历史 |
| 请求等待提示与超时 | 通过 | spinner 提示 Agent/ERP 执行；Chat 客户端超时固定为 120 秒 |
| Agent 执行轨迹 | 通过 | 显示步骤、工具名、成功/失败、耗时、摘要和 request_id；综合问题显示两个工具步骤 |
| RAG 来源 | 通过 | 显示 PDF 文件、页码、chunk、分数和片段；expander 默认收起 |
| 用户错误提示 | 通过 | 结构化 4xx/5xx、连接失败、超时和错误响应格式均有短中文提示 |
| 模拟数据声明 | 通过 | 页面顶部明确标注所有订单与公司资料均为模拟数据 |
| 后端关闭场景 | 通过 | health 显示离线警告，提交问题后在聊天区显示连接错误，不产生 UI 未处理异常 |
| 笔记本与窄屏 | 通过 | 实际检查 1366×768、768×900、430×900；关键控件可读，窄屏纵向堆叠 |
| Streamlit 进程冒烟 | 通过 | 本地 `:8501/_stcore/health` 为 200/ok，首页为 200 |
| Phase 7 定向测试 | 通过 | `9 passed` |
| 默认自动测试 | 通过 | `81 passed, 4 skipped`；跳过项仅为显式本地集成测试 |
| 完整本地集成回归 | 通过 | `85 passed`，真实 BGE/FAISS、Uvicorn Mock ERP 和项目内 headless Chromium 全部正常 |
| uv 环境兼容性 | 通过 | `uv pip check --python .venv\Scripts\python.exe` 检查 90 个包，全部兼容 |
| Python 编译检查 | 通过 | `python -m compileall -q app frontend mock_erp scripts tests` 成功 |
| Git 补丁格式检查 | 通过 | `git diff --check` 无空白错误 |

## Phase 7 产物

- Streamlit 页面与 session_state UI 历史：`frontend/streamlit_app.py`
- HTTP Client、前端响应模型和错误翻译：`frontend/client.py`
- Frontend 包：`frontend/__init__.py`
- Streamlit 项目依赖：更新后的 `requirements.txt`
- HTTP Client 自动测试：`tests/test_frontend_client.py`
- Streamlit AppTest 自动测试：`tests/test_frontend_app.py`

## 当前进度与下一阶段边界

- 当前进度：Phase 0 至 Phase 7 已完整验收，M3 已完成。完整 Agent 多工具链路现在具有可演示 UI，能展示答案、来源与执行轨迹。
- 已确认边界：UI 历史只存在于当前 Streamlit session；后端 Agent 仍按单轮问题独立处理。TTS 按钮目前禁用，`audio_url` 仍为 null。
- 下一步：严格按照 `plan.md` 进入 Phase 8（TTS，P1），先通过独立 TTS API 生成音频，再启用前端播放按钮。
- 尚未开始：Phase 8 TTS、Phase 9 演示稳定性增强、Phase 10 Docker、Phase 11 README/简历材料，以及 P2 会话持久化和知识上传。

## Phase 8 - 已完整验收

- 阶段：Phase 8（TTS，P1）
- 状态：已完成，包括按需中文语音生成、本地 MP3 保存、独立 TTS API、安全静态音频访问、Streamlit 播放、重复点击复用、失败隔离和过期清理。
- 完成日期：2026-08-20
- 累计进度：Phase 0 至 Phase 8 已完整验收，项目已具备文字 Agent 核心链路和可选语音输出；下一阶段为 Phase 9（测试、日志与演示稳定性）。
- 范围控制：本次只实现 `plan.md` 规定的单一 TTS Provider，没有增加 ASR、流式语音、本地 TTS 模型、多 Provider 后台、Avatar 假实现、会话持久化、Docker 或知识上传。

## Phase 8 实施过程

1. 严格以 `plan.md` 的修订阶段为准，将 Phase 8 定义为 TTS；`Idea.md` 仅用于“LLM 回答 → TTS 音频 → 未来数字人输入”的项目背景，不采用其中旧版 Phase 7/8 编号。
2. 采用已确认的单一 Provider `edge-tts` 和中文音色 `zh-CN-XiaoxiaoNeural`。TTS 与 OpenRouter LLM、Agent Loop 和三个业务 Tool 完全解耦，不新增模型下载或 TTS API Key；只有用户点击按钮时才访问在线语音服务。
3. 延续项目内环境隔离：向 `requirements.txt` 增加 `edge-tts>=7.2,<8.0`，使用 uv 只安装到项目 `.venv/`，uv 缓存和 Python 安装目录继续固定为 `.uv-cache/` 与 `.uv-python/`。实际解析为 `edge-tts==7.2.8`，没有修改全局 Python、全局包或系统环境版本。
4. 在集中配置中增加 `TTS_VOICE`、`TTS_MAX_TEXT_LENGTH`、`TTS_TIMEOUT_SECONDS` 和 `AUDIO_RETENTION_HOURS`；默认分别为 `zh-CN-XiaoxiaoNeural`、2000 字符、30 秒和 24 小时，并同步更新 `.env.example`。
5. 创建 `app/tts/service.py`，实现最小 `TTSService.synthesize(text) -> Path`。每次成功请求使用 UUID 作为文件名，将 MP3 保存到配置的 `data/audio/`；生成空文件、Provider 异常或超时时统一转换为安全中文错误，并删除可能残留的部分文件。
6. 创建音频生命周期清理函数，只扫描配置音频目录下的 `*.mp3`，后端启动时删除超过保留时间的文件；不会递归删除目录，也不会触碰其他扩展名文件。`data/audio/` 已由现有 `.gitignore` 排除，不会提交运行时音频。
7. 创建独立 `POST /api/tts`。请求仅接受一个去除首尾空白后的非空 `text`，拒绝未知字段和超过 2000 字符的文本；成功返回 `/audio/<UUID>.mp3` 与 request_id，Provider 失败返回 502，超时返回 504，校验失败返回 422。
8. 在 FastAPI 中挂载只读 `/audio` 静态路径，浏览器可通过后端 URL 获取生成的 MP3；TTS 使用自己的成功和错误响应模型，未改变原有 `/api/chat` 契约，ChatResponse 的 `audio_url` 仍保持按需生成前为 null。
9. 扩展前端 HTTP Client，增加独立 TTS 超时、成功响应校验和错误翻译。只接受后端 `/audio/` 相对路径并拼接为同一 Backend URL，拒绝外部音频 URL，避免由响应数据把播放器重定向到任意站点。
10. 将 Phase 7 的禁用占位按钮替换为每条正常 AI 回答下方的“生成语音”按钮。首次点击把当前 assistant answer 发送给 TTS API；成功后把 audio_url 保存到该条 Streamlit session 消息并使用 `st.audio` 播放，页面刷新或重复渲染不会再次请求 Provider。
11. TTS 失败只在对应回答下显示短提示，原文字答案、来源和 Agent Trace 全部保留，按钮仍可重试；后端 Chat/Agent 错误消息不提供语音按钮，避免为错误提示创建无价值音频。
12. 创建 `tests/test_tts_service.py`，通过可替换 Communicator 覆盖指定中文音色、UUID MP3、本地写入、Provider 异常、超时、部分文件删除，以及只清理过期 MP3 的边界。
13. 创建 `tests/test_tts_api.py`，通过 Fake TTS Service 覆盖文本规范化、空文本、纯空格、超长文本、缺字段、502/504 映射、request_id、OpenAPI 路径和真实 FastAPI 静态 MP3 响应。
14. 扩展前端 Client 与 Streamlit AppTest，覆盖 TTS HTTP 请求、相对音频 URL 解析、外部 URL 拒绝、首次点击生成、session 内重复复用、`st.audio` 渲染，以及失败后保留回答并允许重试。
15. 使用项目 `.venv` 中的真实 `edge-tts==7.2.8` 联网生成中文句子“AI 数字员工语音功能测试成功。”，得到 20,736 字节 MP3，确认当前音色与在线服务可用；验证后删除该明确的冒烟文件，没有在仓库中遗留测试音频。
16. 完成 Phase 8 定向测试、默认回归、真实本地 BGE/FAISS、Mock ERP 和项目内 Chromium 的完整集成回归、Python 编译、uv 依赖兼容性和 Git 补丁格式检查。自动测试中的 TTS Provider 使用 Fake 保持稳定，真实在线调用仅作为手工冒烟，避免测试套件依赖外部服务。

## Phase 8 项目内环境与运行命令

依赖只安装到项目虚拟环境：

```powershell
$env:UV_CACHE_DIR = (Join-Path (Get-Location) '.uv-cache')
$env:UV_PYTHON_INSTALL_DIR = (Join-Path (Get-Location) '.uv-python')
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
uv pip check --python .venv\Scripts\python.exe
```

服务启动命令与 Phase 7 相同；TTS 不需要单独进程，包含在 FastAPI Backend 中：

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
.venv\Scripts\python.exe -m streamlit run frontend\streamlit_app.py --server.port 8501
```

TTS API 示例：

```http
POST http://localhost:8000/api/tts
Content-Type: application/json

{"text":"订单 10001 已经发货。"}
```

成功响应中的 `/audio/<UUID>.mp3` 由同一 Backend 提供。实际语音生成需要后端可以访问互联网，但不需要新的 API Key。

运行 Phase 8 定向测试、默认回归和完整本地集成回归：

```powershell
.venv\Scripts\python.exe -m pytest -q tests\test_tts_service.py tests\test_tts_api.py tests\test_frontend_client.py tests\test_frontend_app.py
.venv\Scripts\python.exe -m pytest -q

$env:PLAYWRIGHT_BROWSERS_PATH = (Join-Path (Get-Location) '.playwright-browsers')
$env:HF_HUB_OFFLINE = '1'
.venv\Scripts\python.exe -m pytest -q --run-integration
```

## Phase 8 验收结果

| 验收项 | 结果 | 证据 |
| --- | --- | --- |
| 中文回答生成 | 通过 | 真实 `edge-tts==7.2.8` + `zh-CN-XiaoxiaoNeural` 生成 20,736 字节中文 MP3 |
| 本地音频保存 | 通过 | UUID 文件写入 `data/audio/`，目录不存在时自动创建且已被 Git 忽略 |
| 独立 TTS API | 通过 | `POST /api/tts` 返回 audio_url/request_id；OpenAPI 包含独立 `tts` tag |
| 安全音频访问 | 通过 | `/audio/<filename>.mp3` 返回 `audio/mpeg`；前端拒绝非 `/audio/` URL |
| 文本限制 | 通过 | 空字符串、纯空格、缺少 text、超过 2000 字符和未知字段均拒绝 |
| Streamlit 按需播放 | 通过 | 每条正常回答提供生成按钮；成功后由 `st.audio` 使用 Backend 音频 URL |
| 重复点击行为 | 通过 | 首次成功后 audio_url 保存在对应 UI 消息；rerun 不再次调用 TTS |
| TTS 故障隔离 | 通过 | Provider 失败/超时不改变文字、来源或 Trace；显示短提示并允许重试 |
| 临时文件清理 | 通过 | 失败/超时删除部分文件；启动时只删除超过 24 小时的 MP3 |
| Phase 8 定向测试 | 通过 | `27 passed`，覆盖 Service、API、Frontend Client 和 Streamlit UI |
| 默认自动测试 | 通过 | 最终 `99 passed, 4 skipped`；跳过项仅为显式本地集成测试 |
| 完整本地集成回归 | 通过 | 最终 `103 passed`，真实 BGE/FAISS、Mock ERP、项目内 headless Chromium 全部正常 |
| uv 环境兼容性 | 通过 | `uv pip check --python .venv\Scripts\python.exe` 检查 99 个包，全部兼容 |
| Python 编译检查 | 通过 | `python -m compileall -q app frontend mock_erp scripts tests` 成功 |
| Git 补丁格式检查 | 通过 | `git diff --check` 无空白错误 |

## Phase 8 产物

- TTS API 与请求/响应契约：`app/api/tts.py`
- Edge TTS 服务、本地 UUID MP3 和过期清理：`app/tts/service.py`
- TTS 包：`app/tts/__init__.py`
- TTS 错误类型：更新后的 `app/core/errors.py`
- TTS 配置：更新后的 `app/core/config.py` 与 `.env.example`
- TTS Router、启动清理和 `/audio` 静态目录：更新后的 `app/main.py`
- 前端 TTS HTTP Client 与安全音频 URL：更新后的 `frontend/client.py`
- 按需生成、播放、复用和失败提示：更新后的 `frontend/streamlit_app.py`
- Provider 依赖：更新后的 `requirements.txt`
- TTS Service/API 自动测试：`tests/test_tts_service.py`、`tests/test_tts_api.py`
- 前端 TTS 自动测试：更新后的 `tests/test_frontend_client.py`、`tests/test_frontend_app.py`

## 当前进度与下一阶段边界

- 当前进度：Phase 0 至 Phase 8 已完整验收。用户可先完成文本聊天，再按需为任一正常 AI 回答生成并播放中文语音；TTS 故障不影响核心 Agent 演示。
- 已确认边界：音频只保存在 Backend 本地 `data/audio/`，默认保留 24 小时；Streamlit 的 audio_url 复用只存在于当前 UI session，不等于服务端会话持久化。
- 下一步：严格按照 `plan.md` 进入 Phase 9（测试、日志与演示稳定性），集中增强演示前检查和故障恢复，不在 Phase 8 提前实现 Docker。
- 尚未开始：Phase 9 演示稳定性增强、Phase 10 Docker、Phase 11 README/简历材料，以及 P2 会话持久化、知识上传和数字人服务。

## Phase 9 - 实现完成，真实稳定模型验收待配置

- 阶段：Phase 9（测试、日志与演示稳定性）
- 实现状态：代码、分层测试、日志契约和演示前检查工具已完成；默认回归与完整本地集成回归全部通过。
- 真实验收状态：OpenRouter 网络、鉴权、Models API、tools 能力与 Credits API 检查通过；当前本机 `.env` 使用 `openai/gpt-oss-20b:free` 且可用余额为 0，三个真实问题中前两个通过，综合问题出现不稳定行为，因此尚不能把当前模型配置标记为“面试时稳定能跑”。
- 完成日期：2026-08-20
- 累计进度：Phase 0 至 Phase 8 已完整验收；Phase 9 实现和本地自动验收完成，等待将本机 `.env` 切换到 `plan.md` 指定的稳定模型并准备可用额度后，重新执行真实 Demo 验收。
- 范围控制：本次没有实现 Phase 10 Docker、Phase 11 README/简历材料、会话持久化或知识上传；按任务要求不准备、不检查录屏和截图。

## Phase 9 实施过程

1. 严格以 `plan.md` 的 Phase 9 为执行范围，并参考 `Idea.md` 中“Multi-Step Demo 必须稳定”“日志展示 Tool Call”“先保证代码可运行和测试”的背景要求；没有采用 `Idea.md` 的旧阶段编号，也没有提前进入 Docker。
2. 先审计 Phase 9 必测清单。原有测试已覆盖订单 `10001`、未发货订单 `10002`、不存在订单、退款政策命中、无关政策拒答、正常计算、除零、恶意表达式、Tool 参数错误、RPA 超时、最大 Agent 步数、综合问题两个工具和来源去重；本阶段补齐了 OpenRouter 超时映射的显式测试。
3. 增强 Agent 可观测性：每一轮 LLM 调用记录 round、耗时和 Tool Call 数量；每个工具记录名称、成功状态、耗时和错误码；达到最大轮数时记录明确警告。日志不写用户完整问题、完整 prompt、工具参数、API Key 或 Authorization header。
4. 增强工具异常日志：Tool Registry 捕获未预期执行器异常时使用异常堆栈日志，同时继续向 Agent 返回安全的 `TOOL_INTERNAL_ERROR`，既保留诊断证据，也不把内部异常暴露给用户。
5. 增强 RPA 页面阶段日志：依次记录打开登录页、登录成功、开始搜索订单、打开订单详情和读取详情完成；自动测试明确断言日志不包含 Mock ERP 密码。
6. 增强 RAG 检索日志：记录 `top_k`、实际命中数、文件名和相似度分数；无匹配和低于阈值分别记录安全摘要，不记录完整用户查询或命中文本内容。
7. 创建 `app/core/preflight.py`，把演示检查拆成可单测的非破坏性检查：`.env` 必填项、固定模型 ID、ERP seed、FAISS/metadata/manifest 完整性、索引模型一致性、端口、项目内 Chromium 实际启动、Mock ERP 可访问性、OpenRouter 模型 tools 能力和 Credits 余额。
8. 创建 `scripts/preflight.py`。`pre-start` 模式用于服务启动前检查 8000/8001/8501 空闲和全部本地/在线依赖；`demo` 模式用于 Mock ERP 启动后依次真实执行三个固定面试问题，并验证所需工具和 RAG Source。
9. 演示问题检查不仅验证 `error_code`、工具名和来源，还拒绝空回答及“同一字符大量重复”的明显退化回答，避免模型虽然调用工具但输出无意义文本时产生假阳性。
10. 为排障提供 `--offline`，只跳过 OpenRouter 网络与余额项并明确显示 `SKIP`；正式演示前必须不带该参数运行。检查输出仅显示密钥“已配置”，永远不输出密钥值。
11. 按计划加入 TTS 降级说明：语音失败时保留文字回答并跳过 TTS，不影响核心 Agent 链路。按本次任务要求，预检明确说明录屏和截图不在检查范围。
12. 将 `.env.example` 的默认模型从不稳定免费端点恢复为 `plan.md` 指定的 `openai/gpt-5-mini`，并明确不能把免费模型作为唯一演示方案；没有修改本机 `.env`、真实 API Key 或用户当前模型选择。
13. 创建 `tests/test_preflight.py`，覆盖配置/密钥脱敏、ERP seed、真实小向量索引、OpenRouter Models/Credits Fake HTTP、三个问题只运行一次、必要工具、来源要求和退化回答拒绝。
14. 创建 `tests/test_observability.py`，覆盖 Agent 轮次与工具日志、耗时、prompt/API Key 不泄漏、RAG top_k/文件/分数日志，以及工具未预期异常保留堆栈。
15. 完成项目内 uv 环境的定向测试、默认回归、真实本地 BGE/FAISS + Mock ERP + 项目内 Chromium 完整集成回归、Python 编译、uv 依赖兼容性和 Git 补丁格式检查；未安装或修改任何全局 Python、浏览器或系统版本。
16. 真实联网 `pre-start` 检查确认当前 OpenRouter 模型仍在 Models API 中且声明支持 `tools`，Credits API 返回剩余额度 `0.0000`；由于当前模型以 `:free` 结尾，余额项允许免费端点继续接受请求。
17. 真实 `demo` 检查中，退款问题成功调用 `search_company_docs` 并返回 1 个来源，订单问题成功调用 `query_order`；综合问题第一次未调用两个必要工具。单独诊断重试时两个工具均执行，但最终回答退化为重复感叹号。该结果证明本地 RAG/RPA 正常，但当前免费模型不满足 Phase 9 的演示稳定性目标，因此如实保留为待办，不以偶发通过冒充完整验收。

## Phase 9 项目内环境与运行命令

所有命令继续使用项目 `.venv/`，uv 缓存和 Python 下载目录仍限制在项目文件夹：

```powershell
$env:UV_CACHE_DIR = (Join-Path (Get-Location) '.uv-cache')
$env:UV_PYTHON_INSTALL_DIR = (Join-Path (Get-Location) '.uv-python')
$env:PLAYWRIGHT_BROWSERS_PATH = (Join-Path (Get-Location) '.playwright-browsers')
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
uv pip check --python .venv\Scripts\python.exe
```

服务启动前执行完整预检；`--offline` 仅用于无网络排障：

```powershell
.venv\Scripts\python.exe scripts\preflight.py pre-start
.venv\Scripts\python.exe scripts\preflight.py pre-start --offline
```

真实 Demo 验收需要先在独立终端启动 Mock ERP，再运行 Demo 模式。自动验收或不希望显示浏览器时使用 headless：

```powershell
.venv\Scripts\python.exe -m uvicorn mock_erp.app:app --port 8001

$env:RPA_HEADLESS = 'true'
$env:HF_HUB_OFFLINE = '1'
.venv\Scripts\python.exe scripts\preflight.py demo
```

运行 Phase 9 定向、默认和完整本地集成回归：

```powershell
.venv\Scripts\python.exe -m pytest -q tests\test_preflight.py tests\test_observability.py tests\test_llm_client.py
.venv\Scripts\python.exe -m pytest -q

$env:PLAYWRIGHT_BROWSERS_PATH = (Join-Path (Get-Location) '.playwright-browsers')
$env:HF_HUB_OFFLINE = '1'
.venv\Scripts\python.exe -m pytest -q --run-integration
```

## Phase 9 验收结果

| 验收项 | 结果 | 证据 |
| --- | --- | --- |
| Phase 9 必测业务清单 | 通过 | 订单 10001/10002/不存在、RAG 命中/拒答、Calculator 正常/除零/恶意表达式、参数错误、LLM/RPA 超时、最大步数、双工具、来源去重均有自动测试 |
| request_id | 通过 | 每个 Chat/TTS 请求继续由中间件生成 UUID，响应体与 `X-Request-ID` 一致，日志格式带 request_id |
| LLM 轮次与耗时日志 | 通过 | Agent 记录每轮 round/duration/tool_calls；LLM Client 记录请求耗时、模型与 token 数 |
| 工具名称、状态与耗时日志 | 通过 | Agent 记录 tool/success/duration/error_code；未预期异常记录堆栈 |
| RPA 页面阶段与密码保护 | 通过 | 完整集成测试断言五个页面阶段均出现，且日志不含 `admin123` |
| RAG 检索日志 | 通过 | 自动测试断言 top_k、命中文件和 scores 存在，完整查询不进入日志 |
| 敏感信息保护 | 通过 | 自动测试断言用户问题标记和 API Key 标记不在日志；代码不记录 Authorization 或完整 prompt |
| 演示前本地检查 | 通过 | seed、4 个向量/4 个 PDF、索引模型、项目内 Chromium 实际启动、8000/8001/8501 空闲均通过 |
| OpenRouter 网络与能力检查 | 通过 | 真实 Models API/鉴权通过，当前模型声明支持 tools |
| OpenRouter 余额检查 | 有条件通过 | Credits API 可访问，当前剩余额度为 0；仅因当前模型是 `:free` 才允许继续，稳定付费模型尚无可用额度 |
| 三个真实示例问题 | 未完整通过 | 前两题通过；综合题在当前免费模型上一次漏调工具，诊断重试又产生重复字符回答 |
| Phase 9 新增定向测试 | 通过 | `14 passed` |
| 默认自动测试 | 通过 | `109 passed, 4 skipped`；跳过项仅为显式本地集成测试 |
| 完整本地集成回归 | 通过 | `113 passed`，真实 BGE/FAISS、临时 Uvicorn Mock ERP、项目内 headless Chromium 全部正常 |
| uv 环境兼容性 | 通过 | `uv pip check --python .venv\Scripts\python.exe` 检查 99 个包，全部兼容 |
| Python 编译检查 | 通过 | `python -m compileall -q app frontend mock_erp scripts tests` 成功 |
| Git 补丁格式检查 | 通过 | `git diff --check` 无空白错误 |

## Phase 9 产物

- 可复用的演示检查逻辑：`app/core/preflight.py`
- 命令行预启动/真实 Demo 检查：`scripts/preflight.py`
- Agent 轮次、工具状态与耗时日志：更新后的 `app/agent/service.py`
- Tool 异常堆栈日志：更新后的 `app/agent/tool_registry.py`
- RAG top_k、文件和分数日志：更新后的 `app/rag/retriever.py`
- RPA 页面阶段日志：更新后的 `app/rpa/order_query.py`
- 稳定模型示例配置：更新后的 `.env.example`
- 演示检查自动测试：`tests/test_preflight.py`
- 安全日志自动测试：`tests/test_observability.py`
- LLM 超时与 RPA 日志断言：更新后的 `tests/test_llm_client.py`、`tests/integration/test_order_query.py`

## 当前进度与下一阶段边界

- 已完成：Phase 9 的代码实现、分层自动测试、日志增强、演示前检查脚本和本地完整集成验收。
- 待用户配置后复验：在本机 `.env` 将 `LLM_MODEL` 切换为 `openai/gpt-5-mini` 或另一个经过验证的稳定 Tool Calling 模型，并准备可用 OpenRouter 额度；随后重新运行 `scripts/preflight.py pre-start` 与 `scripts/preflight.py demo`，要求三个示例问题一次全部通过。
- 阶段门槛：在稳定模型真实 Demo 通过前，不把 Phase 9 标记为“完整验收”；Phase 10 后续已按用户要求忽略，不再作为进入下一阶段的门槛。
- 后续状态：Phase 10 Docker 已忽略，Phase 11 README 已完成；P2 会话持久化、知识上传和数字人服务仍未开始。

## Phase 11 - README 已完成

- 阶段：Phase 11（README、简历和面试材料）
- 实现状态：项目 README 编写完成，并提供中文优先、英文可切换的双语内容。
- 完成日期：2026-08-20
- 项目名称：`Nova AI Agent Employee`（仓库代号 `nova-ai-agent-employee`）。
- 累计进度：Phase 0 至 Phase 8 已完整验收；Phase 9 代码与本地自动验收完成、稳定模型真实三题复验待用户配置；Phase 10 已按本次任务要求忽略；Phase 11 README 已完成。
- 范围控制：按任务要求忽略演示 GIF/截图和 Docker 运行；没有创建或修改 Dockerfile、Compose、录屏、截图、业务代码、密钥或本机 `.env`。

## Phase 11 实施过程

1. 严格读取 `plan.md` 的 Phase 11 README 最终结构，并以 `Idea.md` 的企业知识库、RPA、Calculator、多工具 Agent、TTS、面试展示和最终验收要求作为项目背景。
2. 审计现有代码、配置、脚本、API、测试和 Phase 9 记录，确保 README 只描述已经存在的 `search_company_docs`、`query_order`、`calculate`、FastAPI、Streamlit、Edge TTS、预检和测试能力。
3. 采用英文项目名 `Nova AI Agent Employee`，以简单代号 `Nova` 加 `AI Agent Employee` 表达项目定位；没有继续使用中文名称作为主项目名。
4. 新建根目录 `README.md`，顶部默认展示中文并提供 `中文（默认） | English` 锚点切换；英文版作为同一文件内的独立章节，便于中英文读者直接定位。
5. 中文 README 按计划覆盖一句话介绍、核心功能、架构图、技术选型及取舍、三个固定演示问题、本地安装与运行、配置说明、测试命令、已知限制和后续扩展。
6. 按任务要求省略演示 GIF/截图，不创建占位图片；明确说明演示媒体不属于当前交付，避免读者误以为资源缺失。
7. 按任务要求忽略 Docker 运行，不编造 Dockerfile 或 Compose 命令；README 明确本地运行是当前正式路径。
8. 将本地安装写成可执行的 Windows PowerShell 流程：项目内 Python 3.11/uv 环境、依赖安装、项目内 Chromium、`.env`、ERP seed、FAISS 索引、预启动检查，以及 Mock ERP、Backend、Frontend 三终端启动。
9. 记录正式演示验收命令与三个固定问题，并说明 `pre-start --offline` 只用于排障、`demo` 需要真实 OpenRouter 与运行中的 Mock ERP。
10. 加入 API 快速调用、关键配置分组、默认/完整本地集成测试、依赖与编译检查，使读者可以按照 README 从零启动和验证项目。
11. 如实记录当前限制：单轮会话、离线 PDF 索引、模拟 ERP、RPA 浏览器依赖、在线 LLM/TTS 依赖、Phase 9 稳定模型真实复验待配置，以及未实现 Avatar、Docker 和演示媒体。
12. 添加与实际实现一致的简历描述；没有把未完成的 Docker、会话持久化、知识上传或数字人 Avatar 写成已完成功能。
13. 在 `plan.md` 的 Phase 10 标题及正文前增加状态说明，明确 Phase 10 已按本次任务要求忽略，只有未来新任务明确恢复时才执行原计划。

## Phase 11 验收结果

| 验收项 | 结果 | 证据 |
| --- | --- | --- |
| 英文项目名称 | 通过 | `Nova AI Agent Employee` / `nova-ai-agent-employee` 简短、易记且表达 Agent 员工定位 |
| 中英文切换 | 通过 | README 顶部与英文区均提供中文优先的锚点导航 |
| README 计划结构 | 通过 | 覆盖介绍、功能、架构、选型、三题、本地运行、配置、测试、限制和扩展 |
| 演示媒体范围 | 通过 | 未创建 GIF/截图，README 明确其不在当前交付范围 |
| Docker 范围 | 通过 | 未创建容器文件或命令，`plan.md` 已注明 Phase 10 被忽略 |
| 从零启动路径 | 通过 | 包含环境、依赖、Chromium、配置、seed、索引、预检和三服务命令 |
| 实现一致性 | 通过 | 工具名、API、端口、脚本、模型限制、TTS 降级和当前 Phase 9 状态均与代码/记录一致 |
| 简历描述真实性 | 通过 | 仅描述已完成的 Agent、RAG、RPA、Calculator、Streamlit、来源和 TTS |
| 默认自动测试 | 通过 | `109 passed, 4 skipped`；跳过项仅为显式本地集成测试 |
| Git 补丁格式检查 | 通过 | `git diff --check` 无空白错误 |

## Phase 11 产物与当前进度

- 双语项目说明与运行手册：`README.md`
- Phase 10 忽略状态：更新后的 `plan.md`
- Phase 11 实施与验收记录：更新后的 `step.md`
- 当前结论：Phase 11 的 README 任务已完成；Phase 10 保持忽略。项目代码与本地自动验收状态没有因文档阶段发生变化，Phase 9 的稳定模型真实三题复验仍需用户配置可用模型与额度后执行。
