"""项目配置。

读代码要点：这里只负责"读配置、存配置"，不干别的活。
真实项目常用 pydantic-settings 从 .env 文件读取；本项目为了少一个依赖，直接用 os.environ。
"""
import os

# 当前文件所在目录（app/），再上一层就是项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 数据库地址：默认在项目根目录生成一个 tasks.db 文件
# 环境变量 DATABASE_URL 优先级更高 —— 测试时会把它换成内存数据库
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'tasks.db')}")

# 服务监听地址
HOST = os.getenv("APP_HOST", "127.0.0.1")
PORT = int(os.getenv("APP_PORT", "8000"))

# 接口统一前缀。加 /api/v1 是行业惯例：以后接口要大改时，可以并存 /api/v2 而不弄坏老客户端
API_PREFIX = "/api/v1"

# 是否打印 SQL 语句。调试数据库问题时把它设为 "1" 特别有用
SQL_ECHO = os.getenv("SQL_ECHO", "0") == "1"
