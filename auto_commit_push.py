# auto_commit_push.py
import subprocess
import os

REPO_URL = "https://github.com/AdanY-cool/icppython.git"  # 請將 <repo> 替換為你的專案名稱

def ensure_git_remote():
    # 檢查是否已設定 origin，若無則新增
    remotes = subprocess.run(["git", "remote"], capture_output=True, text=True)
    if "origin" not in remotes.stdout:
        subprocess.run(["git", "remote", "add", "origin", REPO_URL], check=True)

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
    ensure_git_remote()
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", commit_msg], check=True)
    subprocess.run(["git", "push", "origin", "main"], check=True)  # main 或 master，依你的分支名稱

if __name__ == "__main__":
    generate_readme()
    git_commit_push()