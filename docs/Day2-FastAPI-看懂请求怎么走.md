# Day 2 · FastAPI：看懂"请求怎么走"

> 目标：给你任何一个 FastAPI 项目，你能在 20 分钟内回答：
> ① 入口在哪 ② 有哪几层 ③ 某个接口的请求经过了哪些文件 ④ 每个文件的职责是什么。
>
> 配套标本：本项目（`app/` + `tests/`），以及 `02-最小可运行/main_minimal.py`。

---

## 1. 先建立正确的心智模型：后端 = 一个"翻译官 + 一串流水线"

浏览器/App 只会说 HTTP（方法 + 网址 + JSON）。
数据库只会说 SQL（表和字段）。
**后端的工作就是把这门话翻译成那门话**，FastAPI 负责其中的"翻译官"部分。

一次请求就像进了流水线：

```
客户端                       FastAPI app                                    数据库
  │                              │                                            │
  │  POST /api/v1/tasks          │                                            │
  │  {"title": "写论文"}    ─────▶│ ① 路由匹配：找到 @router.post("")           │
  │                              │ ② 参数校验：按 TaskCreate 检查 JSON         │
  │                              │ ③ 依赖注入：开一个数据库 session            │
  │                              │ ④ 业务逻辑：service.create_task()           │
  │                              │ ⑤ 数据读写：repository.create()  ──────────▶│ INSERT
  │                              │ ⑥ 序列化：按 TaskRead 转成 JSON  ◀──────────│
  │  201 {"id":1,...}      ◀─────│                                            │
```

**你读任何后端代码，都是在找这条流水线的各个环节分别在哪个文件里。**

---

## 2. 最小骨架：五行代码就是一个服务

```python
from fastapi import FastAPI

app = FastAPI()                    # ① 创建应用

@app.get("/health")                # ② 把下面这个函数登记到 GET /health
def health():
    return {"status": "ok"}        # ③ 返回 dict，FastAPI 自动转成 JSON
```
启动：`uvicorn main_minimal:app --reload`
拆解这条命令：
- `main_minimal` → 文件名（模块），不含 `.py`
- `app` → 文件里那个 FastAPI 实例的变量名
- `--reload` → 改代码自动重启（开发时用，上线不要用）

**读代码的永恒三步**（对每个接口都这么问）：
1. 网址是什么？（`@app.get("/health")`）
2. 输入是什么？（函数参数）
3. 输出是什么形状？（`return` + `response_model`）

---

## 3. 路由：网址和函数是怎么绑上的

```python
@router.post("", response_model=TaskRead, status_code=201, summary="新建任务")
def create_task(payload: TaskCreate, db: DbSession):
    return service.create_task(db, payload)
```

| 元素 | 含义 | 读代码时你要得到的信息 |
|---|---|---|
| `@router.post` | HTTP 方法 | GET 读 / POST 建 / PATCH 改 / DELETE 删 |
| `""` | 路径（会拼上前缀 `/api/v1/tasks`） | 完整网址 |
| `response_model=TaskRead` | 返回数据的格式 | 响应 JSON 里有哪些字段 |
| `status_code=201` | 成功时的状态码 | 201 = 创建成功 |
| `payload: TaskCreate` | 请求体 | 客户端要传什么 |
| `db: DbSession` | 依赖注入 | 需要数据库会话 |

### 三种输入的区分方法（这是最实用的一个技能）

```python
@app.get("/users/{user_id}")            # ① 路径参数：名字出现在路径里
def get_user(user_id: int): ...

@app.get("/users")                      # ② 查询参数：不在路径里、有默认值/可选
def list_users(role: str = None, keyword: str = ""): ...

@app.post("/users")                     # ③ 请求体：参数类型是 Pydantic 模型
def create_user(payload: UserCreate): ...
```
**判断口诀**：名字在 `@app.xxx("...")` 的路径里 → 路径参数；类型是 `BaseModel` 子类 → 请求体；**剩下的都是查询参数**。

---

