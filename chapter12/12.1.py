#!coding=utf-8
"""
    启动和停止线程
"""
# 你要为需要并发执行的代码创建/销毁线程
# threading 库可以在单独的线程中执行任何的在 Python 中可以调用的对象。你可以创建一个
# Thread 对象并将你要执行的对象以 target 参数的形式提供给该对象。 下面是一个简单的例子：
import time


def countdown(n):
    while n > 0:
        print("T-minus", n)
        n -= 1
        time.sleep(2)


from threading import Thread
t = Thread(target=countdown, args=(5,))
t.start()


# 当你创建好一个线程对象后，该对象并不会立即执行，除非你调用它的 start() 方法（当你调用
# start() 方法时，它会调用你传递进来的函数，并把你传递进来的参数传递给该函数）。Python中
# 的线程会在一个单独的系统级线程中执行（比如说一个 POSIX 线程或者一个 Windows 线程），
# 这些线程将由操作系统来全权管理。线程一旦启动，将独立执行直到目标函数返回。你可以查询一个
# 线程对象的状态，看它是否还在执行：
if t.is_alive():
    print("Still running")
else:
    print("Completed")

# 你也可以将一个线程加入到当前线程，并等待它终止：
t.join()  # 不是主线程等待其完成，而且调用它的线程等待其完成。

