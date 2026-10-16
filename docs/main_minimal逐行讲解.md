# main_minimal.py 逐行讲解（Day1 第一份要读懂的代码）

> 这份文件是**讲解稿**，配合 `02-最小可运行/main_minimal.py` 一起看。
> 所有输出都是我实际跑出来的（用 TestClient 直接调这个 app），不是推测。

---

## 一、这个文件到底是什么？

**一句话**：它是一个**最小完整的 FastAPI 应用**，134 行里只有约 40 行是有效代码，其余全是注释和空行。

**它的定位**：

| 对比项 | `main_minimal.py` | `app/` 目录（主项目） |
|---|---|---|
| 文件数 | 1 个 | 12 个 |
| 数据存哪 | **内存里的一个列表**（关掉服务就没了） | SQLite 数据库文件 |
| 分层 | 不分层，全塞一起 | routes → service → repository → models |
| 有测试吗 | 没有 | 29 个用例 |
| 用来干什么 | **认识 FastAPI 的 6 个核心机制** | 认识"真实项目长什么样" |

**所以：它不是"玩具"，而是"标本"。** 就像学生物先看一张细胞结构图，再看真实的切片。
你不需要改它、不需要扩展它，你只需要**能指着每一段说出它在干什么**。

---

## 二、代码骨架：7 个板块

| 板块 | 行号 | 内容 | 作用 |
|---|---|---|---|
| ① 文件说明 | 1-19 | 三引号包起来的一大段 | Python 的"模块文档字符串"，`help(模块)` 能看到它 |
| ② 导入 + 创建应用 | 20-29 | `from fastapi import ...` / `app = FastAPI(...)` | 把要用的工具拿进来，造出应用对象 |
| ③ 假数据库 | 31-52 | `FAKE_USERS` 列表 + `get_fake_db()` + `DbDep` | 模拟"数据存在某个地方" |
| ④ 无输入接口 | 55-67 | `/` 和 `/health` | 最简单的形态：没有输入，固定输出 |
| ⑤ 查询参数 | 70-85 | `/users` | 网址里 `?` 后面的部分 |
| ⑥ 路径参数 | 88-97 | `/users/{user_id}` | 网址路径里的变量 + 主动报错(404) |
| ⑦ 请求体 + 入口 | 100-134 | `UserCreate` / `UserRead` / `/users` POST / `__main__` | JSON 校验 + 直接运行 |

**读代码的顺序建议**：先看 ④（最简单）→ 再看 ⑤⑥ → 最后看 ⑦（最复杂）。

---

## 三、一个必须纠正的直觉：代码是"倒着执行"的

新手最容易卡住的地方：**文件从上往下读，但它并不是从上往下执行的。**

### 启动阶段（你敲下 `uvicorn main_minimal:app` 那一刻）

```
1. 执行 from fastapi import ...        ← 把工具拿进来
2. 执行 app = FastAPI(...)             ← 造出应用对象
3. 定义 FAKE_USERS = [...]             ← 造出假数据（此时还是普通变量）
4. 定义 get_fake_db / DbDep
5. 遇到 @app.get("/")                  ← 注册！把下面的函数登记到"GET /"这张表上
6. 遇到 @app.get("/health")            ← 注册
7. ... 每个装饰器都是一次"登记"
8. 遇到 if __name__ == "__main__"      ← 被 uvicorn 启动时这里是 False，跳过
```

**关键**：第 5~7 步执行的是**装饰器**，不是函数体！
这些 `def read_root(): ...` 里的代码**一行都没运行**，它们只是被"登记"进了路由表。

> 这就像你在通讯录里存了一个号码 —— 存进去的那一刻并不会打电话。

### 请求阶段（你在 `/docs` 点了按钮）

```
浏览器  GET /users?role=student
   ↓
uvicorn 收到 → 交给 app
   ↓
app 查路由表："/users" 匹配到了 list_users  ← 第 5 步登记的那张表起作用了
   ↓
FastAPI 准备参数：db = get_fake_db() 的返回值、role = "student"、keyword = ""
   ↓
现在才真正执行 list_users 的函数体！
   ↓
返回值 {"total": 2, "items": [...]} → 自动转成 JSON → 200
```

