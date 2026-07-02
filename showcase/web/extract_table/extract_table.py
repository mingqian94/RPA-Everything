"""
[Showcase / Web / 通用]
Skill: 从网页表格提取数据并保存为 CSV

适用场景：
  任何需要登录的 Web 系统，只要有 HTML 表格（<table> 标签），
  就能提取数据，无需针对特定系统写代码。

前提：
  Chrome 以 --remote-debugging-port=9222 启动，并已在浏览器中登录目标系统。

用法：
  # 提取当前页面的第一张表格
  python run.py showcase/web/extract_table/extract_table

  # 指定 URL 和过滤关键词
  python run.py showcase/web/extract_table/extract_table -- \\
    --url "https://your-system.com/list" \\
    --filter "2024" \\
    --output result.csv
"""

import argparse
import csv
import json
import sys
from pathlib import Path

from core.browser import open_page
from core.logger import SkillLogger
from core.config import get


def main():
    parser = argparse.ArgumentParser(description="从网页表格提取数据")
    parser.add_argument("--url", default="", help="目标页面 URL（不填则使用当前浏览器页面）")
    parser.add_argument("--filter", default="", help="在搜索框中输入的过滤关键词（可选）")
    parser.add_argument("--search-selector", default="input[type=search], input[placeholder*='搜索'], input[placeholder*='查询']",
                        help="搜索框 CSS 选择器（默认自动猜测）")
    parser.add_argument("--table-index", type=int, default=0, help="提取第几张表格（从 0 开始，默认 0）")
    parser.add_argument("--output", default="", help="保存路径（.csv），不填则只打印到终端")
    try:
        sep = sys.argv.index("--")
        argv = sys.argv[sep + 1:]
    except ValueError:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)

    log = SkillLogger("web/extract_table")

    async def _run():
        target_url = args.url or get("systems.crm.url") or ""

        async with open_page(target_url or None) as page:
            if target_url:
                log.step(f"打开页面：{target_url}")
                await page.wait_for_load_state("networkidle")
            else:
                log.step(f"使用当前页面：{page.url}")

            # 可选：输入过滤关键词
            if args.filter:
                try:
                    search_box = await page.wait_for_selector(args.search_selector, timeout=3000)
                    await search_box.fill(args.filter)
                    await page.keyboard.press("Enter")
                    await page.wait_for_load_state("networkidle")
                    log.step(f"已过滤：{args.filter}")
                except Exception:
                    log.step("未找到搜索框，跳过过滤")

            # 提取表格数据
            tables = await page.evaluate("""
                (tableIndex) => {
                    const tables = document.querySelectorAll('table');
                    if (!tables[tableIndex]) return null;
                    const table = tables[tableIndex];
                    const rows = Array.from(table.querySelectorAll('tr'));
                    return rows.map(row =>
                        Array.from(row.querySelectorAll('th, td')).map(cell => cell.innerText.trim())
                    ).filter(row => row.some(cell => cell));
                }
            """, args.table_index)

            if not tables:
                log.finish({"error": "页面上未找到表格"})
                print("未找到表格，请检查 --table-index 或页面是否已加载。")
                return

            headers = tables[0]
            rows = tables[1:]
            log.step(f"提取到 {len(rows)} 行 × {len(headers)} 列")

            # 输出
            if args.output:
                output_path = Path(args.output)
                with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerows(tables)
                print(f"已保存到 {output_path.resolve()}")
                log.finish({"rows": len(rows), "output": str(output_path)})
            else:
                # 格式化打印
                data = [dict(zip(headers, row)) for row in rows]
                print(json.dumps(data, ensure_ascii=False, indent=2))
                log.finish({"rows": len(rows)})

            return [dict(zip(headers, row)) for row in rows]

    import asyncio
    return asyncio.run(_run())
