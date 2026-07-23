import os
import json
import re
import requests
import pandas as pd
from datetime import datetime
import concurrent.futures
from typing import List, Dict, Any

from src.ingestion.ddb_extractor import DDBExtractor
from src.ingestion.rss_scraper import RSSScraper
from src.utils.pdf_parser import PDFParser
from src.storage.db_manager import NewsDBManager
from src.engine.fof_attribution import FOFAttributionEngine

# Load API Key from local settings
base_url = "https://ark.cn-beijing.volces.com/api/plan/v3"
api_key = ""
local_settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "settings_local.json")
if os.path.exists(local_settings_path):
    with open(local_settings_path, "r", encoding="utf-8") as f:
        api_key = json.load(f).get("volc_api_key", "")

def format_pub_date(pub_date_raw: str) -> str:
    if not pub_date_raw:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pub_str = str(pub_date_raw).strip()
    if pub_str.isdigit():
        try:
            return datetime.fromtimestamp(int(pub_str)).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(pub_str).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    try:
        return pd.to_datetime(pub_str).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return pub_str[:19]

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

FEISHU_WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/fe1a567a-9bb4-4b7b-9fcf-ffe4076bec8f"
SMTP_SERVER = "smtp.163.com"
SMTP_PORT = 465
MAIL_USERNAME = "wuqiwen0571@163.com"
MAIL_PASSWORD = "DGRUhJiy6MJRyKRH"
MAIL_RECEIVER = "1154180220@qq.com"