## 4. Pydantic：为什么 FastAPI 能"自动"校验

```python
class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    priority: int = Field(default=3, ge=1, le=5)
    status: TaskStatus = Field(default="pending")
```

这一小段干了 5 件事，**你的接口函数一行校验代码都没写**：

| 自动完成的事 | 效果 |
|---|---|
| 类型检查 | `priority: "abc"` → 拒绝 |
| 必填检查 | 缺 `title` → 拒绝 |
| 范围检查 | `priority=0` 或 `=6` → 拒绝（`ge` = greater equal，`le` = less equal） |
| 取值枚举 | `status="finished"` → 拒绝（`Literal` 限定只能是三个值之一） |
| 文档生成 | `/docs` 页面自动显示每个字段的类型、说明、限制 |

拒绝时返回 **422 Unprocessable Entity**，并且响应体里明确指出**哪个字段、什么原因**：

```json
{
  "detail": "请求参数不合法",
  "errors": [{"field": "body.title", "reason": "String should have at least 1 character"}]
}
```

> **这是 FastAPI 最值得掌握的一点**：校验前置。请求不合规时，你的业务代码根本不会被调用。
> 所以你在 service 里看到的 `if` 都是"业务规则"（如标题不能重复），而不是"格式检查"。

### 三层"数据形状"一定要分清

| 层 | 文件 | 回答的问题 | 例子 |
|---|---|---|---|
| ORM 模型 | `app/models.py` | 数据库表长什么样 | `Task` 表有 id/title/status... |
| 接口 Schema | `app/schemas.py` | 接口收发什么 | `TaskCreate` 只需要 title/priority |
| 响应 Schema | `app/schemas.py` | 返回什么（可能过滤字段） | `TaskRead` 不含任何敏感字段 |

**为什么不能混用？** 因为表里可能存了 `password_hash`、`is_deleted` 这类字段，直接返回就泄露了。
`response_model` 会自动砍掉多余的字段 —— 这是安全设计，不是啰嗦。

---

## 5. 依赖注入：`Depends` 到底在做什么

```python
def get_db():
    session = SessionLocal()
    try:
        yield session          # ← yield 出去的值，就是接口函数拿到的 db 参数
    finally:
        session.close()        # ← 接口跑完，回到这里关闭
```
```python
DbSession = Annotated[Session, Depends(get_db)]
```
接口里写 `db: DbSession`，等于告诉 FastAPI："**别让我自己开数据库连接，你帮我开，用完帮我关。**"

**三个必须知道的价值**：
1. **少写重复代码**：不用每个接口都写开/关连接
2. **可替换（测试的关键）**：`app.dependency_overrides[get_db] = 用内存库的版本` → 测试不碰真实数据库
3. **公共参数只校验一次**：`dependencies.py::pagination` 一次定义，所有列表接口复用

> 看到 `Depends(xxx)` 就读成："这个参数由 `xxx` 函数提供"。
> 看到 `yield` 就读成："前半段是准备工作，后半段是收尾工作"。

---

## 6. 分层：为什么会有一堆文件

再看一遍这张地图（**这是你本次学习最该带走的东西**）：

```
请求 ──▶ routes/tasks.py     网址、参数校验、状态码          「翻译官」
            │
            ▼
         service.py          业务规则（标题不能重复、已完成不能改）「大脑」
            │
            ▼
         repository.py       只跟数据库打交道（增删改查）        「手」
            │
            ▼
         models.py           表结构                              「数据形状」
            │
            ▼
         database.py         连接、会话、事务                    「管道」
```

**为什么要分？看这个对比：**

| 如果不分层 | 分层后 |
|---|---|
| service 里写 SQL，换数据库要改几十处 | 只改 repository |
| 测一条业务规则要启动 HTTP 服务 | 直接调 service 函数，毫秒级 |
| 一个文件 800 行，改一行怕影响别处 | 每个文件 < 150 行，职责单一 |
| 报错信息散落各处，格式不统一 | `errors.py` 统一翻译 |

