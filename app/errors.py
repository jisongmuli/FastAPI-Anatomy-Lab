"""自定义异常与统一异常处理器。

为什么需要它？
如果每个接口都写 try/except 再手动 return 错误 JSON，代码会又长又乱，
而且不同人写的接口报错格式还不一样，前端要写一堆兼容代码。

分层做法：
  service 层只管 raise TaskNotFound(task_id)     —— 只表达"出什么事了"
  errors.py 统一翻译成 HTTP 404 + 固定 JSON 格式  —— 只负责"怎么告诉客户端"

这样业务代码干净，错误格式还统一。
"""
import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class TaskNotFound(Exception):
    """任务不存在。"""

    def __init__(self, task_id: int) -> None:
        self.task_id = task_id
        super().__init__(f"任务 {task_id} 不存在")


class TaskConflict(Exception):
    """业务规则冲突，例如标题重复。"""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def register_exception_handlers(app: FastAPI) -> None:
    """把所有自定义异常登记到 app 上。main.py 启动时调用一次。"""

    @app.exception_handler(TaskNotFound)
    async def _task_not_found(request: Request, exc: TaskNotFound) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})

    @app.exception_handler(TaskConflict)
    async def _task_conflict(request: Request, exc: TaskConflict) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": exc.message})

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        """参数校验失败统一返回 422，并把"哪个字段错了"说清楚。

        FastAPI 默认也会返回 422，这里重写是为了把结构简化成 {"detail": [...], "errors": [...]}，
        前端和测试都能稳定解析。
        """
        return JSONResponse(
            # 注：新版 Starlette 把常量名改成了 HTTP_422_UNPROCESSABLE_CONTENT，
            # 老名字还能用但会告警。这里用 getattr 兼容两种版本，避免你看到一堆黄色警告。
            status_code=getattr(
                status, "HTTP_422_UNPROCESSABLE_CONTENT", None
            ) or status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "请求参数不合法",
                "errors": [
                    {"field": ".".join(str(p) for p in err.get("loc", [])), "reason": err.get("msg", "")}
                    for err in exc.errors()
                ],
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        """兜底：任何没被预料到的异常都返回 500，同时把堆栈写进日志。

        注意：绝不能把 str(exc) 返回给客户端 —— 那可能泄露数据库结构、文件路径等信息。
        调试时应该去看服务端日志，而不是看响应体。
        """
        logger.exception("未处理异常: %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})
