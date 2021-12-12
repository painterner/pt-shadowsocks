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

#include <nlohmann/json.hpp>
// json serialization tool
// https://github.com/nlohmann/json#integration
// sudo apt install nlohmann-json-dev

// for convenience
using json = nlohmann::json;

#define BUF_LEN 65 * 1024

class AllData
{
public:
	int ret = 0;
	int *socket_fd;
	// struct sockaddr  src_addr = {0};  //用来存放对方(信息的发送方)的IP地址信息
	struct sockaddr_in src_addr = {0};
	struct msghdr cmsg;
	int len = sizeof(src_addr); //地址信息的大小
	int mLen = sizeof(cmsg);
	char msg[1024] = {0}; //消息缓冲区

	unsigned char buf[BUF_LEN];
	struct iovec iov[1];
	char cbuf[512];
	struct in_pktinfo *pktinfo;
	struct sockaddr_in sin;
	struct sockaddr_in *sorgin;

	struct cmsghdr *pcmsgh;

	char *des_host, *host;
	int port, des_port;

	int udp_socket_fd;
	struct sockaddr_in local_addr = {0};

	json j;

	AllData()
	{
		int port = 1082;
		if (port < 1025 || port > 65535) //0~1024一般给系统使用，一共可以分配到65535
		{
			printf("端口号范围应为1025~65535");
			exit(-1);
		}

		// 1.创建udp通信socket
		udp_socket_fd = socket(AF_INET, SOCK_DGRAM, 0);
		if (udp_socket_fd < 0)
		{
			perror("creat socket fail\n");
			exit(-1);
		}

		//2.设置UDP的地址并绑定
		local_addr.sin_family = AF_INET;		 //使用IPv4协议
		local_addr.sin_port = htons(port);		 //网络通信都使用大端格式
		local_addr.sin_addr.s_addr = INADDR_ANY; //让系统检测本地网卡，自动绑定本地IP

		int ret = bind(udp_socket_fd, (struct sockaddr *)&local_addr, sizeof(local_addr));
		if (ret < 0)
		{
			perror("bind fail:");
			close(udp_socket_fd);
			exit(-1);
		}

		int one = 1;
		// https://stackoverflow.com/questions/5615579/how-to-get-original-destination-port-of-redirected-udp-message
		ret = setsockopt(udp_socket_fd, SOL_IP, IP_RECVORIGDSTADDR, &one, sizeof(one));
		if (ret < 0)
		{
			perror("setsockopt()");
			exit(-1);
		}
		socket_fd = (int *)(void *)&udp_socket_fd;

		iov[0].iov_base = buf;
		iov[0].iov_len = BUF_LEN;

		memset(&cmsg, 0, sizeof(cmsg));
		cmsg.msg_name = &sin;
		cmsg.msg_namelen = sizeof(sin);
		cmsg.msg_iov = iov;
		cmsg.msg_iovlen = 1;
		cmsg.msg_control = cbuf;
		cmsg.msg_controllen = 512;
	}

	~AllData()
	{
		close(*socket_fd);
	}

	int recv_msg()
	{
		memset(buf, 0, BUF_LEN);
		memset(cbuf, 0, 512);

		printf("start to receive\n");
		ret = recvmsg(*socket_fd, &cmsg, 0);
		printf("received\n");
		if (ret == -1)
		{
			printf("recv2 ret is -1\n");
			return -1;
		}
		printf("cmsg name: [%s:%d]\n", inet_ntoa(sin.sin_addr), ntohs(sin.sin_port));
		pktinfo = NULL;
		for (pcmsgh = CMSG_FIRSTHDR(&cmsg); pcmsgh != NULL;
			 pcmsgh = CMSG_NXTHDR(&cmsg, pcmsgh))
		{
			printf("found level %d, type %d\n", pcmsgh->cmsg_level, pcmsgh->cmsg_type);
			if (pcmsgh->cmsg_level == SOL_IP &&
				pcmsgh->cmsg_type == IP_RECVORIGDSTADDR)
			{
				sorgin = (struct sockaddr_in *)CMSG_DATA(pcmsgh);
			}
		}

		if (sorgin == NULL)
		{
			fprintf(stderr, "No cmsghdr received.\n");
			return 0;
		}
		else
		{
			printf("cmsg parsed: [%s:%d]\n", inet_ntoa(sorgin->sin_addr), ntohs(sorgin->sin_port));
			j["des_host"] = inet_ntoa(sorgin->sin_addr);
			j["des_port"] = ntohs(sorgin->sin_port);

			j["host"] = inet_ntoa(sin.sin_addr);
			j["port"] = ntohs(sin.sin_port);

			const char* bufTemp = reinterpret_cast<const char*>(buf);
			j["payload"] = bufTemp;
		}

		return 1;
	}
};

extern "C"
{
	AllData context;

	unsigned char* recv_main()
	{
		context.recv_msg();
		std::string s = context.j.dump();
		// printf("serilized %s, size: %d, length: %d\n", s.c_str(), s.size(), s.length());
		unsigned char *temp = (unsigned char*)malloc(s.length()+1);
		memset(temp, 0, s.length()+1);
		memcpy(temp, s.c_str(), s.length());
		return temp;
	}

	// int main(int argc, char *argv[])
	// {
	// 	recv_main();
	// }
}

// Notes:
// 无法使用python只能调用c，而非c++, 所以需要在c++中声明 extern "C"

// usage:
// # g++   udp-server-c-lib.c++ -o udp-server.so -std=c++11 -shared -W -fPIC

// Test:
// test_main => main, g++ udp-server-c-lib.c++ -o udp-server
// In terminal 1:
// udp-server

// In trminal 2:
// nc -u localhost 1082