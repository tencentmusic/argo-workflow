#!/usr/bin/env bash 

sudo docker rm -f $(sudo docker ps -qa)
sudo rm -rf /etc/ceph \
       /etc/cni \
       /etc/kubernetes \
       /opt/cni \
       /opt/rke \
       /run/secrets/kubernetes.io \
       /run/calico \
       /run/flannel \
       /var/lib/calico \
       /var/lib/etcd \
       /var/lib/cni \
       /var/lib/kubelet \
       /var/lib/rancher/rke/log \
       /var/log/containers \
       /var/log/pods \
       /var/run/calico \
       /var/etcd

for mount in $(mount | grep tmpfs | grep '/var/lib/kubelet' | awk '{ print $3 }') /var/lib/kubelet /var/lib/rancher; do umount $mount; done
for m in $(sudo tac /proc/mounts | sudo awk '{print $2}'|sudo grep /var/lib/kubelet);do
 sudo umount $m||true
done
sudo rm -rf /var/lib/kubelet/
for m in $(sudo tac /proc/mounts | sudo awk '{print $2}'|sudo grep /var/lib/rancher);do
 sudo umount $m||true
done
sudo rm -rf /var/lib/rancher/
sudo rm -rf /run/kubernetes/
sudo docker volume rm $(sudo docker volume ls -q)
sudo docker ps -a
sudo docker volume ls

rm -f /var/lib/containerd/io.containerd.metadata.v1.bolt/meta.db

IPTABLES="/sbin/iptables"
cat /proc/net/ip_tables_names | while read table; do
  $IPTABLES -t $table -L -n | while read c chain rest; do
      if test "X$c" = "XChain" ; then
        $IPTABLES -t $table -F $chain
      fi
  done
  $IPTABLES -t $table -X
done

sudo systemctl restart containerd
sudo systemctl restart docker