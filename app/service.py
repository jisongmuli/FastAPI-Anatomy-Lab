"""业务逻辑层（Service）。

这一层回答的问题：**规则是什么。**
它不关心 HTTP（不知道 404 是什么），也不写 SQL（那是 repository 的活）。
它只接收"干净的数据"，按业务规则处理，出问题就抛自定义异常。

对测试的意义（Day 3 重点）：
  service 层可以**脱离 HTTP 单独测试** —— 这就是"单元测试"。
  单元测试跑得快、定位准，是测试金字塔里数量最多的一层。
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app import models, repository
from app.errors import TaskConflict, TaskNotFound
from app.schemas import TaskCreate, TaskUpdate

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_task(session: Session, payload: TaskCreate) -> models.Task:
    """新建任务。业务规则：标题不能和已有任务重复。"""
    if repository.get_by_title(session, payload.title) is not None:
        # 抛出"业务冲突"，由 errors.py 翻译成 HTTP 409
        raise TaskConflict(f"任务标题已存在：{payload.title}")

    task = repository.create(
        session,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        status=payload.status,
    )
    logger.info("创建任务 id=%s title=%s", task.id, task.title)
    return task


def get_task(session: Session, task_id: int) -> models.Task:
    """按 ID 取任务，找不到就报错。"""
    task = repository.get(session, task_id)
    if task is None:
        raise TaskNotFound(task_id)
    return task


def list_tasks(
    session: Session,
    *,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[int, Sequence[models.Task]]:
    """查询任务列表（条件 + 分页）。这一层目前只是转发，但保留它是为了以后加规则。"""
    return repository.list_tasks(session, status=status, keyword=keyword, limit=limit, offset=offset)


def update_task(session: Session, task_id: int, payload: TaskUpdate) -> models.Task:
    """局部更新任务。这里有两条规则，都是"业务规则"，所以放在 service 而不是 routes。"""
    task = get_task(session, task_id)

    # exclude_unset=True 的效果：只保留"客户端真的传了的字段"。
    # 例如 PATCH 只传 {"priority": 5}，changes 就只有 {"priority": 5}，其他字段不被动。
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return task  # 什么都没传，直接返回原样，也算成功

    # 规则一：已完成的任务不允许再改
    if task.status == "done" and changes.get("status") != "pending":
        raise TaskConflict("已完成的任务不能修改；如需继续请先把状态改回 pending")

    # 规则二：改标题也要保证唯一
    new_title = changes.get("title")
    if new_title is not None and new_title != task.title:
        if repository.get_by_title(session, new_title) is not None:
            raise TaskConflict(f"任务标题已存在：{new_title}")

    return repository.update(session, task, changes)


def complete_task(session: Session, task_id: int) -> models.Task:
    """把任务标记为完成。重复完成是幂等的（再点一次也返回成功，不报错）。"""
    task = get_task(session, task_id)
    if task.status == "done":
        return task  # 幂等：同一个操作执行多次，结果一致

    return repository.update(session, task, {"status": "done"})


def delete_task(session: Session, task_id: int) -> None:
    """删除任务。"""
    task = get_task(session, task_id)
    repository.delete(session, task)
    logger.info("删除任务 id=%s", task_id)
