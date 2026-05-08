# auto_commit_push.py
import subprocess
import os

def generate_readme():
    content = """# Integrated_QA_Tool

自動產生條碼並執行現金儲值的工具。

## 使用方式

1. 編輯 `account.txt`，填入帳號資料。
2. 執行 `Integrated_QA_Tool_GetTopUpBarCode.py`。
3. 結果會自動寫入 `markettoprefund.txt`。

## 主要檔案

- Integrated_QA_Tool_GetTopUpBarCode.py
- account.txt
- markettoprefund.txt
"""
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)

def git_commit_push(commit_msg="Auto commit and push after script execution"):
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", commit_msg], check=True)
    subprocess.run(["git", "push"], check=True)

if __name__ == "__main__":
    generate_readme()
    git_commit_push()