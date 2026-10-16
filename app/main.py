"""应用入口（整个项目从这里开始读）。

一个 FastAPI 项目的 main.py 永远在做这几件事（顺序也基本固定）：
    1. 配置日志
    2. 创建 FastAPI 实例（顺带写好标题、版本，/docs 页面会用到）
    3. 注册异常处理器
    4. 注册路由（把 routes/ 里的 router 挂上来）
    5. 声明生命周期：启动时建表/连数据库，关闭时释放资源
    6. 提供健康检查等全局接口

启动命令：
    uvicorn app.main:app --reload
    解读：在 app/main.py 里找到变量 app 作为 ASGI 应用；--reload 改了代码自动重启。
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.config import API_PREFIX
from app.database import check_connection, init_db
from app.errors import register_exception_handlers
from app.routes import tasks
from app.schemas import HealthResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """生命周期：yield 之前是"启动时做的事"，之后是"关闭时做的事"。

    读法：看到 @asynccontextmanager + yield，就理解成"围绕整个服务生命周期的一段开关逻辑"。
    """
    logger.info("服务启动中……")
    init_db()  # 建表（表已存在时什么都不做）
    logger.info("服务已就绪，接口文档： http://127.0.0.1:8000/docs")
    yield
    logger.info("服务已关闭")


app = FastAPI(
    title="任务清单 API（教学标本）",
    description="分层完整的 FastAPI 示例项目：路由 → 业务 → 数据 → 表。",
    version=__version__,
    lifespan=lifespan,
)

# 注册统一异常处理（TaskNotFound→404、TaskConflict→409、参数错误→422、兜底→500）
register_exception_handlers(app)

# 挂载业务路由：所有 /tasks 接口都带上 /api/v1 前缀
app.include_router(tasks.router, prefix=API_PREFIX)


@app.get("/", tags=["系统"], summary="服务首页")
def read_root():
    return {
        "service": "task-list-api",
        "version": __version__,
        "docs": "/docs",
        "api_prefix": API_PREFIX,
    }


@app.get("/health", response_model=HealthResponse, tags=["系统"], summary="健康检查")
def health():
    """健康检查接口：部署流水线和监控系统会周期性打它。

    测试里这叫"冒烟测试"（smoke test）：连这个都过不了，别的都不用测了。
    """
    db_ok = check_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": db_ok,
        "version": __version__,
    }