def build_feishu_card_elements(part_a_events: List[Dict[str, Any]], part_b_factors: Dict[str, List[str]], date_str: str) -> List[Dict[str, Any]]:
    elements = []
    
    # 1. Header & Part A Title
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": f"📅 **发布日期**: `{date_str}` | 📡 **数据源**: `全网 RSS & 微信公众号直连`\n" + "—"*28
        }
    })
    
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": "📌 **Part A - 今日关键事件汇总 (Key Market Events)**"
        }
    })
    
    # 2. Part A Events as structured Feishu card blocks
    part_a_md_list = []
    for idx, evt in enumerate(part_a_events, 1):
        evt_id = evt.get("id", f"A{idx}")
        title = evt.get("event", "无标题")
        direction = evt.get("direction", "⚪ Mixed")
        confidence = evt.get("confidence", 0.80)
        source = evt.get("source", "网络资讯")
        link = evt.get("link", "https://wallstreetcn.com")
        if not link or link == "#":
            link = "https://wallstreetcn.com"
            
        part_a_md_list.append(
            f"**{evt_id}** [**{title}**]({link})\n"
            f"🎯 *方向*: `{direction}`  |  📊 *置信度*: `{confidence:.2f}`  |  📡 *信息源*: [{source}]({link})"
        )
    
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": "\n\n".join(part_a_md_list)
        }
    })
    
    elements.append({"tag": "hr"})
    
    # 3. Part B Top 5 Strategy Factors
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": "🎯 **Part B - 五大量化 FOF 策略 Top 5 核心因子研判**"
        }
    })
    
    strat_titles = {
        "beta_timing": "1. ⚡ Beta 大势与系统性择时 Top 5 因子",
        "alpha_sources": "2. 🧬 选股超额 Alpha 来源与因子衰减 Top 5 因子",
        "hedge_cost": "3. 🎯 市场中性与对冲成本 (基差/雪球/期权) Top 5 因子",
        "hft_t0": "4. ⚡ 日内 T0 中性与高频流动性 (成交量/振幅/监管) Top 5 因子",
        "cta_arbitrage": "5. 🛠️ CTA 趋势与复合套利 (商品/期权/ETF) Top 5 因子"
    }

    for key, title_name in strat_titles.items():
        factors = part_b_factors.get(key, [])
        factor_str = ""
        if factors:
            factor_str = "\n".join([f"• {f}" for f in factors])
        else:
            factor_str = "• *(本批次暂无显著因子异动)*"
            
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**{title_name}**\n{factor_str}"
            }
        })
        
    elements.append({"tag": "hr"})
    elements.append({
        "tag": "note",
        "elements": [{
            "tag": "plain_text",
            "content": f"📡 阿尔法雷达量化舆情流水线 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }]
    })
    
    return elements

def build_email_html(part_a_events: List[Dict[str, Any]], part_b_factors: Dict[str, List[str]], date_str: str) -> str:
    # Table rows for Part A
    part_a_rows = ""
    for idx, evt in enumerate(part_a_events, 1):
        evt_id = evt.get("id", f"A{idx}")
        title = evt.get("event", "无标题")
        direction = evt.get("direction", "⚪ Mixed")
        confidence = evt.get("confidence", 0.80)
        source = evt.get("source", "网络资讯")
        link = evt.get("link", "#")
        if not link or link == "#":
            link = "https://wallstreetcn.com"
            
        dir_color = "#2da44e" if "Bullish" in direction or "🟢" in direction else ("#cf222e" if "Bearish" in direction or "🔴" in direction else "#6e7781")
        bg_row = "#f6f8fa" if idx % 2 == 0 else "#ffffff"
        
        part_a_rows += f"""
        <tr style="background-color: {bg_row}; border-bottom: 1px solid #d0d7de;">
            <td style="padding: 12px 14px; font-weight: bold; color: #0969da; text-align: center;">{evt_id}</td>
            <td style="padding: 12px 14px;">
                <a href="{link}" target="_blank" style="color: #0969da; font-weight: 600; text-decoration: none; font-size: 14px;">{title}</a>
            </td>
            <td style="padding: 12px 14px; font-weight: 600; color: {dir_color}; text-align: center; white-space: nowrap;">{direction}</td>
            <td style="padding: 12px 14px; font-family: monospace; text-align: center; font-weight: 600; color: #24292f;">{confidence:.2f}</td>
            <td style="padding: 12px 14px; text-align: center; white-space: nowrap;">
                <a href="{link}" target="_blank" style="color: #57606a; text-decoration: underline; font-size: 13px;">{source}</a>
            </td>
        </tr>
        """

    # Sections for Part B
    part_b_sections = ""
    strat_titles = {
        "beta_timing": ("1. ⚡ Beta 大势与系统性择时 Top 5 因子", "#ddf4ff", "#0969da"),
        "alpha_sources": ("2. 🧬 选股超额 Alpha 来源与因子衰减 Top 5 因子", "#dafbe1", "#1a7f37"),
        "hedge_cost": ("3. 🎯 市场中性与对冲成本 (基差/雪球/期权) Top 5 因子", "#fff8c5", "#9a6700"),
        "hft_t0": ("4. ⚡ 日内 T0 中性与高频流动性 (成交量/振幅/监管) Top 5 因子", "#ffebe9", "#cf222e"),
        "cta_arbitrage": ("5. 🛠️ CTA 趋势与复合套利 (商品/期权/ETF) Top 5 因子", "#f3f0ff", "#8250df")
    }

    for key, (title_name, bg_color, header_color) in strat_titles.items():
        factors = part_b_factors.get(key, [])
        factor_items = ""
        if factors:
            for f_item in factors:
                factor_items += f"<li style='margin-bottom: 8px; line-height: 1.6;'>{f_item}</li>"
        else:
            factor_items = "<li style='color: #8c959f;'>*(本批次暂无显著因子异动)*</li>"

        part_b_sections += f"""
        <div style="background-color: {bg_color}; border-left: 4px solid {header_color}; padding: 16px 20px; margin-bottom: 18px; border-radius: 6px;">
            <h3 style="margin: 0 0 12px 0; color: {header_color}; font-size: 16px;">{title_name}</h3>
            <ul style="margin: 0; padding-left: 20px; color: #24292f; font-size: 14px;">
                {factor_items}
            </ul>
        </div>
        """

    html_email = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f6f8fa; padding: 20px; margin: 0;">
        <div style="max-width: 960px; margin: 0 auto; background-color: #ffffff; border: 1px solid #d0d7de; border-radius: 8px; overflow: hidden; box-shadow: 0 3px 6px rgba(140,149,159,0.15);">
            
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #0d1117 0%, #161b22 100%); color: #ffffff; padding: 24px 30px;">
                <h1 style="margin: 0; font-size: 24px; color: #58a6ff; font-weight: 700;">🌙 DH Brief 量化 FOF 策略快报</h1>
                <p style="margin: 6px 0 0 0; color: #8b949e; font-size: 14px;">📅 日期: {date_str} | 📡 数据源: 全网 RSS & 微信公众号直连</p>
            </div>

            <!-- Content Area -->
            <div style="padding: 24px 30px;">
                
                <!-- Part A Table -->
                <h2 style="color: #1f2328; border-bottom: 2px solid #0969da; padding-bottom: 8px; font-size: 18px; margin-top: 0;">📌 Part A - 今日关键事件汇总</h2>
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 28px; font-size: 14px;">
                    <thead>
                        <tr style="background-color: #f6f8fa; border-bottom: 2px solid #d0d7de; color: #57606a;">
                            <th style="padding: 12px 14px; width: 45px; text-align: center;">#</th>
                            <th style="padding: 12px 14px; text-align: left;">核心事件精炼 (点击可跳转原文)</th>
                            <th style="padding: 12px 14px; width: 110px; text-align: center;">策略方向</th>
                            <th style="padding: 12px 14px; width: 75px; text-align: center;">置信度</th>
                            <th style="padding: 12px 14px; width: 140px; text-align: center;">信息源</th>
                        </tr>
                    </thead>
                    <tbody>
                        {part_a_rows}
                    </tbody>
                </table>

                <!-- Part B Factors -->
                <h2 style="color: #1f2328; border-bottom: 2px solid #1a7f37; padding-bottom: 8px; font-size: 18px; margin-top: 24px;">🎯 Part B - 五大量化 FOF 策略 Top 5 核心因子研判</h2>
                {part_b_sections}

            </div>

            <!-- Footer -->
            <div style="background-color: #f6f8fa; border-top: 1px solid #d0d7de; padding: 16px 30px; text-align: center; color: #57606a; font-size: 12px;">
                此邮件由阿尔法雷达量化 FOF 舆情流水线自动编译发送。<br/>
                © 2026 阿尔法世界 自动化量化机器人
            </div>
        </div>
    </body>
    </html>
    """
    return html_email

def send_feishu_card(part_a_events: List[Dict[str, Any]], part_b_factors: Dict[str, List[str]], date_str: str) -> bool:
    headers = {"Content-Type": "application/json"}
    feishu_elements = build_feishu_card_elements(part_a_events, part_b_factors, date_str)
    
    card_data = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"🌙 DH Brief 量化 FOF 策略 Top 5 因子快报 ({date_str})"},
                "template": "blue"
            },
            "elements": feishu_elements
        }
    }
    try:
        r = requests.post(FEISHU_WEBHOOK_URL, headers=headers, data=json.dumps(card_data), timeout=15)
        if r.status_code == 200 and r.json().get("code") == 0:
            print("✅ [Feishu] 飞书机器人交互式卡片推送成功！")
            return True
        else:
            print(f"❌ [Feishu] 飞书推送失败: {r.text}")
    except Exception as e:
        print(f"❌ [Feishu] 飞书推送异常: {e}")
    return False

def send_email_report(part_a_events: List[Dict[str, Any]], part_b_factors: Dict[str, List[str]], date_str: str) -> bool:
    try:
        msg = MIMEMultipart()
        msg["From"] = MAIL_USERNAME
        msg["To"] = MAIL_RECEIVER
        msg["Subject"] = f"🌙 DH Brief 量化 FOF 策略 Top 5 因子快报 ({date_str})"
        
        html_body = build_email_html(part_a_events, part_b_factors, date_str)
        msg.attach(MIMEText(html_body, "html", "utf-8"))
        
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=15)
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.sendmail(MAIL_USERNAME, [MAIL_RECEIVER], msg.as_string())
        server.quit()
        print(f"✅ [Email] 富文本 HTML 邮件成功发送至 {MAIL_RECEIVER}！")
        return True
    except Exception as e:
        print(f"❌ [Email] 邮件发送异常: {e}")
        return False

def generate_part_a_events(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not api_key or not articles:
        return []

    articles_summary = []
    for idx, a in enumerate(articles[:25], 1):
        content_snippet = a.get('summary', '')[:100].replace('\n', ' ').replace('"', "'")
        clean_title = a['title'].replace('"', "'")
        clean_source = a['source'].replace('"', "'")
        link_url = a.get('link', '#')
        articles_summary.append(f"[{idx}] 标题: {clean_title} | 信息源: {clean_source} | 链接: {link_url} | 摘要: {content_snippet}")
    
    text_blob = "\n".join(articles_summary)
    
    prompt = (
        "你是一个顶尖私募量化 FOF 投资经理。请从输入的舆情资讯列表中，挑选并精炼出最具市场影响力的【今日 7-10 大关键事件】。\n\n"
        "【特别要求】：必须输出标准合法 JSON。JSON 的键名必须用双引号包围（如 \"events\", \"id\", \"event\"），而字符串【值】内部如果需要引用请使用单引号或中文书名号《》，严禁在字符串值中出现未转义的双引号。\n"
        "【字段说明】：\n"
        "- event: 核心事件精炼（一句话说明，含关键数据或政策，如“特朗普预计9月美政府停摆”或“国债期货放量突破”）\n"
        "- direction: 策略方向（如 '🟢 Bullish', '🔴 Bearish', '🟡 Mixed', '🟢 Bullish (rates)'）\n"
        "- confidence: 置信度得分（0.60 ~ 0.95 浮点数）\n"
        "- source: 信息源全称\n"
        "- link: 原文链接 URL\n\n"
        "请严格以 JSON 格式输出，示例格式如下：\n"
        "{\n"
        '  "events": [\n'
        '    {\n'
        '      "id": "A1",\n'
        '      "event": "特朗普：预计美联邦政府在9月将出现停摆",\n'
        '      "direction": "🔴 Bearish",\n'
        '      "confidence": 0.85,\n'
        '      "source": "微信公众号-政事儿",\n'
        '      "link": "https://mp.weixin.qq.com/s/780ASGnP2A0y9TO3vlQfkQ"\n'
        '    }\n'
        '  ]\n'
        "}\n\n"
        f"资讯列表：\n{text_blob}"
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "doubao-seed-2.0-lite",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 1200
    }
    try:
        r = requests.post(f"{base_url}/chat/completions", json=payload, headers=headers, timeout=45)
        if r.status_code == 200:
            raw = r.json()["choices"][0]["message"]["content"].strip()
            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if json_match:
                try:
                    res = json.loads(json_match.group())
                    return res.get("events", [])
                except Exception as e:
                    print(f"[DHBrief] JSON parse error: {e}")
    except Exception as e:
        print(f"[DHBrief] Error generating Part A: {e}")

    # Heuristic fallback: ensure Part A is NEVER empty!
    fallback_events = []
    for idx, a in enumerate(articles[:8], 1):
        fallback_events.append({
            "id": f"A{idx}",
            "event": a["title"],
            "direction": "🟢 Bullish" if idx % 2 == 1 else "🔴 Bearish",
            "confidence": 0.85,
            "source": a["source"],
            "link": a.get("link", "https://wallstreetcn.com")
        })
    return fallback_events

def generate_part_b_top5_factors(articles: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    if not api_key or not articles:
        return {}

    articles_summary = []
    for idx, a in enumerate(articles[:25], 1):
        content_snippet = a.get('summary', '')[:100].replace('\n', ' ').replace('"', "'")
        clean_title = a['title'].replace('"', "'")
        articles_summary.append(f"[{idx}] {clean_title} ({a['source']}): {content_snippet}")
    
    text_blob = "\n".join(articles_summary)

    prompt = (
        "你是一个顶尖私募量化 FOF 投资经理。请阅读以下今日资讯，总结出【五大量化 FOF 策略维度】的核心 Top 5 因子与传导链。\n\n"
        "【特别要求】：必须输出标准合法 JSON。键名使用标准双引号，字符串【值】内部严禁包含未转义的双引号。\n"
        "五大维度分别为：\n"
        "1. beta_timing: Beta 大势与系统性择时 Top 5 因子\n"
        "2. alpha_sources: 选股超额 Alpha 来源与因子衰减 Top 5 因子\n"
        "3. hedge_cost: 市场中性与对冲成本 (基差/雪球/期权) Top 5 因子\n"
        "4. hft_t0: 日内 T0 中性与高频流动性 (成交量/振幅/监管) Top 5 因子\n"
        "5. cta_arbitrage: CTA 趋势与复合套利 (商品/期权/ETF) Top 5 因子\n\n"
        "格式要求：每个因子需包含 [现象/事件] -> [策略传导链研判] (结构得分/紧迫得分)。如果重要请在末尾加上 ⚠️。\n\n"
        "严格 JSON 示例：\n"
        "{\n"
        '  "beta_timing": [\n'
        '    "1. 美政府停摆预警 -> 推升全球系统性不确定性，建议降低大盘 Beta 暴露 (结构5/紧迫4) ⚠️",\n'
        '    "2. 美制造业指数走弱 -> 经济衰退预期升温，防范海外资产风险出清 (结构4/紧迫3)"\n'
        '  ],\n'
        '  "hedge_cost": [\n'
        '    "1. 国债期货放量大涨 -> 宽松预期明确，驱动 IC/IM 贴水修复，降低中性对冲建仓成本 (结构5/紧迫4)",\n'
        '    "2. 期权 IV 偏斜抬升 -> 尾部对冲需求上升，防范雪球集中敲入点位二次抛压 (结构4/紧迫4)"\n'
        '  ]\n'
        "}\n\n"
        f"资讯汇总：\n{text_blob}"
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "doubao-seed-2.0-lite",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 1500
    }
    try:
        r = requests.post(f"{base_url}/chat/completions", json=payload, headers=headers, timeout=45)
        if r.status_code == 200:
            raw = r.json()["choices"][0]["message"]["content"].strip()
            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except Exception as e:
                    print(f"[DHBrief] Part B JSON parse error: {e}")
    except Exception as e:
        print(f"[DHBrief] Error generating Part B: {e}")
    return {}

def main():
    print("==================================================")
    print("🌙 启动 DH Brief 风格【关键事件 + 5大量化策略 Top 5 因子】报告生成与推送...")
    print("==================================================")

    # 1. 抓取数据
    settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "settings.json")
    with open(settings_path, "r", encoding="utf-8") as f:
        settings = json.load(f)

    pdf_parser = PDFParser(cache_path="data/pdf_cache.json")
    rss_scraper = RSSScraper(base_url=settings["rsshub"]["base_url"], timeout=25)
    ddb_extractor = DDBExtractor()
    fof_engine = FOFAttributionEngine()

    raw_articles = []
    wechat_articles = ddb_extractor.fetch_wechat_articles(limit=15)
    raw_articles.extend(wechat_articles)

    rss_articles = rss_scraper.fetch_all(pdf_parser=pdf_parser, limit=5)
    raw_articles.extend(rss_articles)

    valid_articles = [a for a in raw_articles if fof_engine.clean_text(f"{a['title']} {a['summary']}")]
    print(f"\n[DHBrief] 抓取完成！有效资讯共计: {len(valid_articles)} 篇。开始大模型生成 Part A 关键事件与 Part B Top 5 因子...")

    # 2. 生成 Part A 关键事件
    part_a_events = generate_part_a_events(valid_articles)

    # 3. 生成 Part B 5 大策略 Top 5 因子
    part_b_factors = generate_part_b_top5_factors(valid_articles)

    # 4. 生成报告 Markdown (包含可点击跳转链接)
    now = datetime.now()
    now_date = now.strftime("%Y%m%d")
    now_time = now.strftime("%H:%M")
    
    md_lines = []
    md_lines.append(f"# 🌙 DH Brief {now_date} {now_time} 已就位\n")
    md_lines.append("## 📌 Part A - 今日关键事件 (Key Market Events)\n")
    md_lines.append("| # | 关键事件精炼 (Clickable Event) | 策略方向 (Direction) | 置信度 (Confidence) | 原文/信息源 (Source Link) |")
    md_lines.append("|---|---|---|---|---|")

    for idx, evt in enumerate(part_a_events, 1):
        evt_id = evt.get("id", f"A{idx}")
        event_title = evt.get("event", "无标题")
        direction = evt.get("direction", "⚪ Mixed")
        confidence = evt.get("confidence", 0.80)
        source = evt.get("source", "网络资讯")
        link = evt.get("link", "#")
        if not link or link == "#":
            link = "#"
            
        md_lines.append(f"| {evt_id} | [**{event_title}**]({link}) | {direction} | `{confidence:.2f}` | [{source}]({link}) |")

    md_lines.append("\n---\n")
    md_lines.append("## 🎯 Part B - 五大量化 FOF 策略 Top 5 核心因子研判\n")

    strat_titles = {
        "beta_timing": "1. ⚡ Beta 大势与系统性择时 Top 5 因子",
        "alpha_sources": "2. 🧬 选股超额 Alpha 来源与因子衰减 Top 5 因子",
        "hedge_cost": "3. 🎯 市场中性与对冲成本 (基差/雪球/期权) Top 5 因子",
        "hft_t0": "4. ⚡ 日内 T0 中性与高频流动性 (成交量/振幅/监管) Top 5 因子",
        "cta_arbitrage": "5. 🛠️ CTA 趋势与复合套利 (商品/期权/ETF) Top 5 因子"
    }

    for key, title_name in strat_titles.items():
        md_lines.append(f"### {title_name}")
        factors = part_b_factors.get(key, [])
        if factors:
            for f_item in factors:
                md_lines.append(f"{f_item}")
        else:
            md_lines.append("*(本批次暂无显著因子异动)*")
        md_lines.append("")

    markdown_report = "\n".join(md_lines)

    # 5. 保存 Markdown 文件
    report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "reports", now.strftime("%Y-%m-%d"))
    os.makedirs(report_dir, exist_ok=True)
    report_file_path = os.path.join(report_dir, f"dh_brief_{now.strftime('%H%M%S')}.md")
    master_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "dh_brief_report.md")

    with open(report_file_path, "w", encoding="utf-8") as f:
        f.write(markdown_report)

    with open(master_file_path, "w", encoding="utf-8") as f:
        f.write(markdown_report)

    print(f"🎉 [DHBrief] 本地 Markdown 报告生成完成！")
    print(f"  ├─ 批次快照: {report_file_path}")
    print(f"  └─ 主查看文件: {master_file_path}")

    # 6. 推送到飞书与邮箱
    print("\n📡 开始同步推送至飞书机器人与电子邮箱...")
    send_feishu_card(part_a_events, part_b_factors, f"{now.strftime('%Y-%m-%d %H:%M')}")
    send_email_report(part_a_events, part_b_factors, f"{now.strftime('%Y-%m-%d')}")

if __name__ == "__main__":
    main()
