#!/bin/bash

# 完整的量化舆情流水线运行脚本
# 包含邮件发送功能

PROJECT_DIR="/root/.openclaw/workspace/quant_sentiment_pipeline"
PYTHON_BIN="$PROJECT_DIR/venv/bin/python"
LOG_FILE="$PROJECT_DIR/data/run.log"

# 设置环境变量
export SMTP_SERVER="smtp.163.com"
export SMTP_PORT="465"
export MAIL_USERNAME="wuqiwen0571@163.com"
export MAIL_PASSWORD="DGRUhJiy6MJRyKRH"
export FEISHU_WEBHOOK="https://open.feishu.cn/open-apis/bot/v2/hook/fe1a567a-9bb4-4b7b-9fcf-ffe4076bec8f"

mkdir -p "$PROJECT_DIR/data"
mkdir -p "$PROJECT_DIR/data/factors"

echo "===========================================" >> "$LOG_FILE"
echo "Starting full pipeline run at: $(date)" >> "$LOG_FILE"
echo "===========================================" >> "$LOG_FILE"

# 执行全套 DH Brief 风格量化 FOF 策略流水线 (包含最新邮件与飞书推送)
"$PYTHON_BIN" -u "$PROJECT_DIR/generate_dh_brief.py" >> "$LOG_FILE" 2>&1

echo "Pipeline run completed at: $(date)" >> "$LOG_FILE"
echo "-------------------------------------------" >> "$LOG_FILE"

# 检查运行结果
if [ $? -eq 0 ]; then
    echo "✅ Pipeline completed successfully!"
    echo "📧 Email report should have been sent."
else
    echo "❌ Pipeline failed!"
    echo "Check $LOG_FILE for details."
fi