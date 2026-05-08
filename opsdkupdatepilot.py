import requests
import os
import json
import hashlib  # 用於計算檔案 HASH
from datetime import datetime
from urllib.parse import urljoin  # (備用) 用於組合相對 URL

# --- 依賴項匯入與檢查 ---
try:
    from dotenv import load_dotenv
except ImportError:
    print("錯誤：缺少 'python-dotenv' 函式庫。")
    print("請執行 'pip install python-dotenv' 來安裝。")
    exit()

try:
    from bs4 import BeautifulSoup  # 用於解析 HTML
except ImportError:
    print("錯誤：缺少 'beautifulsoup4' 函式庫。")
    print("請執行 'pip install beautifulsoup4' 來安裝。")
    exit()

# --- (***設定區***) ---
load_dotenv()

# 1. Slack Webhook URL
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

# 2. 設定要監控的資訊
# *** (變更) *** URL 指向 HTML 頁面
HTML_PAGE_URL = "https://711appcf.pic-aws.com/711APP_Content/dl_App/OPENPOINT_UIUX_Pilot_Prod/app.html"

# *** (變更) *** 儲存檔案 HASH 的路徑，而不是 ETag
HASH_FILE = r"C:\icppython\openpoint_pilot_apk.hash"
# *** (新增) *** 暫時下載 APK 的路徑
TEMP_DOWNLOAD_FILE = r"C:\icppython\temp_openpoint_pilot.apk"

ENV_NAME = "OPENPOINT UIUX (Pilot版)"


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
    (此函式不變，'identifier' 現在將被用於 'hash')
    """
    if not webhook_url:
        print(f"{bcolors.WARNING}警告：未在 .env 檔案中設定 SLACK_WEBHOOK_URL，無法發送 Slack 通知。{bcolors.ENDC}")
        return

    # 為了可讀性，我們只顯示 HASH 的前 12 個字元
    short_old = old_identifier[:12] + "..." if len(old_identifier) > 12 else old_identifier
    short_new = new_identifier[:12] + "..." if len(new_identifier) > 12 else new_identifier

    slack_payload = {
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": "📢 APK 版本更新通知！", "emoji": True}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*偵測目標:*\n`{env_name}`"},
                {"type": "mrkdwn", "text": f"*更新時間:*\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
            ]},
            {"type": "divider"},
            {"type": "section", "text": {"type": "mrkdwn", "text": "*偵測到新版本 (檔案 HASH 已變更):*"}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*舊 HASH (SHA256):*\n`{short_old}`"},
                {"type": "mrkdwn", "text": f"*新 HASH (SHA256):*\n`{short_new}`"}
            ]},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"完整的舊 HASH: `{old_identifier}`"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"完整的新 HASH: `{new_identifier}`"}}
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


def calculate_file_hash(filepath):
    """
    *** (新增) ***
    計算檔案的 SHA256 HASH。
    """
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            # 讀取並更新 HASH，避免一次載入大檔案佔用記憶體
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except IOError as e:
        print(f"{bcolors.FAIL}讀取檔案 HASH 時出錯: {e}{bcolors.ENDC}")
        return None


def check_for_update():
    """
    *** (重大修改) ***
    檢查更新的完整流程：
    1. 爬取 HTML 頁面
    2. 尋找 APK 連結
    3. 下載 APK 檔案
    4. 計算 HASH 並比較
    """
    temp_file_path = None  # 用於 'finally' 區塊中清理暫存檔
    try:
        # 1. 爬取 HTML 頁面
        print(f"正在連線到 HTML 頁面: {HTML_PAGE_URL}")
        page_response = requests.get(HTML_PAGE_URL, timeout=15)
        page_response.raise_for_status()

        # 2. 尋找 APK 連結 (定位元素)
        print("正在解析 HTML 並尋找 APK 連結...")
        soup = BeautifulSoup(page_response.text, 'html.parser')

        # 根據您圖片中的內容，我們尋找包含 'OPENPOINT_Prod_Pilot.apk' 的 <a> 標籤
        link_element = soup.find('a', href=lambda href: href and 'OPENPOINT_Prod_Pilot.apk' in href)

        if not link_element:
            print(f"{bcolors.FAIL}錯誤：在 HTML 頁面中找不到 'OPENPOINT_Prod_Pilot.apk' 連結。{bcolors.ENDC}")
            return

        actual_apk_link = link_element['href']
        # 處理相對路徑 (雖然在此案例中
        # 它是絕對路徑)
        actual_apk_link = urljoin(HTML_PAGE_URL, actual_apk_link)
        print(f"成功找到 APK 連結: {actual_apk_link}")

        # 3. 下載 APK 檔案 (串流模式)
        print(f"正在下載 APK 檔案... (這可能需要一些時間)")
        temp_file_path = TEMP_DOWNLOAD_FILE
        with requests.get(actual_apk_link, stream=True, timeout=300) as r:  # 5分鐘超時
            r.raise_for_status()
            with open(temp_file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"檔案已下載至: {temp_file_path}")

        # 4. 計算 HASH 並比較
        print("正在計算新檔案的 HASH...")
        new_hash = calculate_file_hash(temp_file_path)
        if not new_hash:
            print(f"{bcolors.FAIL}無法計算新檔案的 HASH，已中斷。{bcolors.ENDC}")
            return

        print(f"新檔案的 HASH: {new_hash}")

        saved_hash = "無 (首次檢查)"
        if os.path.exists(HASH_FILE):
            with open(HASH_FILE, 'r') as f:
                saved_hash = f.read().strip()
            print(f"讀取到已儲存 HASH: {saved_hash}")

        # 5. 比較 HASH
        if new_hash != saved_hash:
            title = f"【{ENV_NAME}】版本更新通知！"
            print(f"\n{bcolors.OKCYAN}{'=' * 15} {title} {'=' * 15}{bcolors.ENDC}")
            print(f"{bcolors.WARNING}>>> 偵測到 APK 更新！ (HASH 不符) <<<{bcolors.ENDC}")
            print(f"{bcolors.WARNING}舊 HASH: {saved_hash}{bcolors.ENDC}")
            print(f"{bcolors.WARNING}新 HASH: {new_hash}{bcolors.ENDC}\n")

            # 呼叫 Slack 通知函式
            send_slack_notification(SLACK_WEBHOOK_URL, ENV_NAME, saved_hash, new_hash)

            # 更新本地儲存的 HASH
            with open(HASH_FILE, 'w') as f:
                f.write(new_hash)
            print(f"已將本地 HASH 更新為: {new_hash}")
        else:
            print(f"{bcolors.OKGREEN}APK 檔案 HASH 無變化。{bcolors.ENDC}")

    except requests.exceptions.RequestException as e:
        print(f"{bcolors.FAIL}請求失敗: {e}{bcolors.ENDC}")
    except Exception as e:
        print(f"{bcolors.FAIL}發生未預期的錯誤: {e}{bcolors.ENDC}")
    finally:
        # 無論成功或失敗，都刪除暫存的 APK 檔案
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            print(f"已清理暫存檔案: {temp_file_path}")


if __name__ == "__main__":
    check_for_update()