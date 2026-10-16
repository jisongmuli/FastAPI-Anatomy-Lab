"""数据库表结构（ORM 实体）。

这一层回答的问题：**数据在数据库里长什么样。**

ORM = Object Relational Mapping（对象关系映射）：用 Python 类描述一张表，
类的属性对应字段，一个实例对应一行记录。好处是不用手写 SQL，坏处是"看不见 SQL"，
所以新手要时不时打印真实 SQL 来核对（把 config.SQL_ECHO 设为 1）。
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _now() -> datetime:
    """统一的时间来源：带时区的当前时间（UTC）。避免"服务器时区不同导致时间错乱"。"""
    return datetime.now(timezone.utc)


class Task(Base):
    """任务表：tasks。"""

    __tablename__ = "tasks"  # 数据库里的真实表名

    # Mapped[xxx] 写的是"Python 类型"，mapped_column 里写的是"数据库列定义"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    # pending（待办） / doing（进行中） / done（已完成）
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    def __repr__(self) -> str:  # pragma: no cover - 只在调试打印时用到
        """调试时 print(task) 的输出，方便一眼看清对象内容。"""
        return f"<Task id={self.id} title={self.title!r} status={self.status}>"
