# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

巅峰资本（Apex Capital）基金持仓实时监控系统 — 基于 GitHub Pages 的 PWA，配合 GitHub Actions 实现云端数据自动更新。

## 架构

```
用户截图 → GitHub Issue (holding-sync label)
         → extract_images.py → ocr_screenshots.py (Tesseract)
         → update_holdings.py → portfolio/holdings.md
         → update_cloud.py (天天基金实时估值API) → data.json + data_version.json
         → GitHub Pages 部署 → mobile.html fetch data.json 渲染
```

**前端** (`mobile.html` + `app.js` + `styles.css`):
- `index.html` — 根路径 `<meta http-equiv="refresh">` 重定向到 `mobile.html`（GitHub Pages 入口），无其他内容
- `app.js` — 纯 vanilla JS，无框架，三个核心类：`DataLoader`（数据获取+轮询）、`UIManager`（全部 UI 渲染+事件绑定）、`Settings`（localStorage 读写）。`UIManager` 构造时创建 `DataLoader` 实例并注册为订阅者，单例启动
- `styles.css` — 纯 CSS，无预处理器，885 行，CSS 自定义属性定义在 `:root`，深色主题无独立样式（仅亮色主题）
- `DataLoader` — 观察者模式：fetch `data_version.json` 检测版本 → fetch `data.json` 获取数据，`onChange()` 通知订阅者；`POLL_INTERVAL = 5 * 60 * 1000` 轮询。`checkForUpdate()` 根据 version 变化触发 `load()`，`startPolling()` 用 `setInterval` 定时调用
- `UIManager` — `DataLoader` 订阅者，数据驱动渲染全部 UI。`init()` 流程：bindEvents → showLoading(true) → loader.load() → startPolling。页面结构为 login-page → main-page（含 loading-overlay / error-banner / stale-banner / header / cards / bottom-nav）→ settings-page，用 `.page.active` CSS class 控制切换。密码 `1688` 硬编码在 `APP_PASSWORD` 常量
- `Settings` — localStorage 管理：`apex_settings`（偏好）、`apex_local_funds`（手动添加的本地基金）、`apex_last_visit`（最后访问时间）
- 密码登录只控制本地基金管理区域（手动添加/编辑/删除基金的 `#local-portfolio-section` + 设置页面的清除/导出/导入），云端数据展示（总资产/持仓列表/排名/日报）无需登录，`renderAll()` 始终执行
- `portfolio.html` 是独立的暗色主题静态报告页，与主应用无关
- `upload.html` 是暗色主题的截图上传引导页（提交到 GitHub Issues），`dashboard/upload.html` 是副本
- `manifest.json` — PWA 配置，`display: standalone`，SVG 内联图标
- `#error-banner` — 网络错误横幅（含重试按钮），`#stale-banner` — 数据过期三级警告横幅（yellow/orange/red）

**CSS 关键 class 和动画**:
- `#loading-overlay` / `.loading-content` / `.skeleton-block` — 全屏加载覆盖层（渐变色 SVG logo + 骨架屏占位）
- `.stale-banner.yellow|.orange|.red` — 数据过期三级警告
- `#error-banner` / `.error-banner` — 网络错误横幅（含重试按钮）
- `.type-distribution` / `.type-bar-fill` — 持仓类型分布条
- `.rank-item` — 涨跌排名
- `.fund-warning` — 基金预警标记（CRO 预警、仓位过低等）
- `.pension-badge` — 养老金标签
- `.fund-type-tag` — 基金类型标签
- `@keyframes slideIn` / `fadeOut` / `shake` / `spin` — 页面过渡和加载动画

**数据管道**（GitHub Actions）:
1. `holding-sync.yml` — Issue 带 `holding-sync` 标签时触发：下载截图 → Tesseract OCR → `update_holdings.py` 解析并更新 `portfolio/holdings.md` → 提交到仓库
2. `fund-update.yml` — 工作日四次定时（北京时间 09:35/14:30/15:05/20:00）+ `holdings.md` 变更触发 → `update_cloud.py` 拉取天天基金实时估值 → 生成 `data.json` + `data_version.json` → 提交 → GitHub Pages 自动部署

