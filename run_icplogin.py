import os
import subprocess
import datetime
import base64
import time
# import keyboard # 如果沒有用到可以移除，保持程式碼乾淨
import sys

import matplotlib.pyplot as plt

# --- 開始修改：美化 CSS 樣式 ---
# Define modern CSS styles for the report
styles = '''
    <style>
        /* 基本設定 */
        body {
            font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
            background-color: #f4f7f6;
            margin: 0;
            padding: 20px;
            color: #333;
        }
        /* 主要容器，卡片式設計 */
        .container {
            max-width: 1200px;
            margin: auto;
            background-color: #ffffff;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
        }
        /* 報告主標題 */
        h1 {
            text-align: center;
            color: #2c3e50;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 15px;
            margin-bottom: 25px;
        }

        /* 摘要資訊區塊 (Flexbox 佈局) */
        .summary-container {
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 30px;
            text-align: center;
        }
        .summary-box {
            padding: 20px;
            border-radius: 8px;
            flex-grow: 1;
            color: #fff;
            min-width: 150px;
        }
        .summary-total { background-color: #3498db; }
        .summary-pass { background-color: #2ecc71; }
        .summary-fail { background-color: #e74c3c; }
        .summary-rate { background-color: #9b59b6; }
        .summary-box h3 { margin: 0 0 10px 0; font-size: 1.2em; }
        .summary-box p { margin: 0; font-size: 2em; font-weight: bold; }

        /* 主要內容區塊 (圖表與表格) */
        .main-content {
            display: flex;
            flex-wrap: wrap;
            gap: 30px;
            align-items: flex-start;
        }
        .chart-container {
            flex: 1;
            min-width: 300px;
            text-align: center;
            padding: 20px;
            background: #fdfdfd;
            border-radius: 8px;
            border: 1px solid #eee;
        }
        .chart-container img {
            max-width: 100%;
            height: auto;
        }
        .table-container {
            flex: 2;
            min-width: 500px;
            overflow-x: auto; /* 確保在小螢幕上表格可以水平滾動 */
        }

        /* 表格樣式 */
        table {
            width: 100%;
            border-collapse: collapse;
            border-spacing: 0;
        }
        th, td {
            padding: 12px 15px;
            text-align: left;
            vertical-align: middle; /* 垂直置中 */
            border-bottom: 1px solid #e0e0e0;
        }
        th {
            background-color: #34495e;
            color: white;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        tr:nth-child(even) {
            background-color: #f8f9f9;
        }
        tr:hover {
            background-color: #e8f4f8;
        }

        /* 測試結果高亮 */
        .status-pass {
            color: #27ae60;
            font-weight: bold;
        }
        .status-fail {
            color: #c0392b;
            font-weight: bold;
            background-color: #fbeaea; /* 失敗的儲存格加上淡淡的背景色 */
        }
        .filepath {
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.9em;
            color: #555;
        }

        /* 頁尾 */
        .footer {
            text-align: center;
            margin-top: 40px;
            font-size: 0.9em;
            color: #888;
        }
    </style>
'''
# --- 結束修改：美化 CSS 樣式 ---


# Get a list of all .py files in the ICPAPI directory
scripts_dir = 'C:\\icppython\\OTestCase\\ICPAPI'
# Added a check to ensure the directory exists to prevent a crash
if not os.path.isdir(scripts_dir):
    print(f"錯誤：測試案例目錄不存在: {scripts_dir}")
    sys.exit(1)
scripts = [os.path.join(scripts_dir, f) for f in os.listdir(scripts_dir) if f.endswith('.py')]

# Initialize counters and empty list to store test results
pass_count = 0
fail_count = 0
test_results = []

# --- 前置腳本 (維持原樣) ---
pre_test_scripts = [
    'C:\\icppython\\M0001_1.py',
    'C:\\icppython\\M0007_2.py',
    'C:\\icppython\\M0005_3.py'
]
print("--- 正在執行前置測試腳本 ---")
for script_path in pre_test_scripts:
    try:
        print(f"執行中: {script_path}")
        process = subprocess.run(f'python {script_path}', shell=True, capture_output=True, text=True, encoding='utf-8')
        combined_output = process.stdout + process.stderr
        if 'M0005_3.py' in script_path and '驗證次數已滿，請隔日再使用 (RtnCode: 200032)' in combined_output:
            print(f"偵測到特定錯誤於 {script_path}，程式即將中止。")
            print(f"錯誤詳情: {combined_output.strip()}")
            sys.exit(1)
        if process.returncode != 0:
            print(f"執行 {script_path} 失敗，錯誤碼: {process.returncode}")
            print(f"完整輸出:\n{combined_output.strip()}")
        else:
            print(f"成功執行: {script_path}")
    except Exception as e:
        print(f"執行 {script_path} 時發生未預期的錯誤: {e}")
        sys.exit(1)
