
for namespace in 'infra'  'pipeline' 'jupyter'
do
    kubectl create ns $namespace
    kubectl delete secret docker-registry hubsecret -n $namespace
    kubectl create secret docker-registry hubsecret --docker-username=xxxx --docker-password=xxxx -n $namespace
done



