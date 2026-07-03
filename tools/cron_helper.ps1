# cron_helper.ps1 — 生成把 Skill 加入 Windows 任务计划程序（schtasks）的命令
#
# 用法：
#   powershell -File tools\cron_helper.ps1 <skill路径> <HH:mm> [-Weekdays] [-EveryMinutes N]
#
# 示例：
#   # 每天 09:00 运行
#   powershell -File tools\cron_helper.ps1 skills/my_skill 09:00
#
#   # 每个工作日 09:00 运行
#   powershell -File tools\cron_helper.ps1 skills/my_skill 09:00 -Weekdays
#
#   # 每 30 分钟运行一次
#   powershell -File tools\cron_helper.ps1 skills/my_skill -EveryMinutes 30

param(
    [Parameter(Position = 0)] [string]$SkillPath,
    [Parameter(Position = 1)] [string]$Time,
    [switch]$Weekdays,
    [int]$EveryMinutes = 0
)

if (-not $SkillPath -or (-not $Time -and $EveryMinutes -eq 0)) {
    Get-Content $PSCommandPath | Select-Object -First 14 | ForEach-Object { $_ -replace '^#\s?', '' }
    exit 0
}

$ProjectRoot = Split-Path -Parent $PSScriptRoot

# 优先用项目 venv 里的 python
$PythonBin = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonBin)) { $PythonBin = "python" }

$TaskName = "RPA-Everything\" + ($SkillPath -replace '[/\\]', '_')
$LogDir = Join-Path $ProjectRoot "logs"
# cmd /c 包一层以支持输出重定向（schtasks 本身不支持）
$Action = "cmd /c `"cd /d $ProjectRoot && $PythonBin run.py $SkillPath >> $LogDir\schtasks.log 2>&1`""

if ($EveryMinutes -gt 0) {
    $Schedule = "/SC MINUTE /MO $EveryMinutes"
} elseif ($Weekdays) {
    $Schedule = "/SC WEEKLY /D MON,TUE,WED,THU,FRI /ST $Time"
} else {
    $Schedule = "/SC DAILY /ST $Time"
}

$Command = "schtasks /Create /TN `"$TaskName`" /TR '$Action' $Schedule /F"

Write-Host ""
Write-Host "=========================================="
Write-Host "以下是生成的 schtasks 命令，在管理员 PowerShell 中执行："
Write-Host "=========================================="
Write-Host ""
Write-Host $Command
Write-Host ""
Write-Host "提示："
Write-Host "  1. 执行后可用 schtasks /Query /TN `"$TaskName`" 查看任务"
Write-Host "  2. 删除任务：schtasks /Delete /TN `"$TaskName`" /F"
Write-Host "  3. 日志输出到 $LogDir\schtasks.log"
Write-Host ""
