## 使用方式
```bash
sudo ifconfig wlp1s0 192.168.7.1 netmask 255.255.255.0 up

sudo iptables -A PREROUTING -t nat -d 192.168.7.1 -j ACCEPT
sudo iptables -A PREROUTING -t nat -p tcp --dport 1:65535 -j REDIRECT --to-ports 1082
sudo iptables -A PREROUTING -t nat -p udp --dport 1:65535 -j REDIRECT --to-ports 1082
```

## 一些测试如下:

iptables -A PREROUTING -t nat -d 192.168.7.1 -j ACCEPT
```result
ka@ka-Y470:~$ sudo iptables -t nat --list
Chain PREROUTING (policy ACCEPT)
target     prot opt source               destination         
ACCEPT     all  --  anywhere             ka-Y470 
```
### use ! -d to except one ip
```bash
iptables -A PREROUTING -t nat -p tcp '!' -d 192.168.31.109/24 --dport 1:65535 -j REDIRECT --to-ports 1082
# 然而app测试从本地发送请求到本地地址192.168.31.109的时候，不会经过iptables(可能会和localhost 127.0.0.1做类似的处理)
```


iptables -A PREROUTING -t nat -p tcp --dport 1:65535 -j REDIRECT --to-ports 1082
```result
Chain PREROUTING (policy ACCEPT)
target     prot opt source               destination         
REDIRECT   tcp  --  anywhere             anywhere             tcp dpts:tcpmux:65535 redir ports 1082
```



### Extra tests
iptables -A PREROUTING -t nat -i enp7s0 -p tcp --dport 1:65535 -j DNAT --to-destination 127.0.0.1:1082

```result
ka@ka-Y470:~$ sudo iptables -t nat --list
Chain PREROUTING (policy ACCEPT)
target     prot opt source               destination
DNAT       tcp  --  anywhere             anywhere             tcp dpts:tcpmux:65535 to:127.0.0.1:1082
```
