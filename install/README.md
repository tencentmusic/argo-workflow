
# 平台部署流程

基础环境依赖
 - docker >= 19.03  
 - kubernetes = 1.18  
 - kubectl >=1.18  
 - 分布式存储，挂载到每台机器的 /data/k8s/，不需要可忽略
 - 单机 磁盘>=500G   单机磁盘容量要求不大，仅做镜像容器的的存储  
 - 控制端机器 cpu>=16 mem>=32G   
 - 任务端机器，根据需要自行配置  

请参考install/kubenetes/README.md 部署依赖组件。

平台完成部署之后如下:

<img width="100%" alt="image" src="https://user-images.githubusercontent.com/20157705/167874734-5b1629e0-c3bb-41b0-871d-ffa43d914066.png">



# 本地开发

管理平台web端可连接多个k8s集群用来在k8s集群上调度发起任务实例。同时管理多个k8s集群时，或本地调试时，可以将k8s集群的config文件存储在kubeconfig目录中，按照$ENVIRONMENT-kubeconfig 的规范命名

./docker 目录包含本地开发方案，涉及镜像构建，docker-compose启动，前端构建，后端编码等过程

参考install/docker/README.md


