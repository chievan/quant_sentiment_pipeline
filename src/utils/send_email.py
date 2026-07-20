import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import re
import smtplib
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from engine.fof_attribution import FOFAttributionEngine

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

    # Create email container
    msg = MIMEMultipart()
    msg["From"] = mail_username
    msg["To"] = receiver
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    msg["Subject"] = f"📡 阿尔法雷达量化舆情监测因子日报 ({today_str})"

    # Locate output factor file
    output_dir = "/Users/chievan/Documents/projects/quant_sentiment_pipeline/data/factors"
    # Fallback to local relative path if run inside Actions
    if not os.path.exists(output_dir):
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "factors")
        
    current_month_str = datetime.now().strftime("%Y%m")
    target_csv = os.path.join(output_dir, f"sentiment_factors_{current_month_str}.csv")

    # Generate FOF Report
    fof_report_md = ""
    fof_report_html = ""
    if os.path.exists(target_csv):
        try:
            df = pd.read_csv(target_csv)
            # Filter for rows processed today
            df_today = df[df['timestamp'].str.startswith(today_str)]
            if df_today.empty:
                df_today = df.tail(60) # fallback to last 60 items
            
            records = df_today.to_dict('records')
            os.environ['EXECUTION_TIME'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            fof_engine = FOFAttributionEngine()
            fof_report_md = fof_engine.generate_report(records)
            fof_report_html = render_html_report(fof_report_md)
        except Exception as e:
            print(f"[Email] Failed to generate FOF report: {e}")
            fof_report_md = "错误: 无法在发送前生成归因报告。\n" + str(e)
            fof_report_html = f"<p style='color:red;'>错误: 无法在发送前生成归因报告。{e}</p>"
    else:
        fof_report_md = "警告: 未能找到当日因子数据 CSV 附件，请检查服务器日志。"
        fof_report_html = "<p style='color:orange;'>警告: 未能找到当日因子数据 CSV 附件，请检查服务器日志。</p>"

    # Attach text alternative container
    text_container = MIMEMultipart('alternative')
    text_container.attach(MIMEText(fof_report_md, "plain", "utf-8"))
    if fof_report_html:
        text_container.attach(MIMEText(fof_report_html, "html", "utf-8"))
    msg.attach(text_container)
    
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

def render_html_report(md_text: str) -> str:
    # Convert markdown to basic premium HTML
    html = md_text
    
    lines = html.split("\n")
    html_lines = []
    
    in_list = False
    
    for line in lines:
        line_strip = line.strip()
        
        # Handle headers
        if line_strip.startswith("# "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h1 style='color: #1a73e8; border-bottom: 2px solid #e8f0fe; padding-bottom: 12px; margin-top: 30px; font-family: sans-serif;'>{line_strip[2:]}</h1>")
        elif line_strip.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h2 style='color: #202124; margin-top: 24px; border-left: 4px solid #1a73e8; padding-left: 10px; font-family: sans-serif;'>{line_strip[3:]}</h2>")
        elif line_strip.startswith("### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h3 style='color: #5f6368; margin-top: 18px; font-family: sans-serif;'>{line_strip[4:]}</h3>")
        # Handle blockquotes
        elif line_strip.startswith("> "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<blockquote style='background-color: #f8f9fa; border-left: 4px solid #dadce0; padding: 12px; margin: 16px 0; color: #5f6368; font-style: italic; font-family: sans-serif;'>{line_strip[2:]}</blockquote>")
        # Handle horizontal rule
        elif line_strip == "---":
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("<hr style='border: 0; border-top: 1px solid #e8f0fe; margin: 24px 0;'/>")
        # Handle bullet points
        elif line_strip.startswith("- ") or line_strip.startswith("* "):
            if not in_list:
                html_lines.append("<ul style='padding-left: 20px; margin-top: 8px;'>")
                in_list = True
            content = line_strip[2:]
            html_lines.append(f"<li style='margin-bottom: 8px; color: #3c4043; line-height: 1.6; font-family: sans-serif;'>{content}</li>")
        # Handle empty lines
        elif len(line_strip) == 0:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("<br/>")
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<p style='color: #3c4043; line-height: 1.6; font-family: sans-serif;'>{line_strip}</p>")
            
    if in_list:
        html_lines.append("</ul>")
        
    full_body = "".join(html_lines)
    
    # Replace inline styles for sentiment indicators
    full_body = full_body.replace("🟢 利好", "<span style='background-color: #e6f4ea; color: #137333; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 13px;'>🟢 利好</span>")
    full_body = full_body.replace("🔴 利空", "<span style='background-color: #fce8e6; color: #c5221f; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 13px;'>🔴 利空</span>")
    full_body = full_body.replace("⚪ 中性", "<span style='background-color: #f1f3f4; color: #5f6368; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 13px;'>⚪ 中性</span>")
    
    # Replace markdown code blocks like ` matched `
    full_body = re.sub(r'`([^`]+)`', r"<code style='background-color: #f1f3f4; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 13px; color: #a82354;'>\1</code>", full_body)
    
    # Wrap in a premium email container with max-width and background styling
    premium_html = f"""
    <html>
    <body style="margin: 0; padding: 0; background-color: #f4f6f9; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;">
        <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 800px; background-color: #ffffff; margin: 20px auto; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); overflow: hidden; border: 1px solid #e8f0fe;">
            <tr>
                <td style="padding: 40px 30px; background-color: #1a73e8; color: #ffffff; text-align: center;">
                    <span style="font-size: 28px; font-weight: bold; letter-spacing: 1px;">📡 ALPHA RADAR</span><br/>
                    <span style="font-size: 14px; opacity: 0.85; margin-top: 8px; display: inline-block;">私募量化 FOF 投资策略归因与决策建议报告</span>
                </td>
            </tr>
            <tr>
                <td style="padding: 30px; background-color: #ffffff;">
                    {full_body}
                </td>
            </tr>
            <tr>
                <td style="padding: 20px 30px; background-color: #f8f9fa; text-align: center; font-size: 12px; color: #9aa0a6; border-top: 1px solid #f1f3f4;">
                    此报告由阿尔法雷达自动化系统执行并发送。<br/>
                    © 2026 阿尔法世界 自动化量化机器人
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    return premium_html

if __name__ == "__main__":
    send_email()
