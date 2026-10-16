"""临时演示脚本：把 main_minimal.py 的行为真跑一遍，用于逐行讲解。

跑法（在 02-最小可运行 目录下）：
    使用上一级目录 .venv 的解释器执行本文件
"""
import sys, json

sys.path.insert(0, ".")

from fastapi.testclient import TestClient
from main_minimal import app, FAKE_USERS

client = TestClient(app)

def show(title, resp):
    print(f"\n--- {title}")
    print(f"    请求 -> 状态码 {resp.status_code}")
    print(f"    响应 <- {json.dumps(resp.json(), ensure_ascii=False)}")

print("=" * 70)
print("一、启动时发生了什么")
print("=" * 70)
print(f"app 对象            : {app.title}")
print(f"注册的路由数量       : {len(app.routes)} 条（含 FastAPI 自带的 /docs /openapi.json 等）")
print("业务路由清单：")
for r in app.routes:
    if hasattr(r, "methods") and not r.path.startswith(("/docs", "/openapi", "/redoc")):
        print(f"    {'/'.join(sorted(r.methods)):8} {r.path}")

print()
print("=" * 70)
print("二、6 个概念逐个实测")
print("=" * 70)

show("① 根路径：无输入，固定输出", client.get("/"))
show("① 健康检查", client.get("/health"))
show("② 查询参数：不传 = 全部", client.get("/users"))
show("② 查询参数：?role=student", client.get("/users", params={"role": "student"}))
show("② 查询参数：?keyword=王", client.get("/users", params={"keyword": "王"}))
show("② 两个查询参数叠加", client.get("/users", params={"role": "student", "keyword": "小"}))
show("③ 路径参数：/users/1", client.get("/users/1"))
show("③ 路径参数：/users/999（不存在）", client.get("/users/999"))
show("③ 路径参数类型不对：/users/abc", client.get("/users/abc"))

print()
print("=" * 70)
print("三、请求体校验：四种输入，四种命运")
print("=" * 70)
show("⑤ 合法输入", client.post("/users", json={"name": "小张", "role": "student", "age": 24}))
show("⑤ 最小输入（只给 name，其他走默认值）", client.post("/users", json={"name": "小赵"}))
show("⑤ name 为空串 → 422", client.post("/users", json={"name": ""}))
show("⑤ name 超长 21 字 → 422", client.post("/users", json={"name": "x" * 21}))
show("⑤ age 超出范围 200 → 422", client.post("/users", json={"name": "小钱", "age": 200}))
show("⑤ 完全空 body → 422", client.post("/users", json={}))

print("\n    422 的响应体（看清楚它怎么指出是哪个字段错了）：")
bad = client.post("/users", json={"name": "", "age": 999})
print(f"    {json.dumps(bad.json(), ensure_ascii=False, indent=2)[:600]}")

print()
print("=" * 70)
print("四、三个必须知道的'坑'（实测证据）")
print("=" * 70)

# ---- 坑 1：age 被 response_model 静默丢弃 ----
before = len(FAKE_USERS)
r = client.post("/users", json={"name": "带年龄的人", "age": 30})
print("\n【坑 1】age 提交了，但响应里没有 age —— response_model 在过滤字段")
print(f"    提交: {{'name': '带年龄的人', 'age': 30}}")
print(f"    响应: {json.dumps(r.json(), ensure_ascii=False)}")
print(f"    原因: response_model=UserRead 只声明了 id/name/role，age 不在其中 → 被丢掉")
print(f"    而且 create_user 内部压根没把 age 存进去，所以换了真实数据库它也存不下来")

# ---- 坑 2：内存数据是共享的、会累积、重启即清空 ----
print("\n【坑 2】数据存在内存列表里，是全局共享的（不是每个请求一份）")
now = client.get("/users").json()["total"]
print(f"    最初 3 个人 → 刚才几次 POST 之后，现在 {now} 个人")
print(f"    FAKE_USERS 就是那个模块级列表，所有请求共用同一个：id 已经涨到 {FAKE_USERS[-1]['id']}")
print(f"    停止服务再启动 → 立刻回到最初的 3 个人（数据不会持久化）")

# ---- 坑 3：result = db 是"起别名"，不是复制 ----
print("\n【坑 3】result = db 并没有复制数据，它俩指向同一个列表")
import main_minimal
db_obj = main_minimal.get_fake_db()
print(f"    get_fake_db() 返回的对象 is 模块级 FAKE_USERS 吗？ -> {db_obj is FAKE_USERS}")
print(f"    含义：如果谁写一句 result.append(...)，就会污染全局数据；")
print(f"          本文件之所以安全，是因为用了列表推导式 [u for u in ...] 生成【新列表】再赋值给 result")

print()
print("=" * 70)
print("五、OpenAPI 契约：FastAPI 从代码里自动生成了什么")
print("=" * 70)
schema = client.get("/openapi.json").json()
print("自动生成的全部接口：")
for path, ops in schema["paths"].items():
    for method, spec in ops.items():
        print(f"    {method.upper():6} {path:22} summary={spec.get('summary','')}")
usr = schema["paths"]["/users"]["post"]["requestBody"]["content"]["application/json"]["schema"]
print(f"\n    POST /users 的请求体 schema 引用：{usr}")
model = schema["components"]["schemas"]["UserCreate"]
print(f"    UserCreate 的自动校验规则：")
print(f"      {json.dumps(model, ensure_ascii=False, indent=6)[:500]}")
print("\n    注意：这些规则你一行都没手写，全部来自 Field(min_length=1, max_length=20, ge=0, le=150)")
