import os
import subprocess
import sys


def execute_script(script_path):
    """
    執行單一指定的 Python 腳本並印出其輸出。
    """
    # 檢查檔案是否存在
    if not os.path.isfile(script_path):
        print(f"!!! 錯誤：找不到指定的腳本檔案，已跳過執行：\n    {script_path}\n")
        return

    print(f"--- 正在執行腳本：{os.path.basename(script_path)} ---")

    try:
        # 使用 subprocess 執行 Python 腳本
        process = subprocess.run(
            f'python "{script_path}"',
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=60  # 設置 60 秒超時
        )

        # 印出腳本的標準輸出
        if process.stdout:
            print("--- 腳本輸出 ---")
            print(process.stdout.strip())

        # 如果有錯誤訊息，也印出來
        if process.stderr:
            print("--- 錯誤訊息(如有) ---")
            print(process.stderr.strip())

        print(f"--- 執行完畢，返回碼: {process.returncode} ---\n")

    except subprocess.TimeoutExpired:
        print("!!! 錯誤：腳本執行超時（超過 60 秒）!!!\n")
    except Exception as e:
        print(f"!!! 執行腳本時發生未預期的錯誤: {e} !!!\n")


def main():
    """
    主執行函式，依序執行指定的腳本列表。
    """
    # 您指定要依序執行的三個 .py 檔案路徑
    scripts_to_run = [
        r'C:\icppython\M0001_1closetest.py',
        r'C:\icppython\M0007_2closetest.py',
        r'C:\icppython\M0005_3closetest.py'
    ]

    print("=========================================")
    print("      開始執行指定的 Python 腳本        ")
    print("=========================================\n")

    # 依序執行列表中的每一個腳本
    for script_path in scripts_to_run:
        execute_script(script_path)

    print("=========================================")
    print("      所有指定的腳本皆已執行完畢        ")
    print("=========================================")


if __name__ == '__main__':
    # 確保只有在直接執行此腳本時才調用 main 函式
    main()