**所以你要养成的读代码习惯**：
- 看到 `@app.xxx` → 这是**登记信息**（网址、方法）
- 看到下面的 `def` → 这是**被调用时才执行的逻辑**

### 实际注册了多少条路由？（实测）

```
业务路由 5 条：
    GET      /
    GET      /health
    GET      /users
    GET      /users/{user_id}
    POST     /users

加上 FastAPI 自带的：/docs、/redoc、/openapi.json、/docs/oauth2-redirect
总共 9 条
```
> 这也解释了为什么你打开 `/docs` 就能看到接口文档 —— 那是 FastAPI 自带的，你没写一行前端代码。

---

## 四、6 个核心机制逐个实测

### ① 创建应用 + 装饰器登记（第 25、59 行）

```python
app = FastAPI(title="最小标本 API", ...)

@app.get("/", summary="服务首页")
def read_root():
    return {"service": "minimal-fastapi", "docs": "/docs"}
```

实测：
```
GET / → 200 → {"service": "minimal-fastapi", "docs": "/docs"}
```

**怎么读**：
- `FastAPI(...)` 里的 `title`/`description`/`version` → 显示在 `/docs` 页面的顶部
- `@app.get("/")` → "把下面这个函数登记到 **GET /**"
- 函数返回 **dict** → FastAPI 自动转成 JSON（你不用手写 `json.dumps`）

> **Python 小知识**：`{"service": "..."}` 这种写法叫**字典**，转成 JSON 后长得几乎一样。

---

### ② 查询参数：网址 `?` 后面的部分（第 74-85 行）

```python
@app.get("/users", summary="按角色/关键字筛选用户")
def list_users(
    db: DbDep,
    role: Optional[str] = None,      # 不传就是 None
    keyword: str = "",               # 不传就是空字符串
):
    result = db
    if role is not None:
        result = [u for u in result if u["role"] == role]
    if keyword:
        result = [u for u in result if keyword in u["name"]]
    return {"total": len(result), "items": result}
```

**命中规则**（这是读所有 FastAPI 代码的通用口诀）：
> 参数名**没出现在** `@app.xxx("路径")` 里，且类型不是 Pydantic 模型 → 它就**自动变成查询参数**。

实测四种情况：

| 请求 | 结果 |
|---|---|
| `GET /users` | `total: 3`（全部） |
| `GET /users?role=student` | `total: 2`（小王、小李） |
| `GET /users?keyword=王` | `total: 2`（小王、王老师） |
| `GET /users?role=student&keyword=小` | `total: 2`（两个条件叠加） |

**两个新手必踩的点**：

1. `role is not None` 而不是 `if role:` —— 因为空字符串 `""` 也是"假值"，用 `is not None` 更精确
2. `result = db` **不是复制**！实测：`get_fake_db() is FAKE_USERS` → **True**（同一个列表对象）
   本文件之所以安全，是因为后面用的是**列表推导式** `[u for u in result if ...]`，
   它**生成一个新列表**再赋值给 `result`，所以不会污染原始数据。
   如果谁写成 `result.append(...)`，就会把全局数据改坏 —— 这是 Python 里最经典的坑之一。

**关于 `[u for u in result if u["role"] == role]` 怎么读**：
```
取出 result 里的每个 u，只要 u["role"] == role，就保留，组成一个新列表
```
等价于：
```python
new_list = []
for u in result:
    if u["role"] == role:
        new_list.append(u)
```
**看到方括号里先写结果、再写 for 的，就是"列表推导式"，脑内展开成 for 循环即可。**

---

### ③ 路径参数 + 主动报错（第 91-97 行）

```python
@app.get("/users/{user_id}", summary="按 ID 查一个用户")
def get_user(user_id: int, db: DbDep):
    for user in db:
        if user["id"] == user_id:
            return user
    raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")
```

**命中规则**：参数名**出现在**路径的 `{}` 里 → 路径参数，且会自动按类型提示转换。

实测：

