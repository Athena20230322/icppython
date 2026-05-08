import requests
import os
import json
from datetime import datetime

# --- 依賴項匯入與檢查 ---
try:
    # 用於從 .env 檔案讀取設定，保持機密資訊不外洩
    from dotenv import load_dotenv
except ImportError:
    print("錯誤：缺少 'python-dotenv' 函式庫。")
    print("請執行 'pip install python-dotenv' 來安裝，以便從 .env 檔案讀取設定。")
    exit()

# --- (***設定區***) ---
# 載入 .env 檔案中的環境變數 (例如 SLACK_WEBHOOK_URL)
load_dotenv()

# 1. 從環境變數讀取 Slack Webhook URL。
#    請在 C:\icppython 目錄下建立一個名為 .env 的檔案，
#    並在其中加入一行： SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

# 2. 設定要監控的 APK 資訊
# *** URL 已更新為您提供的最新路徑 ***
APK_URL = "https://711appcf.pic-aws.com/711APP_Content/dl_App/OPENPOINT_UIUX_Test/OPENPOINT_Test.apk"
ETAG_FILE = r"C:\icppython\openpoint_test_apk_etag.txt"  # 使用絕對路徑以避免混淆
ENV_NAME = "OPENPOINT UIUX (測試版)"  # 用於通知中的環境名稱


# --- (***設定結束***) ---

class bcolors:
    """用於在終端機中顯示彩色文字的類別"""
    HEADER = '\033[95m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def send_slack_notification(webhook_url, env_name, old_identifier, new_identifier):
    """
    發送格式化的通知到 Slack。
    """
    if not webhook_url:
        print(f"{bcolors.WARNING}警告：未在 .env 檔案中設定 SLACK_WEBHOOK_URL，無法發送 Slack 通知。{bcolors.ENDC}")
        return

    slack_payload = {
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": "📢 APK 版本更新通知！", "emoji": True}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*偵測目標:*\n`{env_name}`"},
                {"type": "mrkdwn", "text": f"*更新時間:*\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
            ]},
            {"type": "divider"},
            {"type": "section", "text": {"type": "mrkdwn", "text": "*偵測到新版本 (ETag/Identifier 已變更):*"}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*舊有識別碼:*\n`{old_identifier}`"},
                {"type": "mrkdwn", "text": f"*最新識別碼:*\n`{new_identifier}`"}
            ]}
        ]
    }

    try:
        response = requests.post(
            webhook_url, data=json.dumps(slack_payload),
            headers={'Content-Type': 'application/json'}, timeout=10
        )
        if response.status_code == 200:
            print(f"{bcolors.OKGREEN}已成功發送 Slack 通知。{bcolors.ENDC}")
        else:
            print(
                f"{bcolors.FAIL}發送 Slack 通知失敗，狀態碼: {response.status_code}, 回應: {response.text}{bcolors.ENDC}")
    except requests.exceptions.RequestException as e:
        print(f"{bcolors.FAIL}發送 Slack 通知時發生網路錯誤: {e}{bcolors.ENDC}")


def check_for_update():
    """檢查遠端 APK 是否有更新，並在更新時發送 Slack 通知"""
    print(f"正在檢查: {APK_URL}")
    try:
        response = requests.head(APK_URL, timeout=15)
        response.raise_for_status()

        current_etag = response.headers.get('ETag')
        if not current_etag:
            current_identifier = response.headers.get('Last-Modified')
            if not current_identifier:
                print(f"{bcolors.FAIL}錯誤：伺服器未提供 ETag 或 Last-Modified 標頭，無法判斷更新。{bcolors.ENDC}")
                return
            print("注意：伺服器未使用 ETag，改用 Last-Modified 進行比對。")
        else:
            current_identifier = current_etag

        print(f"取得目前檔案識別碼: {current_identifier}")

        saved_identifier = "無 (首次檢查)"
        if os.path.exists(ETAG_FILE):
            with open(ETAG_FILE, 'r') as f:
                saved_identifier = f.read().strip()
            print(f"讀取到已儲存識別碼: {saved_identifier}")

        # 比對識別碼
        if current_identifier != saved_identifier:
            title = f"【{ENV_NAME}】版本更新通知！"
            message = f"偵測到新版本！\n舊識別碼: {saved_identifier}\n新識別碼: {current_identifier}"

            print(f"\n{bcolors.OKCYAN}{'=' * 15} {title} {'=' * 15}{bcolors.ENDC}")
            print(f"{bcolors.WARNING}>>> 偵測到 APK 更新！ <<<{bcolors.ENDC}")
            print(f"{bcolors.WARNING}{message.replace(chr(10), ' | ')}{bcolors.ENDC}\n")

            # 呼叫 Slack 通知函式
            send_slack_notification(SLACK_WEBHOOK_URL, ENV_NAME, saved_identifier, current_identifier)

            # 更新本地儲存的識別碼
            with open(ETAG_FILE, 'w') as f:
                f.write(current_identifier)
            print(f"已將本地識別碼更新為: {current_identifier}")
        else:
            print(f"{bcolors.OKGREEN}APK 版本無變化。{bcolors.ENDC}")

    except requests.exceptions.RequestException as e:
        print(f"{bcolors.FAIL}請求失敗: {e}{bcolors.ENDC}")


if __name__ == "__main__":
    check_for_update()