from flask import render_template,redirect
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder import ModelView, ModelRestApi
from flask_appbuilder import ModelView,AppBuilder,expose,BaseView,has_access
from importlib import reload
from flask_babel import gettext as __
from flask_babel import lazy_gettext as _
import uuid
import re
from sqlalchemy.exc import InvalidRequestError
# 将model添加成视图，并控制在前端的显示
from myapp.models.model_job import Job_Template,Task,Pipeline,Workflow,RunHistory
from myapp.models.model_team import Project,Project_User
from myapp.views.view_team import Project_Join_Filter
from flask_appbuilder.actions import action
from flask import current_app, flash, jsonify, make_response, redirect, request, url_for
from flask_appbuilder.models.sqla.filters import FilterEqualFunction, FilterStartsWith,FilterEqual,FilterNotEqual
from wtforms.validators import EqualTo,Length
from flask_babel import lazy_gettext,gettext
import yaml
from flask_appbuilder.security.decorators import has_access
from flask_appbuilder.forms import GeneralModelConverter
from myapp.utils import core
from myapp import app, appbuilder,db,event_logger
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from jinja2 import Template
from jinja2 import contextfilter
from jinja2 import Environment, BaseLoader, DebugUndefined, StrictUndefined
import os,sys
from wtforms.validators import DataRequired, Length, NumberRange, Optional,Regexp
from myapp.forms import JsonValidator
from myapp.views.view_task import Task_ModelView
from sqlalchemy import and_, or_, select
from myapp.exceptions import MyappException
from wtforms import BooleanField, IntegerField,StringField, SelectField,FloatField,DateField,DateTimeField,SelectMultipleField,FormField,FieldList
from myapp.project import push_message,push_admin
from flask_appbuilder.fieldwidgets import BS3TextFieldWidget,BS3PasswordFieldWidget,DatePickerWidget,DateTimePickerWidget,Select2ManyWidget,Select2Widget,BS3TextAreaFieldWidget
from myapp.forms import MyBS3TextAreaFieldWidget,MySelect2Widget,MyCodeArea,MyLineSeparatedListField,MyJSONField,MyBS3TextFieldWidget,MySelectMultipleField
from myapp.utils.py import py_k8s
from flask_wtf.file import FileField
import shlex
import re,copy
from kubernetes.client.models import (
    V1Container, V1EnvVar, V1EnvFromSource, V1SecurityContext, V1Probe,
    V1ResourceRequirements, V1VolumeDevice, V1VolumeMount, V1ContainerPort,
    V1Lifecycle, V1Volume,V1SecurityContext
)
from .baseApi import (
    MyappModelRestApi
)

from flask import (
    current_app,
    abort,
    flash,
    g,
    Markup,
    make_response,
    redirect,
    render_template,
    request,
    send_from_directory,
    Response,
    url_for,
)
from myapp import security_manager
from myapp.views.view_team import filter_join_org_project

from werkzeug.datastructures import FileStorage
from kubernetes import client as k8s_client
from .base import (
    api,
    BaseMyappView,
    check_ownership,
    data_payload_response,
    DeleteMixin,
    generate_download_headers,
    get_error_msg,
    get_user_roles,
    handle_api_exception,
    json_error_response,
    json_success,
    MyappFilter,
    MyappModelView,
    json_response
)

from flask_appbuilder import CompactCRUDMixin, expose
import pysnooper,datetime,time,json
conf = app.config
logging = app.logger


class Pipeline_Filter(MyappFilter):
    # @pysnooper.snoop()
    def apply(self, query, func):
        user_roles = [role.name.lower() for role in list(self.get_user_roles())]
        if "admin" in user_roles:
            return query

        join_projects_id = security_manager.get_join_projects_id(db.session)
        # public_project_id =
        # logging.info(join_projects_id)
        return query.filter(
            or_(
                self.model.project_id.in_(join_projects_id),
                # self.model.project.name.in_(['public'])
            )
        )




from sqlalchemy.exc import InvalidRequestError,OperationalError

