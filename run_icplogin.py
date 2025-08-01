import os
import subprocess
import datetime
import base64
import time
import sys
import matplotlib.pyplot as plt
import re
from multiprocessing import Pool, cpu_count  # 導入並行處理所需模組

# --- 美化 CSS 樣式 (維持不變) ---
styles = '''
    <style>
        /* Base styles are unchanged */
        body {
            font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
            background-color: #f4f7f6;
            margin: 0;
            padding: 20px;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: auto;
            background-color: #ffffff;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
        }
        h1 {
            text-align: center;
            color: #2c3e50;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 15px;
            margin-bottom: 25px;
        }
        /* Other general styles remain the same */
        .summary-container { display: flex; justify-content: space-around; flex-wrap: wrap; gap: 20px; margin-bottom: 30px; text-align: center; }
        .summary-box { padding: 20px; border-radius: 8px; flex-grow: 1; color: #fff; min-width: 150px; }
        .summary-total { background-color: #3498db; }
        .summary-pass { background-color: #2ecc71; }
        .summary-fail { background-color: #e74c3c; }
        .summary-rate { background-color: #9b59b6; }
        .summary-box h3 { margin: 0 0 10px 0; font-size: 1.2em; }
        .summary-box p { margin: 0; font-size: 2em; font-weight: bold; }
        .main-content { }
        .chart-container { text-align: center; padding: 20px; background: #fdfdfd; border-radius: 8px; border: 1px solid #eee; }
        .chart-container img { max-width: 100%; height: auto; }
        .table-container { width: 100%; overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; border-spacing: 0; }
        th, td { padding: 12px 15px; text-align: left; vertical-align: middle; border-bottom: 1px solid #e0e0e0; word-wrap: break-word; word-break: break-all; }
        th { background-color: #34495e; color: white; font-weight: bold; text-transform: uppercase; letter-spacing: 0.05em; }
        tr:nth-child(even) { background-color: #f8f9f9; }
        tr:hover { background-color: #e8f4f8; }
        .status-pass { color: #27ae60; font-weight: bold; }
        .status-fail { color: #c0392b; font-weight: bold; }
        tr:has(td.status-fail) { background-color: #fbeaea; }
        tr:has(td.status-fail):hover { background-color: #f7e1e1; }
        .filepath {
            font-size: 0.95em;
            color: #555;
            line-height: 1.5;
        }

        .script-id {
            color: #333;
            white-space: nowrap;
        }
        .script-desc {
            display: block;
            padding-left: 15px;
            font-size: 0.9em;
            color: #666;
        }

        details { border: 1px solid #ddd; padding: 8px; border-radius: 4px; background-color: #fafafa; margin-top: 5px;}
        summary { font-weight: bold; cursor: pointer; color: #34495e; }
        details[open] { padding-bottom: 10px; }
        details pre { margin-top: 10px; white-space: pre-wrap; word-wrap: break-word; background-color: #f1f1f1; padding: 10px; border-radius: 4px; color: #333; }
        .footer { text-align: center; margin-top: 40px; font-size: 0.9em; color: #888; }
    </style>
'''


