import os
import subprocess
import datetime
import base64
import time
import sys
import matplotlib.pyplot as plt

# --- 美化 CSS 樣式 (新增 details 標籤樣式) ---
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
            /* display: flex;  (不再需要 flex 佈局) */
        }
        .chart-container {
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
            width: 100%;
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
            word-wrap: break-word; /* 讓長字串可以換行 */
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
        }
        tr:has(td.status-fail) {
            background-color: #fbeaea;
        }
        tr:has(td.status-fail):hover {
            background-color: #f7e1e1;
        }
        .filepath {
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.9em;
            color: #555;
        }

        /*【新功能】可摺疊日誌的樣式 */
        details {
            border: 1px solid #ddd;
            padding: 8px;
            border-radius: 4px;
            background-color: #fafafa;
        }
        summary {
            font-weight: bold;
            cursor: pointer;
            color: #34495e;
        }
        details[open] {
            padding-bottom: 10px;
        }
        details pre {
            margin-top: 10px;
            white-space: pre-wrap;
            word-wrap: break-word;
            background-color: #f1f1f1;
            padding: 10px;
            border-radius: 4px;
            color: #333;
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


def execute_test_script(script_path, test_data_dir):
    """
    執行單一測試腳本，解析其輸出，並返回標準化的結果。
    """
    start_time = time.time()
    try:
        process = subprocess.run(
            f'python "{script_path}"',
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=30
        )
        output = process.stdout + process.stderr
    except subprocess.TimeoutExpired:
        output = "Test Failed: Script timed out after 30 seconds."
    except Exception as e:
        output = f"Test Failed: An unexpected error occurred while running the script: {e}"

    duration = f"{(time.time() - start_time):.3f}s"

    base_filename = os.path.basename(script_path).replace('.py', '.txt')
    test_data_file = os.path.join(test_data_dir, base_filename)
    expected_rtn_code = None
    try:
        with open(test_data_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content.startswith('RtnCode,'):
                expected_rtn_code = content.split(',')[1]
    except Exception:
        pass

    if 'Test Failed' in output:
        status = 'Fail'
        if expected_rtn_code == '0' and 'Decrypted Data:' in output:
            try:
                decrypted_part = output.split('Decrypted Data:')[1].strip()
                log_result = f"Decrypted Data: {decrypted_part}"
            except IndexError:
                log_result = "測試失敗 (期望 RtnCode 0)，但無法從輸出中解析 Decrypted Data。"
        else:
            fail_lines = [line for line in output.splitlines() if 'Test Failed' in line]
            if fail_lines:
                log_result = fail_lines[0].strip()
            else:
                log_result = "測試失敗，但無法提取具體的錯誤訊息。"
    else:
        status = 'Pass'
        log_result = 'N/A'

        if expected_rtn_code == '1':
            try:
                actual_rtn_msg = output.split("RtnMsg:")[1].splitlines()[0].strip()
                if actual_rtn_msg != "成功":
                    status = 'Fail'
                    log_result = f"測試失敗: RtnCode為1，但RtnMsg為「{actual_rtn_msg}」，不符合預期的「成功」。"
            except IndexError:
                status = 'Fail'
                log_result = "測試失敗: 腳本輸出中找不到 'RtnMsg:'，無法進行成功訊息驗證。"

    return (status, duration, log_result)


def generate_html_rows(test_results):
    """
    根據測試結果產生HTML表格的行。
    """
    rows = []
    for result, test, duration, log_result in test_results:
        status_class = result.lower()
        script_name = os.path.basename(test)

        log_html = f"<td>{log_result}</td>"
        if result == 'Fail' and len(log_result) > 80:
            log_html = f"""
            <td>
                <details>
                    <summary>查看日誌 (點擊展開)</summary>
                    <pre>{log_result}</pre>
                </details>
            </td>
            """

        rows.append(f"""
        <tr>
            <td class="status-{status_class}">{result}</td>
            <td class="filepath">{script_name}</td>
            <td>{duration}</td>
            {log_html}
        </tr>
        """)
    return ''.join(rows)


def main():
    """
    主執行函式
    """
    # --- 路徑設定 ---
    scripts_dir = 'C:\\icppython\\OTestCase\\ICPAPI'
    test_data_dir = 'C:\\icppython\\OTestData\\ICPAPI'
    report_dir = r'C:\icppython\icploginapireport'
    pre_test_scripts_paths = [
        'C:\\icppython\\M0001_1.py',
        'C:\\icppython\\M0007_2.py',
        'C:\\icppython\\M0005_3.py'
    ]

    # --- 環境檢查 ---
    if not os.path.isdir(scripts_dir):
        print(f"錯誤：測試案例目錄不存在: {scripts_dir}")
        sys.exit(1)

    # --- 前置腳本執行 ---
    print("--- 正在執行前置測試腳本 ---")
    for script_path in pre_test_scripts_paths:
        try:
            print(f"執行中: {script_path}")
            process = subprocess.run(f'python "{script_path}"', shell=True, capture_output=True, text=True,
                                     encoding='utf-8')
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

    # --- 執行主要測試 ---
    scripts = [os.path.join(scripts_dir, f) for f in os.listdir(scripts_dir) if f.endswith('.py')]
    test_results = []
    print("\n--- 正在執行主要API測試案例 ---")
    for script in scripts:
        print(f"正在測試: {os.path.basename(script)}")
        status, duration, log_result = execute_test_script(script, test_data_dir)
        test_results.append((status, script, duration, log_result))
    print("--- 所有測試執行完畢 ---\n")

    # --- 計算結果 ---
    pass_count = sum(1 for r in test_results if r[0] == 'Pass')
    fail_count = len(test_results) - pass_count
    total_count = len(test_results)
    pass_percentage = round(pass_count / total_count * 100, 2) if total_count > 0 else 0

    # --- 產生圖表 ---
    fig, ax = plt.subplots(figsize=(6, 6))
    if total_count > 0:
        pie_colors = ['#2ecc71', '#e74c3c']
        ax.pie([pass_count, fail_count], labels=['Pass', 'Fail'], autopct='%1.2f%%', colors=pie_colors,
               wedgeprops={'edgecolor': 'white', 'linewidth': 2}, textprops={'color': "black", 'fontsize': 12})
    ax.set_title('Pass/Fail Ratio', fontsize=16)

    chart_dir = os.path.join(os.getcwd(), 'apichart')
    os.makedirs(chart_dir, exist_ok=True)
    chart_path = os.path.join(chart_dir, f"chart_{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}.png")
    fig.savefig(chart_path, bbox_inches='tight', transparent=True)
    print(f"圖表已產生: {chart_path}")

    with open(chart_path, 'rb') as f:
        chart_data = base64.b64encode(f.read()).decode()

    # --- 產生HTML報告 ---
    table_rows_html = generate_html_rows(test_results)

    # ---【開始修改】調整 HTML 模板，將圖表移至表格下方 ---
    html_template = f"""
    <html>
    <head>
        <title>Test Report</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta charset="UTF-8">
        {styles}
    </head>
    <body>
        <div class="container">
            <h1>ICP API 測試報告</h1>
            <div class="summary-container">
                <div class="summary-box summary-total"><h3>總共腳本</h3><p>{total_count}</p></div>
                <div class="summary-box summary-pass"><h3>通過腳本</h3><p>{pass_count}</p></div>
                <div class="summary-box summary-fail"><h3>失敗腳本</h3><p>{fail_count}</p></div>
                <div class="summary-box summary-rate"><h3>通過比率</h3><p>{pass_percentage:.2f}%</p></div>
            </div>

            <div class="main-content">
                <div class="table-container">
                    <h2>詳細測試結果</h2>
                    <table>
                        <thead>
                            <tr>
                                <th style="width: 8%;">Result</th>
                                <th style="width: 22%;">Test Script</th>
                                <th style="width: 10%;">Duration</th>
                                <th>Log Result</th>
                            </tr>
                        </thead>
                        <tbody>{table_rows_html}</tbody>
                    </table>
                </div>
            </div>

            <div class="chart-container" style="margin: 40px auto 0; max-width: 600px;">
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
    # ---【結束修改】---

    # --- 儲存報告 ---
    os.makedirs(report_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_filename = f"report_{timestamp}.html"
    report_path = os.path.join(report_dir, report_filename)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_template)
    print(f"報告已產生: {report_path}")


if __name__ == '__main__':
    main()