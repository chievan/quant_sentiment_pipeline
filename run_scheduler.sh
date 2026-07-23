#!/bin/bash

# Independent Quant Sentiment Pipeline Scheduler Script
# Can be scheduled in crontab (e.g., every 2 hours: 0 */2 * * *)
# 0 */2 * * * /Users/chievan/Documents/projects/quant_sentiment_pipeline/run_scheduler.sh >> /Users/chievan/Documents/projects/quant_sentiment_pipeline/data/scheduler.log 2>&1

PROJECT_DIR="/Users/chievan/Documents/projects/quant_sentiment_pipeline"
PYTHON_BIN="/Users/chievan/Documents/projects/private-fund-pro/venv/bin/python"
LOG_FILE="$PROJECT_DIR/data/run.log"

mkdir -p "$PROJECT_DIR/data"

echo "===========================================" >> "$LOG_FILE"
echo "Starting scheduler run at: $(date)" >> "$LOG_FILE"
echo "===========================================" >> "$LOG_FILE"

# Execute DH Brief pipeline
"$PYTHON_BIN" -u "$PROJECT_DIR/generate_dh_brief.py" >> "$LOG_FILE" 2>&1

echo "Scheduler run completed at: $(date)" >> "$LOG_FILE"
echo "-------------------------------------------" >> "$LOG_FILE"
