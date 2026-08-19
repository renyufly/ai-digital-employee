# Phase 0 实施记录

## 当前进度

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

| 验收项 | 结果 | 证据 |
| --- | --- | --- |
| Python 3.11 项目虚拟环境 | 通过 | `.venv\Scripts\python.exe --version` 返回 `Python 3.11.14` |
| Uvicorn 可启动 | 通过 | `app.main:app` 在 `127.0.0.1:8000` 完成启动 |
| `/health` 响应正确 | 通过 | HTTP 200，响应体为 `{"status":"ok"}` |
| 缺少 `.env` 可启动 | 通过 | 未创建 `.env`，应用导入和服务启动均成功，LLM Key 为可选状态 |
| 测试可独立运行 | 通过 | `1 passed` |
| Python 文件可编译 | 通过 | `python -m compileall -q app tests` 成功 |
| Git 补丁格式检查 | 通过 | `git diff --check` 无错误 |

## Phase 0 产物

- 环境约束：`.python-version`、`uv.toml`、`requirements.txt`
- 安全与配置：`.gitignore`、`.env.example`、`app/core/config.py`
- 基础设施：`app/core/logging.py`
- 最小服务：`app/main.py`
- 自动测试：`tests/test_health.py`
- 后续阶段占位目录：`mock_erp/`、`frontend/`、`scripts/`、`knowledge/`、`data/`

## 下一阶段边界

Phase 0 已满足 `plan.md` 的全部验收条件。按照计划，下一阶段应为 Phase 1：Mock ERP；本次没有提前实现该阶段内容。
