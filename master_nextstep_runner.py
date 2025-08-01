# C:\icppython\master_test_runner.py

import os
import sys
import json
import re
import subprocess
import traceback
import webbrowser
from datetime import datetime
import html

# --- 複製您提供的 HtmlReporter 類別 (無需修改) ---
# --- 修正後的 HTML 報告產生類別 ---
class HtmlReporter:
    """產生並儲存一個 HTML 格式的測試報告。"""

    def __init__(self, report_title):
        self.report_title = report_title
        self.steps = []
        self.start_time = datetime.now()
        self.end_time = None
        self.overall_status = "⏳ 執行中"

    def add_step(self, step_name, status, expected_value=None, actual_value=None, details_dict=None):
        """新增一個測試步驟到報告中。"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        details = {}

        if expected_value is not None:
            details["[期望結果] NextStep"] = str(expected_value)
        if actual_value is not None:
            details["[實際結果] NextStep"] = str(actual_value)

        if details_dict:
            details.update(details_dict)

        self.steps.append({
            "name": step_name,
            "status": status,
            "timestamp": timestamp,
            "details": details
        })
        if "❌" in status:
            self.overall_status = "❌ 失敗"

    def finalize_report(self):
        """設定報告的最終狀態。"""
        self.end_time = datetime.now()
        if self.overall_status == "⏳ 執行中":
            self.overall_status = "✅ 成功"

    def generate_html(self):
        """產生完整的 HTML 報告內容。"""
        if not self.end_time: self.finalize_report()
        duration = self.end_time - self.start_time
        status_color = '#28a745' if '✅' in self.overall_status else '#dc3545'

        # 這裡的 html 變數是區域的，不會與 html 模組衝突
        html_content = f"""
        <!DOCTYPE html><html lang="zh-Hant"><head><meta charset="UTF-8"><title>{self.report_title}</title>
        <style>
            body {{ font-family: 'Segoe UI', 'Microsoft JhengHei', sans-serif; margin: 20px; background-color: #f4f7f6; }}
            .container {{ max-width: 1200px; margin: auto; padding: 20px; background-color: #fff; box-shadow: 0 0 15px rgba(0,0,0,0.1); border-radius: 8px; }}
            h1 {{ text-align: center; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            .summary {{ background-color: #ecf0f1; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 5px solid {status_color}; }}
            .summary p {{ margin: 5px 0; font-size: 1.1em;}}
            .summary-status {{ font-size: 1.3em; font-weight: bold; color: {status_color}; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; table-layout: fixed; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; vertical-align: top; word-wrap: break-word; }}
            th {{ background-color: #3498db; color: white; }}
            .status-success {{ color: #28a745; font-weight: bold; }}
            .status-failure {{ color: #dc3545; font-weight: bold; }}
            details {{ cursor: pointer; }}
            pre {{ background-color: #2d2d2d; color: #f2f2f2; padding: 10px; border-radius: 5px; white-space: pre-wrap; word-wrap: break-word; font-family: 'Courier New', monospace;}}
        </style>
        </head><body><div class="container"><h1>{self.report_title}</h1><div class="summary">
            <p><strong>整體狀態:</strong> <span class="summary-status">{self.overall_status}</span></p>
            <p><strong>開始時間:</strong> {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>結束時間:</strong> {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>總耗時:</strong> {str(duration).split('.')[0]}</p>
        </div><table><thead><tr><th style="width: 5%;">#</th><th style="width: 25%;">測試案例</th><th style="width: 10%;">狀態</th><th style="width: 15%;">時間戳</th><th style="width: 45%;">詳細資料</th></tr></thead><tbody>
        """
        for i, step in enumerate(self.steps, 1):
            status_class = "status-success" if "✅" in step['status'] else "status-failure"
            # *** 這裡是修正點 ***
            # 使用 html.escape() 處理 value，確保特殊字元被正確轉義
            details_html = "".join([
                                       f"<details><summary>{html.escape(str(key))}</summary><pre><code>{html.escape(str(value))}</code></pre></details>"
                                       for key, value in step['details'].items()])
            html_content += f"""<tr><td>{i}</td><td>{html.escape(step['name'])}</td><td class="{status_class}">{step['status']}</td><td>{step['timestamp']}</td><td>{details_html}</td></tr>"""

        html_content += "</tbody></table></div></body></html>"
        return html_content

    def save_and_open_report(self, base_path):
        """儲存報告到檔案並在瀏覽器中開啟。"""
        os.makedirs(base_path, exist_ok=True)
        filename = f"Master_Test_Report_{self.start_time.strftime('%Y%m%d_%H%M%S')}.html"
        filepath = os.path.join(base_path, filename)
        html_content = self.generate_html()
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"\n📄 報告已成功生成: {filepath}")
            webbrowser.open(f'file://{os.path.realpath(filepath)}')
        except Exception as e:
            print(f"\n❌ 錯誤: 無法儲存或開啟報告: {e}")

def run_test_sequence(sequence_config, base_path):
    """
    依序執行定義好的測試腳本序列。
    """
    reporter = HtmlReporter(report_title="iCashPay 自動化測試序列報告")

    for i, step_config in enumerate(sequence_config, 1):
        script_path = os.path.join(base_path, step_config["script_file"])
        description = step_config["description"]
        expected_next_step = step_config["expected_next_step"]

        print("\n" + "=" * 50)
        print(f"▶️  開始執行步驟 {i}: {description}")
        print(f"   - 腳本: {script_path}")
        print(f"   - 預期 NextStep: {expected_next_step}")
        print("=" * 50)

        # 檢查腳本檔案是否存在
        if not os.path.exists(script_path):
            error_msg = f"腳本檔案不存在: {script_path}"
            print(f"❌ {error_msg}")
            reporter.add_step(description, "❌ 失敗", expected_next_step, "N/A", {"錯誤詳情": error_msg})
            break  # 中斷後續測試

        try:
            # 執行子腳本並捕獲其輸出
            process = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                encoding='utf-8',
                check=True  # 如果腳本返回非零碼 (即出錯)，會拋出例外
            )

            stdout = process.stdout
            print("--- 子腳本輸出 (stdout) ---\n" + stdout)

            # 從輸出中解析 NextStep
            match = re.search(r"\[狀態檢查\]\s*NextStep:\s*(\d+)", stdout)

            if match:
                actual_next_step = int(match.group(1))
                print(f"   - 成功解析出 NextStep: {actual_next_step}")

                # 驗證 NextStep 是否符合預期
                if actual_next_step == expected_next_step:
                    print(f"✅ 驗證成功: 實際值 ({actual_next_step}) 符合預期值 ({expected_next_step})。")
                    reporter.add_step(description, "✅ 成功", expected_next_step, actual_next_step,
                                      {"腳本輸出 (stdout)": stdout})
                else:
                    print(f"❌ 驗證失敗: 實際值 ({actual_next_step}) 不符合預期值 ({expected_next_step})。")
                    reporter.add_step(description, "❌ 失敗", expected_next_step, actual_next_step,
                                      {"腳本輸出 (stdout)": stdout})
                    break  # 中斷後續測試
            else:
                print("❌ 驗證失敗: 在腳本輸出中找不到 '[狀態檢查] NextStep'。")
                reporter.add_step(description, "❌ 失敗", expected_next_step, "未找到", {"腳本輸出 (stdout)": stdout})
                break  # 中斷後續測試

        except subprocess.CalledProcessError as e:
            # 腳本執行出錯 (例如，Python 程式碼有 bug)
            stderr = e.stderr
            print(f"❌ 腳本執行時發生錯誤: {description}")
            print("--- 子腳本錯誤輸出 (stderr) ---\n" + stderr)
            reporter.add_step(description, "❌ 失敗", expected_next_step, "執行錯誤",
                              {"錯誤輸出 (stderr)": stderr, "Traceback": traceback.format_exc()})
            break  # 中斷後續測試

        except Exception as e:
            # 主控腳本本身發生其他錯誤
            print(f"❌ 主控腳本發生未預期錯誤: {e}")
            reporter.add_step(description, "❌ 失敗", expected_next_step, "主控腳本錯誤",
                              {"Traceback": traceback.format_exc()})
            break  # 中斷後續測試

    # 無論如何，最後都產生並開啟報告
    reporter.finalize_report()
    reporter.save_and_open_report(base_path)


# --- 主程式進入點 ---
if __name__ == '__main__':
    BASE_PATH = "C:\\icppython"

    # --- ✨ 請在此處設定您的測試序列與預期結果 ✨ ---
    TEST_SEQUENCE = [
        {
            "script_file": "full_registration_next1.py",
            "description": "註冊流程 (Next 1)",
            "expected_next_step": 1  # 假設此腳本應回傳 NextStep: 1
        },
        {
            "script_file": "full_registration_next2.py",
            "description": "註冊流程 (Next 2)",
            "expected_next_step": 2  # 假設此腳本應回傳 NextStep: 2
        },
        {
            "script_file": "fullloginnext4.py",
            "description": "登入流程 (Next 4)",
            "expected_next_step": 4  # 假設此腳本應回傳 NextStep: 4
        },
        {
            "script_file": "fullloginnext5.py",
            "description": "登入流程 (Next 5)",
            "expected_next_step": 5
        },
        {
            "script_file": "fullloginnext6.py",
            "description": "登入流程 (Next 6)",
            "expected_next_step": 6
        },
        {
            "script_file": "fullloginnext9.py",
            "description": "登入流程 (Next 9)",
            "expected_next_step": 9
        },
        {
            "script_file": "fullloginnext13.py",
            "description": "登入流程 (Next 13)",
            "expected_next_step": 13
        },
        # 如果有更多步驟，可以繼續往下加
    ]

    run_test_sequence(TEST_SEQUENCE, BASE_PATH)