#!/bin/bash

# 完整的量化舆情流水线运行脚本（无DolphinDB版本）
# 仅使用公开RSS数据源，不连接私有数据库

PROJECT_DIR="/root/.openclaw/workspace/quant_sentiment_pipeline"
PYTHON_BIN="$PROJECT_DIR/venv/bin/python"
LOG_FILE="$PROJECT_DIR/data/run.log"

# 设置环境变量
export SMTP_SERVER="smtp.163.com"
export SMTP_PORT="465"
export MAIL_USERNAME="wuqiwen0571@163.com"
export MAIL_PASSWORD="***"
export FEISHU_WEBHOOK="https://open.feishu.cn/open-apis/bot/v2/hook/fe1a567a-9bb4-4b7b-9fcf-ffe4076bec8f"

mkdir -p "$PROJECT_DIR/data"
mkdir -p "$PROJECT_DIR/data/factors"

echo "===========================================" >> "$LOG_FILE"
echo "Starting full pipeline (NO DDB) run at: $(date)" >> "$LOG_FILE"
echo "===========================================" >> "$LOG_FILE"

# 执行流水线（无数据库版本）
"$PYTHON_BIN" -u "$PROJECT_DIR/src/pipeline_claude_no_ddb.py" >> "$LOG_FILE" 2>&1

echo "Pipeline run completed at: $(date)" >> "$LOG_FILE"
echo "-------------------------------------------" >> "$LOG_FILE"

# 检查运行结果
if [ $? -eq 0 ]; then
    echo "✅ Pipeline completed successfully!"
    echo "📧 Email report should have been sent."
    echo "💬 Feishu notification should have been sent."
else
    echo "❌ Pipeline failed!"
    echo "Check $LOG_FILE for details."
fi
