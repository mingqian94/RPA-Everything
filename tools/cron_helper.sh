#!/usr/bin/env bash
# cron_helper.sh — 快速生成将 Skill 加入系统 cron 所需的 crontab 行
#
# 用法：
#   sh tools/cron_helper.sh <skill路径> <cron表达式>
#
# 示例：
#   sh tools/cron_helper.sh skills/my_skill "0 9 * * 1-5"
#   sh tools/cron_helper.sh showcase/office/excel_toolkit/excel_toolkit "30 8 * * *"

SKILL_PATH="$1"
CRON_EXPR="$2"

# 推断项目根目录（脚本所在目录的上级）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
# 优先用项目 venv 里的 python，其次 Homebrew Python，最后系统 python3
if [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
elif [ -x "/opt/homebrew/bin/python3.12" ]; then
    PYTHON_BIN="/opt/homebrew/bin/python3.12"
else
    PYTHON_BIN="$(command -v python3)"
fi
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/cron_\$(date +%Y%m%d).log"

if [ -z "$SKILL_PATH" ] || [ -z "$CRON_EXPR" ]; then
    echo ""
    echo "用法："
    echo "  sh tools/cron_helper.sh <skill路径> <cron表达式>"
    echo ""
    echo "示例："
    echo "  # 每个工作日早上 9 点运行"
    echo "  sh tools/cron_helper.sh skills/my_skill \"0 9 * * 1-5\""
    echo ""
    echo "  # 每天 8:30 运行"
    echo "  sh tools/cron_helper.sh showcase/office/excel_toolkit/excel_toolkit \"30 8 * * *\""
    echo ""
    echo "cron 表达式格式：分 时 日 月 周"
    echo "  *      = 每（分/时/日/月/周）"
    echo "  1-5    = 周一到周五"
    echo "  */30   = 每 30 分钟"
    echo ""
    exit 0
fi

# 生成 crontab 行
CRON_LINE="$CRON_EXPR PYTHONPATH=$PROJECT_ROOT $PYTHON_BIN $PROJECT_ROOT/run.py $SKILL_PATH >> $LOG_FILE 2>&1"

echo ""
echo "=========================================="
echo "以下是生成的 crontab 行，复制后执行 crontab -e 粘贴："
echo "=========================================="
echo ""
echo "$CRON_LINE"
echo ""
echo "提示："
echo "  1. 执行 crontab -e 打开编辑器"
echo "  2. 把上面这行粘贴进去，保存退出"
echo "  3. 执行 crontab -l 可查看当前所有定时任务"
echo "  4. 日志输出到 $LOG_DIR/"
echo ""
