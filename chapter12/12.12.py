#!coding=utf-8
"""
    使用生成器代替线程
"""
# 你想使用生成器（协程）替代系统线程来实现并发。这个有时又被称为用户级线程或绿色线程。

# 要使用生成器实现自己的并发，你首先要对生成器函数和 yield 语句有深刻理解。 yield 语句会
# 让一个生成器挂起它的执行，这样就可以编写一个调度器， 将生成器当做某种“任务”并使用任务
# 协作切换来替换它们的执行。 要演示这种思想，考虑下面两个使用简单的 yield 语句的生成器函数：
def countdown(n):
    while n > 0:
        print("T-minus", n)
        yield
        n -= 1
    print("Blastoff!")


def countup(n):
    x = 0
    while x < n:
        print("Counting up", x)
        yield
        x += 1


# 这些函数在内部使用yield语句，下面是一个实现了简单任务调度器的代码：
from collections import deque


class TaskScheduler:
    def __init__(self):
        self._task_queue = deque()

    def new_task(self, task):
        """提交一个新的开始任务给调度器"""
        self._task_queue.append(task)

    def run(self):
        """运行任务直到没有任务"""
        while self._task_queue:
            task = self._task_queue.popleft()
            try:
                # 运行直到下一个yield表达式
                next(task)
                self._task_queue.append(task)  # 往队列放回任务，直到任务跳出循环
            except StopIteration:
                pass


# Example use
# sched = TaskScheduler()
# sched.new_task(countdown(10))
# sched.new_task(countdown(5))
# sched.new_task(countup(15))
# sched.run()


# 到此为止，我们实际上已经实现了一个“操作系统”的最小核心部分。 生成器函数就是任务，
# 而yield语句是任务挂起的信号。 调度器循环检查任务列表直到没有任务要执行为止。

# 实际上，你可能想要使用生成器来实现简单的并发。 那么，在实现actor或网络服务器的时候你可以
# 使用生成器来替代线程的使用。
#
# 下面的代码演示了使用生成器来实现一个不依赖线程的actor：
from collections import deque


class ActorScheduler:
    def __init__(self):
        self._actors = {}  # actors的名字映射
        self._msg_queue = deque()

    def new_actor(self, name, actor):
        self._msg_queue.append((actor, None))  # 给None用于激活生成器
        self._actors[name] = actor

    def send(self, name, msg):
        """发送信息给一个actor"""
        actor = self._actors.get(name)
        if actor:
            self._msg_queue.append((actor, msg))

    def run(self):
        """不断运行只要还有候补信息"""
        while self._msg_queue:
            actor, msg = self._msg_queue.popleft()
            try:
                actor.send(msg)  # 发送消息时，这里会挂起，把控制权交给actor
            except StopIteration:
                pass


# Example use
if __name__ == "__main__":
    def printer():
        while True:
            msg = yield  # 可以通过printer.send(None)或者next(printer)激活生成器，效果一样
            print("Got:", msg)

    def counter(sched):
        while True:
            # 接收当前count
            n = yield
            if n == 0:
                break
            # 发送printer任务
            sched.send("printer", n)  # 向调度器发送这个任务，printer执行完打印会挂起，然后返回到这里
            # 发送下一个计数到计数器任务（递归）
            sched.send("counter", n - 1)  # printer挂起后返回这里，再向调度器发送任务，然后执行到yield挂起


    sched = ActorScheduler()
    # 创建初始化actors
    sched.new_actor("printer", printer())  # 这两个用于激活生成器
    sched.new_actor("counter", counter(sched))
    # 发送初始化信息给counter用于初始化
    sched.send("counter", 10000)
    sched.run()


# 完全弄懂这段代码需要更深入的学习，但是关键点在于收集消息的队列。 本质上，调度器在有需要
# 发送的消息时会一直运行着。 计数生成器会给自己发送消息并在一个递归循环中结束。
#
# 下面是一个更加高级的例子，演示了使用生成器来实现一个并发网络应用程序：
from collections import deque
from select import select


# 这个类展示一个在调度器中的通用生成事件
class YieldEvent:
    def handle_yield(self, sched, task):
        pass

    def handle_resume(self, sched, task):
        pass


# 任务调度器
class Scheduler:
    def __init__(self):
        self._numtasks = 0  # 总的任务数
        self._ready = deque()  # 准备运行的任务
        self._read_waiting = {}  # 等待执行读的任务
        self._write_waiting = {}  # 等待执行写的任务

    # 轮询I/O事件和重启等待任务
    def _iopoll(self):
        rset, wset, eset = select(self._read_waiting, self._write_waiting, [])
        for r in rset:
            evt, task = self._read_waiting.pop(r)
            evt.handle_resume(self, task)
        for w in wset:
            evt, task = self._write_waiting.pop(w)
            evt.handle_resume(self, task)

    def new(self, task):
        """添加一个新任务到调度器"""
        self._ready.append((task, None))
        self._numtasks += 1

    def add_ready(self, task, msg=None):
        """添加一个准备开始的任务到准备队列，
        msg是发送给任务"""
        self._ready.append((task, msg))

    # 添加任务到读集合
    def _read_wait(self, fileno, evt, task):
        self._read_waiting[fileno] = (evt, task)

    # 添加任务到写集合
    def _write_wait(self, fileno, evt, task):
        self._write_waiting[fileno] = (evt, task)

    def run(self):
        """运行一个任务调度器直到没有任务"""
        while self._numtasks:
            if not self._ready:
                self._iopoll()
            task, msg = self._ready.popleft()
            try:
                # 运行协程到下一个yield
                r = task.send(msg)
                if isinstance(r, YieldEvent):
                    r.handle_yield(self, task)
                else:
                    raise RuntimeError("unrecognized yield event")
            except StopIteration:
                self._numtasks -= 1


