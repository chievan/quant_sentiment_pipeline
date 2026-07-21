#!/usr/bin/env python3
import requests
import json
from datetime import datetime

def send_feishu_notification(webhook_url, content):
    """发送飞书消息通知"""
    headers = {
        "Content-Type": "application/json"
    }
    
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
                    "content": "✅ 测试通知 - 量化舆情日报"
                },
                "template": "green"
            }
        }
    }
    
    try:
        response = requests.post(webhook_url, headers=headers, data=json.dumps(data))
        if response.status_code == 200 and response.json().get("code") == 0:
            print("✅ 飞书消息发送成功！")
            return True
        else:
            print(f"❌ 飞书消息发送失败：{response.text}")
            return False
    except Exception as e:
        print(f"❌ 飞书消息发送异常：{e}")
        return False

if __name__ == "__main__":
    webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/fe1a567a-9bb4-4b7b-9fcf-ffe4076bec8f"
    
    test_content = """
    🎉 **飞书消息推送测试成功！**
    
    🔹 **测试时间**：{}
    🔹 **功能状态**：飞书通知集成完成
    🔹 **运行频率**：每天09:00、12:50、16:30自动推送
    🔹 **通知内容**：
       • 每日舆情分析概览
       • 利好/利空风险提示
       • FOF投资策略归因
       • 完整数据下载链接
    
    💡 今天中午12:50就会收到第一份正式的舆情日报哦~
    """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    send_feishu_notification(webhook_url, test_content)