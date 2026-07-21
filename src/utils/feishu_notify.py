#!/usr/bin/env python3
import requests
import json
import os
from datetime import datetime

FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK", "https://open.feishu.cn/open-apis/bot/v2/hook/fe1a567a-9bb4-4b7b-9fcf-ffe4076bec8f")

def send_feishu_report(total_articles, pos_count, neg_count, neu_count, top_pos=None, top_neg=None, hot_keywords=None, csv_path=None):
    """发送飞书舆情日报通知"""
    headers = {
        "Content-Type": "application/json"
    }
    
    # 计算占比
    total = total_articles if total_articles > 0 else 1
    pos_rate = f"{(pos_count / total * 100):.1f}%"
    neg_rate = f"{(neg_count / total * 100):.1f}%"
    neu_rate = f"{(neu_count / total * 100):.1f}%"
    
    # 情绪颜色
    if float(neg_rate.replace('%', '')) > 30:
        template = "red"
        title = "🔴 今日舆情偏负面，注意风险"
    elif float(pos_rate.replace('%', '')) > 30:
        template = "green"
        title = "🟢 今日舆情偏正面，机会较多"
    else:
        template = "blue"
        title = "📊 今日舆情整体中性"
    
    # 构建内容
    content = f"""
    ## {title}
    
    ### 📈 今日舆情概览
    | 指标 | 数值 | 占比 |
    |------|------|------|
    | 分析文章总数 | {total_articles}篇 | - |
    | 正面利好文章 | {pos_count}篇 | {pos_rate} |
    | 负面利空文章 | {neg_count}篇 | {neg_rate} |
    | 中性文章 | {neu_count}篇 | {neu_rate} |
    """
    
    # 添加top利好文章
    if top_pos and len(top_pos) > 0:
        content += "\n### 🟢 今日Top3利好文章\n"
        for i, article in enumerate(top_pos[:3], 1):
            score = article.get('score_claude', 0)
            title = article.get('title', '')[:30] + '...'
            content += f"{i}. **{title}** (评分: {score:.2f})\n"
    
    # 添加top利空文章
    if top_neg and len(top_neg) > 0:
        content += "\n### 🔴 今日Top3利空文章\n"
        for i, article in enumerate(top_neg[:3], 1):
            score = article.get('score_claude', 0)
            title = article.get('title', '')[:30] + '...'
            content += f"{i}. **{title}** (评分: {score:.2f})\n"
    
    # 添加热门关键词
    if hot_keywords and len(hot_keywords) > 0:
        content += "\n### 🔥 今日热门关键词\n"
        keyword_str = "、".join([f"`{kw}`" for kw in hot_keywords[:10]])
        content += f"{keyword_str}\n"
    
    # 重点提示
    content += f"""
    ### 🔔 重点提示
    {'⚠️  负面舆情占比较高，建议关注持仓风险' if float(neg_rate.replace('%', '')) > 30 else '✅  市场情绪整体平稳，可关注结构性机会'}
    
    ### 📎 附件信息
    完整CSV数据和详细分析报告已发送到你的邮箱：1154180220@qq.com
    包含所有文章的详细评分、情感标签、FOF策略归因等完整数据。
    """
    
    data = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": content
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"📡 阿尔法雷达量化舆情流水线 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        }
                    ]
                }
            ],
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📡 量化舆情日报 ({datetime.now().strftime('%Y-%m-%d')})"
                },
                "template": template
            }
        }
    }
    
    try:
        response = requests.post(FEISHU_WEBHOOK, headers=headers, data=json.dumps(data))
        if response.status_code == 200 and response.json().get("code") == 0:
            print("[Feishu] 飞书通知发送成功！")
            return True
        else:
            print(f"[Feishu] 飞书通知发送失败：{response.text}")
            return False
    except Exception as e:
        print(f"[Feishu] 飞书通知发送异常：{e}")
        return False