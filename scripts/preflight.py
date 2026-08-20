"""Interview-demo preflight checklist.

Run ``pre-start`` before starting services. Start Mock ERP, then run ``demo``
to execute the three real OpenRouter + RPA + RAG interview questions once.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.agent.service import AgentService
from app.core.config import get_settings
from app.core.preflight import (
    CheckResult,
    check_chromium,
    check_configuration,
    check_demo_questions,
    check_erp_seed,
    check_erp_service,
    check_openrouter,
    check_ports_available,
    check_vector_index,
)


def _print_results(results: list[CheckResult]) -> bool:
    for result in results:
        icon = {"PASS": "[PASS]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}[result.status]
        print(f"{icon} {result.name}: {result.detail}")
    return all(result.passed for result in results)


async def main() -> int:
    parser = argparse.ArgumentParser(description="AI 数字员工演示前检查")
    parser.add_argument(
        "mode",
        nargs="?",
        choices=("pre-start", "demo"),
        default="pre-start",
        help="pre-start 检查本地资源和空闲端口；demo 在 Mock ERP 启动后跑三个真实问题",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="仅排障时跳过 OpenRouter 网络和余额检查；正式演示前不要使用",
    )
    args = parser.parse_args()
    settings = get_settings()

    results = [
        check_configuration(settings),
        check_erp_seed(settings),
        check_vector_index(settings),
        await check_chromium(settings),
    ]
    if args.mode == "pre-start":
        results.append(check_ports_available())
    else:
        results.append(await check_erp_service(settings))

    if args.offline:
        results.append(
            CheckResult("OpenRouter 联网与余额", "SKIP", "已通过 --offline 跳过")
        )
    else:
        results.extend(await check_openrouter(settings))

    if args.mode == "demo" and all(result.passed for result in results):
        results.extend(await check_demo_questions(AgentService(settings=settings)))

    print("\n演示降级策略：TTS 失败时保留文字回答并跳过语音，不影响核心链路。")
    print("录屏和截图不属于本次检查范围。")
    return 0 if _print_results(results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
