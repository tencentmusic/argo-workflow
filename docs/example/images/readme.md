# 在线构建镜像

![](../pic/tapd_20424693_1630748567_87.png)

扩展字段高级配置(例如)：
```
{
  "volume_mount":"kubeflow-user-workspace(pvc):/mnt",
  "resource_memory":"8G",
  "resource_cpu": "4"
}
```

# 修改默认python版本

	rm /usr/bin/python
	ln -s /usr/bin/python3.6 /usr/bin/python
	rm /usr/bin/pip
	ln -s /usr/bin/pip3 /usr/bin/pip
	pip install pip --upgrade
	
# ubuntu 容器基础工具的封装

	RUN apt update

	# 安装运维工具
	RUN apt install -y --force-yes --no-install-recommends vim apt-transport-https gnupg2 ca-certificates-java rsync jq  wget git dnsutils iputils-ping net-tools curl mysql-client locales zip

	# 安装python
	RUN apt install -y python3.6-dev python3-pip libsasl2-dev libpq-dev \
		&& ln -s /usr/bin/python3 /usr/bin/python \
		&& ln -s /usr/bin/pip3 /usr/bin/pip


	# 安装中文
	RUN apt install -y --force-yes --no-install-recommends locales ttf-wqy-microhei ttf-wqy-zenhei xfonts-wqy && locale-gen zh_CN && locale-gen zh_CN.utf8
	ENV LANG zh_CN.UTF-8
	ENV LC_ALL zh_CN.UTF-8
	ENV LANGUAGE zh_CN.UTF-8

	# 便捷操作
	RUN echo "alias ll='ls -alF'" >> /root/.bashrc && \
		echo "alias la='ls -A'" >> /root/.bashrc && \
		echo "alias vi='vim'" >> /root/.bashrc && \
		/bin/bash -c "source /root/.bashrc"

	# 安装其他工具
	### 安装kubectl
	RUN curl -LO https://dl.k8s.io/release/v1.16.0/bin/linux/amd64/kubectl && chmod +x kubectl && mv kubectl /usr/local/bin/
	### 安装mysql客户端
	RUN apt install -y mysql-client-5.7
	### 安装java
	RUN apt install -y openjdk-8-jdk
	### 安装最新版的nodejs
	RUN curl -sL https://deb.nodesource.com/setup_13.x | bash -
	RUN apt-get install -y nodejs && npm config set unicode false




# 常用基础镜像

### ubuntu
    cuda10.1-cudnn7
    - ai.tencentmusic.com/tme-public/ubuntu-gpu:cuda10.1-cudnn7
		
	python3.6
		- ai.tencentmusic.com/tme-public/ubuntu-gpu:cuda10.1-cudnn7-python3.6
		
	python3.7
		- ai.tencentmusic.com/tme-public/ubuntu-gpu:cuda10.1-cudnn7-python3.7
		
	python3.8
		- ai.tencentmusic.com/tme-public/ubuntu-gpu:cuda10.1-cudnn7-python3.8
		
		
	cuda10.0-cudnn7
		- ai.tencentmusic.com/tme-public/ubuntu-gpu:cuda10.0-cudnn7
		
	python3.6
		- ai.tencentmusic.com/tme-public/ubuntu-gpu:cuda10.0-cudnn7-python3.6
		
	python3.7
		- ai.tencentmusic.com/tme-public/ubuntu-gpu:cuda10.0-cudnn7-python3.7
		
	python3.8
		- ai.tencentmusic.com/tme-public/ubuntu-gpu:cuda10.0-cudnn7-python3.8
		
		
	cuda9.1-cudnn7
		- ai.tencentmusic.com/tme-public/ubuntu-gpu:cuda9.1-cudnn7
		
	python3.6
		- ai.tencentmusic.com/tme-public/ubuntu-gpu:cuda9.1-cudnn7-python3.6
		
	python3.7
		- ai.tencentmusic.com/tme-public/ubuntu-gpu:cuda9.1-cudnn7-python3.7
		
	python3.8
		- ai.tencentmusic.com/tme-public/ubuntu-gpu:cuda9.1-cudnn7-python3.8
		
	
	cuda9.0-cudnn7
		- ai.tencentmusic.com/tme-public/ubuntu-gpu:cuda9.0-cudnn7
		
	python3.6
		- ai.tencentmusic.com/tme-public/ubuntu-gpu:cuda9.0-cudnn7-python3.6
		
	python3.7
		- ai.tencentmusic.com/tme-public/ubuntu-gpu:cuda9.0-cudnn7-python3.7
		
	python3.8
		- ai.tencentmusic.com/tme-public/ubuntu-gpu:cuda9.0-cudnn7-python3.8
		
		
	cuda10.1-cuda10.0-cuda9.0-cudnn7.6
		- ai.tencentmusic.com/tme-public/gpu:ubuntu18.04-python3.6-cuda10.1-cuda10.0-cuda9.0-cudnn7.6-base