print("--- 前置測試腳本執行完畢 ---")
# --- 前置腳本結束 ---


# Run each script and record the result
for script in scripts:
    start_time = datetime.datetime.now()
    process = subprocess.run(f'python {script}', shell=True, capture_output=True, text=True, encoding='utf-8')
    end_time = datetime.datetime.now()
    duration = end_time - start_time
    # 格式化執行時間為 秒.毫秒
    duration_formatted = f"{duration.total_seconds():.3f}s"
    output = process.stdout
    if 'Test Failed' in output:
        fail_count += 1
        try:
            rtnmsg = output.split('RtnMsg:')[1].strip()
        except:
            rtnmsg = 'N/A'
        test_results.append(('Fail', script, duration_formatted, rtnmsg))
    else:
        pass_count += 1
        test_results.append(('Pass', script, duration_formatted, 'N/A'))

# Calculate total count and pass/fail percentages
total_count = len(scripts)
pass_percentage = round(pass_count / total_count * 100, 2) if total_count > 0 else 0
fail_percentage = round(fail_count / total_count * 100, 2) if total_count > 0 else 0

# Generate the pie chart
fig, ax = plt.subplots(figsize=(6, 6))
# 讓圖表更好看
pie_colors = ['#2ecc71', '#e74c3c']  # 使用與摘要卡片匹配的顏色
ax.pie([pass_count, fail_count], labels=['Pass', 'Fail'], autopct='%1.2f%%', colors=pie_colors,
       wedgeprops={'edgecolor': 'white', 'linewidth': 2}, textprops={'color': "black", 'fontsize': 12})
ax.set_title('Pass/Fail Ratio', fontsize=16)

# Save the chart to a file
chart_dir = os.path.join(os.getcwd(), 'apichart')
os.makedirs(chart_dir, exist_ok=True)
chart_path = os.path.join(chart_dir, f"chart_{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}.png")
fig.savefig(chart_path, bbox_inches='tight', transparent=True)  # 使用透明背景儲存
print(f"圖表已產生: {chart_path}")
# --- (您程式碼的其他部分...維持原樣) ---

# Read the chart as a base64-encoded string for embedding
with open(chart_path, 'rb') as f:
    chart_data = base64.b64encode(f.read()).decode()

# --- 開始修改：僅調整 HTML 模板中的區塊順序 ---
# Generate the HTML report with the new structure and styles
html_template = f"""
<html>
<head>
    <title>Test Report</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {styles}
</head>
<body>
    <div class="container">
        <h1>ICP API 測試報告</h1>

        <div class="summary-container">
            <div class="summary-box summary-total">
                <h3>總共腳本</h3>
                <p>{total_count}</p>
            </div>
            <div class="summary-box summary-pass">
                <h3>通過腳本</h3>
                <p>{pass_count}</p>
            </div>
            <div class="summary-box summary-fail">
                <h3>失敗腳本</h3>
                <p>{fail_count}</p>
            </div>
            <div class="summary-box summary-rate">
                <h3>通過比率</h3>
                <p>{pass_percentage:.2f}%</p>
            </div>
        </div>

        <div class="table-container">
            <h2>詳細測試結果</h2>
            <table>
                <thead>
                    <tr>
                        <th>Result</th>
                        <th>Test Script</th>
                        <th>Duration</th>
                        <th>Log Result</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join([f'<tr><td class="status-{result.lower()}">{result}</td><td class="filepath">{os.path.basename(test)}</td><td>{duration}</td><td>{log_result}</td></tr>' for result, test, duration, log_result in test_results])}
                </tbody>
            </table>
        </div>

        <div class="chart-container">
            <h2>測試結果比例</h2>
            <img src='data:image/png;base64,{chart_data}' alt='Pass/Fail Ratio Pie Chart'/>
        </div>
        <div class="footer">
            <p>Report generated on {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p>Thank you for reviewing the API Test Report!</p>
        </div>
    </div>
</body>
</html>
"""
# --- 結束修改：僅調整 HTML 模板中的區塊順序 ---

# Save the report to a new file with a timestamp in the specified directory
report_dir = r'C:\icppython\icploginapireport'
os.makedirs(report_dir, exist_ok=True)
timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
report_filename = f"report_{timestamp}.html"
report_path = os.path.join(report_dir, report_filename)

with open(report_path, 'w', encoding='utf-8') as f:
    f.write(html_template)
print(f"報告已產生: {report_path}")