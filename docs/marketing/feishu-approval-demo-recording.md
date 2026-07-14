# 飞书审批案例录屏操作清单

目标：录制一个不超过 30 秒的演示 GIF，突出 RPA-Everything 的核心取舍：AI 负责探索和写脚本，稳定重复执行交给确定性脚本；飞书审批案例使用图像模板匹配，3/3 成功，18 秒完成，零 AI 调用。

## 录屏参数

- 时长：建议 20-30 秒，最长不超过 30 秒。
- 画面：终端为主，飞书审批窗口为辅；不要露出真实客户、公司、人员、审批内容或内部 URL。
- 重点：终端中必须能看到 `3/3`、`18s` 或 `18 seconds`、`zero AI calls` / `零 AI 调用` 这类结果输出。
- 输出：最终 GIF 控制在 10 MB 内，便于 GitHub README 直接渲染。
- 分辨率：建议录制 1280x720 或裁剪到终端 + 飞书窗口区域，避免全屏录制过大。

## 录制前准备

1. 准备一个无敏感信息的飞书审批测试环境，审批标题和申请人使用假数据。
2. 打开飞书桌面端，停在待审批列表或可快速进入待审批列表的位置。
3. 打开终端，进入 RPA-Everything 仓库根目录。
4. 确认模板图片已经准备好，例如 `assets/feishu/approve_btn.png`、`assets/feishu/confirm_btn.png`。
5. 确认脚本默认不会越权处理真实审批；正式审批动作只在你明确确认的测试数据上执行。

## 建议录屏脚本

1. 开场 2 秒：画面显示 README 或终端标题，说明这是飞书审批自动化演示。
2. 3-6 秒：终端展示运行命令，强调这是固定脚本，不是每次都让 AI 看屏幕点坐标。
3. 6-22 秒：脚本运行，飞书窗口中可以看到它定位审批入口、打开审批单、点击同意或确认。镜头保持稳定，不要快速切换窗口。
4. 22-27 秒：终端展示结果摘要：`passed 3/3`、`finished in 18 seconds`、`zero AI calls`。
5. 27-30 秒：停留在结果摘要上，让观众看清关键数字。

## 可用命令示例

实际仓库目前提供的是通用模板点击 showcase，可用它说明模板匹配路线；如果你已有本地飞书审批脚本，用同样的展示节奏替换下面命令。

```powershell
python run.py showcase/app/desktop/template_click/template_click -- --template assets/feishu/approve_btn.png --app "飞书"
```

如果使用专门审批脚本，建议让脚本最后打印类似摘要：

```text
Feishu approval automation
Passed: 3/3
Elapsed: 18 seconds
AI calls: 0
```

## GIF 压缩命令

使用 ffmpeg 生成调色板再压缩：

```bash
ffmpeg -i feishu-approval-demo.mp4 -vf "fps=12,scale=1280:-1:flags=lanczos,palettegen" palette.png
ffmpeg -i feishu-approval-demo.mp4 -i palette.png -filter_complex "fps=12,scale=1280:-1:flags=lanczos[x];[x][1:v]paletteuse" docs/media/demo.gif
```

如果安装了 gifski，通常体积和观感更好：

```bash
ffmpeg -i feishu-approval-demo.mp4 -vf "fps=12,scale=1280:-1:flags=lanczos" frame-%04d.png
gifski --fps 12 --quality 75 --width 1280 -o docs/media/demo.gif frame-*.png
```

压缩后检查文件大小：

```powershell
Get-Item docs\media\demo.gif | Select-Object Name,Length
```

如果超过 10 MB，优先把 `fps` 降到 10、`scale` 降到 960，或裁剪掉无关区域。
