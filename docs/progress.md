## todo
为了完成udp proxy：
1. 将udp-server-c-lib.c++代码改成library done
1.1 udp-server-c-lib.c++需要返回一个json格式的数据， 然后在python端parse
2. eventloop 增加一个定时器调度
3. nginx 能否处理重定向然后从比如数据的额外部分获取真实信息？ 但是nginx好像是处理http协议的。

## done
1. 2021-12-12 再次测试udp-server-c-lib.c++失败了，并不能找到iptables重定向后的真实的目的地址。