# Xiaohongshu Crawling Showcase

小红书采集 showcase，提供 3 个固化 Skill：

1. `user_posts`：采集某个用户主页中的帖子链接和卡片文本。
2. `search_posts`：采集某个搜索词或 tag 下的帖子链接和卡片文本。
3. `post_detail`：采集单篇帖子内的文字、图片、视频链接和可见互动数据。

这些脚本复用本机已登录 Chrome，通过 Playwright 操作页面，不处理登录绕过，也不读取任何本地账号配置。执行时包含随机慢等待和慢滚动，避免机器式快速请求。

## Prerequisites / 前置条件

1. 先启动调试 Chrome：

```bash
tools\start_chrome.bat
```

2. 在这个 Chrome 里手动登录小红书。
3. 采集公开可见或你账号有权限查看的内容；遵守目标网站规则和频率限制。

## Tools / 工具

### 1. Crawl User Posts / 采集用户帖子

```bash
python run.py showcase/web/xiaohongshu/user_posts -- \
  --user-url "https://www.xiaohongshu.com/user/profile/<user-id>" \
  --limit 30 \
  --output data/xhs_user_posts.json
```

也可以传 `--user-id <id>`，脚本会拼成用户主页 URL。

### 2. Crawl Search or Tag Posts / 采集搜索词或 Tag 帖子

```bash
python run.py showcase/web/xiaohongshu/search_posts -- \
  --keyword "露营" \
  --limit 30 \
  --output data/xhs_search_posts.json
```

Tag 可直接作为关键词传入，例如 `--keyword "#露营装备"`。

### 3. Crawl Post Detail / 采集帖子详情

```bash
python run.py showcase/web/xiaohongshu/post_detail -- \
  --url "https://www.xiaohongshu.com/explore/<note-id>" \
  --output data/xhs_post_detail.json
```

输出包含：

- `text`：页面可见正文文本
- `images`：页面中可见图片 URL
- `videos`：页面中可见视频 URL
- `engagement`：从可见文本中尽力提取的点赞/收藏/评论等互动信息

页面结构会随小红书版本变化；这些 showcase 的重点是“让 Agent 快速干活并导出数据”，不是保证所有版本永久稳定。
