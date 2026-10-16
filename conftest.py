"""项目根级 conftest.py —— 只有一个作用：让测试能 import app 包。

原理：pytest 会把 conftest.py 所在目录加入模块搜索路径（sys.path），
所以 tests/ 里的 `from app.main import app` 才能找到 app/ 目录。

如果你在别处看到"ModuleNotFoundError: No module named 'app'"，八成就是缺了这个文件，
或者你在错误目录下执行了 pytest（应该在项目根目录执行）。
"""
