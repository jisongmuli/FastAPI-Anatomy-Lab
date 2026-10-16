"""单元测试：只测 service 层，不经过 HTTP。

单元测试的特征（也是它和集成测试的区别）：
    · 不启动服务、不发 HTTP 请求 → 跑得极快（本文件全部用例通常 < 0.2 秒）
    · 直接调用函数、直接检查返回值或异常
    · 一个用例只验证一条规则 → 失败时你能立刻知道是哪个规则坏了

做研究/写论文时，这种测试的价值是：改代码后能立刻知道"我的规则有没有被改坏"。
"""
import pytest
from sqlalchemy.orm import Session

from app import service
from app.errors import TaskConflict, TaskNotFound
from app.schemas import TaskCreate, TaskUpdate


# ---------------------------------------------------------------------------
# 用 pytest.raises 断言"这里应该报错"。
# 光测"正常情况"是不够的：真正容易出 bug 的是异常路径。
# ---------------------------------------------------------------------------
def test_get_task_raises_when_missing(db_session: Session) -> None:
    """查一个不存在的任务，应该抛 TaskNotFound（而不是返回 None）。"""
    with pytest.raises(TaskNotFound) as exc_info:
        service.get_task(db_session, 999)

    assert exc_info.value.task_id == 999
    assert "999" in str(exc_info.value)


def test_create_task_persists_all_fields(db_session: Session) -> None:
    """创建任务后，字段应原样落到数据库，并自动获得 id / 时间戳。"""
    task = service.create_task(
        db_session,
        TaskCreate(title="跑对比实验", description="三个基线", priority=4, status="doing"),
    )

    assert task.id is not None              # 自增主键由数据库生成
    assert task.title == "跑对比实验"
    assert task.description == "三个基线"
    assert task.priority == 4
    assert task.status == "doing"
    assert task.created_at is not None       # 默认值生效
    # 重新查一次，确认真的写进了数据库（而不是只存在于内存对象里）
    assert service.get_task(db_session, task.id).title == "跑对比实验"


def test_create_task_rejects_duplicate_title(db_session: Session) -> None:
    """标题重复应触发 TaskConflict —— 这是本项目的核心业务规则之一。"""
    service.create_task(db_session, TaskCreate(title="写开题报告"))

    with pytest.raises(TaskConflict) as exc_info:
        service.create_task(db_session, TaskCreate(title="写开题报告"))

    assert "已存在" in str(exc_info.value)


def test_update_uses_only_provided_fields(db_session: Session) -> None:
    """PATCH 语义：只改传了的字段，没传的保持原样。"""
    task = service.create_task(db_session, TaskCreate(title="改论文", priority=2))

    updated = service.update_task(db_session, task.id, TaskUpdate(priority=5))

    assert updated.priority == 5
    assert updated.title == "改论文"           # 没传 title，所以不能被清空
    assert updated.status == "pending"        # 没传 status，保持默认


def test_update_done_task_is_rejected(db_session: Session) -> None:
    """已完成的任务不允许再修改（除非把状态改回 pending）。"""
    task = service.create_task(db_session, TaskCreate(title="已交的作业"))
    service.complete_task(db_session, task.id)

    with pytest.raises(TaskConflict):
        service.update_task(db_session, task.id, TaskUpdate(title="偷偷改标题"))

    # 但"改回 pending"是允许的
    reopened = service.update_task(db_session, task.id, TaskUpdate(status="pending"))
    assert reopened.status == "pending"


def test_complete_task_is_idempotent(db_session: Session) -> None:
    """幂等：同一个操作执行多次，结果一致，不报错。

    这是接口设计里的重要概念——网络重试很常见，接口必须能承受重复调用。
    """
    task = service.create_task(db_session, TaskCreate(title="交周报"))

    first = service.complete_task(db_session, task.id)
    second = service.complete_task(db_session, task.id)

    assert first.status == "done"
    assert second.status == "done"
    assert first.id == second.id


def test_list_tasks_filters_and_paginates(db_session: Session) -> None:
    """列表：状态筛选、关键字搜索、分页三件事要一起对。"""
    for i in range(5):
        service.create_task(db_session, TaskCreate(title=f"任务{i}", status="pending"))
    service.create_task(db_session, TaskCreate(title="紧急任务", status="done"))

    total, rows = service.list_tasks(db_session, status="pending")
    assert total == 5
    assert len(rows) == 5

    total_done, rows_done = service.list_tasks(db_session, status="done")
    assert total_done == 1
    assert rows_done[0].title == "紧急任务"

    # 关键字命中标题
    total_kw, _ = service.list_tasks(db_session, keyword="紧急")
    assert total_kw == 1

    # 分页：total 是"符合条件的总数"，不是"这一页的条数" ← 新手最常搞混的点
    total_page, page_rows = service.list_tasks(db_session, limit=2, offset=0)
    assert total_page == 6
    assert len(page_rows) == 2


def test_delete_task_removes_it(db_session: Session) -> None:
    """删除后就查不到了。"""
    task = service.create_task(db_session, TaskCreate(title="临时任务"))

    service.delete_task(db_session, task.id)

    with pytest.raises(TaskNotFound):
        service.get_task(db_session, task.id)