| 请求 | 状态码 | 响应 |
|---|---|---|
| `GET /users/1` | 200 | `{"id": 1, "name": "小王", "role": "student"}` |
| `GET /users/999` | **404** | `{"detail": "用户 999 不存在"}` |
| `GET /users/abc` | **422** | 见下方 |

**`GET /users/abc` 的真实响应**（注意 `loc` 里的 `path`）：
```json
{"detail": [{
  "type": "int_parsing",
  "loc": ["path", "user_id"],
  "msg": "Input should be a valid integer, unable to parse string as an integer",
  "input": "abc"
}]}
```
因为函数写了 `user_id: int`，FastAPI 尝试把 `"abc"` 转成整数失败了 → **422**。

> **这里藏着一个重要观念**：
> `raise HTTPException(404)` 是**你主动报错**（业务判断：这个人不存在）。
> `422` 是**框架自动报错**（格式都不对，函数根本没被调用）。
> 两者是完全不同的层次，你要能区分。

**另一个观念**：为什么找不到时要报错，而不是 `return None`？
因为前端需要区分"这个用户不存在"（404）和"用户存在但字段为空"（200 + 空数据）。
**沉默地返回空数据，会让前端无法判断，是接口设计的坏习惯。**

---

### ④ 请求体 + 自动校验（第 104-125 行）

这是整个文件最值钱的部分。

```python
class UserCreate(BaseModel):          # ← "客户端要提交什么"的规格表
    name: str = Field(min_length=1, max_length=20, description="用户名")
    role: str = Field(default="student", description="角色")
    age: Optional[int] = Field(default=None, ge=0, le=150, description="年龄")


class UserRead(BaseModel):            # ← "服务端返回什么"的规格表
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
```

**`BaseModel` 是什么**：Pydantic 提供的类，你只要写字段名和类型，它就自动获得
"解析 JSON + 类型转换 + 范围校验 + 生成文档"四种能力。

**`Field(...)` 参数速查**：

| 参数 | 含义 | 例子 |
|---|---|---|
| `default` | 不传时的默认值 | `default="student"` |
| `min_length` / `max_length` | 字符串长度限制 | `min_length=1` |
| `ge` / `le` | 大于等于 / 小于等于 | `ge=0, le=150` |
| `gt` / `lt` | 大于 / 小于 | `gt=0` |
| `description` | 说明文字，会显示在 `/docs` 上 | `"用户名"` |

#### 实测：五种输入，五种命运

| # | 输入 | 状态码 | 结果 |
|---|---|---|---|
| 1 | `{"name":"小张","role":"student","age":24}` | **201** | `{"id":4,"name":"小张","role":"student"}` |
| 2 | `{"name":"小赵"}` | **201** | `{"id":5,"name":"小赵","role":"student"}` ← role 走了默认值 |
| 3 | `{"name":""}` | **422** | `loc:["body","name"]`，`string_too_short` |
| 4 | `{"name":"x"*21}` | **422** | `loc:["body","name"]`，`string_too_long` |
| 5 | `{"name":"小钱","age":200}` | **422** | `loc:["body","age"]`，`less_than_equal` |
| 6 | `{}`（空 body） | **422** | `loc:["body","name"]`，`missing` / `Field required` |

**422 响应体的通用读法**（这是你调试接口的必备技能）：

```json
{"detail": [{
  "type": "string_too_short",        ← 错误类型（机器可读）
  "loc": ["body", "name"],           ← ★ 出错位置：请求体(body)里的 name 字段
  "msg": "String should have at least 1 character",  ← 人话解释
  "input": "",                       ← 你实际传了什么
  "ctx": {"min_length": 1}           ← 违反了哪条规则
}]}
```
**`loc` 的第一个元素告诉你错在哪一层**：`body`（请求体）/ `path`（路径）/ `query`（查询参数）。
**一次可以报多个错** —— 实测同时传空 name 和 age=999，它一次把两个都列出来了。

> **最重要的一句话**：这四种 422 里，`create_user` 的**函数体一行都没执行**。
> 校验发生在"进入函数之前"。这就是为什么你的业务代码里不需要写一堆 `if not name: return 400`。

