"""演示文件：**故意写错的测试**，用来让你认识"测试失败长什么样"。

用法（两种都试试，对比感受）：
    pytest tests/演示-失败的测试.py -v                    → 2 个失败
    pytest tests/演示-失败的测试.py -v -k 先跑通的那个      → 1 个通过

为什么要有这个文件？
    初学者容易以为"测试失败 = 我的代码全错了"，其实失败信息里写得很清楚：
    是哪一行、期望什么、实际什么。**会读失败信息，比会写测试更值钱。**

读完以后，务必把这个文件删掉或改名（文件名里带"演示"二字，
所以默认的 `pytest` 命令**不会**收集它——注意看 pytest 的默认规则：
只有文件名匹配 test_*.py 或 *_test.py 的才会被自动收集）。

这里名字特意用 演示_ 开头，所以：

    pytest               → 只跑 29 个正常用例，不会看到红色
    pytest tests/演示-失败的测试.py   → 手动指定文件，才会跑这几个故意失败的用例
"""
import pytest
from fastapi.testclient import TestClient


def test_先跑通的那个_断言是对的(client: TestClient) -> None:
    """这个会通过。用来对比"通过"和"失败"的输出差别。"""
    assert client.get("/health").status_code == 200


def test_故意断言错误的状态码(client: TestClient) -> None:
    """失败示例 1：状态码断言写错了。

    实际返回 200，但断言写成 201 → 失败信息会明确告诉你
    "assert 200 == 201"，左边是实际值，右边是期望值。
    """
    resp = client.get("/health")
    assert resp.status_code == 201, "健康检查应该是 200，写成 201 就会看到这条消息"


def test_故意断言错误的内容(client: TestClient) -> None:
    """失败示例 2：响应体内容对不上。

    失败时会打印完整的实际 JSON，你可以直接对比是哪几个字段不一样。
    """
    client.post("/api/v1/tasks", json={"title": "写论文"})

    body = client.get("/api/v1/tasks").json()
    assert body["total"] == 99, f"实际拿到的响应是：{body}"


def test_故意不存在的接口(client: TestClient) -> None:
    """失败示例 3：测了一个根本不存在的接口 → 404，断言 200 就失败。

    这类失败最常见的原因不是你写错了测试，而是**地址拼错了**或**路由没挂上**。
    排查第一步：打开 /openapi.json 或 /docs 看接口到底存不存在。
    """
    assert client.get("/api/v1/not-exist").status_code == 200