# --- execute_test_script 函式 (維持不變) ---
def execute_test_script(script_path, test_data_dir):
    """
    執行單一測試腳本，並解析其輸出以判斷成功或失敗。
    現在可以解析包含 RtnMsg 的詳細錯誤訊息。
    """
    start_time = time.time()
    try:
        # 執行 python 腳本
        process = subprocess.run(
            f'python "{script_path}"',
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=30
        )
        # 合併 stdout 和 stderr 以便於分析
        output = process.stdout + process.stderr
    except subprocess.TimeoutExpired:
        output = "Test Failed: Script timed out after 30 seconds."
    except Exception as e:
        output = f"Test Failed: An unexpected error occurred while running the script: {e}"

    duration = f"{(time.time() - start_time):.3f}s"

    # 預設狀態與日誌
    status = 'Pass'
    log_result = 'N/A'

    # 檢查輸出中是否有 "Test Failed" 字樣
    if 'Test Failed' in output:
        status = 'Fail'
        # 從輸出中尋找包含 "Test Failed" 的那一行
        fail_lines = [line for line in output.splitlines() if 'Test Failed' in line]
        if fail_lines:
            # 我們只取第一行找到的失敗訊息
            log_result = fail_lines[0].strip()
        else:
            # 如果找不到特定的失敗行，則給一個通用訊息
            log_result = "測試失敗，但無法提取具體的錯誤訊息。"

    # 檢查輸出中是否有 "Test Passed" 字樣
    elif 'Test Passed' not in output:
        # 如果既沒有 "Test Failed" 也沒有 "Test Passed"，視為失敗
        status = 'Fail'
        log_result = "測試失敗: 腳本輸出不符合預期 (未找到 'Test Passed' 或 'Test Failed' 訊息)。"
        # 附加完整日誌以供除錯
        log_result += f"<details><summary>完整輸出日誌</summary><pre>{output.strip()}</pre></details>"

    # 針對 RtnCode=1 但 RtnMsg 不是「成功」的特殊情況進行檢查
    if status == 'Pass':
        try:
            # 從輸出中解析實際的 RtnMsg
            actual_rtn_msg = output.split("RtnMsg:")[1].splitlines()[0].strip()

            # 讀取期望的 RtnCode
            base_filename = os.path.basename(script_path).replace('.py', '.txt')
            test_data_file = os.path.join(test_data_dir, base_filename)
            expected_rtn_code = None
            with open(test_data_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content.startswith('RtnCode,'):
                    expected_rtn_code = content.split(',')[1]

            # 如果期望 RtnCode 是 1，但訊息不是「成功」，則覆寫結果為失敗
            if expected_rtn_code == '1' and actual_rtn_msg != "成功":
                status = 'Fail'
                log_result = f"測試失敗: RtnCode為1，但RtnMsg為「{actual_rtn_msg}」，不符合預期的「成功」。"
        except (IndexError, FileNotFoundError):
            # 如果解析失敗或找不到對應的測試資料檔，則忽略此項檢查
            pass

    return (status, duration, log_result)


# --- generate_html_rows 函式 (維持不變) ---
def generate_html_rows(test_results):
    """
    根據測試結果產生HTML表格的行。
    如果腳本名稱包含中文字元，會將其拆分為編號和說明兩部分，並套用不同樣式。
    """
    rows = []
    chinese_char_pattern = re.compile(r'[\u4e00-\u9fff]')

    for result, test, duration, log_result in test_results:
        status_class = result.lower()
        script_name = os.path.basename(test)

        match = chinese_char_pattern.search(script_name)
        if match:
            split_index = match.start()
            script_id = script_name[:split_index]
            script_desc = script_name[split_index:]
            formatted_script_name = (f'<span class="script-id">{script_id}</span>'
                                     f'<span class="script-desc">{script_desc}</span>')
        else:
            formatted_script_name = f'<span class="script-id">{script_name}</span>'

        log_html = f"<td>{log_result}</td>"

        # 這段邏輯是為了讓過長的日誌可以被折疊，但我們在上面已經處理了更複雜的折疊情況
        # 為了避免重複，我們可以簡化這裡的邏輯或直接使用上面生成的 log_result
        if result == 'Fail' and not log_result.startswith("<details>"):
            if len(log_result) > 80:
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
            <td class="filepath">{formatted_script_name}</td>
            <td>{duration}</td>
            {log_html}
        </tr>
        """)
    return ''.join(rows)


# --- 為並行處理準備的輔助函數 (維持不變) ---
def run_single_test_wrapper(script_info):
    """
    這是給 multiprocessing.Pool.map() 使用的包裝器函數。
    它接收一個包含 script_path 和 test_data_dir 的元組，並執行單個測試腳本。
    """
    script_path, test_data_dir = script_info
    print(f"正在執行測試 (並行): {os.path.basename(script_path)}")
    status, duration, log_result = execute_test_script(script_path, test_data_dir)
    print(f"完成測試 (並行): {os.path.basename(script_path)}, 結果: {status}")
    return (status, script_path, duration, log_result)


def main():
    scripts_dir = 'C:\\icppython\\OTestCase\\ICPAPI'
    test_data_dir = 'C:\\icppython\\OTestData\\ICPAPI'
    report_dir = r'C:\icppython\icploginapireport'
    pre_test_scripts_paths = [
        'C:\\icppython\\M0001_1.py',
        'C:\\icppython\\M0007_2.py',
        'C:\\icppython\\M0005_3.py'
    ]

    if not os.path.isdir(scripts_dir):
        print(f"錯誤：測試案例目錄不存在: {scripts_dir}")
        sys.exit(1)

    print("--- 正在執行前置測試腳本 (串行執行以確保環境初始化) ---")
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

    scripts = [os.path.join(scripts_dir, f) for f in os.listdir(scripts_dir) if f.endswith('.py')]

    print("\n--- 正在並行執行主要API測試案例 ---")
    num_processes = cpu_count()
    print(f"將使用 {num_processes} 個進程並行執行測試。")
    script_inputs = [(script, test_data_dir) for script in scripts]

    test_results = []
    with Pool(num_processes) as pool:
        test_results = pool.map(run_single_test_wrapper, script_inputs)

    print("\n--- 所有主要API測試執行完畢 ---\n")

    pass_count = sum(1 for r in test_results if r[0] == 'Pass')
    fail_count = len(test_results) - pass_count
    total_count = len(test_results)
    pass_percentage = round(pass_count / total_count * 100, 2) if total_count > 0 else 0

    fig, ax = plt.subplots(figsize=(6, 6))
    if total_count > 0:
        pie_colors = ['#2ecc71', '#e74c3c']
        ax.pie([pass_count, fail_count], labels=['Pass', 'Fail'], autopct='%1.2f%%', colors=pie_colors,
               wedgeprops={'edgecolor': 'white', 'linewidth': 2}, textprops={'color': "black", 'fontsize': 12})
    ax.set_title('Pass/Fail Ratio', fontsize=16)

    chart_dir = os.path.join(os.getcwd(), 'apichart')
    os.makedirs(chart_dir, exist_ok=True)

    # --- 【***程式碼修改處 1***】 ---
    # 從 datetime.now() 改為 datetime.datetime.now()
    chart_path = os.path.join(chart_dir, f"chart_{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}.png")
    fig.savefig(chart_path, bbox_inches='tight', transparent=True)
    print(f"圖表已產生: {chart_path}")

    with open(chart_path, 'rb') as f:
        chart_data = base64.b64encode(f.read()).decode()

    table_rows_html = generate_html_rows(test_results)

    # --- 【***程式碼修改處 2***】 ---
    # 從 datetime.now() 改為 datetime.datetime.now()
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
                                <th style="width: 8%;">測試結果</th>
                                <th style="width: 22%;">測試腳本</th>
                                <th style="width: 10%;">執行時間</th>
                                <th>日誌訊息</th>
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

    os.makedirs(report_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_filename = f"report_{timestamp}.html"
    report_path = os.path.join(report_dir, report_filename)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_template)
    print(f"報告已產生: {report_path}")


if __name__ == '__main__':
    main()