#### `max((u["id"] for u in db), default=0) + 1` 在干什么？

拆开看：
- `u["id"] for u in db` → 生成器：产出所有的 id（1, 2, 3, ...）
- `max(..., default=0)` → 取最大值；如果列表是空的，返回默认值 0
- `+ 1` → 新 id

**为什么要写 `default=0`**？因为如果 `db` 是空列表，`max()` 会直接报错。
写了默认值，空列表时 `max` 返回 0，`+1` 后新 id 就是 1。
**这是"防御性写法"的典型例子** —— 你要能看出作者在这一行防了"空数据"这种边界情况。

（真实项目里 id 由数据库自增生成，不需要手算。）

---

### ⑤ 依赖注入：`Depends` 到底做了什么（第 43-52 行）

```python
def get_fake_db() -> List[dict]:
    return FAKE_USERS

DbDep = Annotated[List[dict], Depends(get_fake_db)]
```

然后接口里写 `db: DbDep`。

**翻译成人话**：
> `DbDep` = "类型是 `List[dict]`，但**别让调用方传**，交给 `get_fake_db` 提供"

**实测验证**：`get_fake_db() is FAKE_USERS` → **True**
也就是说，依赖注入给你的就是**那个全局列表本身**，不是副本。

**为什么要有这个"多此一举"的函数？** 看它的注释就明白了：
> 后面换成真实数据库时，只改这一个函数，接口代码一行都不用动。

这就是依赖注入最大的价值 —— **把"数据从哪来"和"接口怎么用"解耦**。
在 `app/` 主项目里，同样是这个位置，换成了 `get_db()`，它返回的是真实的数据库会话。

**`Annotated[A, B]` 怎么读**："类型是 A，附带一条说明 B"。
它只是把"类型 + 依赖"打包成一个短名字，让函数签名干净。等价于直接写：
```python
def list_users(db: List[dict] = Depends(get_fake_db)):  # 老写法，效果一样
```

---

### ⑥ 直接运行的入口（第 131-134 行）

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

**`if __name__ == "__main__":` 怎么读**：
> "如果这个文件是被**直接运行**的（`python main_minimal.py`），就执行下面这段；
> 如果它是被**导入**的（`uvicorn main_minimal:app` 会导入它），就跳过。"

**为什么需要它**：同一个文件既能当脚本跑、又能当模块被导入。
`uvicorn main_minimal:app` 的时候它是被导入的，所以这段不执行；
你直接 `python main_minimal.py` 时，这段才执行，帮你启动服务。

---

## 五、三个"光看代码看不出来"的坑（全部实测）

### 坑 1：`age` 提交了，但响应里没有它 —— 字段被静默丢弃

```
提交: {"name": "带年龄的人", "age": 30}
响应: {"id": 6, "name": "带年龄的人", "role": "student"}   ← age 消失了！
```

**两层原因**（都要看懂）：
1. `response_model=UserRead` 只声明了 `id/name/role`，**age 不在其中 → 被过滤掉**
2. 更根本的：`create_user` 的函数体里**压根没把 age 存进 `new_user`**，所以就算用了真实数据库它也存不下来

**这是 bug 吗？** 在这个教学文件里它是"设计如此"。但它演示了一个真实世界的重要现象：
> **`response_model` 会静默丢弃未声明的字段 —— 这是安全特性（防止泄露密码），
> 也会成为"我明明提交了但没生效"的调试陷阱。**

排查这类问题的第一步永远是：**去看 `response_model` 声明了哪些字段。**

### 坑 2：数据是全局共享的，会累积、重启即清空

```
最初 3 个人 → 刚才几次 POST 之后，现在 6 个人
FAKE_USERS 是模块级变量，所有请求共用同一个列表
停止服务再启动 → 立刻回到最初的 3 个人
```

**含义**：
- ✅ 好处：所以你测试时"新建了就能查到"，看起来像真数据库
- ❌ 坏处：多个用户同时用会互相看到对方的数据；服务一重启全没了
- **这就是为什么真实项目必须用数据库** —— 数据库提供了持久化和并发安全

