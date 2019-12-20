#!coding=utf-8
"""
    发送与接收大型数组
"""
# 你要通过网络连接发送和接受连续数据的大型数组，并尽量减少数据的复制（这是核心）操作。
# 实际上是利用memoryview不会重复产生新对象，永远都是同一个对象

# 下面的函数利用 memoryviews 来发送和接受大数组：
def send_from(arr, dest):
    # 为arr创建memoryview，并以无符号型分隔每一个元素
    view = memoryview(arr).cast("B")
    while len(view):
        nsent = dest.send(view)  # send会返回实际发送了多少字节
        view = view[nsent:]  # 根据发送的字节往后移动，发送剩下的字节


def recv_into(arr, source):
    view = memoryview(arr).cast("B")
    while len(view):
        nrecv = source.recv_into(view)  # 把接收到的数据放进memoryview，返回实际放入的字节数
        view = view[nrecv:]  # memoryview做切片不会产生新对象


# 服务端
from socket import *
server = socket(AF_INET, SOCK_STREAM)
server.bind(("", 25000))
server.listen(1)
while True:
    client, addr = server.accept()
    import numpy
    arr = numpy.arange(0.0, 50000000.0)
    send_from(arr, client)



# 客户端
client = socket(AF_INET, SOCK_STREAM)
client.connect(("", 25000))
arr = numpy.zeros(shape=50000000, dtype=float)
recv_into(arr, client)


# 本节的目标是你能通过连接传输一个超大数组。这种情况的话，可以通过 array 模块或 numpy
# 模块来创建数组。


# 在数据密集型分布式计算和平行计算程序中，自己写程序来实现发送/接受大量数据并不常见。
# 不过，要是你确实想这样做，你可能需要将你的数据转换成原始字节，以便给低层的网络函数使用。
# 你可能还需要将数据切割成多个块，因为大部分和网络相关的函数并不能一次性发送或接受超大数据块。
#
# 一种方法是使用某种机制序列化数据——可能将其转换成一个字节字符串。 不过，这样最终会创建数据
# 的一个复制。 就算你只是零碎的做这些，你的代码最终还是会有大量的小型复制操作。
#
# 本节通过使用内存视图展示了一些魔法操作。 本质上，一个内存视图就是一个已存在数组的覆盖层。
# 不仅仅是那样， 内存视图还能以不同的方式转换成不同类型来表现数据。 这个就是下面这个语句的目的：
#
# view = memoryview(arr).cast('B')
# 它接受一个数组 arr并将其转换为一个无符号字节的内存视图。这个视图能被传递给socket相关函数，
# 比如 socket.send() 或 send.recv_into() 。 在内部，这些方法能够直接操作这个内存区域。
# 例如，sock.send() 直接从内存中发生数据而不需要复制。 send.recv_into() 使用这个内存区域
# 作为接受操作的输入缓冲区。
#
# 剩下的一个难点就是socket函数可能只操作部分数据。 通常来讲，我们得使用很多不同的 send()
# 和 recv_into() 来传输整个数组。 不用担心，每次操作后，视图会通过发送或接受字节数量被
# 切割成新的视图。 新的视图同样也是内存覆盖层。因此，还是没有任何的复制操作。
#
# 缺陷：
# 这里有个问题就是接受者必须事先知道有多少数据要被发送， 以便它能预分配一个数组或者确保它
# 能将接受的数据放入一个已经存在的数组中。 如果没办法知道的话，发送者就得先将数据大小发送
# 过来，然后再发送实际的数组数据。