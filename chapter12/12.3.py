#!coding=utf-8
"""
    线程间通信
"""
# 你的程序中有多个线程，你需要在这些线程之间安全地交换信息或数据
# 从一个线程向另一个线程发送数据最安全的方式可能就是使用 queue 库中的队列了。创建一个
# 被多个线程共享的 Queue 对象，这些线程通过使用 put() 和 get() 操作来向队列中添加或
# 者删除元素。 例如：
from queue import Queue
from threading import Thread
import random


# 生产线程
def producer(out_q):
    while True:
        data = random.randint(1, 100)
        out_q.put(data)


# 消费线程
def consumer(in_q):
    while True:
        data = in_q.get()
        print(data)


q = Queue()
t1 = Thread(target=consumer, args=(q, ))
t2 = Thread(target=producer, args=(q, ))
t1.start()
t2.start()


# Queue 对象已经包含了必要的锁，所以你可以通过它在多个线程间多安全地共享数据。
# 当使用队列时，协调生产者和消费者的关闭问题可能会有一些麻烦。一个通用的解决方法是
# 在队列中放置一个特殊的值，当消费者读到这个值的时候，终止执行。例如：
# from queue import Queue
# from threading import Thread
#
# # Object that signals shutdown
# _sentinel = object()
#
# # A thread that produces data
# def producer(out_q):
#     while running:
#         # Produce some data
#         ...
#         out_q.put(data)
#
#     # Put the sentinel on the queue to indicate completion
#     out_q.put(_sentinel)
#
# # A thread that consumes data
# def consumer(in_q):
#     while True:
#         # Get some data
#         data = in_q.get()
#
#         # Check for termination
#         if data is _sentinel:
#             in_q.put(_sentinel)
#             break
#
#         # Process the data
#         ...

# 本例中有一个特殊的地方：消费者在读到这个特殊值之后立即又把它放回到队列中，将之传递下去。
# 这样，所有监听这个队列的消费者线程就可以全部关闭了。 尽管队列是最常见的线程间通信机制，
# 但是仍然可以自己通过创建自己的数据结构并添加所需的锁和同步机制来实现线程间通信。最常见的
# 方法是使用 Condition 变量来包装你的数据结构。下边这个例子演示了如何创建一个线程安全的
# 优先级队列，如同1.5节中介绍的那样。
# https://python3-cookbook.readthedocs.io/zh_CN/latest/c12/p03_communicating_between_threads.html
