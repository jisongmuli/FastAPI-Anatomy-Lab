"""依赖注入汇总（Dependencies）。

这一层回答的问题：**接口函数需要的"外部东西"，从哪儿来。**

FastAPI 的依赖注入（DI）就是"框架帮你把参数准备好"：
    接口函数写 db: SessionDep  →  框架调用 get_session() 开一个数据库会话递进来

好处（这三个理由足够你在组会上讲清楚）：
  1) 不用每个接口都写一遍"开连接/关连接"
  2) 测试时可以**替换**它（tests/conftest.py 里 app.dependency_overrides 就干了这件事），
     从而让测试用内存数据库而不是真实数据库 —— 这是本项目能安全跑测试的关键
  3) 公共参数校验只写一次，例如分页参数
"""
from typing import Annotated, Generator

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.database import get_session


def get_db() -> Generator[Session, None, None]:
    """接口层用的数据库会话依赖。

    这里没有直接写 Depends(get_session)，而是再包一层，是个小技巧：
    测试时只要覆盖 get_db 这一个名字，简单直观。
    """
    yield from get_session()


# 起个短名字，接口签名里写 db: DbSession 就行
DbSession = Annotated[Session, Depends(get_db)]


def pagination(
    limit: int = Query(default=20, ge=1, le=100, description="每页条数，1~100"),
    offset: int = Query(default=0, ge=0, description="跳过多少条"),
) -> dict:
    """公共分页参数。凡是列表接口都注入它，避免每个接口重复写校验。"""
    return {"limit": limit, "offset": offset}


PageParams = Annotated[dict, Depends(pagination)]
