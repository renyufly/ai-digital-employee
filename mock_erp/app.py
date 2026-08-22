"""Server-rendered mock ERP application used by people and later by RPA."""
'''
用 FastAPI + Jinja2 + Session + SQLite 搭建了一个
带登录、订单列表、订单搜索、订单详情的模拟 ERP 网站，
主要给人工操作和后续 Playwright RPA 自动查询订单使用
'''

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import get_settings
from mock_erp.database import get_order, initialize_database, list_orders


TEMPLATES = Jinja2Templates(directory=Path(__file__).parent / "templates")


def create_app(
    database_path: Path | None = None,
    username: str | None = None,
    password: str | None = None,
    session_secret: str | None = None,
) -> FastAPI:
    '''
    创建整个 ERP 应用
    '''
    settings = get_settings()
    db_path = database_path or settings.mock_erp_database_path
    expected_username = username or settings.mock_erp_username
    expected_password = password or settings.mock_erp_password

    erp = FastAPI(title="Mock ERP", version="0.1.0")

    '''
    保存登录状态, 给网站增加 Session 会话功能.
    之后访问订单页面，就不用重复登录
    '''
    erp.add_middleware(
        SessionMiddleware,
        secret_key=session_secret or settings.mock_erp_session_secret,
        same_site="lax",
        https_only=False,
    )

    initialize_database(db_path)

    def logged_in(request: Request) -> bool:
        '''
        判断是否登录
        '''
        return request.session.get("authenticated") is True

    @erp.get("/", include_in_schema=False)
    async def root(request: Request) -> RedirectResponse:
        '''
        访问 / 时自动跳转：
            已登录 → /orders
            未登录 → /login
        '''
        target = "/orders" if logged_in(request) else "/login"
        return RedirectResponse(target, status_code=303)

    @erp.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request) -> HTMLResponse:
        '''
        显示登录页面
        '''
        if logged_in(request):
            return RedirectResponse("/orders", status_code=303)
        return TEMPLATES.TemplateResponse(request, "login.html", {"error": None})

    @erp.post("/login")
    async def login(
        request: Request,
        submitted_username: str = Form(alias="username"),
        submitted_password: str = Form(alias="password"),
    ) -> HTMLResponse:
        '''
        处理登录
        '''
        if submitted_username == expected_username and submitted_password == expected_password:
            '''
            从 HTML 表单读取：username, password
            和配置中的账号密码比较
            '''
            request.session.clear()
            request.session["authenticated"] = True
            return RedirectResponse("/orders", status_code=303)

        return TEMPLATES.TemplateResponse(
            request,
            "login.html",
            {"error": "用户名或密码错误"},
            status_code=401,
        )

    @erp.post("/logout")
    async def logout(request: Request) -> RedirectResponse:
        request.session.clear()  # 把 Session 清空
        return RedirectResponse("/login", status_code=303)

    @erp.get("/orders", response_class=HTMLResponse)
    async def orders_page(request: Request, order_no: str | None = None) -> HTMLResponse:
        '''
        订单列表 + 搜索
        '''
        if not logged_in(request):
            return RedirectResponse("/login", status_code=303)
        search = order_no.strip() if order_no is not None else ""
        orders = list_orders(db_path, search or None)
        message = None
        if order_no is not None and not search:
            message = "请输入订单号"
            orders = []
        elif search and not orders:
            message = f"未找到订单 {search}"
        return TEMPLATES.TemplateResponse(
            request,
            "orders.html",
            {"orders": orders, "search": search, "message": message},
        )

    @erp.get("/orders/{order_no}", response_class=HTMLResponse)
    async def order_detail(request: Request, order_no: str) -> HTMLResponse:
        '''
        订单详情
        '''

        if not logged_in(request):
            return RedirectResponse("/login", status_code=303)
        order = get_order(db_path, order_no)
        if order is None:
            return TEMPLATES.TemplateResponse(
                request,
                "order_detail.html",
                {"order": None, "message": f"未找到订单 {order_no}"},
                status_code=404,
            )
        return TEMPLATES.TemplateResponse(
            request, "order_detail.html", {"order": order, "message": None}
        )

    return erp


app = create_app()