**测试上的启示**：这种"全局共享状态"会让测试之间**相互污染**
（上一个用例新建的人，下一个用例还能查到）。
主项目的 `tests/conftest.py` 专门用内存数据库 + 每个用例重建表来解决这个问题 —— 这就是"测试隔离"。

### 坑 3：`result = db` 是起别名，不是复制

```python
result = db    # ← 这不是复制！result 和 db 指向同一个列表
```

实测：`get_fake_db() is FAKE_USERS` → **True**

Python 里 `变量 = 列表` 只是给同一个对象**再起一个名字**（像给同一个人起外号）。
真正复制要用 `result = list(db)` 或 `result = db.copy()`。

本文件之所以没出事，是因为后面用列表推导式生成了**新列表**：
```python
result = [u for u in result if u["role"] == role]   # ← 每次都生成新列表
```

> **这条对你未来读代码极重要**：看到 `a = b` 时要问一句"b 是可变对象（列表/字典/对象）吗？
> 如果是，改 a 会不会连带改 b？"—— 这是 Python 里最容易产生诡异 bug 的地方。

---

## 六、FastAPI 从这份代码里"白送"了你什么（实测）

打开 `/openapi.json`，全部接口自动列出来了：

```
GET    /                      summary=服务首页
GET    /health                summary=健康检查：运维和测试最常打的接口
GET    /users                 summary=按角色/关键字筛选用户
POST   /users                 summary=新增用户
GET    /users/{user_id}       summary=按 ID 查一个用户
```

而 `UserCreate` 的校验规则也被自动转成了 OpenAPI 标准格式：
```json
"name": {"type": "string", "minLength": 1, "maxLength": 20, "description": "用户名"},
"role": {"type": "string", "default": "student", "description": "角色"}
```

**你一行都没手写这些**。它们的来源只有一处：
```python
name: str = Field(min_length=1, max_length=20, description="用户名")
```

**这就是 FastAPI 最大的价值**：`字段定义 = 校验规则 = 文档 = 给前端/测试的契约`，四合一。

对比一下 Flask 之类的框架：这些全都要你手写第二遍，写漏了就前后端不一致。

---

## 七、自己动手验证（3 分钟，强烈建议做）

```powershell
cd ".\02-最小可运行"
..\.venv\Scripts\Activate.ps1
python "_演示脚本.py"        # ← 直接看到上面所有实测输出
```

然后换成**真实服务**的方式再体验一遍：
```powershell
uvicorn main_minimal:app --reload
# 浏览器打开 http://127.0.0.1:8000/docs
```
在 `/docs` 上做这 4 件事（每一步都要问自己"状态码是多少、为什么"）：
1. 点 `GET /users` → Execute → 看响应
2. 在 `role` 输入框填 `student` 再 Execute → 对比结果条数变化
3. 点 `POST /users` → 把 body 改成 `{"name": ""}` → Execute → **看到 422**
4. 点 `GET /users/{user_id}` → 填 `999` → Execute → **看到 404**

**做完这 4 步，你就真正理解"校验在函数之前发生"这件事了。**

---

## 八、自检：能答出这 8 条就算真读懂了

1. 文件是从上往下"顺序执行"的吗？装饰器那一行执行的是什么？
2. `list_users` 里的 `role` 和 `keyword` 为什么是查询参数？判断依据是什么？
3. `GET /users/abc` 返回什么？是 `get_user` 函数报的错吗？
4. `raise HTTPException(404)` 和框架自动返回 422，哪个是"业务报错"？
5. `payload.name` 这个写法里，`payload` 是什么类型的对象？为什么能用 `.` 取值？
6. 为什么提交了 `age` 却没有返回？两个原因各是什么？
7. `result = db` 是复制吗？本文件为什么没被这个坑影响？
8. `if __name__ == "__main__":` 在 `uvicorn main_minimal:app` 启动时会执行吗？

> 答不出来的，回到对应的章节重读一遍。**目标是"知道去哪找"，不是"背下来"。**
