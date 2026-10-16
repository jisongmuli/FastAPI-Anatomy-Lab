# 任务清单 API · FastAPI 解剖标本

一个**故意做小但分层完整**的 FastAPI 后端项目，用于"看懂项目结构和代码文件"。
所有数据存本地 SQLite 文件，不需要装 MySQL，安装依赖后可以在本机运行。

> 不要试图背下这里的实现。你的目标是：**能指着任意一个文件说出它扮演什么角色、数据从哪来到哪去。**

---

## 一、30 秒启动

```powershell
# 1) 进入项目
git clone https://github.com/jisongmuli/FastAPI-Anatomy-Lab.git
cd FastAPI-Anatomy-Lab
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2) 激活虚拟环境（前面出现 (.venv) 就对了）
.\.venv\Scripts\Activate.ps1

# 3) 启动服务（--reload 表示改了代码自动重启）
uvicorn app.main:app --reload
```

然后打开：

| 地址 | 作用 |
|---|---|
| <http://127.0.0.1:8000/docs> | **Swagger UI**：网页上直接点按钮发请求，初学阶段最重要的一页 |
| <http://127.0.0.1:8000/redoc> | 另一种风格的接口文档 |
| <http://127.0.0.1:8000/openapi.json> | 机器可读的接口契约（前端/测试靠它对接） |
| <http://127.0.0.1:8000/health> | 健康检查 |

## 二、跑测试（Day 3 的主角）

```powershell
pytest -v                      # 逐个用例看通过情况
pytest -v -k create            # 只跑用例名包含 create 的
pytest --cov=app --cov-report=term-missing   # 顺便看覆盖率与"哪几行没被测到"
```

## 三、你会踩到的第一个坑（已帮你验证过）

**Windows PowerShell 5.1 里 `curl` 发中文会显示成乱码**，但**数据本身是好的**。
原因有两个，都不是你代码的问题：
1. PowerShell 里的 `curl` 是 `Invoke-WebRequest` 的别名，行为和老版 curl 不一样 → 请写 `curl.exe`
2. 老版 PowerShell 控制台的输出编码默认不是 UTF-8 → 显示乱码，但**数据库里存的是正确的 UTF-8**

要验证数据真的没问题，用 Python 直读数据库（本项目实测通过）：
```powershell
.\.venv\Scripts\python.exe -c "import sqlite3; print([r for r in sqlite3.connect('tasks.db').execute('select id,title from tasks')])"
# 输出示例：[(1, '验证中文是否正常存储')]  ← 中文正常，说明存储没问题
```
或者干脆用浏览器打开 <http://127.0.0.1:8000/docs> 发请求 —— 那里没有编码问题，**初学阶段首选这个**。

> 附：本项目已实测验证的接口行为（你可以照着复现）
> | 请求 | 结果 |
> |---|---|
> | `GET /health` | `200` `{"status":"ok","database":true,"version":"0.1.0"}` |
> | `POST /api/v1/tasks` 合法 JSON | `201`，返回带 id 和时间的完整对象 |
> | `POST /api/v1/tasks` 空 body `{}` | `422`，被校验层挡住，不写数据库 |
> | `GET /docs` | `200`，Swagger UI 可用 |
> | `GET /openapi.json` | 列出 5 条路径（tasks 的增删改查 + complete + health + 根路径） |

## 四、目录即地图（先看这张表，再打开文件）