**分层的直接好处就是"可以分开测试"** —— 这就是 Day 3 里"单元测试测 service、集成测试测 routes"的由来。

---

## 7. 一条请求的完整旅程（对照本项目真实文件）

### 目标：`POST /api/v1/tasks`，请求体 `{"title": "写论文", "priority": 4}`

| 步骤 | 发生什么 | 在哪个文件 |
|---|---|---|
| 1 | uvicorn 收到请求 → 交给 `app` 对象 | `app/main.py` |
| 2 | lifespan 已建好表，`include_router` 已挂上任务路由 | `app/main.py` |
| 3 | 路由匹配到 `@router.post("")` | `app/routes/tasks.py` |
| 4 | 请求体按 `TaskCreate` 校验，`priority=4` 合法 → 通过 | `app/schemas.py` |
| 5 | 注入 `DbSession`：打开 session | `app/dependencies.py` → `app/database.py` |
| 6 | 调用 `service.create_task(db, payload)` | `app/service.py` |
| 7 | service 查标题是否重复：`repository.get_by_title` | `app/repository.py` |
| 8 | 没重复 → `repository.create` 插入并 commit | `app/repository.py` → `app/models.py` |
| 9 | 返回 `Task` 对象 → 按 `TaskRead` 序列化 → **HTTP 201** | `app/schemas.py` |

如果第 7 步发现标题重复 → `raise TaskConflict` → `errors.py` 捕获 → **HTTP 409**。
如果第 4 步校验不通过 → **HTTP 422**，第 5 步之后完全不会执行。

**练习**：自己把 `GET /api/v1/tasks?status=done&limit=2` 按这张表写一遍，写不出来就回去看文件。

---

## 8. 怎么自己验证接口（不写任何前端代码）

### 方式一：Swagger UI（首选）
浏览器打开 <http://127.0.0.1:8000/docs>：
1. 点开 `POST /api/v1/tasks` → 点 **Try it out**
2. 编辑请求体的 JSON → 点 **Execute**
3. 看 **Response body**（返回的 JSON）和 **Code**（状态码）

### 方式二：curl（PowerShell 里）
```powershell
# 新建
curl.exe -s -X POST http://127.0.0.1:8000/api/v1/tasks `
  -H "Content-Type: application/json" `
  -d '{\"title\":\"写论文\",\"priority\":4}'

# 列表（带筛选和分页）
curl.exe -s "http://127.0.0.1:8000/api/v1/tasks?status=pending&limit=2"

# 故意发错：缺 title → 422
curl.exe -s -o NUL -w "%{http_code}`n" -X POST http://127.0.0.1:8000/api/v1/tasks `
  -H "Content-Type: application/json" -d '{}'
