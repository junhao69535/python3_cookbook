#!coding=utf-8
"""
    进程间传递Socket文件描述符
"""
# 你有多个Python解释器进程在同时运行，你想将某个打开的文件描述符从一个解释器传递给另外一个。
# 比如，假设有个服务器进程相应连接请求，但是实际的相应逻辑是在另一个解释器中执行的。

# 这里解释一下为什么需要。对于网络服务器多进程编程，特别是长连接，使用一个进程一个端口监听
# 所有客户端的请求，然后把这个客户端的socket传递给其他进程处理，这时候就需要进程间传递
# socket文件描述符。为什么平常写服务器多进程编程没有遇到这个是因为c和python都是通过fork()
# 去产生一个进程，fork()已经帮我们处理了socket文件描述符在进程间的传递。

# 为了在多个进程中传递文件描述符，你首先需要将它们连接到一起。在Unix机器上，你可能需要
# 使用Unix域套接字， 而在windows上面你需要使用命名管道。不过你无需真的需要去操作这些底层，
# 通常使用 multiprocessing 模块来创建这样的连接会更容易一些。
#
# 一旦一个连接被创建，你可以使用 multiprocessing.reduction 中的 send_handle()
# 和 recv_handle() 函数在不同的处理器直接传递文件描述符。 下面的例子演示了最基本的用法：
import multiprocessing
from multiprocessing.reduction import recv_handle, send_handle  # 这里屏蔽了unix和win32的区别
import socket


def worker(in_p, out_p):
    out_p.close()
    while True:
        fd = recv_handle(in_p)  # 当server没有发送fd过来，这里会阻塞
        print("CHILD: GOT FD", fd)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM, fileno=fd) as s:
            while True:
                msg = s.recv(1024)
                if not msg:
                    break
                print("CHILD: RECV {!r}".format(msg))
                s.send(msg)


def server(address, in_p, out_p, worker_pid):
    in_p.close()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    s.bind(address)
    s.listen(1)
    while True:
        client, addr = s.accept()
        print("SERVER: Got connection from", addr)
        send_handle(out_p, client.fileno(), worker_pid)
        client.close()  # 当发送完这个连接之后，服务端需要立刻关闭这个连接，但这个连接还是会在worker工作
        # 执行close()操作后，这个socket已经不再可用，因此此时fd已经释放


if __name__ == "__main__":
    # server_p和worker_p是通过同一个管道连接的，这个管道是双向的，因此server关闭了in，worker关闭了out
    c1, c2 = multiprocessing.Pipe()  # 创建一个管道，一个用于in，一个用于out
    # 服务端通过out管道发送获取到的客户端fd，worker通过in管道接收服务端发过来的fd
    worker_p = multiprocessing.Process(target=worker, args=(c1, c2))
    worker_p.start()
    server_p = multiprocessing.Process(target=server,
                                       args=(("", 15000), c1, c2, worker_p.pid))
    server_p.start()
    c1.close()
    c2.close()


# 在这个例子中，两个进程被创建并通过一个 multiprocessing 管道连接起来。 服务器进程打开一个
# socket并等待客户端连接请求。 工作进程仅仅使用 recv_handle() 在管道上面等待接收一个文件
# 描述符。 当服务器接收到一个连接，它将产生的socket文件描述符通过 send_handle() 传递给
# 工作进程。 工作进程接收到socket后向客户端回应数据，然后此次连接关闭。

# 此例最重要的部分是服务器接收到的客户端socket实际上被另外一个不同的进程处理。 服务器仅
# 仅只是将其转手并关闭此连接，然后等待下一个连接。


# 对于大部分程序员来讲在不同进程之间传递文件描述符好像没什么必要。 但是，有时候它是构建
# 一个可扩展系统的很有用的工具。例如，在一个多核机器上面， 你可以有多个Python解释器实例，
# 将文件描述符传递给其它解释器来实现负载均衡。