# 基于协程实现的socket I/O
class ReadSocket(YieldEvent):
    def __init__(self, sock, nbytes):
        self.sock = sock
        self.nbytes = nbytes

    def handle_yield(self, sched, task):
        sched._read_wait(self.sock.fileno(), self, task)

    def handle_resume(self, sched, task):
        data = self.sock.recv(self.nbytes)
        sched.add_ready(task, data)


class WriteSocket(YieldEvent):
    def __init__(self, sock, data):
        self.sock = sock
        self.data = data

    def handle_yield(self, sched, task):
        sched._write_wait(self.sock.fileno(), self, task)

    def handle_resume(self, sched, task):
        nsent = self.sock.send(self.data)
        sched.add_ready(task, nsent)


class AcceptSocket(YieldEvent):
    def __init__(self, sock):
        self.sock = sock

    def handle_yield(self, sched, task):
        sched._read_wait(self.sock.fileno(), self, task)

    def handle_resume(self, sched, task):
        r = self.sock.accept()
        sched.add_ready(task, r)


# 用yield包装一个socket对象
class Socket(object):
    def __init__(self, sock):
        self._sock = sock

    def recv(self, maxbytes):
        return ReadSocket(sock, maxbytes)

    def send(self, data):
        return WriteSocket(self._sock, data)

    def accept(self):
        return AcceptSocket(self._sock)

    def __getattr__(self, name):
        return getattr(self._sock, name)


if __name__ == "__main__":
    from socket import socket, AF_INET, SOCK_STREAM
    import time

    # 涉及生成器的函数，这应该这样调用：
    # line = yield from readline(sock)
    def readline(sock):
        chars = []
        while True:
            c = yield sock.recv(1)
            if not c:
                break
            chars.append(c)
            if c == b"\n":
                break
        return b"".join(chars)

    # 使用协程的Echo server
    class EchoServer:
        def __init__(self, addr, sched):
            self.sched = sched
            sched.new(self.server_loop(addr))

        def server_loop(self, addr):
            s = Socket(socket(AF_INET, SOCK_STREAM))
            s.bind(addr)
            s.listen(5)
            while True:
                c, a = yield s.accept()
                print("Got connection from ", a)
                self.sched.new(self.client_handler(Socket(c)))

        def client_handler(self, client):
            while True:
                line = yield from readline(client)
                if not line:
                    break
                line = b"GOT:" + line
                while line:
                    nsent = yield client.send(line)
                    line = line[nsent:]
            client.close()
            print("Client closed")

    sched = Scheduler()
    EchoServer(("", 16000), sched)
    sched.run()
# 这段代码有点复杂。不过，它实现了一个小型的操作系统。 有一个就绪的任务队列，并且还有
# 因I/O休眠的任务等待区域。 还有很多调度器负责在就绪队列和I/O等待区域之间移动任务。


# 在构建基于生成器的并发框架时，通常会使用更常见的yield形式：
#
# def some_generator():
#     ...
#     result = yield data
#     ...
# 使用这种形式的yield语句的函数通常被称为“协程”。 通过调度器，yield语句在一个循环中被处理，如下：
#
# f = some_generator()
#
# # Initial result. Is None to start since nothing has been computed
# result = None
# while True:
#     try:
#         data = f.send(result)
#         result = ... do some calculation ...
#     except StopIteration:
#         break
# 这里的逻辑稍微有点复杂。不过，被传给 send() 的值定义了在yield语句醒来时的返回值。 因此，
# 如果一个yield准备在对之前yield数据的回应中返回结果时，会在下一次 send() 操作返回。
# 如果一个生成器函数刚开始运行，发送一个None值会让它排在第一个yield语句前面。
#
# 除了发送值外，还可以在一个生成器上面执行一个 close() 方法。 它会导致在执行yield语句
# 时抛出一个 GeneratorExit 异常，从而终止执行。 如果进一步设计，一个生成器可以捕获这个
# 异常并执行清理操作。 同样还可以使用生成器的 throw() 方法在yield语句执行时生成一个任意
# 的执行指令。 一个任务调度器可利用它来在运行的生成器中处理错误。
#
# 最后一个例子中使用的 yield from 语句被用来实现协程，可以被其它生成器作为子程序或过程
# 来调用。 本质上就是将控制权透明的传输给新的函数。 不像普通的生成器，一个使用
# yield from 被调用的函数可以返回一个作为 yield from 语句结果的值。 关于 yield from
# 的更多信息可以在 PEP 380 中找到。
#
# 最后，如果使用生成器编程，要提醒你的是它还是有很多缺点的。 特别是，你得不到任何线程
# 可以提供的好处。例如，如果你执行CPU依赖或I/O阻塞程序， 它会将整个任务挂起知道操作完成。
# 为了解决这个问题， 你只能选择将操作委派给另外一个可以独立运行的线程或进程。 另外一个
# 限制是大部分Python库并不能很好的兼容基于生成器的线程。 如果你选择这个方案，你会发现
# 你需要自己改写很多标准库函数。 作为本节提到的协程和相关技术的一个基础背景，可以查看
# PEP 342 和 “协程和并发的一门有趣课程”
#
# PEP 3156 同样有一个关于使用协程的异步I/O模型。 特别的，你不可能自己去实现一个底层的
# 协程调度器。 不过，关于协程的思想是很多流行库的基础， 包括 gevent, greenlet,
# Stackless Python 以及其他类似工程。

