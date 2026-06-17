# AI Daily Brief 📡

每日自动收集 AI 工具资讯，生成精华简报推送到微信。

## 数据源

| 平台 | 方式 | 说明 |
|------|------|------|
| Product Hunt | GraphQL API | AI 分类每日新品 |
| Hacker News | Firebase API | 按关键词过滤 |
| Reddit | JSON API | r/AITools 等子版块 |
| GitHub Trending | 页面解析 | AI 相关热门项目 |
| Hugging Face | 官方 API | 每日论文 |
| 知乎 | RSSHub | 热门/科技话题 |
| 少数派 | RSS | AI 效率工具 |
| 即刻 | RSSHub | AI 圈子动态 |

## 快速开始

### 1. 配置 GitHub Secrets

在 GitHub 仓库的 Settings → Secrets and variables → Actions 中添加：

| Secret | 说明 |
|--------|------|
| `DEEPSEEK_API_KEY` | DeepSeek 平台 API Key |
| `WXPUSHER_TOKEN` | WxPusher 应用 Token |
| `WXPUSHER_UID` | WxPusher 用户 UID |
| `PRODUCT_HUNT_TOKEN` | (可选) Product Hunt API Token |

### 2. 部署

把代码 push 到 GitHub 仓库即可。

GitHub Actions 会自动在 **每天北京时间 09:00** 执行简报生成和推送。

也可以手动触发：GitHub 仓库 → Actions → Daily AI Brief → Run workflow。

### 3. 本地调试

```bash
pip install -r requirements.txt
set DEEPSEEK_API_KEY=sk-xxx
set WXPUSHER_TOKEN=AT_xxx
set WXPUSHER_UID=UID_xxx
python src/main.py
```

## 项目结构

```
├── .github/workflows/daily-brief.yml   # GitHub Actions 定时任务
├── src/
│   ├── main.py                         # 入口编排
│   ├── config.py                       # 全局配置
│   ├── models.py                       # 数据模型
│   ├── summarizer.py                   # DeepSeek 摘要
│   ├── pusher.py                       # WxPusher 推送
│   └── sources/                        # 各平台抓取器
│       ├── base.py                     # 抽象基类
│       ├── hacker_news.py
│       ├── reddit.py
│       ├── product_hunt.py
│       ├── huggingface.py
│       ├── github_trending.py
│       ├── zhihu.py
│       ├── sspai.py
│       └── jike.py
├── requirements.txt                    # Python 依赖
└── README.md
```

## 成本

| 项目 | 费用 |
|------|------|
| GitHub Actions | 免费（2000 分钟/月） |
| DeepSeek API | ~¥0.5-1/月 |
| WxPusher | 免费 |

## 推送效果预览

推送到你微信的样子：

```
📡 AI Daily Brief · 2025-06-17

1. [工具名] 一句话简介 [Product Hunt]
2. [项目名] 一句话简介 [GitHub Trending]
3. [论文名] 一句话简介 [Hugging Face]
...

---
今日趋势：AI 编程助手和 RAG 工具是今日热点。
---
共收录 35 条资讯
```
