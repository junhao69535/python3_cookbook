#!coding=utf-8
"""
    通过CIDR地址生成对应的IP地址集
"""
# 你有一个CIDR网络地址比如“123.45.67.89/27”，你想将其转换成它所代表的所有IP
# （比如，“123.45.67.64”, “123.45.67.65”, …, “123.45.67.95”)）

# 可以使用 ipaddress 模块很容易的实现这样的计算。例如：
import ipaddress
net = ipaddress.ip_network("123.45.67.64/27")  # 前27位是网络号，剩下5位是主机号
for n in net:
    print(n)


print("===================")
net6 = ipaddress.ip_network("12:3456:78:90ab:cd:ef01:23:30/125")
for n in net6:
    print(n)


# Network 也允许像数组一样的索引取值，例如：
print(net.num_addresses)
print(net[0])


# 另外，你还可以执行网络成员检查之类的操作：
a = ipaddress.ip_address("123.45.67.69")
print(a in net)

# 一个IP地址和网络地址能通过一个IP接口来指定，例如：
inet = ipaddress.ip_interface("123.45.67.73/27")
print(inet.network)  # 网络地址
print(inet.ip)  # ip地址

# ipaddress 模块有很多类可以表示IP地址、网络和接口。 当你需要操作网络地址（比如解析、
# 打印、验证等）的时候会很有用。

# 要注意的是，ipaddress 模块跟其他一些和网络相关的模块比如 socket 库交集很少。 所以，你不能使用
# IPv4Address 的实例来代替一个地址字符串，你首先得显式的使用 str() 转换它。例如：
# a = ipaddress.ip_address("127.0.0.1")
# from socket import socket, AF_INET, SOCK_STREAM
# s = socket(AF_INET, SOCK_STREAM)
# s.connect((a, 8080))  # 错误
# s.connect((str(a), 8080))  # 正确

# 更多相关内容，请参考https://docs.python.org/3/howto/ipaddress.html