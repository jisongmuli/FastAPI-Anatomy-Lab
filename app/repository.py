"""数据访问层（Repository / DAO）。

这一层只做一件事：**跟数据库打交道。**
规则：不许写业务判断（"标题不能重复"不属于这里），也不许碰 HTTP（不返回状态码）。
好处是以后换数据库、改表结构，只动这一层。
"""
from typing import List, Optional, Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import models


def create(session: Session, *, title: str, description: Optional[str], priority: int, status: str) -> models.Task:
    """插入一行并返回它。"""
    task = models.Task(title=title, description=description, priority=priority, status=status)
    session.add(task)      # 放进"待写入"队列
    session.commit()       # 真正写进数据库
    session.refresh(task)  # 回读一次，拿到数据库生成的 id / created_at
    return task


def get(session: Session, task_id: int) -> Optional[models.Task]:
    """按主键查一行，查不到返回 None（注意：不在这里抛错，那是 service 的事）。"""
    return session.get(models.Task, task_id)


def get_by_title(session: Session, title: str) -> Optional[models.Task]:
    """按标题查一行 —— service 用它来判断标题是否重复。"""
    stmt = select(models.Task).where(models.Task.title == title)
    return session.execute(stmt).scalars().first()


def list_tasks(
    session: Session,
    *,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[int, Sequence[models.Task]]:
    """条件查询 + 分页，返回 (符合条件的总数, 当前页数据)。

    读代码要点：
      1) 先拼 where 条件（列表里每个元素都会被 AND 起来）
      2) count 用单独的 select(func.count()) 查总数
      3) 最后 .offset().limit() 取当前页 —— 顺序不能反
    """
    conditions = []
    if status is not None:
        conditions.append(models.Task.status == status)
    if keyword:
        # or_ 表示"或"：标题或描述里包含关键字都算命中；ilike 是忽略大小写的 like
        like = f"%{keyword}%"
        conditions.append(or_(models.Task.title.ilike(like), models.Task.description.ilike(like)))

    count_stmt = select(func.count()).select_from(models.Task)
    data_stmt = select(models.Task)
    for cond in conditions:
        count_stmt = count_stmt.where(cond)
        data_stmt = data_stmt.where(cond)

    total = session.execute(count_stmt).scalar_one()
    # 默认按创建时间倒序：新任务在前，符合直觉
    rows = session.execute(
        data_stmt.order_by(models.Task.created_at.desc(), models.Task.id.desc()).offset(offset).limit(limit)
    ).scalars().all()
    return total, rows


def update(session: Session, task: models.Task, changes: dict) -> models.Task:
    """局部更新：changes 里只包含"客户端真的传了的字段"。"""
    for field, value in changes.items():
        setattr(task, field, value)  # 等价于 task.title = value 这种写法，只是字段名是动态的
    session.commit()
    session.refresh(task)
    return task


def delete(session: Session, task: models.Task) -> None:
    """删除一行。"""
    session.delete(task)
    session.commit()
