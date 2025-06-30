import os
import subprocess
import datetime
import base64
import time
import keyboard
import sys  # <--- 新增 import

import matplotlib.pyplot as plt

# Define CSS styles for the report
styles = '''
    <style>
        body{font-family:sans-serif;}
        h1{text-align:center;}
        table{border-collapse:collapse;margin:auto;width:80%;}
        th,td{border:1px solid black;padding:8px;text-align:left;vertical-align:top;}
        th{background-color:#b2c2bf;color:white;}
        tr:nth-child(even){background-color:#f2f2f2;}
    </style>
'''
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

# --- 開始修改 ---
# 定義並依序執行前置 Python 腳本
pre_test_scripts = [
    'C:\\icppython\\M0001_1.py',
    'C:\\icppython\\M0007_2.py',
    'C:\\icppython\\M0005_3.py'
]

print("--- 正在執行前置測試腳本 ---")
for script_path in pre_test_scripts:
    try:
        print(f"執行中: {script_path}")
        # 執行腳本，但不自動拋出例外，以便我們手動檢查輸出
        process = subprocess.run(f'python {script_path}', shell=True, capture_output=True, text=True, encoding='utf-8')

        # 組合標準輸出與錯誤輸出，方便搜尋
        combined_output = process.stdout + process.stderr

        # 檢查是否為 M0005_3.py 且包含特定錯誤訊息
        if 'M0005_3.py' in script_path and '驗證次數已滿，請隔日再使用 (RtnCode: 200032)' in combined_output:
            print(f"偵測到特定錯誤於 {script_path}，程式即將中止。")
            print(f"錯誤詳情: {combined_output.strip()}")
            sys.exit(1)  # 直接中斷整個程式

        # 檢查是否有其他錯誤 (非零返回碼)
        if process.returncode != 0:
            print(f"執行 {script_path} 失敗，錯誤碼: {process.returncode}")
            print(f"完整輸出:\n{combined_output.strip()}")
            # 可以在此決定是否也要因其他錯誤中止
            # sys.exit(1)
        else:
            print(f"成功執行: {script_path}")

    except Exception as e:
        print(f"執行 {script_path} 時發生未預期的錯誤: {e}")
        sys.exit(1)  # 如果連執行都出錯，也中止程式

print("--- 前置測試腳本執行完畢 ---")
# --- 結束修改 ---


# Run each script and record the result
for script in scripts:
    start_time = datetime.datetime.now()
    process = subprocess.run(f'python {script}', shell=True, capture_output=True, text=True, encoding='utf-8')
    end_time = datetime.datetime.now()
    duration = end_time - start_time
    output = process.stdout
    if 'Test Failed' in output:
        fail_count += 1
        # Get the RtnMsg from the error message
        try:
            rtnmsg = output.split('RtnMsg:')[1].strip()
        except:
            rtnmsg = 'N/A'
        # Append the test result to the list
        test_results.append(('Fail', script, str(duration), rtnmsg))
    else:
        pass_count += 1
        test_results.append(('Pass', script, str(duration), 'N/A'))

# Calculate total count and pass/fail percentages
total_count = len(scripts)
pass_percentage = round(pass_count / total_count * 100, 2) if total_count > 0 else 0
fail_percentage = round(fail_count / total_count * 100, 2) if total_count > 0 else 0

# Generate the pie chart
fig, ax = plt.subplots(figsize=(6, 6))
ax.pie([pass_percentage, fail_percentage], labels=['Pass', 'Fail'], autopct='%1.2f%%', colors=['#4CAF50', '#F44336'])
ax.set_title('Pass/Fail Ratio')

# Save the chart to a file
# Note: os.getcwd() is the directory where this script is run from.
chart_dir = os.path.join(os.getcwd(), 'apichart')
os.makedirs(chart_dir, exist_ok=True)
chart_path = os.path.join(chart_dir, f"chart_{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}.png")
fig.savefig(chart_path)
print(f"圖表已產生: {chart_path}")

# Read the chart as a base64-encoded string for embedding
with open(chart_path, 'rb') as f:
    chart_data = base64.b64encode(f.read()).decode()

# Generate the HTML report with the chart embedded
html_template = (f"""
<html>
<head>
<title>Test Report</title>
{styles}
</head>
<body>
<h1>ICP API New Test Report</h1>
<p><strong>Total Scripts:</strong> {total_count}</p>
<p><strong>Passed Scripts:</strong> {pass_count}</p>
<p><strong>Failed Scripts:</strong> {fail_count}</p>
<p><strong>Pass Percentage:</strong> {pass_percentage:.2f}%</p>
<p><strong>Fail Percentage:</strong> {fail_percentage:.2f}%</p>
<div style='text-align: center;'>
<img src='data:image/png;base64,{chart_data}'/>
</div>
<table>
<tr>
<th>Result</th>
<th>Test</th>
<th>Duration</th>
<th>Log Result</th>
</tr>
{''.join([f'<tr><td>{result}</td><td>{test}</td><td>{duration}</td><td>{log_result}</td></tr>' for result, test, duration, log_result in test_results])}
</table>
<p>Thank you for reviewing the API Test Report!</p>
</body>
</html>
""")

# Save the report to a new file with a timestamp in the specified directory
report_dir = r'C:\icppython\icploginapireport'
os.makedirs(report_dir, exist_ok=True)
timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
report_filename = f"report_{timestamp}.html"
report_path = os.path.join(report_dir, report_filename)

with open(report_path, 'w', encoding='utf-8') as f:
    f.write(html_template)
print(f"報告已產生: {report_path}")