# 将定义pipeline的流程
# @pysnooper.snoop(watch_explode=())
def dag_to_pipeline(pipeline,dbsession,**kwargs):
    if not pipeline.id:
        return

    pipeline.dag_json = pipeline.fix_dag_json(dbsession)
    dbsession.commit()
    dag = json.loads(pipeline.dag_json)

    # 如果dag为空，就直接退出
    if not dag:
        return None

    all_tasks = {}
    for task_name in dag:
        # 使用临时连接，避免连接中断的问题
        # try:
            # db.session().ping()
            task = dbsession.query(Task).filter_by(name=task_name, pipeline_id=pipeline.id).first()
            if not task:
                raise MyappException('task %s not exist ' % task_name)
            all_tasks[task_name]=task

    # 渲染字符串模板变量
    def template_str(src_str):
        rtemplate = Environment(loader=BaseLoader, undefined=DebugUndefined).from_string(src_str)
        des_str = rtemplate.render(creator=pipeline.created_by.username,
                                   datetime=datetime,
                                   runner=g.user.username if g and g.user and g.user.username else pipeline.created_by.username,
                                   uuid = uuid,
                                   pipeline_id=pipeline.id,
                                   pipeline_name=pipeline.name,
                                   cluster_name=pipeline.project.cluster.get('NAME','dev'),
                                   **kwargs
                                   )
        return des_str

    pipeline_global_env = template_str(pipeline.global_env.strip()) if pipeline.global_env else ''   # 优先渲染，不然里面如果有date就可能存在不一致的问题
    pipeline_global_env = [ env.strip() for env in pipeline_global_env.split('\n') if '=' in env.strip()]
    global_envs = json.loads(template_str(json.dumps(conf.get('GLOBAL_ENV', {}),indent=4,ensure_ascii=False)))
    for env in pipeline_global_env:
        key,value = env[:env.index('=')],env[env.index('=')+1:]
        global_envs[key]=value


    # @pysnooper.snoop()
    def get_ops(task_name):
        task = all_tasks[task_name]

        task_spec = {
            "name": task_name,
            "retryStrategy": {
                "limit": str(task.retry),
                "retryPolicy": "Always"
            },
            "activeDeadlineSeconds": task.timeout if task.timeout else 5184000,
            "metadata": {
                "labels": {
                }
            },
            "volumes": [],
            "nodeSelector": {},
            "affinity": {},
            "container": {
                "resources":{
                    "requests":{},
                    "limits":{}
                },
                "env":[],
                "volumeMounts":[],
                "imagePullPolicy":"Always",
            },
        }



        ops_args = []
        task_args = json.loads(task.args)
        for task_attr_name in task_args:
            # 添加参数名
            if type(task_args[task_attr_name])==bool:
                if task_args[task_attr_name]:
                    ops_args.append('%s' % str(task_attr_name))
            # 添加参数值
            elif type(task_args[task_attr_name])==dict or type(task_args[task_attr_name])==list:
                ops_args.append('%s' % str(task_attr_name))
                ops_args.append('%s' % json.dumps(task_args[task_attr_name],ensure_ascii=False))
            elif not task_args[task_attr_name]:     # 如果参数值为空，则都不添加
                pass
            else:
                ops_args.append('%s' % str(task_attr_name))
                ops_args.append('%s'%str(task_args[task_attr_name]))   # 这里应该对不同类型的参数名称做不同的参数处理，比如bool型，只有参数，没有值


        # 创建ops的pod的创建参数
        container_kwargs={}

        # 设置环境变量

        if task.job_template.env:
            envs = re.split('\r|\n',task.job_template.env)
            for env in envs:
                env_key,env_value = env.split('=')[0],env.split('=')[1]
                task_spec['container']['env'].append(
                    {
                        "name":env_key,
                        "value":env_value
                    }
                )

        # 设置全局环境变量
        for global_env_key in global_envs:
            task_spec['container']['env'].append(
                {
                    "name": global_env_key,
                    "value": global_envs[global_env_key]
                }
            )
        def set_env(key,value):
            task_spec['container']['env'].append(
                {
                    "name": key,
                    "value": value
                }
            )

        # 设置task的默认环境变量
        set_env("KFJ_TASK_ID",str(task.id))
        set_env("KFJ_TASK_NAME", str(task.name))
        set_env("KFJ_TASK_NODE_SELECTOR", str(task.get_node_selector()))
        set_env("KFJ_TASK_VOLUME_MOUNT", str(task.volume_mount))
        set_env("KFJ_TASK_IMAGES", str(task.job_template.images))
        set_env("KFJ_TASK_RESOURCE_CPU", str(task.resource_cpu))
        set_env("KFJ_TASK_RESOURCE_MEMORY", str(task.resource_memory))
        set_env("KFJ_TASK_RESOURCE_GPU", str(task.resource_gpu.replace("+",'')))


        # 创建工作目录
        if task.job_template.workdir and task.job_template.workdir.strip():
            task_spec['container']['workingDir'] = task.job_template.workdir.strip()
        if task.working_dir and task.working_dir.strip():
            task_spec['container']['workingDir'] = task.working_dir.strip()

        task_command = ''

        if task.command:
            commands = re.split('\r|\n',task.command)
            commands = [command.strip() for command in commands if command.strip()]
            if task_command:
                task_command += " && " + " && ".join(commands)
            else:
                task_command += " && ".join(commands)

        job_template_entrypoint = task.job_template.entrypoint.strip() if task.job_template.entrypoint else ''

        if task.job_template.name==conf.get('CUSTOMIZE_JOB'):
            task_spec['container']['command']=['bash','-c',json.loads(task.args).get('command')]
            task_spec['container']['image'] = json.loads(task.args).get('images')

        else:
            command = None
            if job_template_entrypoint:
                command = job_template_entrypoint

            if task_command:
                command = task_command

            command = command.split(' ') if command else []
            command = [com for com in command if com]
            task_spec['container']['command'] = command if command else None
            task_spec['container']['args'] = ops_args
            task_spec['container']['image'] = task.job_template.images



        # 添加用户自定义挂载
        task.volume_mount=task.volume_mount.strip() if task.volume_mount else ''
        if task.volume_mount:
            volume_mounts = re.split(',|;',task.volume_mount)
            for volume_mount in volume_mounts:
                volume,mount = volume_mount.split(":")[0].strip(),volume_mount.split(":")[1].strip()
                if "(pvc)" in volume:
                    pvc_name = volume.replace('(pvc)','').replace(' ','')
                    temps = re.split('_|\.|/', pvc_name)
                    temps = [temp for temp in temps if temp]
                    volumn_name = ('-'.join(temps))[:60].lower().strip('-')

                    task_spec['volumes'].append({
                        "name":volumn_name,
                        "persistentVolumeClaim":{
                            "claimName":pvc_name
                        }
                    })

                    task_spec['container']["volumeMounts"].append({
                        "mountPath":os.path.join(mount,task.pipeline.created_by.username),
                        "name":volumn_name,
                        "sub_path":task.pipeline.created_by.username
                    })

                if "(hostpath)" in volume:
                    hostpath_name = volume.replace('(hostpath)', '').replace(' ', '')
                    temps = re.split('_|\.|/', hostpath_name)
                    temps = [temp for temp in temps if temp]
                    volumn_name = ('-'.join(temps))[:60].lower().strip('-')

                    task_spec['volumes'].append({
                        "name":volumn_name,
                        "hostPath":{
                            "path":hostpath_name
                        }
                    })

                    task_spec['container']["volumeMounts"].append({
                        "mountPath":mount,
                        "name":volumn_name,
                    })

                if "(configmap)" in volume:
                    configmap_name = volume.replace('(configmap)', '').replace(' ', '')
                    temps = re.split('_|\.|/', configmap_name)
                    temps = [temp for temp in temps if temp]
                    volumn_name = ('-'.join(temps))[:60].lower().strip('-')

                    task_spec['volumes'].append({
                        "name":volumn_name,
                        "configMap":{
                            "name":configmap_name
                        }
                    })

                    task_spec['container']["volumeMounts"].append({
                        "mountPath":mount,
                        "name":volumn_name,
                    })

                if "(memory)" in volume:
                    memory_size = volume.replace('(memory)', '').replace(' ', '').lower().replace('g','')
                    volumn_name = ('memory-%s'%memory_size)[:60].lower().strip('-')

                    task_spec['volumes'].append({
                        "name":volumn_name,
                        "emptyDir":{
                            "medium":"Memory",
                            "sizeLimit":'%sGi'%memory_size
                        }
                    })

                    task_spec['container']["volumeMounts"].append({
                        "mountPath":mount,
                        "name":volumn_name,
                    })

        # 添加node selector
        for selector in re.split(',|;|\n|\t', task.get_node_selector()):
            selector=selector.replace(' ','')
            if '=' in selector:
                task_spec['nodeSelector'][selector.strip().split('=')[0].strip()]=selector.strip().split('=')[1].strip()


        # 添加pod label
        task_spec['metadata']['labels']["pipeline-id"]=str(pipeline.id)
        task_spec['metadata']['labels']["pipeline-name"]= str(pipeline.name)
        task_spec['metadata']['labels']["task-name"]=str(task.name)
        task_spec['metadata']['labels']["task-id"]=str(task.id)
        task_spec['metadata']['labels']["task-id"]=str(task.id)
        task_spec['metadata']['labels']['upload-rtx']=g.user.username if g and g.user and g.user.username else pipeline.created_by.username
        task_spec['metadata']['labels']['run-rtx']=g.user.username if g and g.user and g.user.username else pipeline.created_by.username
        task_spec['metadata']['labels']['pipeline-rtx']=pipeline.created_by.username


        task_spec['affinity']={
            "podAntiAffinity":{
                "preferredDuringSchedulingIgnoredDuringExecution":[{
                    "weight":80,
                    "podAffinityTerm":{
                        "topologyKey":"kubernetes.io/hostname",
                        "labelSelector": {
                            "matchLabels":{
                                "pipeline-id": str(pipeline.id)
                            }
                        }
                    }
                }]
            }
        }


        resource_cpu = task.job_template.get_env('TASK_RESOURCE_CPU') if task.job_template.get_env('TASK_RESOURCE_CPU') else task.resource_cpu
        resource_gpu = task.job_template.get_env('TASK_RESOURCE_GPU') if task.job_template.get_env('TASK_RESOURCE_GPU') else task.resource_gpu
        resource_memory = task.job_template.get_env('TASK_RESOURCE_MEMORY') if task.job_template.get_env('TASK_RESOURCE_MEMORY') else task.resource_memory

        # 设置资源限制
        if resource_memory:
            if not '~' in resource_memory:
                task_spec['container']['resources']['requests']['memory']=resource_memory
                task_spec['container']['resources']['limits']['memory'] = resource_memory

            else:
                task_spec['container']['resources']['requests']['memory']=resource_memory.split("~")[0]
                task_spec['container']['resources']['limits']['memory'] = resource_memory.split("~")[1]

        if resource_cpu:
            if not '~' in resource_cpu:
                task_spec['container']['resources']['requests']['cpu'] = resource_cpu
                task_spec['container']['resources']['limits']['cpu'] = resource_cpu
            else:
                task_spec['container']['resources']['requests']['cpu'] = resource_cpu.split("~")[0]
                task_spec['container']['resources']['limits']['cpu'] = resource_cpu.split("~")[1]

        if resource_gpu:
            if resource_gpu and core.get_gpu(resource_gpu)[0]>0:
                task_spec['container']['resources']['limits']['nvidia.com/gpu'] = core.get_gpu(resource_gpu)[0]

        return task_spec


    workflow_json = {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Workflow",
        "metadata": {
            "namespace": conf.get('PIPELINE_NAMESPACE','pipeline'),
            "name": pipeline.name,
            "labels":{
                "upload-rtx":g.user.username if g and g.user and g.user.username else pipeline.created_by.username,
                "run-rtx":g.user.username if g and g.user and g.user.username else pipeline.created_by.username,
                "pipeline-rtx": pipeline.created_by.username,
                "save-time": datetime.datetime.now().strftime('%Y-%m-%dT%H-%M-%S'),
                "pipeline-id": str(pipeline.id)
            },
            "annotations":{
                "pipelines.kubeflow.org/pipeline_spec":json.dumps({
                    "description": pipeline.describe,
                    "name": pipeline.name
                })
            }
        },
        "spec": {
            "serviceAccountName":"default",
            "parallelism": pipeline.parallelism,
            "imagePullSecrets": [{"name":pullsecret} for pullsecret in conf.get('HUBSECRET',[])],
            "entrypoint":pipeline.name,
            "templates":[
                {
                    "name":pipeline.name,
                    "dag":{
                        "tasks":[
                            {
                                "name":task_name,
                                "template":task_name,
                                "dependencies": dag[task_name].get('upstream',[])
                            } for task_name in dag
                        ]
                    }
                }
            ]

        }
    }

    for task_name in all_tasks:
        task_spec = get_ops(task_name)
        # print(json.dumps(task_spec,indent=4,ensure_ascii=False))
        workflow_json['spec']['templates'].append(task_spec)


    return json.dumps(workflow_json,indent=4,ensure_ascii=False)


