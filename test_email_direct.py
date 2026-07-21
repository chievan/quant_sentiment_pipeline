#!/usr/bin/env python3
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# 直接测试邮件发送
def send_test_email():
    # 邮件配置
    smtp_server = 'smtp.163.com'
    smtp_port = 465
    mail_username = 'wuqiwen0571@163.com'
    mail_password = 'DGRUhJiy6MJRyKRH'
    receiver = '1154180220@qq.com'  # 你的QQ邮箱
    
    # 创建邮件
    msg = MIMEMultipart()
    msg['From'] = mail_username
    msg['To'] = receiver
    msg['Subject'] = f'📡 测试邮件 - 量化舆情流水线 ({datetime.now().strftime("%Y-%m-%d %H:%M:%S")})'
    
    # 邮件正文
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #1a73e8;">📡 阿尔法雷达量化舆情测试邮件</h2>
        <p>这是一封测试邮件，用于验证量化舆情流水线的邮件发送功能。</p>
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3>测试信息：</h3>
            <ul>
                <li><strong>发送时间：</strong>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</li>
                <li><strong>发件人：</strong>{mail_username}</li>
                <li><strong>收件人：</strong>{receiver}</li>
                <li><strong>SMTP服务器：</strong>{smtp_server}:{smtp_port}</li>
            </ul>
        </div>
        <p>如果收到此邮件，说明邮件发送功能正常。</p>
        <p style="color: #666; font-size: 12px; margin-top: 30px;">
            此邮件由阿尔法雷达量化舆情流水线自动发送<br/>
            © 2026 阿尔法世界 自动化量化机器人
        </p>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(body, 'html', 'utf-8'))
    
    try:
        print(f"正在连接到SMTP服务器: {smtp_server}:{smtp_port}...")
        # 使用SSL连接（端口465）
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        
        print("正在登录邮箱...")
        server.login(mail_username, mail_password)
        
        print("正在发送邮件...")
        server.sendmail(mail_username, receiver, msg.as_string())
        server.quit()
        
        print(f"✅ 测试邮件发送成功！")
        print(f"📧 发件人: {mail_username}")
        print(f"📧 收件人: {receiver}")
        print(f"⏰ 发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("💡 请检查QQ邮箱的收件箱、垃圾邮件箱或订阅邮件文件夹")
        return True
        
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        print("可能的原因：")
        print("1. SMTP服务器或端口错误")
        print("2. 邮箱密码/授权码错误")
        print("3. 163邮箱需要开启SMTP服务")
        print("4. 网络连接问题")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("开始测试邮件发送功能...")
    print("=" * 50)
    send_test_email()