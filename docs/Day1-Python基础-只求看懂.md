# Day 1 · Python 基础：只求"看懂"，不求"手写"

> 目标：任何一段 Python 代码递到你面前，你能说出**三件事**——
> ① 数据是什么形状 ② 数据从哪里来、到哪里去 ③ 哪几行是"真正干活"的。
>
> 读完本页 = 你能读懂本仓库 `02-最小可运行/main_minimal.py`，以及 90% 的实验室代码。

---

## 0. 先接受一个事实：你不需要会写

研究生阶段你和代码的关系有三种，**你只需要第二种**：

| 关系 | 描述 | 你 |
|---|---|---|
| 作者 | 从空白文件写出实现 | ✗ 不需要 |
| **读者 + 验收者** | 看懂结构，判断对不对，指出问题 | ✓ **你的定位** |
| 使用者 | 会跑、会调、会看报错 | ✓ 必须会 |

所以下面每条语法，我都只回答"**它在代码里长什么样、看到它你要想到什么**"。

---

## 1. 数据形状：看懂变量和类型

Python 不需要声明类型，看到赋值语句 `x = ...`，你只需要判断右边是**哪种形状**：

```python
title = "写论文"                 # 字符串：一段文字
count = 3                        # 整数
ratio = 0.75                     # 小数
done = False                     # 布尔：真/假（注意首字母大写）
tags = ["python", "测试"]         # 列表 list：有顺序、可重复、用 []  ← 最常用
user = {"name": "小王", "age": 24} # 字典 dict：键值对、用 {}          ← 第二常用
point = (3, 5)                   # 元组 tuple：不可修改的列表，用 ()
ids = {1, 2, 3}                  # 集合 set：去重、无序
```

**看到 `[]` 想列表，看到 `{"key": ...}` 想字典**——这两条能覆盖后端代码 80% 的数据。

嵌套很常见，读法是从外往里剥：

```python
tasks = [
    {"id": 1, "title": "写论文", "done": False},
    {"id": 2, "title": "跑实验", "done": True},
]
# 读法：tasks 是一个列表，每个元素是一个字典，字典的键是 id/title/done
```

**取数据**：
```python
tasks[0]              # 列表第 1 个（下标从 0 开始！）
tasks[0]["title"]     # 第 1 个任务的标题
tasks[-1]             # 最后一个
user["name"]          # 字典按键取值
user.get("phone")     # 按键取值，键不存在时返回 None，不报错 ← 更安全
```

---

## 2. 控制流：看懂"分叉"和"重复"

```python
# 分叉：满足条件才执行
if task["done"]:
    print("已完成")
elif task["id"] > 100:
    print("是个老任务")
else:
    print("进行中")
```
**重点**：Python 用**缩进（4 个空格）**表示"属于上一行"。看到缩进变深 = 进入了一个分支/循环/函数。

```python
# 重复
for task in tasks:            # 把 tasks 里每个元素依次叫 task
    print(task["title"])

for i, task in enumerate(tasks):   # 同时拿到序号 i 和元素
    print(i, task["title"])

if any(t["done"] for t in tasks):  # 有没有任意一个是完成的
    ...
```

**看到 `for ... in ...:` 就问一句：我在遍历什么？** 答案永远在 `in` 后面。

---

## 3. 函数：看懂"输入和输出"

```python
def add_task(title: str, priority: int = 3) -> dict:
    """创建一个任务字典。"""
    return {"title": title, "priority": priority, "done": False}
```

拆解这 4 个部分，**这是你读所有代码的通用公式**：

| 部分 | 含义 | 你要问的 |
|---|---|---|
| `def add_task` | 函数名 | 它负责干什么？ |
| `(title: str, priority: int = 3)` | 参数 + 类型提示 + 默认值 | 要喂给它什么？ |
| `-> dict` | 返回类型提示 | 它吐出什么？ |
| `return {...}` | 真正的返回值 | 数据流向哪？ |

调用它：`add_task("写论文")` → 得到 `{"title": "写论文", "priority": 3, "done": False}`。

> **重要**：`title: str` 和 `-> dict` 这些**类型提示是给人看的说明书**，Python 运行时并不强制检查。
> 但对 FastAPI 来说它们是**真正的功能**（后面 Day2 会讲，这是 FastAPI 的魔法来源）。

---

## 4. 类：看懂"模板和实例"

```python
class Task:
    def __init__(self, title: str):
        self.title = title      # self.xxx 就是"这个实例自己的属性"
        self.done = False

    def finish(self):           # 方法：属于这个类的函数，第一个参数永远是 self
        self.done = True

t = Task("写论文")   # 造一个实例
t.finish()          # 调用方法
print(t.title)      # 访问属性
```

**读类的三步**：
1. 看 `__init__`（构造函数）→ 知道**创建它需要什么、它有哪些属性**
2. 看其他方法 → 知道**它能干什么**
3. 看谁在用 `类名(...)` → 知道**它在哪里被创建**

