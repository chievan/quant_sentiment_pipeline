#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置环境变量
os.environ['SMTP_SERVER'] = 'smtp.163.com'
os.environ['SMTP_PORT'] = '465'
os.environ['MAIL_USERNAME'] = 'wuqiwen0571@163.com'
os.environ['MAIL_PASSWORD'] = 'DGRUhJiy6MJRyKRH'

# 创建测试数据文件
import pandas as pd
from datetime import datetime
today_str = datetime.now().strftime("%Y-%m-%d")

# 创建测试数据
test_data = {
    'timestamp': [f'{today_str} 10:00:00', f'{today_str} 10:30:00'],
    'pub_date': [f'{today_str} 09:00:00', f'{today_str} 09:30:00'],
    'source': ['微信公众号', '东方财富-策略'],
    'title': ['测试文章1: 量化投资前景分析', '测试文章2: 市场情绪观察'],
    'link': ['https://example.com/1', 'https://example.com/2'],
    'score_finnlp': [0.8, -0.3],
    'channel_finnlp': ['finance_zh', 'finance_zh'],
    'score_finbert': [0.7, -0.2],
    'channel_finbert': ['finbert-base-zh', 'finbert-base-zh'],
    'score_gemini': [0.6, -0.1],
    'channel_gemini': ['Gemini-API', 'Gemini-API'],
    'fof_strategy': ['STYLE_FACTOR,BETA_TIMING', 'HEDGE_COST,HFT_REGULATION'],
    'fof_keywords': ['量化,风格切换', '基差,对冲成本']
}

df = pd.DataFrame(test_data)

# 确保目录存在
os.makedirs('data/factors', exist_ok=True)

# 保存测试数据
current_month_str = datetime.now().strftime("%Y%m")
target_csv = f'data/factors/sentiment_factors_{current_month_str}.csv'
df.to_csv(target_csv, index=False)
print(f"测试数据已保存到: {target_csv}")

# 导入邮件发送模块
from src.utils.send_email import send_email

print("开始测试邮件发送...")
result = send_email()

if result:
    print("✅ 邮件发送测试成功！")
else:
    print("❌ 邮件发送测试失败！")