**Python 脚本** (`scripts/`):
| 脚本 | 用途 | 运行环境 |
|------|------|---------|
| `update_cloud.py` | 读 holdings.md → 调天天基金 API → 生成 data.json | GitHub Actions |
| `update_holdings.py` | OCR 文本 → 解析基金数据 → 更新 holdings.md | GitHub Actions / 本地 |
| `extract_images.py` | 从 Issue body 提取 base64/URL 图片 | GitHub Actions |
| `ocr_screenshots.py` | Tesseract OCR 识别持仓截图 | GitHub Actions |
| `post_review_report.py` | 生成审核报告并发布到 Issue 评论 | GitHub Actions |
| `data_quality_check.py` | 检查 holdings.md 数据基准日是否过期 | GitHub Actions |
| `check_holding_sync.py` | 完整 OCR 管线前端：检测 Issue → 下载 base64 图片 → 本地 OCR（Node.js）→ 发布 Issue 评论 + 标记 processing 标签 → 缓存结果供 CEO Agent | 本地 WorkBuddy |

**数据文件**:
- `portfolio/holdings.md` — 持仓台账，分两个账户 section（`## 账户一：普通基金账户` + `## 账户二：个人养老金账户`），Markdown 表格格式。`update_cloud.py` 按 section header 解析账户归属，`update_holdings.py` 生成时硬编码养老金代码集合 `{"017268", "017294", "017353", "022951", "022979"}` 用于区分账户
- `data.json` — CI 生成含实时估值的完整数据（25 只基金、类型分布、排名 TOP5、日报文本、过期警告）
- `data_version.json` — 轻量版本标记 `{v, t, ts}`，前端用它检测是否有新数据（避免缓存）

## 常用命令

```bash
# 本地预览前端
python -m http.server 8080
# 浏览器访问 http://localhost:8080/mobile.html

# 本地运行云端更新脚本（需先有 portfolio/holdings.md）
python scripts/update_cloud.py

# 本地 OCR 识别截图（需安装 tesseract + 中文语言包）
python scripts/ocr_screenshots.py /path/to/screenshots /tmp/ocr_results /tmp/ocr_combined.txt
python scripts/update_holdings.py /tmp/ocr_combined.txt portfolio/holdings.md

# 数据质量检查
python scripts/data_quality_check.py
```

## 重要约束

- `data.json` 和 `data_version.json` 由 CI 自动维护，**不要手动编辑**
- `portfolio/holdings.md` 数据基准日格式严格为 `# 数据基准日：YYYY-MM-DD`，脚本依赖此格式
- 天天基金 API: `http://fundgz.1234567.com.cn/js/{code}.js`，仅交易日 9:00-15:00 北京时间返回实时估值
- `update_cloud.py` 自定义 `BeijingTime(tzinfo)` 类（UTC+8），通过 `beijing_now()` 获取北京时间；`is_trading_day()` / `run_update()` 均使用 `beijing_now()` 替代 `datetime.now()`
- 法定节假日列表 `HOLIDAYS_2026` 在 `update_cloud.py` 和 `data_quality_check.py` 中**各自维护一份**，修改时需两边同步
- `update_cloud.py` 内联了数据新鲜度检测逻辑（与 `data_quality_check.py` 功能重叠），后者作为独立脚本可单独调用
- `fund-update.yml` 有两层交易日守卫：shell 层 `check_day`（周几判断）+ Python 层 `is_trading_day()`（节假日排除），防御性设计
- `holding-sync.yml` 仅对 `issues.opened` 事件触发，不对 `issues.edited` 触发；手动触发时查询最新的 open issue
- `check_holding_sync.py` 使用 `subprocess.run`（非 `shell=True`）调用 `gh auth token`
- `apex-final/`、`apex-working/`、`backup/` 是发布/工作/备份快照目录
- `check_holding_sync.py` 仅用于本地 WorkBuddy，硬编码了 Windows 开发机路径（`C:\Users\Administrator\Documents\基金监控及推荐`），CI 中不可用；OCR 调用依赖 `~/.workbuddy/skills/ocr-local/scripts/ocr.js`（Node.js 脚本）
- `check_holding_sync.py` 使用的 OCR 脚本路径和 GitHub 仓库地址均硬编码为 `rebornwl/apex-capital-dashboard`
- `.gitignore` 已排除 `scripts/__pycache__/`
- `manifest.json` 中 `start_url: "index.html"`，通过 `<meta http-equiv="refresh">` 重定向到 `mobile.html`——PWA 场景下注意 index.html 的缓存策略
- 底部导航栏（首页/设置）的 tab 切换按钮（`data-tab` 属性）在 `bindEvents()` 中尚未绑定 click 事件，当前仅 `#back-btn` 可以触发 `showPage('main')`
