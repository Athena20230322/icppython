# auto_commit_push.py
import subprocess
import os

REPO_URL = "https://github.com/AdanY-cool/icppython.git"

def ensure_git_remote():
    remotes = subprocess.run(["git", "remote"], capture_output=True, text=True)
    if "origin" not in remotes.stdout:
        subprocess.run(["git", "remote", "add", "origin", REPO_URL], check=True)

def generate_readme():
    content = """# icppython

本專案為 iCash Pay (ICP) 相關 API 的 Python 自動化測試腳本。

## 主要功能腳本

- run_icplogin.py：執行登入流程，並產出 API 測試報告。
- run_icpaccountclose.py：結清帳號流程。
- full_registration_flow.py / full_registration_flowUAT：一鍵註冊本國人會員。
- master_nextstep_runner.py：註冊後 NextStep 狀態流程。
- 其他腳本詳見 README.md。

## 目錄說明

- icploginapireport/：存放登入流程產生的 HTML 測試報告。

## 使用說明

請參閱各腳本說明與 README.md 內容。
"""
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)

def git_commit_push(commit_msg="Auto commit and push after script execution"):
    ensure_git_remote()
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", commit_msg], check=True)
    subprocess.run(["git", "push", "origin", "main"], check=True)

if __name__ == "__main__":
    generate_readme()
    git_commit_push()