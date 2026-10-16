"""数据库连接与会话管理。

这是全项目最"底层"的三个对象，读懂它们，数据库部分就通了：

  engine       —— 连接池：负责"怎么连上数据库"，一个进程一个就够
  SessionLocal —— 会话工厂：每次请求开一个 session（一次数据库对话），用完就关
  Base         —— ORM 基类：models.py 里所有表都继承它，它负责记住"有哪些表"
  get_session  —— 依赖注入函数：给每个请求发一个 session，请求结束自动关闭

注意：本文件不定义任何表结构、不写任何业务逻辑，只负责"连接"。
"""
import logging
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import DATABASE_URL, SQL_ECHO

logger = logging.getLogger(__name__)

# --- 1. 引擎 ---------------------------------------------------------------
# connect_args 里的 check_same_thread 是 SQLite 专属设置：
# FastAPI 可能在不同线程里处理同一个连接，SQLite 默认禁止跨线程，这里放开。
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, echo=SQL_ECHO, connect_args=_connect_args, future=True)

# --- 2. 会话工厂 -----------------------------------------------------------
# autoflush=False：不自动把内存改动刷进数据库，由我们自己显式 commit，行为更好预测
# expire_on_commit=False：commit 之后对象属性仍可读（否则访问 obj.id 会再查一次库，容易踩坑）
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


# --- 3. ORM 基类 -----------------------------------------------------------
class Base(DeclarativeBase):
    """所有数据库表的父类。models.py 里写 class Task(Base) 就自动注册到 metadata。"""


# --- 4. 依赖注入函数 -------------------------------------------------------
def get_session() -> Generator[Session, None, None]:
    """给一个请求发一个数据库会话，请求结束后一定关闭。

    看到 yield 你就理解成：yield 之前是"准备"，yield 出去的值给接口用，
    接口跑完后回到这里执行 finally —— 这就是 FastAPI 依赖的标准写法（也叫"生成器依赖"）。
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    """建表。开发阶段图省事用 create_all；
    正式项目应该用 Alembic 做数据库迁移（可追溯、可回滚的建表/改表脚本）。
    """
    # 必须先把 models 导入进来，Base.metadata 才知道有哪些表 —— 这是新手常见坑
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("数据库已就绪：%s", DATABASE_URL)


def check_connection() -> bool:
    """健康检查用：能不能真的连上数据库。"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:  # pragma: no cover - 只在数据库挂了时走到
        logger.exception("数据库连接失败")
        return False
