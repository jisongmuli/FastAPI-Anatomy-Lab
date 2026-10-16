"""
最小可运行的 FastAPI 标本（约 40 行有效代码）。
================================================================
它把 FastAPI 最核心的 6 个概念压缩进一个文件，用来看懂"一个后端接口"的全貌：
  ① 创建应用 app = FastAPI(...)
  ② 路由装饰器 @app.get / @app.post      —— 网址与函数的绑定
  ③ 查询参数  def f(keyword: str = "")   —— 网址里 ?keyword=xxx 的部分
  ④ 路径参数  @app.get("/users/{user_id}") —— 网址里 /users/3 的 3
  ⑤ Pydantic 请求体 + 自动校验            —— 客户端 POST 上来的 JSON
  ⑥ 依赖注入 Depends + HTTPException      —— 复用逻辑与主动报错

启动：
    uvicorn main_minimal:app --reload
或（不装 uvicorn 也能跑）：
    python main_minimal.py

打开文档： http://127.0.0.1:8000/docs
================================================================
"""
from typing import Annotated, List, Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="最小标本 API",
    description="用来读懂 FastAPI 请求流转的玩具服务，数据只存在内存里。",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# 0. 「假数据库」：一个内存列表。
#    真实项目这里是 MySQL / SQLite，但读代码时你只要知道：
#    "数据存在某个地方，接口通过函数把它取出来"。
# ---------------------------------------------------------------------------
FAKE_USERS: List[dict] = [
    {"id": 1, "name": "小王", "role": "student"},
    {"id": 2, "name": "小李", "role": "student"},
    {"id": 3, "name": "王老师", "role": "teacher"},
]


def get_fake_db() -> List[dict]:
    """依赖注入用的函数：谁需要数据，FastAPI 就把这个列表递给谁。

    看到 Depends(get_fake_db) 你就理解成：这个参数不用调用方传，框架帮你准备好。
    后面换成真实数据库时，只改这一个函数，接口代码一行都不用动 —— 这就是依赖注入的价值。
    """
    return FAKE_USERS


DbDep = Annotated[List[dict], Depends(get_fake_db)]  # 给这个依赖起个短名字，读起来更清爽


# ---------------------------------------------------------------------------
# 1. 最简单的接口：没有输入，固定输出。
#    读法：@app.get("/") 说明网址是根路径；函数返回 dict，FastAPI 自动转成 JSON。
# ---------------------------------------------------------------------------
@app.get("/", summary="服务首页")
def read_root():
    return {"service": "minimal-fastapi", "docs": "/docs"}


@app.get("/health", summary="健康检查：运维和测试最常打的接口")
def health_check():
    # 真实项目里这里会顺便检查数据库连接。测试流水线第一步通常就是打这个接口。
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# 2. 查询参数：网址里 ? 后面的部分，例如 /users?role=student&keyword=小
#    读法：函数参数只要不是路径里出现的名字，就被 FastAPI 当成查询参数。
# ---------------------------------------------------------------------------
@app.get("/users", summary="按角色/关键字筛选用户")
def list_users(
    db: DbDep,
    role: Optional[str] = None,      # 可选：不传就是 None
    keyword: str = "",               # 有默认值：不传就是空字符串
):
    result = db
    if role is not None:
        result = [u for u in result if u["role"] == role]
    if keyword:
        result = [u for u in result if keyword in u["name"]]
    return {"total": len(result), "items": result}


# ---------------------------------------------------------------------------
# 3. 路径参数：网址的一部分，例如 /users/1 里的 1，自动转成 int。
# ---------------------------------------------------------------------------
@app.get("/users/{user_id}", summary="按 ID 查一个用户")
def get_user(user_id: int, db: DbDep):
    for user in db:
        if user["id"] == user_id:
            return user
    # 找不到时要主动报错，而不是返回空——这是后端的基本礼貌（让前端知道是 404 而不是"空数据"）
    raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")


# ---------------------------------------------------------------------------
# 4. 请求体 + 自动校验：客户端 POST 上来的 JSON，由 Pydantic 模型负责"格式检查"。
#    读法：class Xxx(BaseModel) 就是一张"数据规格表"，字段类型写了就自动校验。
# ---------------------------------------------------------------------------
class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=20, description="用户名")
    role: str = Field(default="student", description="角色")
    age: Optional[int] = Field(default=None, ge=0, le=150, description="年龄")


class UserRead(BaseModel):
    """返回给客户端的形状。用 response_model 声明后，多余字段会被自动过滤掉（防止泄露密码之类）。"""
    id: int
    name: str
    role: str


@app.post("/users", response_model=UserRead, status_code=201, summary="新增用户")
def create_user(payload: UserCreate, db: DbDep):
    new_user = {
        "id": max((u["id"] for u in db), default=0) + 1,
        "name": payload.name,
        "role": payload.role,
    }
    db.append(new_user)
    return new_user


# ---------------------------------------------------------------------------
# 5. 直接运行本文件时的启动方式（方便不想敲 uvicorn 命令的同学）。
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
