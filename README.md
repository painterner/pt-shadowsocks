## 其他执行参考:
search: python/tproxy, tproxy

## 重写代码目的:为了任意代码语言的执行， 所以记录。
1. 找到一个方法能够获得任意语言的socket的数据状态的方法(以决定POLL_IN, POLL_OUT)

## todo
1. 自定义自己的一套编码体系，从实践意义上来看到底转义符的可能性和逻辑到底有多复杂。
2. 客户端断开连接后，需要通知server去断开server 连接. 否则当使用sockserver-simple.py来测试的时候， 会出现使用直接请求和proxy请求不一致的结果。

## Idea
从硬件驱动层面proxy所有的数据到vps, 然后vps中建立一个docker, 在这个docker内部把数据发送出去, 由docker的net来自动进行
地址转换 ?


## start
Machine B:
```bash
python3 main.py --local -v 
python3 main.py --server --port 1092 -v

python3 sockserver.py  # 或者使用 python3 sockserver-close.py(传输一次即close的测试)
python3 servers/https-server.py #(listen data from netcard, then convert to socks protocol)
python3 servers/udp-server.py #(listen data from netcard by udp, then convert to socks protocol, uncompleted)
```

* Open Port forward (否则 iptables的配置不起作用)
>  
  vim /etc/systctl.conf  
  sudo sysctl -p
* Deploy iptables according to `iptables.md`

Machine A:
curl www.baidu.com -v

### test1
python3 request.py


### test2-done
python3 backward-proxy.py
curl https://localhost:8100
> failed ! proxy remote didn't receive anything  from baidu , why?
> possibile: 1. after connect to server, server will send https first. 2. client data need separated send to server for serveral times
> to solve: build two threads to receive data from client and receive data from server and proxy them.

### test3 (把test2中所有socke修改为recv64 --> sock.recv(1024*64)解决了无法连到baidu的问题(所以https必须一次性接受足够的数据量才行?))
cd clients
python3 backward-proxy.py
curl https://localhost:8100 --insecure
> failed !  最终收到('b'\x15\x03\x03\x00\x1a\x00\x00\x00\x00\x00\x00\x00\x02\xaaj\x01\xef\x9e\xd7;\x7fT\xf4\x07\x028\x8bx\x9b>$') (接受到的数据是什么意思?仍然是ssl过程,但是由于不符合约定所以告诉curl去关闭连接?)
但是 curl 命令行返回empty
==> 说明还是与host的payload有关？ 但是test2的问题解决了说明不会存在这种问题?

### test4 succeed
cd clients
python3 py-https-proxy.py
参考例子clients/py-https.py可以看出HTTP协议头也会被ssl加密，HTTP头部如果与目标主机不对应，会出错（测试py-https.py如果出错会报405 not allowed)。

todo:
nodejs 建立httpSever proxy（这样就不用使用python的select来处理麻烦的多用户io map问题了)

## 可能出现问题
1. 如果服务器根据http的header中的host来cros或者路由(不可能路由,因为客户端一般在内网).那么有可能日后需要更改host ?

## 理论
1. 服务器理论上是无法区分http/https的连接是否是代理的。 http不用说，如果是https, 可以先转化为http连接，然后在
header上标记需要进行https代理，那么所有的加密工作就可以转交为代理服务器来做，所以目标服务器只能认定请求是从代理服务器
发出的。