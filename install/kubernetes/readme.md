# 机器/k8s环境/分布式存储环境准备  
机器环境准备：准备docker，准备rancher，部署k8s。如果已经有可以忽略，没有可以参考[rancher/readme.md](https://github.com/tencentmusic/cube-studio/tree/master/install/kubernetes/rancher) 


# 分布式存储

如果不使用分布式存储可忽略。

需要每台机器都有对应的目录/data/k8s为分布式存储目录，如果使用云存储，自定义修改pv的yaml文件
```bash  
mkdir -p /data/k8s/kubeflow/pipeline/workspace  
```  
平台pvc会使用这些分布式存储目录下的subpath，所以如果你是rancher部署k8s集群，需要在kubelet容器中挂载主机的/data/k8s/目录到kubelet容器的/data/k8s/目录。
rancher修改kubelet容器挂载目录(选中集群-升级-编辑yaml)
```
    kubelet:
      extra_binds:
        - '/data/k8s:/data/k8s'
```
  
# 创建仓库秘钥
```bash  
修改里面的docker hub拉取账号密码  
sh create_ns_secret.sh  
```  
  
# 通过label进行机器管理  
开发训练服务机器管理：
- 对于cpu的任务会选择cpu=true的机器  
- 对于gpu的任务会选择gpu=true的机器  

- pipeline任务会选择train=true的机器  
- notebook会选择notebook=true的机器  
- 不同项目的任务会选择对应org=xx的机器。默认为org=public 
- 可以通过gpu-type=xx表示gpu的型号

  
# 部署平台
```bash  
kubectl apply -k cube/overlays
```  

组件说明  
 - cube/base/deploy.yaml为myapp的前后端代码  
 - cube/base/deploy-schedule.yaml 为任务产生器  
 - cube/base/deploy-worker.yaml 为任务执行器  
 - cube/base/deploy-watch.yaml 任务监听器  

配置文件说明  
 - cube/overlays/config/entrypoint.sh 镜像启动脚本  
 - cube/overlays/config/config.py  配置文件，需要将其中的配置项替换为自己的  
 

## 部署pv-pvc.yaml  

```bash  
kubectl create -f pv-pvc-pipeline.yaml  
```  

# 版本升级
数据库升级，数据库记录要批量添加默认值到原有记录上，不然容易添加失败


