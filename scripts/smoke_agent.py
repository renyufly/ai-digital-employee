"""Manual real-OpenRouter smoke test; requires a local .env API key."""

import asyncio
from pathlib import Path
import sys

# Keep the documented `python scripts/smoke_agent.py` entry point runnable.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Model output may contain Unicode characters unavailable in Windows GBK consoles.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.agent.service import AgentService


QUESTIONS = (
    "公司的退款政策是什么？",
    "订单金额 1280 元，如果退款 80%，需要退款多少钱？",
    "帮我查询订单 10001。",
    "查询订单 10001，如果已经发货，告诉我物流信息，同时根据退款政策告诉我是否还能申请退款。",
)


async def main() -> None:
    agent = AgentService()
    questions = tuple(sys.argv[1:]) or QUESTIONS
    for question in questions:
        print(f"\n用户：{question}")
        result = await agent.run(question)
        print(f"回答：{result.answer}")
        print("轨迹：", " -> ".join(trace.name or trace.type for trace in result.traces))
        if result.error_code:
            print(f"错误码：{result.error_code}")


if __name__ == "__main__":
    asyncio.run(main())
