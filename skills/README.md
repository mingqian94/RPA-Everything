# skills/ — 自建 Skill 目录

这里存放不适合放入 `showcase/` 的自建 Skill——通常是依赖特定系统配置、或场景过于垂直的流程。

## feishu_project_daily — 飞书项目日报

每日拉取飞书项目视图数据，输出今日到期、已延期、各负责人在跟需求。

**前提：** 在 `config.yaml` 中填写以下配置（获取方式见 skill 文件顶部注释）：

```yaml
feishu_project:
  view_url: "https://project.feishu.cn/your-project/storyView/Xxx"
  project_key: "625eb563..."
  due_field_id: "a817fb"   # 截止日期自定义字段 ID，没有可留空
```

**运行：**

```bash
python run.py skills/feishu_project_daily
```

**定时执行（每天早 9 点）：**

```bash
sh tools/cron_helper.sh skills/feishu_project_daily "0 9 * * 1-5"
```
