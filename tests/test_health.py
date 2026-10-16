"""冒烟测试（smoke test）：服务的基本骨架活着吗？

为什么叫"冒烟"：早期硬件通电后如果冒烟，说明根本不用往下测了。
所以冒烟测试只验证"能启动、能响应"，是最快的一道防线，CI 里第一步就跑它。
"""
import pytest
from fastapi.testclient import TestClient

import app as app_package


@pytest.mark.integration
def test_health_returns_ok(client: TestClient) -> None:
    """健康检查应返回 200，且报告数据库可用。"""
    resp = client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] is True
    assert body["version"] == app_package.__version__


@pytest.mark.integration
def test_root_lists_docs_and_version(client: TestClient) -> None:
    """首页应告诉调用者文档地址和接口前缀。"""
    resp = client.get("/")

    assert resp.status_code == 200
    assert resp.json()["docs"] == "/docs"


@pytest.mark.integration
def test_openapi_schema_is_available(client: TestClient) -> None:
    """OpenAPI 契约能正常生成 —— 前端和自动化测试都依赖它对接接口。"""
    resp = client.get("/openapi.json")

    assert resp.status_code == 200
    paths = resp.json()["paths"]
    # 至少要有这两个接口，否则说明路由没挂上
    assert "/api/v1/tasks" in paths
    assert "/api/v1/tasks/{task_id}" in paths


@pytest.mark.integration
def test_unknown_path_returns_404(client: TestClient) -> None:
    """访问不存在的地址应返回 404，而不是 500。"""
    assert client.get("/api/v1/不存在").status_code == 404