# send_handle() 和 recv_handle() 函数只能够用于 multiprocessing 连接。 使用它们来代
# 替管道的使用（参考11.7节），只要你使用的是Unix域套接字或Windows管道。 例如，你可以让
# 服务器和工作者各自以单独的程序来启动。下面是服务器的实现例子：
# servermp.py
from multiprocessing.connection import Listener
from multiprocessing.reduction import send_handle
import socket


def server(work_address, port):
    work_serv = Listener(work_address, authkey=b"peekaboo")
    worker = work_serv.accept()  # 接收worker进程的连接
    worker_pid = worker.recv()  # 获取worker进程的pid

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    s.bind(("", port))
    s.listen(1)
    while True:
        client, addr = s.accept()
        print("SERVER: Got connection from", addr)
        send_handle(worker, client.fileno(), worker_pid)
        client.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: server.py server_address port", file=sys.stderr)
        raise SystemExit(1)
    server(sys.argv[1], int(sys.argv[2]))


# workermp.py
from multiprocessing.connection import Client
from multiprocessing.reduction import recv_handle
import os
from socket import socket, AF_INET, SOCK_STREAM


def worker(server_address):
    serv = Client(server_address, authkey=b"peekaboo")
    serv.send(os.getpid())
    while True:
        fd = recv_handle(serv)  # 接收服务端发过来的socket
        print("WORKER: GOT FD", fd)
        with socket(AF_INET, SOCK_STREAM, fileno=fd) as client:
            while True:
                msg = client.recv(1024)
                if not msg:
                    break
                print("WORKER: RECV {!r}".format(msg))
                client.send(msg)


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: worker.py server_address", file=sys.stderr)
        raise SystemExit(1)
    worker(sys.argv[1])


# 要运行工作者，执行执行命令 python3 workermp.py /tmp/servconn . 效果跟使用Pipe()
# 例子是完全一样的。 文件描述符的传递会涉及到UNIX域套接字的创建和套接字的 sendmsg()
# 方法。 不过这种技术并不常见，下面是使用套接字来传递描述符的另外一种实现：
# server.py
import socket
import struct


def send_fd(sock, fd):
    """
    发送一个文件描述符fd
    """
    sock.sendmsg([b"x"],
                 [(socket.SOL_SOCKET, socket.SCM_RIGHTS, struct.pack("i", fd))])
    ack = sock.recv(2)
    assert ack == b"OK"


def server(work_address, port):
    work_serv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    work_serv.bind(work_address)
    work_serv.listen(1)
    worker, addr = work_serv.accept()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    s.bind(("", port))
    s.listen(1)
    while True:
        client, addr = s.accept()
        print("SERVER: Got connection from", addr)
        send_fd(worker, client.fileno())


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: server.py server_address port", file=sys.stderr)
        raise SystemExit(1)
    server(sys.argv[1], int(sys.argv[2]))


# 下面是使用套接字的工作者实现：
# worker.py
import socket
import struct


def recv_fd(sock):
    msg, ancdata, flags, addr = sock.recvmsg(1, socket.CMSG_LEN(struct.calcsize("i")))
    cmsg_level, cmsg_type, cmsg_data = ancdata[0]
    assert cmsg_level == socket.SOL_SOCKET and cmsg_type == socket.SCM_RIGHTS
    sock.sendall(b"OK")
    return struct.unpack("i", cmsg_data[0])


def worker(server_address):
    serv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    serv.connect(server_address)
    while True:
        fd = recv_fd(serv)
        print("WORKER: GOT FD", fd)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM, fileno=fd) as client:
            while True:
                msg = client.recv(1024)
                if not msg:
                    break
                print("WORKER: RECV {!r}".format(msg))
                client.send(msg)


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: worker.py server_address", file=sys.stderr)
        raise SystemExit(1)
    worker(sys.argv[1])


# 如果你想在你的程序中传递文件描述符，建议你参阅其他一些更加高级的文档， 比如
# Unix Network Programming by W. Richard Stevens  (Prentice  Hall,  1990) .
# 在Windows上传递文件描述符跟Unix是不一样的，建议你研究下 multiprocessing.reduction
# 中的源代码看看其工作原理。
