import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

def send_email():
    # Retrieve SMTP configurations from environment variables
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.163.com")
    try:
        smtp_port = int(os.environ.get("SMTP_PORT", "465"))
    except ValueError:
        smtp_port = 465
    
    mail_username = os.environ.get("MAIL_USERNAME")
    mail_password = os.environ.get("MAIL_PASSWORD")
    
    receiver = "1154180220@qq.com"
    
    if not mail_username or not mail_password:
        print("[Email] Error: MAIL_USERNAME or MAIL_PASSWORD environment variables not set.")
        return False

    print(f"[Email] Preparing message from {mail_username} to {receiver}...")
    
    # Create email container
    msg = MIMEMultipart()
    msg["From"] = mail_username
    msg["To"] = receiver
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    msg["Subject"] = f"📡 阿尔法雷达量化舆情监测因子日报 ({today_str})"
    
    body = f"""您好，
    
    阿尔法雷达量化舆情监测流水线已于云端 (GitHub Actions) 定时执行完毕。
    
    执行时间 (北京时间): {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    本次运行使用的模型: FinNLP 金融情感分析词典 (非LLM简单部署版本)
    
    最新的情绪因子记录已以附件形式发送，请查收。
    
    --
    阿尔法世界 自动化机器人
    """
    msg.attach(MIMEText(body, "plain", "utf-8"))
    
    # Locate output factor file
    output_dir = "/Users/chievan/Documents/projects/quant_sentiment_pipeline/data/factors"
    # Fallback to local relative path if run inside Actions
    if not os.path.exists(output_dir):
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "factors")
        
    current_month_str = datetime.now().strftime("%Y%m")
    target_csv = os.path.join(output_dir, f"sentiment_factors_{current_month_str}.csv")
    
    if os.path.exists(target_csv):
        print(f"[Email] Attaching factor CSV: {target_csv}")
        attachment = open(target_csv, "rb")
        
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        
        # Attach header with raw filename
        filename = os.path.basename(target_csv)
        part.add_header("Content-Disposition", f"attachment; filename= {filename}")
        msg.attach(part)
        attachment.close()
    else:
        print(f"[Email] Warning: Attachment file not found at {target_csv}. Sending plain email instead.")
        msg.attach(MIMEText("\n警告: 未能找到当日因子数据 CSV 附件，请检查服务器日志。", "plain", "utf-8"))
        
    # Send email via SMTP (support SSL/TLS)
    try:
        print(f"[Email] Connecting to SMTP server: {smtp_server}:{smtp_port}...")
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            
        server.login(mail_username, mail_password)
        text = msg.as_string()
        server.sendmail(mail_username, receiver, text)
        server.quit()
        print("[Email] Email sent successfully!")
        return True
    except Exception as e:
        print(f"[Email] Failed to send email: {e}")
        return False

if __name__ == "__main__":
    send_email()