# @pysnooper.snoop(watch_explode=())
def run_pipeline(pipeline):
    # 直接yaml文件创建crd
    try:
        k8s_client = py_k8s.K8s(pipeline.project.cluster.get('KUBECONFIG',''))
        crd_info =conf.get('CRD_INFO',{}).get("workflow",{})
        namespace =conf.get('PIPELINE_NAMESPACE','pipeline')
        workflow_json = json.loads(pipeline.pipeline_file)
        run_id = (pipeline.name+"-"+uuid.uuid4().hex[:4])[0:60].strip('-')
        workflow_json['metadata']['name']=run_id
        workflow_json['metadata']['labels']['run-id'] = run_id
        # 为每个task新增run-id字段，这样每个pod都能找到run-id
        for task in workflow_json['spec']['templates']:
            if task.get('container',''):  # 只针对容器task
                task['container']['env'].append({
                    "name": "KFJ_RUN_ID",
                    "value": run_id
                })

        k8s_client.create_crd(
            group=crd_info['group'],
            version=crd_info['version'],
            plural=crd_info['plural'],
            namespace=namespace,
            body=workflow_json
        )
        return run_id
    except Exception as e:
        print(e)
        raise e


class Pipeline_ModelView_Base():
    label_title='任务流'
    datamodel = SQLAInterface(Pipeline)
    check_redirect_list_url = '/pipeline_modelview/list/?_flt_2_name='

    base_permissions = ['can_show','can_edit','can_list','can_delete','can_add']
    base_order = ("changed_on", "desc")
    # order_columns = ['id','changed_on']
    order_columns = ['id']

    list_columns = ['id','project','pipeline_url','creator','modified']
    add_columns = ['project','name','describe','schedule_type','cron_time','depends_on_past','max_active_runs','expired_limit','parallelism','global_env','alert_status','alert_user']
    show_columns = ['project','name','describe','schedule_type','cron_time','depends_on_past','max_active_runs','expired_limit','parallelism','global_env','dag_json_html','pipeline_file_html','run_id','created_by','changed_by','created_on','changed_on','expand_html','parameter_html']
    edit_columns = add_columns


    base_filters = [["id", Pipeline_Filter, lambda: []]]  # 设置权限过滤器
    conv = GeneralModelConverter(datamodel)


    add_form_extra_fields = {

        "name": StringField(
            _(datamodel.obj.lab('name')),
            description="英文名(字母、数字、- 组成)，最长50个字符",
            widget=BS3TextFieldWidget(),
            validators=[Regexp("^[a-z][a-z0-9\-]*[a-z0-9]$"),Length(1,54),DataRequired()]
        ),
        "project":QuerySelectField(
            _(datamodel.obj.lab('project')),
            query_factory=filter_join_org_project,
            allow_blank=True,
            widget=Select2Widget()
        ),
        "dag_json": StringField(
            _(datamodel.obj.lab('dag_json')),
            widget=MyBS3TextAreaFieldWidget(rows=10),  # 传给widget函数的是外层的field对象，以及widget函数的参数
        ),
        "namespace": StringField(
            _(datamodel.obj.lab('namespace')),
            description="部署task所在的命名空间(目前无需填写)",
            default='pipeline',
            widget=BS3TextFieldWidget()
        ),
        "node_selector": StringField(
            _(datamodel.obj.lab('node_selector')),
            description="部署task所在的机器(目前无需填写)",
            widget=BS3TextFieldWidget(),
            default=datamodel.obj.node_selector.default.arg
        ),
        "image_pull_policy": SelectField(
            _(datamodel.obj.lab('image_pull_policy')),
            description="镜像拉取策略(always为总是拉取远程镜像，IfNotPresent为若本地存在则使用本地镜像)",
            widget=Select2Widget(),
            choices=[['Always','Always'],['IfNotPresent','IfNotPresent']]
        ),

        "depends_on_past": BooleanField(
            _(datamodel.obj.lab('depends_on_past')),
            description="任务运行是否依赖上一次的示例状态",
            default=True
        ),
        "max_active_runs": IntegerField(
            _(datamodel.obj.lab('max_active_runs')),
            description="当前pipeline可同时运行的任务流实例数目",
            widget=BS3TextFieldWidget(),
            default=1,
            validators=[DataRequired()]
        ),
        "expired_limit": IntegerField(
            _(datamodel.obj.lab('expired_limit')),
            description="定时调度最新实例限制数目，0表示不限制",
            widget=BS3TextFieldWidget(),
            default=1,
            validators=[DataRequired()]
        ),
        "parallelism": IntegerField(
            _(datamodel.obj.lab('parallelism')),
            description="一个任务流实例中可同时运行的task数目",
            widget=BS3TextFieldWidget(),
            default=3,
            validators=[DataRequired()]
        ),
        "global_env": StringField(
            _(datamodel.obj.lab('global_env')),
            description="公共环境变量会以环境变量的形式传递给每个task，可以配置多个公共环境变量，每行一个，支持datetime/creator/runner/uuid/pipeline_id等变量 例如：USERNAME={{creator}}",
            widget=BS3TextAreaFieldWidget()
        ),
        "schedule_type":SelectField(
            _(datamodel.obj.lab('schedule_type')),
            description="调度类型，once仅运行一次，crontab周期运行，crontab配置保存一个小时候后才生效",
            widget=Select2Widget(),
            choices=[['once','once'],['crontab','crontab']]
        ),
        "cron_time": StringField(
            _(datamodel.obj.lab('cron_time')),
            description="周期任务的时间设定 * * * * * 表示为 minute hour day month week",
            widget=BS3TextFieldWidget()
        ),
        "alert_status":MySelectMultipleField(
            label=_(datamodel.obj.lab('alert_status')),
            widget=Select2ManyWidget(),
            choices=[[x, x] for x in
                     ['Created', 'Pending', 'Running', 'Succeeded', 'Failed', 'Unknown', 'Waiting', 'Terminated']],
            description="选择通知状态"
        ),
        "alert_user": StringField(
            label=_(datamodel.obj.lab('alert_user')),
            widget=BS3TextFieldWidget(),
            description="选择通知用户，每个用户使用逗号分隔"
        )
    }

    edit_form_extra_fields = add_form_extra_fields

    related_views = [Task_ModelView, ]


    # 检测是否具有编辑权限，只有creator和admin可以编辑
    def check_edit_permission(self, item):
        user_roles = [role.name.lower() for role in list(get_user_roles())]
        if "admin" in user_roles:
            return True
        if g.user and g.user.username and hasattr(item,'created_by'):
            if g.user.username==item.created_by.username:
                return True
        flash('just creator can edit/delete ', 'warning')
        return False


    # 验证args参数
    # @pysnooper.snoop(watch_explode=('item'))
    def pipeline_args_check(self, item):
        core.validate_str(item.name,'name')
        if not item.dag_json:
            item.dag_json='{}'
        core.validate_json(item.dag_json)
        # 校验task的关系，没有闭环，并且顺序要对。没有配置的，自动没有上游，独立
        # @pysnooper.snoop()
        def order_by_upstream(dag_json):
            order_dag={}
            tasks_name = list(dag_json.keys())  # 如果没有配全的话，可能只有局部的task
            i=0
            while tasks_name:
                i+=1
                if i>100:  # 不会有100个依赖关系
                    break
                for task_name in tasks_name:
                    # 没有上游的情况
                    if not dag_json[task_name]:
                        order_dag[task_name]={}
                        tasks_name.remove(task_name)
                        continue
                    # 没有上游的情况
                    elif 'upstream' not in dag_json[task_name] or not dag_json[task_name]['upstream']:
                        order_dag[task_name] = {}
                        tasks_name.remove(task_name)
                        continue
                    # 如果有上游依赖的话，先看上游任务是否已经加到里面了。
                    upstream_all_ready=True
                    for upstream_task_name in dag_json[task_name]['upstream']:
                        if upstream_task_name not in order_dag:
                            upstream_all_ready=False
                    if upstream_all_ready:
                        order_dag[task_name]=dag_json[task_name]
                        tasks_name.remove(task_name)
            if list(dag_json.keys()).sort()!=list(order_dag.keys()).sort():
                flash('dag pipeline 存在循环或未知上游',category='warning')
                raise MyappException('dag pipeline 存在循环或未知上游')
            return order_dag

        # 配置上缺少的默认上游
        dag_json = json.loads(item.dag_json)
        tasks = item.get_tasks(db.session)
        if tasks and dag_json:
            for task in tasks:
                if task.name not in dag_json:
                    dag_json[task.name]={
                        "upstream": []
                    }
        item.dag_json = json.dumps(order_by_upstream(copy.deepcopy(dag_json)),ensure_ascii=False,indent=4)
        # 生成workflow，如果有id，
        if item.id and item.get_tasks():
            item.pipeline_file = dag_to_pipeline(item,db.session)
        else:
            item.pipeline_file = None


        # raise Exception('args is not valid')

    # 合并上下游关系
    # @pysnooper.snoop(watch_explode=('pipeline'))
    def merge_upstream(self,pipeline):
        logging.info(pipeline)

        dag_json={}
        # 根据参数生成args字典。一层嵌套的形式
        for arg in pipeline.__dict__:
            if len(arg)>5 and arg[:5] == 'task.':
                task_upstream = getattr(pipeline,arg)
                dag_json[arg[5:]]={
                    "upstream":task_upstream if task_upstream else []
                }
        if dag_json:
            pipeline.dag_json = json.dumps(dag_json)

    # @pysnooper.snoop()
    def pre_add(self, item):
        item.name = item.name.replace('_', '-')[0:54].lower().strip('-')
        # item.alert_status = ','.join(item.alert_status)
        self.pipeline_args_check(item)
        item.create_datetime=datetime.datetime.now()
        item.change_datetime = datetime.datetime.now()
        item.parameter = json.dumps({"cronjob_start_time":datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, indent=4, ensure_ascii=False)



    # @pysnooper.snoop()
    def pre_update(self, item):

        if item.expand:
            core.validate_json(item.expand)
            item.expand = json.dumps(json.loads(item.expand),indent=4,ensure_ascii=False)
        else:
            item.expand='{}'
        item.name = item.name.replace('_', '-')[0:54].lower()
        # item.alert_status = ','.join(item.alert_status)
        self.merge_upstream(item)
        self.pipeline_args_check(item)
        item.change_datetime = datetime.datetime.now()
        if item.parameter:
            item.parameter = json.dumps(json.loads(item.parameter),indent=4,ensure_ascii=False)
        else:
            item.parameter = '{}'

        if (item.schedule_type=='crontab' and self.src_item_json.get("schedule_type")=='once') or (item.cron_time!=self.src_item_json.get("cron_time",'')):
            parameter = json.loads(item.parameter if item.parameter else '{}')
            parameter.update({"cronjob_start_time":datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
            item.parameter = json.dumps(parameter,indent=4,ensure_ascii=False)

        # 限制提醒
        if item.schedule_type=='crontab':
            if not item.project.node_selector:
                print('无法保障公共集群的稳定性，定时任务请选择专门的日更集群项目组','warning')
            else:
                org = item.project.node_selector.replace('org=','')
                if not org or org=='public':
                    print('无法保障公共集群的稳定性，定时任务请选择专门的日更集群项目组','warning')


    def pre_update_get(self,item):
        item.dag_json = item.fix_dag_json()
        # item.expand = json.dumps(item.fix_expand(),indent=4,ensure_ascii=False)
        db.session.commit()

    # 删除前先把下面的task删除了
    # @pysnooper.snoop()
    def pre_delete(self, pipeline):
        tasks = pipeline.get_tasks()
        for task in tasks:
            db.session.delete(task)
        db.session.commit()
        if "(废弃)" not in pipeline.describe:
            pipeline.describe+="(废弃)"
        pipeline.schedule_type='once'
        pipeline.expand=""
        pipeline.dag_json="{}"
        db.session.commit()


    @expose("/my/list/")
    def my(self):
        try:
            user_id=g.user.id
            if user_id:
                pipelines = db.session.query(Pipeline).filter_by(created_by_fk=user_id).all()
                back=[]
                for pipeline in pipelines:
                    back.append(pipeline.to_json())
                return json_response(message='success',status=0,result=back)
        except Exception as e:
            print(e)
            return json_response(message=str(e),status=-1,result={})


    @expose("/demo/list/")
    def demo(self):
        try:
            pipelines = db.session.query(Pipeline).filter(Pipeline.parameter.contains('"demo": "true"')).all()
            back=[]
            for pipeline in pipelines:
                back.append(pipeline.to_json())
            return json_response(message='success',status=0,result=back)
        except Exception as e:
            print(e)
            return json_response(message=str(e),status=-1,result={})


    @event_logger.log_this
    @expose("/list/")
    @has_access
    def list(self):
        args = request.args.to_dict()
        if '_flt_0_created_by' in args and args['_flt_0_created_by']=='':
            print(request.url)
            print(request.path)
            flash('去除过滤条件->查看所有pipeline','success')
            return redirect(request.url.replace('_flt_0_created_by=','_flt_0_created_by=%s'%g.user.id))

        widgets = self._list()
        res = self.render_template(
            self.list_template, title=self.list_title, widgets=widgets
        )
        return res


    # @event_logger.log_this
    @action(
        "download", __("Download"), __("Download Yaml"), "fa-download", multiple=False, single=True
    )
    def download(self, item):
        file_name = item.name+'-download.yaml'
        file_dir = os.path.join(conf.get('DOWNLOAD_FOLDER'),'pipeline')
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        file = open(os.path.join(file_dir,file_name), mode='wb')
        pipeline_file = item.pipeline_file
        try:
            import yaml
            # pipeline_yaml = yaml.load(pipeline_file)
            pipeline_yaml = yaml.safe_load(pipeline_file)
            pipeline_yaml['metadata']['name']=item.name+'-'+uuid.uuid4().hex[:4]
            pipeline_yaml['metadata']['namespace'] = conf.get('PIPELINE_NAMESPACE','pipeline')
            pipeline_file = yaml.safe_dump(pipeline_yaml)
        except Exception as e:
            print(e)

        file.write(bytes(pipeline_file, encoding='utf-8'))
        file.close()
        response = make_response(send_from_directory(file_dir, file_name, as_attachment=True, conditional=True))

        response.headers[
            "Content-Disposition"
        ] = f"attachment; filename={file_name}"
        logging.info("Ready to return response")
        return response




    # 删除手动发起的workflow，不删除定时任务发起的workflow
    def delete_bind_crd(self,crds):

        for crd in crds:
            try:
                run_id = json.loads(crd['labels']).get("run-id",'')
                if run_id:
                    # 定时任务发起的不能清理
                    run_history = db.session.query(RunHistory).filter_by(run_id=run_id).first()
                    if run_history:
                        continue

                    db_crd = db.session.query(Workflow).filter_by(name=crd['name']).first()
                    pipeline = db_crd.pipeline
                    if pipeline:
                        k8s_client = py_k8s.K8s(pipeline.project.cluster.get('KUBECONFIG',''))
                    else:
                        k8s_client = py_k8s.K8s()

                    k8s_client.delete_workflow(
                        all_crd_info = conf.get("CRD_INFO", {}),
                        namespace=crd['namespace'],
                        run_id = run_id
                    )
                    # push_message(conf.get('ADMIN_USER', '').split(','),'%s手动运行新的pipeline %s，进而删除旧的pipeline run-id: %s' % (pipeline.created_by.username,pipeline.describe,run_id,))
                    if db_crd:
                        db_crd.status='Deleted'
                        db_crd.change_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        db.session.commit()
            except Exception as e:
                print(e)


    def check_pipeline_perms(user_fun):
        # @pysnooper.snoop()
        def wraps(*args, **kwargs):
            pipeline_id = int(kwargs.get('pipeline_id','0'))
            if not pipeline_id:
                response = make_response("pipeline_id not exist")
                response.status_code = 404
                return response

            user_roles = [role.name.lower() for role in g.user.roles]
            if "admin" in user_roles:
                return user_fun(*args, **kwargs)

            join_projects_id = security_manager.get_join_projects_id(db.session)
            pipeline = db.session.query(Pipeline).filter_by(id=pipeline_id).first()
            if pipeline.project.id in join_projects_id:
                return user_fun(*args, **kwargs)

            response = make_response("no perms to run pipeline %s"%pipeline_id)
            response.status_code = 403
            return response

        return wraps


    # # @event_logger.log_this
    @expose("/run_pipeline/<pipeline_id>", methods=["GET", "POST"])
    @check_pipeline_perms
    def run_pipeline(self,pipeline_id):
        print(pipeline_id)
        pipeline = db.session.query(Pipeline).filter_by(id=pipeline_id).first()

        pipeline.delete_old_task()

        time.sleep(1)
        # if pipeline.changed_on+datetime.timedelta(seconds=5)>datetime.datetime.now():
        #     flash("发起运行实例，太过频繁，5s后重试",category='warning')
        #     return redirect('/pipeline_modelview/list/?_flt_2_name=')
        back_crds = pipeline.get_workflow()

        # 把消息加入到源数据库
        for crd in back_crds:
            try:
                workflow = db.session.query(Workflow).filter_by(name=crd['name']).first()
                if not workflow:
                    username = ''
                    labels = json.loads(crd['labels'])
                    if 'run-rtx' in labels:
                        username = labels['run-rtx']
                    elif 'upload-rtx' in labels:
                        username = labels['upload-rtx']

                    workflow = Workflow(name=crd['name'], namespace=crd['namespace'], create_time=crd['create_time'],
                                        status=crd['status'],
                                        annotations=crd['annotations'],
                                        labels=crd['labels'],
                                        spec=crd['spec'],
                                        status_more=crd['status_more'],
                                        username=username
                                        )
                    db.session.add(workflow)
                    db.session.commit()
            except Exception as e:
                print(e)

        # 这里直接删除所有的历史任务流，正在运行的也删除掉
        # not_running_crds = back_crds  # [crd for crd in back_crds if 'running' not in crd['status'].lower()]
        self.delete_bind_crd(back_crds)

        # running_crds = [1 for crd in back_crds if 'running' in crd['status'].lower()]
        # if len(running_crds)>0:
        #     flash("发现当前运行实例 %s 个，目前集群仅支持每个任务流1个运行实例，若要重新发起实例，请先stop旧实例"%len(running_crds),category='warning')
        #     # run_instance = '/workflow_modelview/list/?_flt_2_name=%s'%pipeline.name.replace("_","-")[:54]
        #     run_instance = r'/workflow_modelview/list/?_flt_2_labels="pipeline-id"%3A+"'+'%s"' % pipeline_id
        #     return redirect(run_instance)


        # self.delete_workflow(pipeline)
        pipeline.pipeline_file = dag_to_pipeline(pipeline, db.session)  # 合成workflow
        # print('make pipeline file %s' % pipeline.pipeline_file)
        # return
        print('begin upload and run pipeline %s' % pipeline.name)
        pipeline.run_id = ''
        run_id = run_pipeline(pipeline=pipeline)   # 会根据版本号是否为空决定是否上传
        if run_id:
            pipeline.run_id = run_id
            db.session.commit()  # 更新
        pipeline_log_url = pipeline.project.cluster.get('PIPELINE_URL','')
        run_url = pipeline_log_url + pipeline.run_id
        print(pipeline_log_url,run_url)
        time.sleep(3)
        # return redirect("/pipeline_modelview/web/log/%s"%pipeline_id)
        return redirect(run_url)


    # # @event_logger.log_this
    @expose("/web/<pipeline_id>", methods=["GET"])
    def web(self,pipeline_id):
        pipeline = db.session.query(Pipeline).filter_by(id=pipeline_id).first()

        pipeline.dag_json = pipeline.fix_dag_json()
        # pipeline.expand = json.dumps(pipeline.fix_expand(), indent=4, ensure_ascii=False)
        pipeline.expand = json.dumps(pipeline.fix_position(), indent=4, ensure_ascii=False)

        # db_tasks = pipeline.get_tasks(db.session)
        # if db_tasks:
        #     try:
        #         tasks={}
        #         for task in db_tasks:
        #             tasks[task.name]=task.to_json()
        #         expand = core.fix_task_position(pipeline.to_json(),tasks)
        #         pipeline.expand=json.dumps(expand,indent=4,ensure_ascii=False)
        #         db.session.commit()
        #     except Exception as e:
        #         print(e)

        db.session.commit()
        print(pipeline_id)
        data = {
            "url": '/static/appbuilder/vison/index.html?pipeline_id=%s'%pipeline_id  # 前后端集成完毕，这里需要修改掉
        }
        # 返回模板
        return self.render_template('link.html', data=data)


    # # @event_logger.log_this
    @expose("/web/log/<pipeline_id>", methods=["GET"])
    def web_log(self,pipeline_id):
        pipeline = db.session.query(Pipeline).filter_by(id=pipeline_id).first()
        if pipeline.run_id:
            url = pipeline.project.cluster.get('PIPELINE_URL') + pipeline.run_id
            return redirect(url)
        else:
            flash('no running instance','warning')
            return redirect('/pipeline_modelview/web/%s'%pipeline.id)


    # # @event_logger.log_this
    @expose("/web/monitoring/<pipeline_id>", methods=["GET"])
    def web_monitoring(self,pipeline_id):
        pipeline = db.session.query(Pipeline).filter_by(id=int(pipeline_id)).first()
        if pipeline.run_id:
            url = pipeline.project.cluster.get('GRAFANA_HOST','').strip('/')+conf.get('GRAFANA_TASK_PATH')+ pipeline.name
            return redirect(url)
            # data = {
            #     "url": pipeline.project.cluster.get('GRAFANA_HOST','').strip('/')+conf.get('GRAFANA_TASK_PATH') + pipeline.name,
            #     # "target": "div.page_f1flacxk:nth-of-type(0)",   # "div.page_f1flacxk:nth-of-type(0)",
            #     "delay":1000,
            #     "loading": True
            # }
            # # 返回模板
            # if pipeline.project.cluster['NAME']==conf.get('ENVIRONMENT'):
            #     return self.render_template('link.html', data=data)
            # else:
            #     return self.render_template('external_link.html', data=data)
        else:
            flash('no running instance','warning')
            return redirect('/pipeline_modelview/web/%s'%pipeline.id)

    # # @event_logger.log_this
    @expose("/web/pod/<pipeline_id>", methods=["GET"])
    def web_pod(self,pipeline_id):
        pipeline = db.session.query(Pipeline).filter_by(id=pipeline_id).first()
        data = {
            "url": pipeline.project.cluster.get('K8S_DASHBOARD_CLUSTER', '') + '#/search?namespace=%s&q=%s' % (conf.get('PIPELINE_NAMESPACE'), pipeline.name.replace('_', '-')),
            "target":"div.kd-chrome-container.kd-bg-background",
            "delay":500,
            "loading": True
        }
        # 返回模板
        if pipeline.project.cluster.get('NAME','dev')==conf.get('ENVIRONMENT'):
            return self.render_template('link.html', data=data)
        else:
            return self.render_template('external_link.html', data=data)


    # @pysnooper.snoop(watch_explode=('expand'))
    def copy_db(self,pipeline):
        new_pipeline = pipeline.clone()
        expand = json.loads(pipeline.expand) if pipeline.expand else {}
        new_pipeline.name = new_pipeline.name.replace('_', '-') + "-copy-" + uuid.uuid4().hex[:4]
        new_pipeline.created_on = datetime.datetime.now()
        new_pipeline.changed_on = datetime.datetime.now()
        db.session.add(new_pipeline)
        db.session.commit()

        def change_node(src_task_id, des_task_id):
            for node in expand:
                if 'source' not in node:
                    # 位置信息换成新task的id
                    if int(node['id']) == int(src_task_id):
                        node['id'] = str(des_task_id)
                else:
                    if int(node['source']) == int(src_task_id):
                        node['source'] = str(des_task_id)
                    if int(node['target']) == int(src_task_id):
                        node['target'] = str(des_task_id)

        # 复制绑定的task，并绑定新的pipeline
        for task in pipeline.get_tasks():
            new_task = task.clone()
            new_task.pipeline_id = new_pipeline.id
            new_task.create_datetime = datetime.datetime.now()
            new_task.change_datetime = datetime.datetime.now()
            db.session.add(new_task)
            db.session.commit()
            change_node(task.id, new_task.id)

        new_pipeline.expand = json.dumps(expand)
        db.session.commit()
        return new_pipeline

    # # @event_logger.log_this
    @expose("/copy_pipeline/<pipeline_id>", methods=["GET", "POST"])
    def copy_pipeline(self,pipeline_id):
        print(pipeline_id)
        message=''
        try:
            pipeline = db.session.query(Pipeline).filter_by(id=pipeline_id).first()
            new_pipeline = self.copy_db(pipeline)
            return jsonify(new_pipeline.to_json())
            # return redirect('/pipeline_modelview/web/%s'%new_pipeline.id)
        except InvalidRequestError:
            db.session.rollback()
        except Exception as e:
            logging.error(e)
            message=str(e)
        response = make_response("copy pipeline %s error: %s" % (pipeline_id,message))
        response.status_code = 500
        return response

    @action(
        "copy", __("Copy Pipeline"), confirmation=__('Copy Pipeline'), icon="fa-copy",multiple=True, single=False
    )
    def copy(self, pipelines):
        if not isinstance(pipelines, list):
            pipelines = [pipelines]
        try:
            for pipeline in pipelines:
                self.copy_db(pipeline)
        except InvalidRequestError:
            db.session.rollback()
        except Exception as e:
            logging.error(e)
            raise e

        return redirect(request.referrer)


class Pipeline_ModelView(Pipeline_ModelView_Base,MyappModelView,DeleteMixin):
    datamodel = SQLAInterface(Pipeline)
    # base_order = ("changed_on", "desc")
    # order_columns = ['changed_on']

appbuilder.add_view(Pipeline_ModelView,"任务流",href="/pipeline_modelview/list/",icon = 'fa-sitemap',category = '任务')

# 添加api
class Pipeline_ModelView_Api(Pipeline_ModelView_Base,MyappModelRestApi):
    datamodel = SQLAInterface(Pipeline)
    route_base = '/pipeline_modelview/api'
    show_columns = ['project','name','describe','namespace','schedule_type','cron_time','node_selector','image_pull_policy','depends_on_past','max_active_runs','parallelism','global_env','dag_json','pipeline_file','run_id','created_by','changed_by','created_on','changed_on','expand']
    list_columns = show_columns
    add_columns = ['project','name','describe','namespace','schedule_type','cron_time','node_selector','image_pull_policy','depends_on_past','max_active_runs','parallelism','dag_json','global_env','expand']
    edit_columns = add_columns

appbuilder.add_api(Pipeline_ModelView_Api)



