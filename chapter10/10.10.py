#!coding=utf-8
"""
    通过字符串名导入模块
"""
# 你想导入一个模块，但是模块的名字在字符串里。你想对字符串调用导入命令。

# 使用importlib.import_module()函数来手动导入名字为字符串给出的一个模块或者包的一部分。举个例子：
import importlib  # 这是更好的方式，而不应该用__import__
math = importlib.import_module("math")
print(math.sin(2))
mod = importlib.import_module("urllib.request")
u = mod.urlopen("http://www.python.org")
# 这是python反射机制，利用字符串实现导入模块
# import_module只是简单地执行和import相同的步骤，但是返回生成的模块对象。你只需要将其
# 存储在一个变量，然后像正常的模块一样使用。


# 如果你正在使用的包，import_module()也可用于相对导入。但是，你需要给它一个额外的参数。例如：
# import importlib
# # Same as 'from . import b'
# b = importlib.import_module('.b', __package__)

# 使用import_module()手动导入模块的问题通常出现在以某种方式编写修改或覆盖模块的代码时候。
# 例如，也许你正在执行某种自定义导入机制，需要通过名称来加载一个模块，通过补丁加载代码。
#
# 在旧的代码，有时你会看到用于导入的内建函数__import__()。尽管它能工作，但是
# importlib.import_module() 通常更容易使用。
#
# 自定义导入过程的高级实例见10.11小节