```
fastapi-标本-任务清单/
├── app/                        ← 后端主程序包
│   ├── main.py                 ★ 入口：创建 app、挂路由、挂异常处理、启动时建表
│   ├── config.py                 配置：端口、数据库地址、日志
│   ├── database.py               数据库连接：engine / SessionLocal / Base / get_session
│   ├── models.py                 数据库表结构（ORM 实体，决定"数据长什么样"）
│   ├── schemas.py                接口出入参格式（Pydantic，决定"接口收什么发什么"）
│   ├── repository.py             数据访问层：只跟数据库打交道（增删改查）
│   ├── service.py                业务逻辑层：判断规则、抛业务异常
│   ├── dependencies.py           依赖注入汇总：把 session 递给接口
│   ├── errors.py                 自定义异常 + 统一异常处理器
│   └── routes/
│       └── tasks.py            ★ 路由层：定义网址、校验参数、调用 service、返回结果
└── tests/                      ← 测试包
    ├── conftest.py             ★ 测试夹具：每个用例一套干净的内存数据库 + 测试客户端
    ├── test_health.py            冒烟测试：服务活着吗
    ├── test_tasks_service.py     单元测试：只测业务逻辑，不经过 HTTP
    └── test_tasks_api.py         集成/接口测试：模拟真实 HTTP 请求走完整链路
```

**一句话记住分层**（读任何后端项目都适用）：

```
请求进来 → routes(网址/参数) → service(业务规则) → repository(读写数据库) → models(表)
                 ↑                                        ↓
              schemas(出入参校验)                    database(连接/事务)
```

**为什么非要分这么多层？** 因为每层只干一件事，所以你能**单独测试某一层**——
这就是 Day 3 里"单元测试只测 service、集成测试才走完整链路"的由来。

## 五、一次请求的完整旅程（读代码时对照这张图）

以 `POST /tasks`（新建任务）为例：

1. **uvicorn** 收到 HTTP 请求 → 交给 **FastAPI app**
2. **路由匹配**：`app/routes/tasks.py` 里 `@router.post("")` 命中
3. **参数校验**：请求体 JSON 按 `app/schemas.py::TaskCreate` 校验，不合规直接返回 **422**（你的函数根本不会被调用）
4. **依赖注入**：`app/dependencies.py::get_db` 打开一个数据库 session 递给接口
5. **业务层**：`app/service.py::create_task` 判断规则（比如标题重复就报错）
6. **数据层**：`app/repository.py::create_task` 组装 `Task` 对象，`session.add` + `commit`
7. **响应序列化**：返回的 ORM 对象按 `response_model=TaskRead` 转成 JSON，**HTTP 201**
8. 途中任何一步抛 `TaskNotFound` → `app/errors.py` 的处理器统一转成 **404** JSON

## 六、接口一览

| 方法 | 路径 | 说明 | 主要考点 |
|---|---|---|---|
| GET | `/health` | 健康检查 | 冒烟测试 |
| POST | `/tasks` | 新建任务 | 请求体校验、201 状态码 |
| GET | `/tasks` | 列表（可按 `status`/`keyword` 筛选、`limit`/`offset` 分页） | 查询参数、分页 |
| GET | `/tasks/{task_id}` | 查单个 | 路径参数、404 |
| PATCH | `/tasks/{task_id}` | 局部更新（只传想改的字段） | PATCH vs PUT |
| POST | `/tasks/{task_id}/complete` | 标记完成 | 业务动作型接口 |
| DELETE | `/tasks/{task_id}` | 删除 | 204 无内容响应 |

## 七、配套讲义（建议按顺序读）

| 文件 | 内容 |
|---|---|
| `docs/00-三天速成路线图.md` | 先看这个：三天怎么分配、每小时的产出是什么 |
| `docs/Day1-Python基础-只求看懂.md` | 数据形状、控制流、函数、类、模块、装饰器 |
| `docs/Day2-FastAPI-看懂请求怎么走.md` | 路由↔函数映射、Pydantic、依赖注入、分层、终端验证 |
| `docs/Day3-软件测试-看懂测试报告.md` | pytest 结构、夹具、单元 vs 集成、覆盖率、Bug 报告 |
| `docs/常见疑问-概念对照表.md` | 装饰器/类型提示/async/yield/虚环境等 20 个卡点 |
| `docs/自检手册-怀疑清单.md` | 拿到任何陌生项目时的 15 分钟体检流程 |
| `docs/术语表-中英对照.md` | 组会和论文里会反复出现的词 |

---

**这个项目里没有一行"炫技"代码。** 如果某处你觉得绕，那大概率不是因为难，而是因为我注释写得不够 —— 直接问我。
