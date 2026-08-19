"""Generate the four short, text-based mock knowledge PDFs."""

import os
from pathlib import Path

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


DOCUMENTS: dict[str, tuple[str, list[str]]] = {
    "company_intro.pdf": (
        "公司介绍",
        [
            "星河智联科技有限公司成立于 2021 年，总部位于上海。本文所有公司信息均为面试 Demo 使用的模拟数据。",
            "公司主要为中小企业提供智能办公终端、订单协同和知识管理软件服务。客户支持时间为工作日 09:00 至 18:00。",
            "公司的服务原则是信息准确、过程可追踪，并且不得将客户的真实个人数据写入演示系统。",
        ],
    ),
    "refund_policy.pdf": (
        "退款与退货政策",
        [
            "用户提交退款申请后需要经过审核，审核通常需要 1 至 2 个工作日。审核通过后，退款将在 3 至 5 个工作日内原路返回。",
            "尚未发货的订单可以直接申请取消和退款。已经发货的订单仍可申请退款，但必须先完成退货；商品退回并验收成功后才进入退款流程。",
            "已完成超过 30 天的订单原则上不支持无理由退款。商品质量问题不受该限制，但需要提交照片或检测材料，由客服人工复核。",
            "运费承担规则：质量问题由公司承担退货运费；非质量问题由客户承担退货运费。",
        ],
    ),
    "shipping_policy.pdf": (
        "物流与发货政策",
        [
            "普通订单通常会在付款完成后 24 小时内发货；节假日、大促或缺货商品可能延迟，并由客服发送通知。",
            "默认物流公司包括顺丰、中通和京东物流。系统会根据收货地区、商品类型和仓库库存选择承运商。",
            "订单发货后，用户可以通过订单详情中的物流单号查询运输状态。物流单号通常在揽收后 2 小时内产生首条轨迹。",
            "易碎品和高价值设备默认优先使用顺丰，偏远地区可能改用可送达的其他承运商。",
        ],
    ),
    "product_manual.pdf": (
        "智能办公终端 A100 产品手册",
        [
            "A100 是用于会议室和前台场景的模拟智能办公终端，支持有线网络、Wi-Fi 6 和 HDMI 输出。",
            "首次启动时连接电源和显示器，长按电源键 2 秒。设备进入引导页后，管理员需要完成网络设置和演示账号绑定。",
            "设备标准保修期为 12 个月。保修不覆盖人为进水、私自拆机、非原装电源导致的损坏。",
            "如设备无法联网，应先检查路由器、网线和系统时间，再重启设备；仍无法恢复时联系工作日客户支持。",
        ],
    ),
}


def _find_chinese_font() -> Path:
    configured = os.environ.get("KNOWLEDGE_PDF_FONT")
    candidates = [
        Path(configured) if configured else None,
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/System/Library/Fonts/PingFang.ttc"),
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "未找到可嵌入的中文字体；请通过 KNOWLEDGE_PDF_FONT 指定 TrueType/OpenType 字体"
    )


def create_pdfs(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pdfmetrics.registerFont(TTFont("KnowledgeChinese", str(_find_chinese_font())))
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "ChineseTitle",
        parent=styles["Title"],
        fontName="KnowledgeChinese",
        fontSize=20,
        leading=28,
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    body = ParagraphStyle(
        "ChineseBody",
        parent=styles["BodyText"],
        fontName="KnowledgeChinese",
        fontSize=11,
        leading=19,
        spaceAfter=8,
    )

    for filename, (heading, paragraphs) in DOCUMENTS.items():
        document = SimpleDocTemplate(
            str(output_dir / filename),
            pagesize=A4,
            leftMargin=25 * mm,
            rightMargin=25 * mm,
            topMargin=25 * mm,
            bottomMargin=25 * mm,
            title=heading,
            author="AI Digital Employee Demo",
        )
        story = [Paragraph(heading, title), Spacer(1, 4 * mm)]
        story.extend(
            Paragraph(f"{index}. {paragraph}", body)
            for index, paragraph in enumerate(paragraphs, start=1)
        )
        document.build(story)


if __name__ == "__main__":
    create_pdfs(Path(__file__).resolve().parents[1] / "knowledge")
