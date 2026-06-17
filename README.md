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

### 1. 准备工作：获取公众号 API 凭证

登录 [mp.weixin.qq.com](https://mp.weixin.qq.com) →
**设置与开发** → **开发接口管理**，找到：

- **AppID**（`appid`）
- **AppSecret**（`appsecret`，如果没生成过就点"重置"）

### 2. 配置 GitHub Secrets

在 GitHub 仓库的 Settings → Secrets and variables → Actions 中添加：

| Secret | 说明 |
|--------|------|
| `DEEPSEEK_API_KEY` | DeepSeek 平台 API Key |
| `WECHAT_APP_ID` | 微信公众号 AppID |
| `WECHAT_APP_SECRET` | 微信公众号 AppSecret |
| `PRODUCT_HUNT_TOKEN` | (可选) Product Hunt API Token |

### 3. 部署

把代码 push 到 GitHub 仓库即可。

GitHub Actions 会自动在 **每天北京时间 09:00**：
1. 抓取 8 个平台资讯
2. DeepSeek 生成摘要简报
3. 排版为公众号图文
4. 自动上传到你的公众号 **草稿箱**

你每天只需要登录 [mp.weixin.qq.com](https://mp.weixin.qq.com) →
**草稿箱** → 找到今日简报 → 点 **"发布"** 即可。

也可以手动触发：GitHub 仓库 → Actions → Daily AI Brief → Run workflow。

### 4. 本地调试

```bash
pip install -r requirements.txt
set DEEPSEEK_API_KEY=sk-xxx
set WECHAT_APP_ID=xxx
set WECHAT_APP_SECRET=xxx
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
| 微信公众号 API | 免费 |

## 使用流程

每天系统自动完成 90% 的工作：

```
抓取 8 个平台 → AI 摘要 → 排版为公众号图文 → 上传草稿箱
                                                      ↓
                                       你登录 mp.weixin.qq.com
                                       打开草稿箱 → 点"发布"
                                                      ↓
                                       你的粉丝就能看到日报了 🎉
```

## 草稿预览

每天生成的草稿长这样：

- 📰 **标题**：📡 AI Daily Brief · 2025-06-17
- ✍️ **摘要**：共收录 35 条资讯，AI 工具行业每日速览
- 📄 **正文**：排版好的图文，含来源标签、今日趋势总结
