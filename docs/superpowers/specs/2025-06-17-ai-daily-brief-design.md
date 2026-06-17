# AI Daily Brief — AI 工具资讯每日简报系统

> 日期：2025-06-17  
> 状态：设计已批准，待实现

## 1. 概述

每天自动从多个平台抓取最新的 AI 工具资讯，经 AI 摘要后通过微信推送给用户，实现「一目了然获取 AI 行业动态」的目标。

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                   GitHub Actions                         │
│               cron: 0 1 * * * (UTC)                      │
│               = 每天北京时间 09:00 触发                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │PH 抓取   │  │HN 抓取   │  │Reddit 抓取│  ...          │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘               │
│       │             │             │                      │
│       └─────────────┼─────────────┘                      │
│                     ▼                                    │
│              ┌──────────────┐                            │
│              │  清洗 & 去重  │                            │
│              │ (InfoItem)   │                            │
│              └──────┬───────┘                            │
│                     ▼                                    │
│              ┌──────────────┐                            │
│              │ DeepSeek API │                            │
│              │  生成简报    │                            │
│              └──────┬───────┘                            │
│                     ▼                                    │
│              ┌──────────────┐                            │
│              │ WxPusher API │                            │
│              │ 推送到微信   │                            │
│              └──────────────┘                            │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## 3. 数据源

### 3.1 海外平台（如不可达则自动跳过）

| 平台 | 接入方式 | 备注 |
|------|---------|------|
| Product Hunt | 官方 API（producthunt.com/v2/api） | 关注 AI 分类每日 Top |
| Hacker News | 免费 API（hacker-news.firebaseio.com） | 按关键词过滤 AI 相关 |
| Reddit | JSON API（reddit.com/r/*/hot.json） | 订阅 r/AITools, r/artificial, r/MachineLearning |
| GitHub Trending | BeautifulSoup 爬取 | 筛选 AI 相关项目 |
| Hugging Face Daily Papers | 免费 API | 每日论文列表 |

### 3.2 中文平台

| 平台 | 接入方式 | 备注 |
|------|---------|------|
| 知乎 | RSS（zhuanlan.zhihu.com/...） | 关注 AI 工具推荐话题 |
| 少数派 | RSS（sspai.com/feed） | 关注效率工具/AI 分类 |
| 即刻 | RSS 或第三方 API | 关注 AI 工具圈子 |

### 3.3 统一数据模型

```python
@dataclass
class InfoItem:
    title: str          # 标题
    url: str            # 原文链接
    source: str         # 来源标识
    description: str    # 简要描述（150字以内）
    score: int          # 热度分
    published: str      # 发布日期 YYYY-MM-DD
```

## 4. 处理流程

### 4.1 抓取阶段
- 每个数据源独立抓取，互不影响
- 单源失败（网络超时/被封）不影响其他源
- 配置化开关：config.py 中控制每个源的启用/禁用

### 4.2 摘要阶段
- 合并当天所有源的数据，按 score 排序取 Top 30-50
- 调用 DeepSeek API（deepseek-v4-flash）生成中文简报
- Prompt 示例：将以下 AI 工具资讯整理为中文每日简报，每条不超过 50 字，按推荐度排序

### 4.3 推送阶段
- 调用 WxPusher API（wxpusher.zjiecode.com）
- 发送模板消息到用户微信
- 推送内容为摘要文本，包含来源标注和链接

## 5. 技术栈

| 组件 | 技术选型 |
|------|---------|
| 语言 | Python 3.11+ |
| 依赖管理 | pip + requirements.txt |
| HTTP 请求 | requests |
| RSS 解析 | feedparser |
| HTML 解析 | beautifulsoup4 |
| AI 摘要 | DeepSeek API（deepseek-v4-flash） |
| 推送 | WxPusher API |
| 调度 | GitHub Actions（cron: 0 1 * * * UTC = 09:00 CST） |
| 配置 | GitHub Secrets + config.py |

## 6. 项目结构

```
ai-daily-brief/
├── .github/
│   └── workflows/
│       └── daily-brief.yml
├── src/
│   ├── main.py                 # 入口：编排抓取→摘要→推送
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── base.py             # 基础抓取器抽象类
│   │   ├── product_hunt.py
│   │   ├── hacker_news.py
│   │   ├── reddit.py
│   │   ├── github_trending.py
│   │   ├── huggingface.py
│   │   ├── zhihu.py
│   │   ├── sspai.py
│   │   └── jike.py
│   ├── models.py               # InfoItem 等数据模型
│   ├── summarizer.py           # DeepSeek API 调用
│   └── pusher.py               # WxPusher 推送
├── config.py                   # 全局配置
├── requirements.txt
└── README.md
```

## 7. 配置项（GitHub Secrets）

| Secret 名 | 用途 |
|-----------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 |
| `WXPUSHER_TOKEN` | WxPusher 应用 Token |
| `WXPUSHER_UID` | 目标用户 UID |

## 8. 成本预估

| 项目 | 预估费用 |
|------|---------|
| GitHub Actions | $0（免费额度内） |
| DeepSeek API | ¥0.5-1/月 |
| WxPusher | $0（免费额度 200 条/天，仅用 1 条） |

## 9. 错误处理

- 单源抓取失败：记录日志，继续执行其他源
- 所有源均失败：推送错误通知
- DeepSeek API 失败：跳过摘要，推送原文列表
- WxPusher 推送失败：记录日志到 GitHub Actions

## 10. 后续可扩展

- 网页版简报存档（GitHub Pages）
- 添加更多数据源（Twitter, 公众号等）
- 支持多用户订阅
- 自定义关键词过滤
- 每周/每月趋势汇总