```
> Windows PowerShell 里 `curl` 是 `Invoke-WebRequest` 的别名，行为不一样，所以要写 `curl.exe`。

### 方式三：让测试帮你发请求（Day 3 主线）
```powershell
pytest tests/test_tasks_api.py -v
```

---

## 9. 你要会看的 5 个状态码

| 码 | 含义 | 什么时候出现 | 你要检查什么 |
|---|---|---|---|
| **200** | OK | 查询/更新成功 | 响应体内容对不对 |
| **201** | Created | 新建成功 | 有没有返回新对象的 id |
| **204** | No Content | 删除成功 | 响应体必须是空的 |
| **404** | Not Found | 资源不存在 | 是"真不存在"还是"路径拼错了" |
| **409** | Conflict | 业务规则冲突 | 例如标题重复、已完成不能改 |
| **422** | Unprocessable | 参数校验失败 | 看 `errors` 里哪个字段错了 |
| **500** | Server Error | 代码 bug | **去看服务端日志**，响应体里不会有细节 |

**排查顺序**：先看状态码 → 再看响应体 `detail` → 最后才去看日志里的堆栈。

---

## 10. 绿灯练习：故意改错代码，看会怎样（强烈建议做满 5 个）

做完每个练习后**改回原样**（或者 `Ctrl+Z`）。改完 `--reload` 会自动重启，直接刷新 `/docs` 重新发请求。

| # | 改哪里 | 观察什么 | 你学到的概念 |
|---|---|---|---|
| 1 | `schemas.py` 里把 `title` 的 `min_length=1` 改成 `3` | POST 一个两字标题 → 422 | 校验规则怎么写 |
| 2 | `schemas.py` 里给 `TaskRead` 加一个 `secret: str = "x"` | GET 返回里多了字段 | response_model 决定输出 |
| 3 | `routes/tasks.py` 里把 `status_code=201` 改成 `200` | POST 返回 200 而不是 201 | 状态码是可配的 |
| 4 | `service.py` 里删掉标题重复检查那三行 | POST 两个同标题 → 都成功 | 业务规则在哪一层 |
| 5 | `repository.py` 里把 `session.commit()` 注释掉 | POST 返回成功但 GET 查不到 | 事务/提交的意义 |
| 6 | `errors.py` 里把 `TaskNotFound` 的处理器改成返回 400 | 查不存在的任务 → 400 | 异常到状态码的翻译 |
| 7 | `routes/tasks.py` 的 `@router.delete` 函数里加 `return {"ok": True}` | 报错（204 不能有响应体） | 204 的约束 |
| 8 | `dependencies.py` 里把 `pagination` 的 `le=100` 改成 `le=10` | `limit=50` → 422 | 依赖里的公共校验 |

**第 5 个练习最重要** —— 它解释了为什么"接口返回成功"不等于"数据真的存进去了"，也是 Day 3 里 `test_create_then_read_task` 这个用例存在的理由。

---

## 11. 陌生 FastAPI 项目的 15 分钟体检法

拿到任何 FastAPI 项目，按这个顺序看：

| 顺序 | 看什么 | 得到什么 |
|---|---|---|
| 1 | `README.md` / `requirements.txt` | 怎么装、怎么跑、依赖有哪些 |
| 2 | 找 `FastAPI()` 出现在哪个文件 | **入口**（通常 `main.py`） |
| 3 | 入口里的 `include_router` | **一共有哪几个业务模块** |
| 4 | `routes/` 目录 | 所有接口的网址、方法、输入输出 |
| 5 | `schemas.py` 或 `models/` 里的 Pydantic 类 | **接口契约**（前端/测试对接靠它） |
| 6 | 找 `Depends(` | 有哪些依赖（数据库、登录用户、权限） |
| 7 | 数据库相关文件（`database.py` / `db.py` / `session.py`） | 用的什么数据库、表怎么建 |
| 8 | 有 `service/` 目录吗？ | 业务逻辑在哪一层 |
| 9 | 有 `tests/` 目录吗？跑一下 `pytest` | 这项目有没有测试、测试过不过 |
| 10 | 启动服务打开 `/docs` | **对着文档点一遍接口，比读代码快得多** |

---

## 12. Day 2 自检（答对 8 道即过关）

1. `uvicorn app.main:app --reload` 里的 `app.main:app` 分别指什么？
2. 一个函数参数，你怎么判断它是路径参数、查询参数还是请求体？
3. `response_model` 有什么用？为什么不能直接返回 ORM 对象？
4. `Depends(get_db)` 帮你做了什么？测试时为什么能替换它？
5. 请求体校验失败返回哪个状态码？此时 service 函数会被调用吗？
6. `service.py` 和 `repository.py` 的职责边界在哪？
7. 删除接口为什么返回 204，且函数里不能 `return`？
8. `TaskConflict` 是在哪里被翻译成 HTTP 409 的？
9. 为什么 `models.py` 和 `schemas.py` 不能合成一个文件？
10. 加了 `--reload` 后改了代码需要手动重启吗？
11. 想看某个接口的完整契约（字段、类型、限制），最快的办法是什么？
12. 服务返回 500，你应该去哪里找原因？

> 答题时的通用方法：**不知道就去对应文件里找**，找到并说出"在哪个文件第几行"就算答对。
> 学习目标是"知道去哪找"，而不是"背下来"。
