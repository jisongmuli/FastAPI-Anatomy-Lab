"""接口的"出入参格式表"（Pydantic 模型）。

这一层回答的问题：**接口收什么、发什么。** 它和 models.py 的区别一定要分清：

    models.py    → 数据库里的表结构（持久化，长期存在）
    schemas.py   → 接口上的数据格式（传输，一次请求就没了）

两者经常长得很像，但**不要混用**：表里有 password_hash，接口绝不能返回它。

Pydantic 的价值：请求一进来就自动校验。字段类型不对、少了必填项、
字符串太短，FastAPI 直接返回 422，**你的业务函数根本不会被调用** ——
这就是"校验前置"，能让后面的代码少写一堆 if。
"""
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# 用 Literal 限定取值：只能是这三个之一，写错了 Pydantic 直接拒绝
TaskStatus = Literal["pending", "doing", "done"]


class TaskCreate(BaseModel):
    """POST /tasks 的请求体：客户端新建任务时提交的 JSON。"""

    title: str = Field(min_length=1, max_length=100, description="任务标题，必填")
    description: Optional[str] = Field(default=None, max_length=1000, description="详细描述，可选")
    priority: int = Field(default=3, ge=1, le=5, description="优先级 1~5，数字越大越紧急")
    status: TaskStatus = Field(default="pending", description="初始状态")


class TaskUpdate(BaseModel):
    """PATCH /tasks/{id} 的请求体：局部更新。

    PATCH 的语义是"只改我传的字段"，所以这里**所有字段都可选、默认 None**。
    配合 service 里的 model_dump(exclude_unset=True)，
    就能区分"没传这个字段"和"传了 null"——这是新手最容易写错的地方。
    """

    title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    status: Optional[TaskStatus] = None


class TaskRead(BaseModel):
    """接口返回的任务形状。

    from_attributes=True 让 Pydantic 能从 SQLAlchemy 对象的属性里取值，
    这样 service 层可以直接把 ORM 对象丢出来，不用手动拼字典。
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str] = None
    priority: int
    status: str
    created_at: datetime
    updated_at: datetime


class TaskList(BaseModel):
    """列表接口的返回：除了数据本身，还带上总数，方便前端做分页控件。"""

    total: int = Field(description="符合条件的总条数")
    items: List[TaskRead]


class Message(BaseModel):
    """简单消息响应，例如删除成功。"""

    detail: str


class HealthResponse(BaseModel):
    """健康检查响应。status 只有 ok / degraded 两种。"""

    status: Literal["ok", "degraded"]
    database: bool
    version: str
