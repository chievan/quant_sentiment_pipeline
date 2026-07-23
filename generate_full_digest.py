import os
import sys
import json
import requests
import pandas as pd
from datetime import datetime
import concurrent.futures

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.ingestion.rss_scraper import RSSScraper
from src.ingestion.ddb_extractor import DDBExtractor
from src.utils.pdf_parser import PDFParser
from src.engine.fof_attribution import FOFAttributionEngine
from src.storage.db_manager import NewsDBManager

# Load API credentials from settings_local.json or env
local_settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "settings_local.json")
api_key = None
if os.path.exists(local_settings_path):
    with open(local_settings_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
        api_key = cfg.get("volc_api_key")

if not api_key:
    api_key = os.getenv("VOLC_API_KEY", "")

base_url = "https://ark.cn-beijing.volces.com/api/plan/v3"

from email.utils import parsedate_to_datetime

def format_pub_date(pub_date_raw: str) -> str:
    """Normalize various date formats (Unix timestamp, RFC GMT string, etc.) into YYYY-MM-DD HH:MM:SS."""
    if not pub_date_raw:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pub_str = str(pub_date_raw).strip()
    
    # Check if Unix timestamp
    if pub_str.isdigit():
        try:
            ts = int(pub_str)
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
            
    # Check if RFC 822 / GMT string (e.g., Tue, 21 Jul 2026 16:00:00 GMT)
    try:
        dt = parsedate_to_datetime(pub_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
        
    # Check standard ISO or string date
    try:
        return pd.to_datetime(pub_str).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return pub_str[:19]

def get_channel_category(source_name: str) -> str:
    """Categorize source name into human-readable source channel."""
    if "微信" in source_name or "公众号" in source_name:
        return "微信公众号"
    elif "研报" in source_name or "东方财富" in source_name or "晨报" in source_name:
        return "卖方研报"
    elif "财联社" in source_name or "要闻" in source_name or "日历" in source_name:
        return "电报快讯"
    elif "雪球" in source_name or "热榜" in source_name or "格隆汇" in source_name or "有知有行" in source_name:
        return "社区热帖"
    elif "彭博" in source_name or "麦肯锡" in source_name or "富途" in source_name:
        return "海外跨境"
    return "网络资讯"

def generate_ai_brief(title: str, text: str) -> str:
    """Generate concise AI brief using Volcengine Agent Plan LLM."""
    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    prompt = (
        "你是一个金融量化投研专家。请阅读以下资讯标题和内容，用一到两句话（不超过80字）给出核心【AI 资讯简介】，重点突出该资讯对市场、行业或策略的边际影响。\n\n"
        f"标题：{title}\n"
        f"内容：{text[:600]}"
    )
    payload = {
        "model": "doubao-seed-2.0-lite",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 120
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"].strip()
            return content if content else "（AI 简介生成完成）"
    except Exception as e:
        pass
    return "（AI 简介生成中/暂缺）"

from src.engine.claude_model import ClaudeModel
scoring_model = ClaudeModel(mock_mode=False)

def process_single_article(article: dict, fof_engine: FOFAttributionEngine) -> dict:
    title = article.get("title", "无标题")
    content = article.get("summary", "无正文")
    source_name = article.get("source", "未标注来源")
    source_channel = get_channel_category(source_name)
    pub_date_formatted = format_pub_date(article.get("pubDate", ""))
    
    # Single-pass All-in-One LLM Processor (AI Brief + Sentiment Score + Quant Strategy Attribution)
    res = fof_engine.process_article_all_in_one(title, content)
    
    return {
        "title": title,
        "source_channel": source_channel,
        "source_name": source_name,
        "pubDate": pub_date_formatted,
        "link": article.get("link", ""),
        "ai_brief": res["ai_brief"],
        "content": content,
        "fof_strategy": res["fof_strategy"],
        "quant_reasoning": res["quant_reasoning"],
        "sentiment_score": res["sentiment_score"],
        "rating_label": res["rating_label"]
    }

def main():
    print("==================================================")
    print("🚀 启动全网舆情与公众号提取、LLM 策略归因与 SQLite 入库...")
    print("==================================================")
    
    settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "settings.json")
    with open(settings_path, "r", encoding="utf-8") as f:
        settings = json.load(f)
        
    db_manager = NewsDBManager("data/quant_news.db")
    pdf_parser = PDFParser(cache_path="data/pdf_cache.json")
    rss_scraper = RSSScraper(base_url=settings["rsshub"]["base_url"], timeout=25)
    ddb_extractor = DDBExtractor(
        host=settings["dolphindb"]["host"],
        port=settings["dolphindb"]["port"],
        userid=settings["dolphindb"]["userid"],
        password=settings["dolphindb"]["password"]
    )
    fof_engine = FOFAttributionEngine()
    
    raw_articles = []
    
    # 1. 抓取 DolphinDB 微信公众号
    wechat_articles = ddb_extractor.fetch_wechat_articles(limit=10)
    raw_articles.extend(wechat_articles)
    
    # 2. 抓取 18 路 RSS Hub 资讯 (包含研报、快讯、热帖)
    rss_articles = rss_scraper.fetch_all(pdf_parser=pdf_parser, limit=5)
    raw_articles.extend(rss_articles)
    
    # 3. 过滤去噪
    valid_articles = [a for a in raw_articles if fof_engine.clean_text(f"{a['title']} {a['summary']}")]
    print(f"\n[Digest] 抓取完成！全网有效资讯共计: {len(valid_articles)} 篇。开始大模型并发生成 AI 简介与 FOF 策略归因...")
    
    # 4. 并发生成 AI 简介与字段整理
    processed_articles = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_single_article, item, fof_engine) for item in valid_articles]
        for future in concurrent.futures.as_completed(futures):
            try:
                res = future.result()
                processed_articles.append(res)
            except Exception as e:
                print(f"[Digest] Article processing error: {e}")
                
    # Sort by publication date descending
    processed_articles.sort(key=lambda x: str(x.get("pubDate", "")), reverse=True)
    
    # 5. 存入 SQLite 数据库
    inserted_count = db_manager.upsert_batch(processed_articles)
    print(f"💾 [SQLite] 成功将 {inserted_count} 篇包含全套大模型策略归因标签的资讯持久化存入 SQLite (data/quant_news.db)！")
    
    # 6. 生成按日期批次归档的 Markdown 文件夹与报告
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H%M%S")
    
    report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "reports", date_str)
    os.makedirs(report_dir, exist_ok=True)
    report_file_path = os.path.join(report_dir, f"digest_{time_str}.md")
    master_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "full_news_digest.md")
    
    md_lines = []
    md_lines.append("# 📰 全网与微信公众号舆情全量提炼与大模型策略归档报告\n")
    md_lines.append(f"- **📅 归档日期**: `{date_str}`")
    md_lines.append(f"- **⏰ 提取时间**: `{now.strftime('%H:%M:%S')}`")
    md_lines.append(f"- **📊 本批次全量提取**: `{len(processed_articles)}` 篇")
    md_lines.append(f"- **🧠 策略归因驱动**: `Volcengine LLM (Doubao-Seed-2.0-Lite / DeepSeek-V4-Pro)`")
    md_lines.append(f"- **💾 SQLite 数据库**: `data/quant_news.db` (表: `articles`)")
    md_lines.append(f"- **📁 归档目录**: `data/reports/{date_str}/digest_{time_str}.md`\n")
    md_lines.append("\n---\n")
    
    for idx, item in enumerate(processed_articles, 1):
        md_lines.append(f"## {idx}. {item['title']}\n")
        md_lines.append(f"- **📌 来源渠道**: `{item['source_channel']}` | **📡 信息源**: `{item['source_name']}`")
        md_lines.append(f"- **⏰ 发布时间**: `{item['pubDate']}`")
        md_lines.append(f"- **🎯 大模型FOF策略归因**: `{item['fof_strategy']}`")
        md_lines.append(f"- **⚡ 策略传导逻辑与影响**: `{item['quant_reasoning']}`")
        md_lines.append(f"- **📊 极性评分与预警**: `{item['rating_label']}` (得分: `{item['sentiment_score']:.4f}`)")
        if item['link']:
            md_lines.append(f"- **🔗 原文链接**: [点击查看原文]({item['link']})")
            
        md_lines.append(f"\n> **💡 【AI 资讯简介】**:\n> {item['ai_brief']}\n")
        md_lines.append(f"**📖 【正文内容/研报提炼】**:\n```text\n{item['content']}\n```\n")
        md_lines.append("\n---\n")
        
    markdown_content = "\n".join(md_lines)
    
    # Save batch report into date folder
    with open(report_file_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
        
    # Save master file for immediate user review
    with open(master_file_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
        
    print(f"🎉 [Digest] Markdown 归档完成！")
    print(f"  ├─ 批次文件: {report_file_path}")
    print(f"  └─ 汇总文件: {master_file_path}")

if __name__ == "__main__":
    main()
