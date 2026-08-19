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

## 当前进度

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
