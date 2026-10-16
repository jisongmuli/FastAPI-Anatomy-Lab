# 测试夹具（fixture）集中定义在这里。
#
# conftest.py 是 pytest 的"魔法文件"：放在某个目录下，这个目录及子目录里的
# 所有测试文件都能直接使用里面定义的 fixture，不需要 import。
#
# fixture 是什么？
#   中文叫"夹具"，作用就是"测试开始前把环境准备好，测试结束后清理干净"，
#   类似实验前先把仪器校准好。这样每个用例都从同一个干净状态开始，结果才可复现。
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_session
from app.dependencies import get_db
from app.main import app  # 导入被测对象——测试永远要 import 你测的那个 app

# ---------------------------------------------------------------------------
# 关键设计：测试用「内存数据库」，不用真实的 tasks.db
#   sqlite://            → 内存数据库，进程退出就没了，绝不污染开发数据
#   StaticPool           → 让所有连接共用同一个内存库（否则每次连接都是新空库，表会"消失"）
#   check_same_thread=False → 允许跨线程使用（TestClient 内部会切线程）
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """一个干净的数据库会话。

    yield 之前：建表（每个用例都重新建，互不干扰）
    yield 出来：交给用例使用
    yield 之后：删表 + 关连接（清理现场）

    需要"直接操作数据库"的单元测试（test_tasks_service.py）就注入它。
    """
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """一个能发"假 HTTP 请求"的测试客户端。

    TestClient 不需要真的启动 uvicorn、不需要占端口：它把请求直接递给 app 对象，
    但走的是**和真实请求完全一样的链路**（路由匹配、参数校验、依赖注入、序列化、状态码）。
    所以它既能测得很真，又跑得很快。

    app.dependency_overrides 是依赖注入最实用的地方：
    把"生产用的 get_db"换成"测试用的内存库 session"，被测代码一行都不用改。

    依赖顺序说明：client 依赖 db_session，所以每个用例都会先拿到干净数据库。
    """

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_session] = _override_get_db
    with TestClient(app) as test_client:
        # with 语句会触发 lifespan 启动逻辑（建表等），测试因此更接近真实启动过程
        yield test_client
    app.dependency_overrides.clear()  # 清理覆盖，避免影响别的测试


# ---------------------------------------------------------------------------
# 一个自定义 fixture：预先造好一条任务，省得每个用例都写一遍创建流程。
# ---------------------------------------------------------------------------
@pytest.fixture()
def sample_task(client: TestClient) -> dict:
    """通过接口创建一条示例任务，返回服务端响应里的 JSON。"""
    resp = client.post("/api/v1/tasks", json={"title": "写毕业论文初稿", "priority": 5})
    assert resp.status_code == 201, f"前置数据创建失败：{resp.text}"
    return resp.json()
