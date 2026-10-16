"""路由层（Router）。

这一层回答的问题：**什么网址、什么方法、收什么、返回什么。**
它是"HTTP 世界"和"业务世界"的翻译官，自身**不写业务规则**。

读任何 FastAPI 路由文件的固定套路：
    1. 看 @router.xxx("/路径")      → 网址和方法
    2. 看函数参数                    → 输入（路径参数 / 查询参数 / 请求体 / 依赖）
    3. 看 response_model 和 status_code → 输出格式和状态码
    4. 看函数体                      → 调用哪个 service 函数
"""
from fastapi import APIRouter, status

from app import service
from app.dependencies import DbSession, PageParams
from app.schemas import Message, TaskCreate, TaskList, TaskRead, TaskUpdate
from typing import Optional
from fastapi import Query

# prefix：这个文件里所有路径都会自动加上 /tasks
# tags：在 /docs 页面上分组显示，接口多了以后特别好用
router = APIRouter(prefix="/tasks", tags=["任务"])


@router.post(
    "",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,  # 新建成功用 201，不是 200
    summary="新建任务",
)
def create_task(payload: TaskCreate, db: DbSession):
    """请求体自动按 TaskCreate 校验；不合规直接 422，下面的函数体不会执行。"""
    return service.create_task(db, payload)


@router.get("", response_model=TaskList, summary="任务列表（可按状态/关键字筛选并分页）")
def list_tasks(
    db: DbSession,
    page: PageParams,  # 分页参数由依赖注入提供，不用手写
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",  # 地址栏里叫 status，函数里叫 status_filter（避免和 import 的 status 撞名）
        pattern="^(pending|doing|done)$",
        description="按状态筛选",
    ),
    keyword: Optional[str] = Query(default=None, max_length=50, description="标题或描述里的关键字"),
):
    total, items = service.list_tasks(
        db, status=status_filter, keyword=keyword, limit=page["limit"], offset=page["offset"]
    )
    # 注意这里返回的是字典，FastAPI 会用 response_model=TaskList 把它校验+序列化
    return {"total": total, "items": items}


@router.get("/{task_id}", response_model=TaskRead, summary="查询单个任务")
def get_task(task_id: int, db: DbSession):
    """task_id 写在路径里（"路径参数"），FastAPI 自动转成 int；转不了就是 422。"""
    return service.get_task(db, task_id)


@router.patch("/{task_id}", response_model=TaskRead, summary="局部更新任务")
def update_task(task_id: int, payload: TaskUpdate, db: DbSession):
    """PATCH = 只改传过来的字段。想整体替换用 PUT，语义不同。"""
    return service.update_task(db, task_id, payload)


@router.post("/{task_id}/complete", response_model=TaskRead, summary="标记任务完成")
def complete_task(task_id: int, db: DbSession):
    """业务动作型接口：路径里用动词，适合"不是简单改字段"的操作。"""
    return service.complete_task(db, task_id)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除任务")
def delete_task(task_id: int, db: DbSession):
    """204 = 成功但没有响应体。所以这个函数什么都不返回。
    如果你在这里 return 了东西，FastAPI 会报错 —— 这是个经典新手坑。"""
    service.delete_task(db, task_id)
