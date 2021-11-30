#include <stdio.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <string.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <stdlib.h>
#include <pthread.h>

void *recv_msg(void *arg); //接收消息

int main(int argc, char *argv[])
{
	//判断命令行参数是否满足
	if (argc != 2)
	{
		printf("请传递一个端口号\n");
		return -1;
	}

	//将接收端口号并转换为int
	int port = atoi(argv[1]);
	if (port < 1025 || port > 65535) //0~1024一般给系统使用，一共可以分配到65535
	{
		printf("端口号范围应为1025~65535");
		return -1;
	}

	// 1.创建udp通信socket
	int udp_socket_fd = socket(AF_INET, SOCK_DGRAM, 0);
	if (udp_socket_fd < 0)
	{
		perror("creat socket fail\n");
		return -1;
	}

	//2.设置UDP的地址并绑定
	struct sockaddr_in local_addr = {0};
	local_addr.sin_family = AF_INET;		 //使用IPv4协议
	local_addr.sin_port = htons(port);		 //网络通信都使用大端格式
	local_addr.sin_addr.s_addr = INADDR_ANY; //让系统检测本地网卡，自动绑定本地IP

	int ret = bind(udp_socket_fd, (struct sockaddr *)&local_addr, sizeof(local_addr));
	if (ret < 0)
	{
		perror("bind fail:");
		close(udp_socket_fd);
		return -1;
	}

	int one = 1;
	// https://stackoverflow.com/questions/5615579/how-to-get-original-destination-port-of-redirected-udp-message
	ret = setsockopt(udp_socket_fd, SOL_IP, IP_RECVORIGDSTADDR, &one, sizeof(one));
	if (ret < 0)
	{
		perror("setsockopt()");
		return (1);
	}

	// 实际上实验是根据这个blog, 实际使用可以移除以下的几行。
	// https://blogs.itmedia.co.jp/komata/2010/03/recvmsgsendmsgu.html
	ret = setsockopt(udp_socket_fd, IPPROTO_IP, IP_PKTINFO, &one, sizeof(one));
	if (ret < 0)
	{
		perror("setsockopt()");
		return (1);
	}

	//开启接收线程
	pthread_t recv_thread;
	pthread_create(&recv_thread, NULL, recv_msg, (void *)&udp_socket_fd);

	//设置目的IP地址
	struct sockaddr_in dest_addr = {0};
	dest_addr.sin_family = AF_INET; //使用IPv4协议

	int dest_port = 0;		//目的端口号
	char dest_ip[32] = {0}; //目的IP
	char msg[1024] = {0};

	//循环发送消息
	while (1)
	{
		printf("ip port msg\n");

		scanf("%s %d %s", dest_ip, &dest_port, msg);	//输入目的ip 与 端口号
		dest_addr.sin_port = htons(dest_port);			//设置接收方端口号
		dest_addr.sin_addr.s_addr = inet_addr(dest_ip); //设置接收方IP

		sendto(udp_socket_fd, msg, strlen(msg), 0, (struct sockaddr *)&dest_addr, sizeof(dest_addr));
		if (strcmp(msg, "exit") == 0 || strcmp(msg, "") == 0)
		{
			pthread_cancel(recv_thread); //取消子线程
			break;						 //退出循环
		}
		memset(msg, 0, sizeof(msg)); //清空存留消息
		memset(dest_ip, 0, sizeof(dest_ip));
	}

	//4 关闭通信socket
	close(udp_socket_fd);
}

//接收线程所要执行的函数 接收消息
void *recv_msg(void *arg)
{
	int ret = 0;
	int *socket_fd = (int *)arg; //通信的socket
	// struct sockaddr  src_addr = {0};  //用来存放对方(信息的发送方)的IP地址信息
	struct sockaddr_in src_addr = {0};
	struct msghdr cmsg;
	int len = sizeof(src_addr); //地址信息的大小
	int mLen = sizeof(cmsg);
	char msg[1024] = {0}; //消息缓冲区

#define BUF_LEN 512

	unsigned char buf[BUF_LEN];
	struct iovec iov[1];
	char cbuf[512];
	struct in_pktinfo *pktinfo;
	struct sockaddr_in sin;
	struct sockaddr_in *sorgin;

	struct cmsghdr *pcmsgh;

	iov[0].iov_base = buf;
	iov[0].iov_len = BUF_LEN;

	memset(&cmsg, 0, sizeof(cmsg));
	cmsg.msg_name = &sin;
	cmsg.msg_namelen = sizeof(sin);
	cmsg.msg_iov = iov;
	cmsg.msg_iovlen = 1;
	cmsg.msg_control = cbuf;
	cmsg.msg_controllen = 512;

	//循环接收客户发送过来的数据
	while (1)
	{
		// ret = recvfrom(*socket_fd, msg, sizeof(msg), 0, (struct sockaddr *)&src_addr, &len);
		// if(ret == -1)
		// {
		// 	printf("recv1 ret is -1\n");
		// 	break;
		// }
		// printf("[%s:%d]",inet_ntoa(src_addr.sin_addr),ntohs(src_addr.sin_port));//打印消息发送方的ip与端口号

		ret = recvmsg(*socket_fd, &cmsg, 0);
		if (ret == -1)
		{
			printf("recv2 ret is -1\n");
			break;
		}
		printf("cmsg name: [%s:%d]\n", inet_ntoa(sin.sin_addr), ntohs(sin.sin_port));
		pktinfo = NULL;
		for (pcmsgh = CMSG_FIRSTHDR(&cmsg); pcmsgh != NULL;
			 pcmsgh = CMSG_NXTHDR(&cmsg, pcmsgh))
		{
			printf("found leve %d, type %d\n", pcmsgh->cmsg_level, pcmsgh->cmsg_type);
			if (pcmsgh->cmsg_level == IPPROTO_IP &&
				pcmsgh->cmsg_type == IP_PKTINFO)
			{
				pktinfo = (struct in_pktinfo *)CMSG_DATA(pcmsgh);
				// break;
			}
			if (pcmsgh->cmsg_level == SOL_IP &&
				pcmsgh->cmsg_type == IP_RECVORIGDSTADDR)
			{
				sorgin = (struct sockaddr_in*)CMSG_DATA(pcmsgh);
			}
		}

		if (sorgin == NULL) {
			fprintf(stderr, "No cmsghdr received.\n");
			continue;
		}else {
			printf("cmsg parsed: [%s:%d]\n", inet_ntoa(sorgin->sin_addr), ntohs(sorgin->sin_port));
		}


		if (pktinfo == NULL)
		{
			fprintf(stderr, "No pktinfo received.\n");
			continue;
		}
		else
		{
			printf("*************************\n");
			printf("buf=[%s]\n", buf);
			printf("from %s:%d\n", inet_ntoa(sin.sin_addr), ntohs(sin.sin_port));
			printf("pktinfo->ipi_ifindex=%d\n", pktinfo->ipi_ifindex);
			printf("pktinfo->ipi_spec_dst=%s\n", inet_ntoa(pktinfo->ipi_spec_dst));
			printf("pktinfo->ipi_addr=%s\n", inet_ntoa(pktinfo->ipi_addr));
			printf("*************************\n");
		}
	}
	//关闭通信socket
	close(*socket_fd);
	return NULL;
}

//  TPROXY test for IP_RECVORIGDSTADDR,

// usage:
// gcc udp-server-c.c -o udp -lpthread

// in terminal 1:
// $: udp 1111
// in terminal 2:
// $: udp 2222

// then in terminal 1, send a message to terminal 2:
// $: 127.0.0.1 2222 hello

// todo: convert to cpython