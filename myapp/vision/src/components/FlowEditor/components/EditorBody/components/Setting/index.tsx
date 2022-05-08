import React, { useState, useEffect, FormEvent } from 'react';
import { IconButton, Dropdown, IDropdownOption, TextField } from '@fluentui/react';
import { isEdge } from 'react-flow-renderer';
import api from '@src/api';
import { useAppDispatch, useAppSelector } from '@src/models/hooks';
import { selectElements } from '@src/models/element';
import { selectInfo, updateChanged, updateEditing, selectChanged } from '@src/models/pipeline';
import { selectShow, toggle } from '@src/models/setting';
import style from './style';

const Setting: React.FC = () => {
  const dispatch = useAppDispatch();
  const pipelineInfo = useAppSelector(selectInfo);
  const settingShow = useAppSelector(selectShow);
  const pipelineChanged = useAppSelector(selectChanged);
  const elements = useAppSelector(selectElements);
  const [current, setCurrent] = useState<any>({});
  const [dropItem, setDropItem] = useState([]);
  const [selectedItem, setSelectedItem] = useState<IDropdownOption>();

  // 配置变化事件
  const handleOnChange = (key: string, value: string | number | IDropdownOption) => {
    const obj: any = {};
    obj[key] = value;
    if (key === 'project') {
      const item = value as IDropdownOption;
      setSelectedItem(item);
      obj[key] = item.key;
    }
    if (pipelineInfo) {
      setCurrent({ ...current, ...obj });
      dispatch(updateChanged({ ...pipelineChanged, ...obj }));
    }
  };

  // 初始化选项
  useEffect(() => {
    if (pipelineInfo) {
      setCurrent(pipelineInfo);
      const selected: IDropdownOption = {
        key: pipelineInfo?.project?.id,
        text: pipelineInfo?.project?.name,
      };
      setSelectedItem(selected);
    }
  }, [pipelineInfo]);

  // 将 setting 编辑变化的数据同步至 redux
  useEffect(() => {
    if (Object.keys(pipelineChanged).length > 1) {
      dispatch(updateEditing(true));
    }
  }, [pipelineChanged]);

  // 项目组选项
  useEffect(() => {
    api.project_modelview().then((res: any) => {
      const orgProject = res?.result.reduce((acc: any, cur: any) => {
        if (cur.type === 'org') {
          const item = {
            key: cur.id,
            text: cur.name,
          };
          acc.push(item);
        }
        return acc;
      }, []);
      setDropItem(orgProject);
    });
  }, []);

  // 根据节点的变化实时更新 dag_json
  useEffect(() => {
    const temp: any = {};
    elements.forEach(ele => {
      if (isEdge(ele)) {
        const source = elements.filter(el => el.id === ele.source)[0];
        const target = elements.filter(el => el.id === ele.target)[0];

        if (temp[`${target.data.name}`]?.upstream) {
          temp[`${target.data.name}`].upstream.push(`${source.data.name}`);
        } else {
          temp[`${target.data.name}`] = {};
          temp[`${target.data.name}`]['upstream'] = [`${source.data.name}`];
        }
      }
    });

    const dag_json = { ...temp };
    setCurrent({
      ...current,
      ...{ dag_json: JSON.stringify(dag_json, undefined, 4) },
    });
    dispatch(
      updateChanged({
        ...pipelineChanged,
        ...{ dag_json: JSON.stringify(dag_json) },
      }),
    );
  }, [elements]);

  return (
    <div
      style={{
        visibility: settingShow ? 'visible' : 'hidden',
      }}
      className={style.settingContainer}
    >
      <div className={style.settingHeader}>
        <div className={style.headerTitle}>流水线设置</div>
        <IconButton
          iconProps={{
            iconName: 'ChromeClose',
            styles: {
              root: {
                fontSize: 12,
                color: '#000',
              },
            },
          }}
          onClick={() => {
            dispatch(toggle());
          }}
        />
      </div>
      <div className={style.settingContent}>
        <div className={style.contentWrapper}>
          <Dropdown
            label="项目组"
            onChange={(e: FormEvent, item?: IDropdownOption) => {
              handleOnChange('project', item || '');
            }}
            selectedKey={selectedItem ? selectedItem.key : undefined}
            placeholder="Select an option"
            options={dropItem}
          />
          <div className={style.splitLine}></div>
          <TextField
            label="名称"
            description="英文名(字母、数字、- 组成)，最长50个字符"
            onChange={(event: FormEvent, value?: string) => {
              handleOnChange('name', value ? value : '');
            }}
            value={current?.name || ''}
            disabled
          />
          <div className={style.splitLine}></div>
          <TextField
            label="描述"
            required
            onChange={(event: FormEvent, value?: string) => {
              handleOnChange('describe', value ? value : '');
            }}
            value={current?.describe || ''}
          />
          <div className={style.splitLine}></div>
          <TextField
            label="命名空间"
            description="部署task所在的命名空间(目前无需填写)"
            value={current?.namespace || ''}
            readOnly
            disabled
          />
          <div className={style.splitLine}></div>
          <Dropdown
            label="调度类型"
            options={[
              { key: 'once', text: 'once' },
              { key: 'crontab', text: 'crontab' },
            ]}
            selectedKey={current?.schedule_type}
            onChange={(event: FormEvent, option?: IDropdownOption) => {
              handleOnChange('schedule_type', `${option?.text}` || '');
            }}
          />
          <div className={style.splitLine}></div>
          <TextField
            label="调度周期"
            description="周期任务的时间设定 * * * * * 表示为 minute hour day month week"
            onChange={(event: FormEvent, value?: string) => {
              handleOnChange('cron_time', value ? value : '');
            }}
            value={current?.cron_time || ''}
          />
          <div className={style.splitLine}></div>
          <TextField
            label="调度机器"
            description="部署task所在的机器(目前无需填写)"
            onChange={(event: FormEvent, value?: string) => {
              handleOnChange('node_selector', value ? value : '');
            }}
            value={current?.node_selector || ''}
          />
          <div className={style.splitLine}></div>
          <Dropdown
            label="镜像拉取策略"
            options={[
              { key: 'Always', text: 'Always' },
              { key: 'IfNotPresent', text: 'IfNotPresent' },
            ]}
            selectedKey={current.image_pull_policy}
            onChange={(event: FormEvent, option?: IDropdownOption) => {
              handleOnChange('image_pull_policy', `${option?.text}` || '');
            }}
          />
          <div className={style.splitLine}></div>
          <Dropdown
            label="过往依赖"
            options={[
              { key: 'true', text: '是', data: true },
              { key: 'false', text: '否', data: false },
            ]}
            selectedKey={`${current.depends_on_past}`}
            onChange={(event: FormEvent, option?: IDropdownOption) => {
              handleOnChange('depends_on_past', option?.data);
            }}
          />
          <div className={style.splitLine}></div>
          <TextField
            label="最大激活运行数"
            description="当前pipeline可同时运行的任务流实例数目"
            onChange={(event: FormEvent, value?: string) => {
              handleOnChange('max_active_runs', value ? +value : '');
            }}
            value={current?.max_active_runs || ''}
            required
          />
          <div className={style.splitLine}></div>
          <TextField
            label="任务并行数"
            description="pipeline中可同时运行的task数目"
            onChange={(event: FormEvent, value?: string) => {
              handleOnChange('parallelism', value ? +value : '');
            }}
            value={current?.parallelism || ''}
            required
          />
          <div className={style.splitLine}></div>
          <TextField
            label="流向图"
            onChange={(event: FormEvent, value?: string) => {
              handleOnChange('dag_json', value ? value : '{}');
            }}
            value={current?.dag_json || '{}'}
            multiline
            autoAdjustHeight
            disabled
          />
          <div className={style.splitLine}></div>
          <TextField
            label="全局环境变量"
            description="为每个task都添加的公共参数"
            onChange={(event: FormEvent, value?: string) => {
              handleOnChange('global_env', value ? value : '');
            }}
            multiline
            autoAdjustHeight
            value={current?.global_env || ''}
          />
        </div>
      </div>
    </div>
  );
};

export default Setting;
