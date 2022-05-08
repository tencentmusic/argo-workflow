# docker build -t ai.tencentmusic.com/tme-public/kubeflow-dashboard:argo-2022.05.01 -f install/docker/Dockerfile .

FROM ai.tencentmusic.com/tme-public/kubeflow-dashboard:base

RUN apt-get update && apt-get install -y mysql-client zip

RUN curl -sL https://deb.nodesource.com/setup_14.x | bash
RUN apt-get -y install nodejs && npm install yarn -g

RUN rm /usr/bin/python && ln -s /usr/bin/python3 /usr/bin/python && rm /usr/bin/pip && ln -s /usr/bin/pip3 /usr/bin/pip
RUN pip install pip --upgrade && pip install docstring_parser
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && chmod +x kubectl && mv kubectl /usr/bin/

RUN pip install kubernetes==18.20.0 click==6.7 pyyaml
COPY install/docker/docker-add-file/rest.py /usr/local/lib/python3.6/dist-packages/kubernetes/client/rest.py
COPY install/docker/docker-add-file/__init__.py /usr/local/lib/python3.6/dist-packages/marshmallow_enum/__init__.py

COPY myapp /home/myapp/myapp
ENV PATH=/home/myapp/myapp/bin:$PATH
ENV PYTHONPATH=/home/myapp:$PYTHONPATH


USER root
COPY install/docker/entrypoint.sh /entrypoint.sh

# ENTRYPOINT ["/entrypoint.sh"]
# HEALTHCHECK CMD ["curl", "-f", "http://localhost:80/health"]




