# -*- coding: utf-8 -*-
"""
APK 版本更新歷史報告生成器

功能：
1. 讀取由 download_files.py 產生的 version_history.log 檔案。
2. 分析日誌內容，統計本週與本月的版本更新次數。
3. 生成兩個格式化的 HTML 報告檔案 (weekly_report.html, monthly_report.html)。
"""
import os
from datetime import datetime, timedelta
from collections import Counter

# --- 設定區 ---
# LOG_FILE_PATH 必須與監控腳本中的設定完全相同
LOG_FILE_PATH = r"C:\icppython\version_history.log"
WEEKLY_REPORT_PATH = r"C:\icppython\weekly_report.html"
MONTHLY_REPORT_PATH = r"C:\icppython\monthly_report.html"
# --- 設定結束 ---

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', 'Microsoft JhengHei', 'PingFang TC', sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f4f7f9;
            color: #333;
        }}
        .container {{
            max-width: 900px;
            margin: auto;
            background-color: #ffffff;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            padding: 30px;
        }}
        h1, h2 {{
            color: #1a237e;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 10px;
        }}
        h1 {{
            text-align: center;
            font-size: 2em;
        }}
        .summary {{
            background-color: #e8eaf6;
            border-left: 5px solid #3f51b5;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        .summary p {{
            margin: 5px 0;
            font-size: 1.1em;
        }}
        .summary b {{
            color: #3f51b5;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
            word-break: break-all;
        }}
        th {{
            background-color: #3f51b5;
            color: white;
            font-weight: bold;
        }}
        tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
        .no-data {{
            text-align: center;
            font-size: 1.2em;
            color: #757575;
            padding: 40px;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            font-size: 0.9em;
            color: #aaa;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <p style="text-align: center; color: #666;">報告生成時間: {generation_time}</p>

        <h2>更新摘要</h2>
        <div class="summary">
            {summary_content}
        </div>

        <h2>詳細記錄</h2>
        {table_content}

        <div class="footer">
            由 icash Pay APK 監控報告系統自動產生
        </div>
    </div>
</body>
</html>
"""


def read_log_file():
    """讀取並解析日誌檔案"""
    if not os.path.exists(LOG_FILE_PATH):
        print(f"錯誤：日誌檔案 '{LOG_FILE_PATH}' 不存在。請先執行監控腳本以產生記錄。")
        return []

    records = []
    with open(LOG_FILE_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split(', ')
            if len(parts) == 4:
                try:
                    record = {
                        "timestamp": datetime.strptime(parts[0], '%Y-%m-%d %H:%M:%S'),
                        "env": parts[1],
                        "old_file": parts[2],
                        "new_file": parts[3]
                    }
                    records.append(record)
                except ValueError:
                    print(f"警告：忽略格式錯誤的日誌行: {line.strip()}")
    return records


def generate_html_report(title, records, output_path):
    """根據範本與資料生成 HTML 報告"""

    # --- 生成摘要 ---
    if not records:
        summary_content = "<p>此期間內<b>無</b>任何版本更新記錄。</p>"
    else:
        total_updates = len(records)
        env_counts = Counter(r['env'] for r in records)

        summary_content = f"<p>總更新次數: <b>{total_updates}</b> 次</p>"
        summary_content += "<ul>"
        for env, count in env_counts.items():
            summary_content += f"<li>{env}: <b>{count}</b> 次</li>"
        summary_content += "</ul>"

    # --- 生成表格 ---
    if not records:
        table_content = "<p class='no-data'>無詳細記錄</p>"
    else:
        table_rows = ""
        for r in sorted(records, key=lambda x: x['timestamp'], reverse=True):
            table_rows += f"""
            <tr>
                <td>{r['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}</td>
                <td>{r['env']}</td>
                <td>{r['old_file']}</td>
                <td>{r['new_file']}</td>
            </tr>
            """
        table_content = f"""
        <table>
            <thead>
                <tr>
                    <th>更新時間</th>
                    <th>環境</th>
                    <th>舊檔名</th>
                    <th>新檔名</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
        """

    generation_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    html_output = HTML_TEMPLATE.format(
        title=title,
        generation_time=generation_time,
        summary_content=summary_content,
        table_content=table_content
    )

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_output)
    print(f"成功生成報告: {output_path}")


def main():
    """主執行函數"""
    all_records = read_log_file()
    if not all_records:
        return

    now = datetime.now()

    # --- 處理週報告 ---
    start_of_week = now - timedelta(days=now.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59)
    weekly_records = [r for r in all_records if start_of_week <= r['timestamp'] <= end_of_week]

    week_title = f"APK 版本更新週報 ({start_of_week.strftime('%Y/%m/%d')} - {end_of_week.strftime('%Y/%m/%d')})"
    generate_html_report(week_title, weekly_records, WEEKLY_REPORT_PATH)

    # --- 處理月報告 ---
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # 找到下個月的第一天，再減去一秒，即可得到這個月的最後一秒
    next_month = (start_of_month.replace(day=28) + timedelta(days=4)).replace(day=1)
    end_of_month = next_month - timedelta(seconds=1)
    monthly_records = [r for r in all_records if start_of_month <= r['timestamp'] <= end_of_month]

    month_title = f"APK 版本更新月報 ({now.strftime('%Y年%m月')})"
    generate_html_report(month_title, monthly_records, MONTHLY_REPORT_PATH)


if __name__ == "__main__":
    main()