> 后面 FastAPI 项目里你会看到很多 `class TaskCreate(BaseModel)` 这种写法——那是**继承**：
> `TaskCreate` 白拿了 `BaseModel` 的全部能力，再补上自己的字段。看懂"括号里是谁"就够了。

---

## 5. 模块与导入：为什么代码要拆成很多文件

```python
import os                          # 导入整个模块
from datetime import datetime      # 只导入里面一个东西
from fastapi import FastAPI, HTTPException
from app.database import get_session   # 从「包.文件」里导入函数
```

- 一个 `.py` 文件 = 一个**模块**
- 一个装着多个 `.py` 的文件夹 = 一个**包**（通常带 `__init__.py`）
- `from app.database import get_session` → 读作"**从 app 包的 database 文件里，拿 get_session 这个函数**"

**这一行就是你跨文件追踪代码的绳子**。看到不认识的函数，就去它的 import 来源文件里找定义。
在 PyCharm 里按住 `Ctrl` 点击函数名 = 直接跳过去，这是你最该练的肌肉记忆。

---

## 6. 异常：看懂报错和控制流跳转

```python
try:
    result = 10 / 0
except ZeroDivisionError as e:
    print("出错了：", e)      # 出错时不崩，走这里
finally:
    print("无论成功失败都执行")
```

看到 `try/except` 你就知道：**这是代码在防意外**。
看到 `raise HTTPException(...)` 你就知道：**这是代码主动报错**（后端的报错，就是给前端看的 HTTP 状态码）。

---

## 7. 装饰器：看到 `@` 开头的那一行

```python
@app.get("/health")
def health():
    return {"status": "ok"}
```

`@app.get("/health")` 的意思是：**"把下面这个函数登记到 /health 这个网址上"**。

它不改变函数体内的逻辑，只是**给函数挂了个标签/登记表**。你读代码时把 `@xxx` 当成"这一行是配置说明"，
真正干活的还是下面那个 `def`。

后端里最常见的三种装饰器：
- `@app.get(...)` / `@app.post(...)` → **注册接口地址**（Day2 主角）
- `@pytest.fixture` → **准备测试用的数据**（Day3 主角）
- `@property` → 把方法当属性用（少见，知道即可）

---

## 8. 你必须在今天之内动手做的 3 件事（总耗时 < 40 分钟）

### ① 跑起最小标本（10 分钟）
```powershell
cd ".\02-最小可运行"
python -m venv .venv                        # 建虚拟环境（独立的小盒子）
.\.venv\Scripts\Activate.ps1                # 进入盒子（前面会出现 (.venv)）
pip install fastapi uvicorn
uvicorn main_minimal:app --reload           # 启动服务
```
浏览器打开 <http://127.0.0.1:8000/docs> —— **这是 FastAPI 自动生成的接口文档**，
你能在网页上直接点按钮发请求。停止服务按 `Ctrl+C`。

### ② 逐行读 `main_minimal.py`（20 分钟）
打开 `02-最小可运行/main_minimal.py`，对每个 `@app.xxx` 回答三个问题：
- 这个接口的**网址**是什么？
- 它**需要什么输入**（路径参数 / 查询参数 / 请求体）？
- 它**返回什么形状**的数据？

### ③ 跑测试看"绿色通过"长什么样（10 分钟）
```powershell
cd "."
.\.venv\Scripts\Activate.ps1
pytest -v            # 看每个用例 PASSED / FAILED
```

---

## 9. Day 1 自检：能答出 7 条就算过关

1. 看到 `{"a": 1}` 和 `[1, 2]`，分别是什么类型？
2. `def f(x: int = 3) -> str:` —— 参数是什么？默认值多少？返回什么？
3. Python 靠什么判断"这几行属于同一个 if 分支"？
4. `from app.database import get_session` 这句话在说什么？
5. `class TaskCreate(BaseModel)` 里的 `(BaseModel)` 是什么意思？
6. `@app.get("/health")` 这一行是干什么的？函数的逻辑变了吗？
7. `try / except / raise` 三者分别在什么场景下出现？

> 答不出第 2、4、5 条 → 重读第 3、5、4 节。
> 能答出全部 → 直接进 `docs/Day2-FastAPI-看懂请求怎么走.md`。

---

## 10. 抄给 AI 的"读代码提问模板"（今天就开始用）

看不懂某个文件时，别问"这段代码什么意思"（太泛，AI 会给你一堆废话），用这个模板：

```
我在读 <文件路径>，只读到第 X 行。
请只回答四点，不要给我改写代码：
1) 这个文件在整个项目里扮演什么角色（一句话）
2) 它从哪些文件拿数据，又把数据交给谁
3) 逐个解释它定义的函数/类：输入是什么、输出是什么、干什么用
4) 有哪 3 个概念是我作为初学者最可能不懂的，各用两句话解释
```
