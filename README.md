# 📡 阿尔法雷达系统 (Alpha Radar System)
> **独立量化舆情情绪分析与特征提取流水线 (Standalone Quant Sentiment Pipeline)**

本项目是一个专为私募/公募机构主动管理设计的**独立量化舆情打分系统**。它基于华安证券 AI 投研 Session 3 培训关于**阿尔法雷达系统**的底层设计哲学构建，旨在将海量非标信息过滤、降噪并收敛为量化可下注的“待验证投资假设”因子。

---

## 🎯 核心设计哲学 (Core Methodology)

本项目严格贯彻**阿尔法雷达系统**的以下核心逻辑：

```text
  [全网信息洪流]  ──> (获取: RSS/DolphinDB/API)
        │
  [可信来源过滤]  ──> (判源: 公告事实高权重/小作文动态贝叶斯更新)
        │
  [边际增量识别]  ──> (判增量: 去除已知预期，提取增量)
        │
  [能力圈主线映射] ──> (判相关: 映射赛道/个股/核心自选)
        │
  [待验证假设草稿] ──> (判验证: 输出结构化因子 CSV -> 投研交接单)
```

1. **五层过滤漏斗**：全网洪流 $\rightarrow$ 可信来源 $\rightarrow$ 净增量 $\rightarrow$ 能力圈相关信号 $\rightarrow$ 待验证信号。
2. **四步评估模型**：
   * **判源**：研判信息来源的利益立场与置信度等级。
   * **判增量**：计算相比市场一致预期的边际变化。
   * **判相关**：映射至具体持仓/行业/主线。
   * **判验证**：生成下一步需找产业链或分析师复核的核心未知变量与验证问题。
3. **信息权重分层**：
   * **高权重 (事实确认)**：官方公告、企业财报（年报为核心）。
   * **中权重 (逻辑推演)**：卖方行业深度报告、会议纪要。
   * **低权重 (情绪因子)**：网络媒体报道、微信公众号、小作文（通过贝叶斯逻辑更新置信度，作为拥挤度与资金抢跑观测指标）。

---

## 📂 模块架构与代码对照

系统彻底解耦了获取、清洗、筛选与输出四个技术层，使得整个投研流可以 7*24 自动高信噪比运行：

*   **获取层 (Acquisition)**：
    *   [ddb_extractor.py](src/ingestion/ddb_extractor.py)：直接对接基金内部的 DolphinDB 数据库事实表（`dfs://HAZQ.articles`），增量拉取自选公众号文章。
    *   [rss_scraper.py](src/ingestion/rss_scraper.py)：并发拉取 18 个精选跨境财经资讯源（财联社、华尔街见闻、富途要闻/AI专题、彭博新闻、麦肯锡、格隆汇等），支持多线程异步调度。
*   **清洗层 (Cleaning)**：
    *   [pdf_parser.py](src/utils/pdf_parser.py)：**自动研报 PDF 解析器**。针对东方财富等研报的 PDF 链接，自动流式下载并使用 `pypdf` 精准提取前两页（包含“核心观点”与“投资要点”），过滤干扰性空行及排版字符。内置 `pdf_cache.json` 增量缓存，确保同一 PDF 决不重复下载。
*   **筛选与打分层 (Filtering)**：
    *   [lexicon_model.py](src/engine/lexicon_model.py) (**FinNLP 词典模型**)：匹配中文/英文专属金融情感极性词典，计算频次极性差。
    *   [bert_model.py](src/engine/bert_model.py) (**FinBERT 本地深度学习模型**)：本地加载运行 `yiyanghkust/finbert-tone` (中文) 与 `ProsusAI/finbert` (英文) 神经网络分类器。**0 Token 消耗，100% 本地脱网计算**，在没有 PyTorch 环境时可自动优雅降级，防止主干线程挂起。
*   **输出与交接层 (Output / Hand-off)**：
    *   [pipeline.py](src/pipeline.py)：将打分结果对齐，自动生成量化情绪因子数据表（以 `sentiment_factors_YYYYMM.csv` 格式按月追加写入）。这就相当于雷达输出的结构化 **“待验证假设草稿单”**。

---

## 📊 因子数据表字段说明

流水线输出的 CSV 因子格式与量化回测系统完全兼容：

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `timestamp` | string | 雷达扫描打分生成的时间戳 (`YYYY-MM-DD HH:mm:ss`) |
| `pub_date` | string | 资讯源原始发布时间 |
| `source` | string | 资讯来源渠道名称 (如: 东方财富-行业, 微信公众号, 富途要闻) |
| `title` | string | 资讯标题 |
| `link` | string | 原文链接（或研报 PDF 直链，供进一步追溯事实） |
| `score_finnlp` | float | 本地词典 (FinNLP) 打分值（区间 `[-1.0, 1.0]`，代表极性强弱） |
| `channel_finnlp` | string | 使用的词典语种分类通道 |
| `score_finbert` | float | 本地 BERT 深度学习模型预测极性差分值值（区间 `[-1.0, 1.0]`） |
| `channel_finbert` | string | 使用的本地 BERT 模型版本 |

---

## ⚡ 快速开始与自动化部署

### 1. 环境准备
确保您的本地虚拟环境已安装了基础 Python 环境并安装了相关依赖：
```bash
./venv/bin/pip install requests pandas openpyxl pypdf
```
*(选修) 若要在本地跑 FinBERT 神经网络，需安装 `torch` 和 `transformers`：*
```bash
./venv/bin/pip install torch transformers -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 2. 配置文件配置
打开 `config/settings.json`，按需配置您的 DolphinDB 内网连接参数以及资讯拉取的频率限制。

### 3. 手动单次测试运行
```bash
cd /Users/chievan/Documents/projects/quant_sentiment_pipeline
../private-fund-pro/venv/bin/python src/pipeline.py
```

### 4. 2小时自动化定时调度
在终端运行：
```bash
crontab -e
```
添加以下 Cron 定时任务（每 2 小时执行一次流水线扫描并输出日志）：
```text
0 */2 * * * /Users/chievan/Documents/projects/quant_sentiment_pipeline/run_scheduler.sh >> /Users/chievan/Documents/projects/quant_sentiment_pipeline/data/scheduler.log 2>&1
```

---

## 💡 下一步规划 (Session 4 对接)
雷达系统生成的量化舆情因子，是决策的前哨站。在 Session 4 中，我们将在此基础上构建 **“判断层工作流”**，即：
1. 量化因子发生极端偏离（如连续 3 天 Score > 0.8 或快速下挫）。
2. 自动触发持仓赛道/个股的状态机转移。
3. 调取 `PDFParser` 缓存的研报原文片段，配合产业链核实数据，转化为实盘买入/卖出/观察的“下注决策”。
