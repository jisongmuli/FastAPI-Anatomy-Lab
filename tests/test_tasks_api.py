"""接口 / 集成测试：用 TestClient 发"假 HTTP 请求"，走完整链路。

和单元测试的区别：
    单元测试   service.create_task(db, payload)      → 直接调函数
    集成测试   client.post("/api/v1/tasks", json=…)  → 真的经过路由、校验、依赖注入、序列化

集成测试更接近"用户真实用法"，但跑得慢一些。两者都要有：
集成测试保证"接口能通"，单元测试保证"规则没错"。

读每个用例的固定三步：
    1. Arrange（准备）：造数据 / 准备请求体
    2. Act（执行）：client.get/post/patch/delete
    3. Assert（断言）：先断言状态码，再断言响应体内容
"""
import pytest
from fastapi.testclient import TestClient

TASKS_URL = "/api/v1/tasks"


# ---------------------------------------------------------------------------
# 一、正常路径（happy path）：功能能不能用
# ---------------------------------------------------------------------------
@pytest.mark.integration
def test_create_then_read_task(client: TestClient) -> None:
    """新建后能按 id 查回来 —— 验证"写进去的数据真的落库了"。"""
    create_resp = client.post(TASKS_URL, json={"title": "读论文 5 篇", "priority": 4})
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["title"] == "读论文 5 篇"
    assert created["status"] == "pending"
    assert created["id"] > 0

    get_resp = client.get(f"{TASKS_URL}/{created['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json() == created  # 存进去什么，读出来就该是什么


@pytest.mark.integration
def test_read_missing_task_returns_404(client: TestClient) -> None:
    """查不存在的任务 → 404，且带可读的 detail。"""
    resp = client.get(f"{TASKS_URL}/123456")

    assert resp.status_code == 404
    assert "不存在" in resp.json()["detail"]


@pytest.mark.integration
def test_list_supports_filter_and_pagination(client: TestClient) -> None:
    """列表接口：筛选参数、分页参数都要真的生效。"""
    for title in ("任务A", "任务B", "任务C"):
        client.post(TASKS_URL, json={"title": title})
    client.post(TASKS_URL, json={"title": "已完成的任务", "status": "done"})

    # 全量：4 条
    all_resp = client.get(TASKS_URL)
    assert all_resp.status_code == 200
    assert all_resp.json()["total"] == 4

    # 按状态筛选
    done_resp = client.get(TASKS_URL, params={"status": "done"})
    assert done_resp.json()["total"] == 1

    # 分页：total 是总数，items 才是这一页
    page_resp = client.get(TASKS_URL, params={"limit": 2, "offset": 0})
    body = page_resp.json()
    assert body["total"] == 4
    assert len(body["items"]) == 2

    # 按关键字搜索
    kw_resp = client.get(TASKS_URL, params={"keyword": "任务A"})
    assert kw_resp.json()["total"] == 1


@pytest.mark.integration
def test_patch_updates_only_sent_field(client: TestClient, sample_task: dict) -> None:
    """PATCH 只改传过来的字段，其他字段保持不变。"""
    resp = client.patch(f"{TASKS_URL}/{sample_task['id']}", json={"priority": 1})

    assert resp.status_code == 200
    body = resp.json()
    assert body["priority"] == 1
    assert body["title"] == sample_task["title"]       # 没传 → 不变
    assert body["description"] == sample_task["description"]


@pytest.mark.integration
def test_complete_task_endpoint(client: TestClient, sample_task: dict) -> None:
    """标记完成接口：状态变 done；重复调用应幂等成功。"""
    first = client.post(f"{TASKS_URL}/{sample_task['id']}/complete")
    assert first.status_code == 200
    assert first.json()["status"] == "done"

    second = client.post(f"{TASKS_URL}/{sample_task['id']}/complete")
    assert second.status_code == 200
    assert second.json()["status"] == "done"


@pytest.mark.integration
def test_delete_then_get_returns_404(client: TestClient, sample_task: dict) -> None:
    """删除返回 204（无响应体），之后查不到。"""
    resp = client.delete(f"{TASKS_URL}/{sample_task['id']}")

    assert resp.status_code == 204
    assert resp.content == b""          # 204 明确规定不能有响应体
    assert client.get(f"{TASKS_URL}/{sample_task['id']}").status_code == 404


# ---------------------------------------------------------------------------
# 二、异常路径：坏输入必须被挡住（这类用例最能体现测试的价值）
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.parametrize(
    "bad_payload, reason",
    [
        ({}, "缺少必填的 title"),
        ({"title": ""}, "title 不允许空字符串"),
        ({"title": "x" * 101}, "title 超过 100 字上限"),
        ({"title": "正常", "priority": 0}, "priority 小于下限 1"),
        ({"title": "正常", "priority": 6}, "priority 超过上限 5"),
        ({"title": "正常", "status": "finished"}, "status 只能是 pending/doing/done"),
    ],
)
def test_invalid_payload_returns_422(client: TestClient, bad_payload: dict, reason: str) -> None:
    """参数校验必须在校验层被挡住，返回 422 且不写入数据库。

    parametrize 是 pytest 最实用的功能之一：一份逻辑跑多组数据，
    报告里会显示成 6 个独立用例，哪组坏了看得清清楚楚。
    """
    resp = client.post(TASKS_URL, json=bad_payload)

    assert resp.status_code == 422, f"这组数据本该被拒绝：{reason}"
    assert "errors" in resp.json()


@pytest.mark.integration
def test_duplicate_title_returns_409(client: TestClient) -> None:
    """业务规则冲突用 409 Conflict，不是 400 也不是 500。"""
    client.post(TASKS_URL, json={"title": "独一无二的标题"})

    resp = client.post(TASKS_URL, json={"title": "独一无二的标题"})

    assert resp.status_code == 409
    assert "已存在" in resp.json()["detail"]


@pytest.mark.integration
def test_patch_completed_task_returns_409(client: TestClient, sample_task: dict) -> None:
    """已完成的任务再改 → 409，验证业务规则在 HTTP 层也被正确翻译。"""
    client.post(f"{TASKS_URL}/{sample_task['id']}/complete")

    resp = client.patch(f"{TASKS_URL}/{sample_task['id']}", json={"title": "改一下"})

    assert resp.status_code == 409


@pytest.mark.integration
def test_bad_query_params_return_422(client: TestClient) -> None:
    """查询参数同样要校验：limit 超范围、status 取值非法都应被拒。"""
    assert client.get(TASKS_URL, params={"limit": 0}).status_code == 422
    assert client.get(TASKS_URL, params={"limit": 1000}).status_code == 422
    assert client.get(TASKS_URL, params={"status": "unknown"}).status_code == 422


@pytest.mark.integration
def test_task_id_must_be_integer(client: TestClient) -> None:
    """路径参数类型不对 → 422（FastAPI 自动转换失败时的行为）。"""
    assert client.get(f"{TASKS_URL}/abc").status_code == 422


# ---------------------------------------------------------------------------
# 三、隔离性：证明每个用例真的从干净数据库开始
# ---------------------------------------------------------------------------
@pytest.mark.integration
def test_each_test_starts_with_empty_database(client: TestClient) -> None:
    """这个用例依赖"数据库是空的"。

    它能通过，就证明 conftest.py 里的 fixture 真的在用例之间清理了数据。
    如果哪天它开始失败，说明测试之间开始互相污染了 —— 这是测试代码自己出的 bug，
    比业务 bug 更隐蔽，所以专门留一个用例守着它。
    """
    assert client.get(TASKS_URL).json()["total"] == 0
