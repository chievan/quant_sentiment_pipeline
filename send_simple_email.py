#!/usr/bin/env python3
import smtplib
import os
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

def send_simple_email():
    # 邮件配置
    smtp_server = 'smtp.163.com'
    smtp_port = 465
    mail_username = 'wuqiwen0571@163.com'
    mail_password = 'DGRUhJiy6MJRyKRH'
    receiver = '1154180220@qq.com'
    
    # 创建邮件
    msg = MIMEMultipart()
    msg['From'] = mail_username
    msg['To'] = receiver
    msg['Subject'] = f'📡 阿尔法雷达量化舆情日报 ({datetime.now().strftime("%Y-%m-%d")})'
    
    # 邮件正文
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # 读取CSV文件
    csv_path = '/root/.openclaw/workspace/quant_sentiment_pipeline/data/factors/sentiment_factors_202607.csv'
    
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            # 获取今天的记录
            df_today = df[df['timestamp'].str.startswith(today_str)]
            
            if len(df_today) > 0:
                # 生成简单报告
                report = f"""
                <html>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2 style="color: #1a73e8;">📡 阿尔法雷达量化舆情日报</h2>
                    <p><strong>报告日期：</strong>{today_str}</p>
                    <p><strong>分析文章数：</strong>{len(df_today)}篇</p>
                    
                    <h3>📊 今日舆情概览</h3>
                    <table border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse; width: 100%;">
                        <tr style="background-color: #f2f2f2;">
                            <th>来源</th>
                            <th>标题</th>
                            <th>FinNLP评分</th>
                            <th>Claude评分</th>
                            <th>FOF策略</th>
                        </tr>
                """
                
                # 添加数据行（最多10条）
                for i, row in df_today.head(10).iterrows():
                    report += f"""
                        <tr>
                            <td>{row['source']}</td>
                            <td>{row['title'][:50]}...</td>
                            <td style="color: {'green' if row['score_finnlp'] > 0 else 'red' if row['score_finnlp'] < 0 else 'gray'}">
                                {row['score_finnlp']:.4f}
                            </td>
                            <td style="color: {'green' if row.get('score_claude', 0) > 0 else 'red' if row.get('score_claude', 0) < 0 else 'gray'}">
                                {row.get('score_claude', 0):.4f if 'score_claude' in row else 'N/A'}
                            </td>
                            <td>{row['fof_strategy'][:30] if pd.notna(row['fof_strategy']) else ''}...</td>
                        </tr>
                    """
                
                report += """
                    </table>
                    
                    <div style="margin-top: 30px; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">
                        <h3>📈 情感评分分布</h3>
                        <p><strong>正面文章：</strong>{pos_count}篇</p>
                        <p><strong>负面文章：</strong>{neg_count}篇</p>
                        <p><strong>中性文章：</strong>{neu_count}篇</p>
                    </div>
                    
                    <p style="color: #666; font-size: 12px; margin-top: 30px;">
                        详细数据请查看附件CSV文件<br/>
                        此报告由阿尔法雷达量化舆情流水线自动生成并发送<br/>
                        © 2026 阿尔法世界 自动化量化机器人
                    </p>
                </body>
                </html>
                """.format(
                    pos_count=len(df_today[df_today['score_finnlp'] > 0.1]),
                    neg_count=len(df_today[df_today['score_finnlp'] < -0.1]),
                    neu_count=len(df_today[(df_today['score_finnlp'] >= -0.1) & (df_today['score_finnlp'] <= 0.1)])
                )
                
                msg.attach(MIMEText(report, 'html', 'utf-8'))
                
                # 添加附件
                with open(csv_path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename="sentiment_factors_{today_str}.csv"')
                    msg.attach(part)
                    
            else:
                # 没有今天的数据
                body = f"""
                <html>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2 style="color: #1a73e8;">📡 阿尔法雷达量化舆情日报</h2>
                    <p><strong>报告日期：</strong>{today_str}</p>
                    <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px;">
                        <p>⚠️ 今日暂无新的舆情数据，请检查数据源连接。</p>
                        <p>历史数据文件已作为附件发送。</p>
                    </div>
                </body>
                </html>
                """
                msg.attach(MIMEText(body, 'html', 'utf-8'))
                
                # 添加历史附件
                with open(csv_path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename="sentiment_factors_historical.csv"')
                    msg.attach(part)
                    
        except Exception as e:
            print(f"读取CSV文件失败: {e}")
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #1a73e8;">📡 阿尔法雷达量化舆情日报</h2>
                <p><strong>报告日期：</strong>{today_str}</p>
                <div style="background-color: #f8d7da; padding: 15px; border-radius: 5px;">
                    <p>❌ 生成报告时出错: {e}</p>
                </div>
            </body>
            </html>
            """
            msg.attach(MIMEText(body, 'html', 'utf-8'))
    else:
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #1a73e8;">📡 阿尔法雷达量化舆情日报</h2>
            <p><strong>报告日期：</strong>{today_str}</p>
            <div style="background-color: #f8d7da; padding: 15px; border-radius: 5px;">
                <p>❌ 未找到数据文件: {csv_path}</p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html', 'utf-8'))
    
    # 发送邮件
    try:
        print(f"正在连接到SMTP服务器: {smtp_server}:{smtp_port}...")
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        
        print("正在登录邮箱...")
        server.login(mail_username, mail_password)
        
        print("正在发送邮件...")
        server.sendmail(mail_username, receiver, msg.as_string())
        server.quit()
        
        print(f"✅ 量化舆情日报发送成功！")
        print(f"📧 发件人: {mail_username}")
        print(f"📧 收件人: {receiver}")
        print(f"📊 数据文件: {csv_path}")
        print(f"⏰ 发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("💡 请检查QQ邮箱的收件箱、垃圾邮件箱")
        return True
        
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("开始发送量化舆情日报...")
    print("=" * 50)
    send_simple_email()