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
