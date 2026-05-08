# -*- coding: utf-8 -*-
"""
icash Pay APK 版本監控與自動下載腳本 - 完整修正版
更新內容：
1. 修改 XPath 定位以精準抓取彈窗中第一個（最新）版本。
2. 加入 JavaScript 點擊補強，避免 Selenium 在某些 Web 環境下無法點擊按鈕的問題。
3. 優化檔案下載與名比對邏輯。
"""
import requests
import os
import re
import time
import json
from datetime import datetime, timedelta

# --- 依賴項匯入與檢查 ---
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
except ImportError:
    print("錯誤：缺少必要的函式庫。請執行：")
    print("pip install selenium webdriver-manager requests plyer python-dotenv")
    exit()

try:
    from plyer import notification
except ImportError:
    notification = None

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = lambda: None

# --- (***設定區***) ---
load_dotenv()

# 1. Slack 通知設定
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

# 2. 設定檢查間隔（秒）
CHECK_INTERVAL_SECONDS = 60 * 30  # 30 分鐘

# 3. 環境設定
ENVIRONMENTS = {
    "SIT": {
        "url": "https://download.icashsys.com.tw/sit",
        "save_dir": r"C:\icppython\sit",
        "prefix": "sit"
    },
    "UAT": {
        "url": "https://download.icashsys.com.tw/uat",
        "save_dir": r"C:\icppython\uat",
        "prefix": "UAT"
    },
    "Pilot": {
        "url": "https://download.icashsys.com.tw/pilot",
        "save_dir": r"C:\icppython\pilot",
        "prefix": "pilot"
    },
    "BIZ_SIT": {
        "url": "https://download.icashsys.com.tw/biz/sit",
        "save_dir": r"C:\icppython\biz\sit",
        "prefix": "biz_sit"
    },
    "BIZ_UAT": {
        "url": "https://download.icashsys.com.tw/biz/uat",
        "save_dir": r"C:\icppython\biz\uat",
        "prefix": "biz_uat"
    },
    "BIZ_Pilot": {
        "url": "https://download.icashsys.com.tw/biz/pilot",
        "save_dir": r"C:\icppython\biz\pilot",
        "prefix": "biz_pilot"
    }
}

# 4. 日誌路徑
LOG_FILE_PATH = r"C:\icppython\version_history.log"


# --- (***工具類別與函數***) ---

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        print(f"{bcolors.FAIL}WebDriver 啟動失敗: {e}{bcolors.ENDC}")
        return None


def log_update_to_file(env_name, old_filename, new_filename):
    try:
        log_dir = os.path.dirname(LOG_FILE_PATH)
        if log_dir: os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"{timestamp}, {env_name}, {old_filename}, {new_filename}\n"
        with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        print(f"{bcolors.OKBLUE}已記錄至日誌: {LOG_FILE_PATH}{bcolors.ENDC}")
    except Exception as e:
        print(f"{bcolors.FAIL}日誌寫入失敗: {e}{bcolors.ENDC}")


def send_slack_notification(webhook_url, env_name, old_filename, new_filename):
    if not webhook_url: return
    payload = {
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": "📢 icash Pay APK 更新通知", "emoji": True}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*環境:* `{env_name}`"},
                {"type": "mrkdwn", "text": f"*時間:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
            ]},
            {"type": "divider"},
            {"type": "section",
             "text": {"type": "mrkdwn", "text": f"*舊檔:* `{old_filename}`\n*新檔:* `{new_filename}`"}}
        ]
    }
    try:
        requests.post(webhook_url, data=json.dumps(payload), headers={'Content-Type': 'application/json'}, timeout=10)
    except:
        pass


def find_existing_apk(directory, prefix):
    if not os.path.isdir(directory): return None
    for filename in os.listdir(directory):
        if filename.upper().startswith(prefix.upper()) and filename.lower().endswith('.apk'):
            return filename
    return None


def download_and_compare(env_name, download_url, save_directory, existing_filename):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        with requests.get(download_url, stream=True, headers=headers, allow_redirects=True, timeout=300) as r:
            r.raise_for_status()

            # 從 Header 或 URL 提取檔名
            detected_filename = None
            cd = r.headers.get('content-disposition')
            if cd:
                fname = re.findall('filename="?([^"]+)"?', cd)
                if fname: detected_filename = fname[0]

            if not detected_filename:
                detected_filename = download_url.split('/')[-1].split('?')[0]
                if not detected_filename.lower().endswith('.apk'): detected_filename += ".apk"

            # 版本比對邏輯
            if existing_filename and detected_filename != existing_filename:
                print(f"{bcolors.WARNING}偵測到版本更新！ {existing_filename} -> {detected_filename}{bcolors.ENDC}")

                log_update_to_file(env_name, existing_filename, detected_filename)
                send_slack_notification(SLACK_WEBHOOK_URL, env_name, existing_filename, detected_filename)

                if notification:
                    notification.notify(title=f"icash Pay {env_name} 更新", message=f"新版本: {detected_filename}")

                # 刪除舊檔
                try:
                    os.remove(os.path.join(save_directory, existing_filename))
                except:
                    pass

            elif existing_filename == detected_filename:
                print(f"[{env_name}] 版本無變化。")
                return

            # 執行下載儲存
            local_path = os.path.join(save_directory, detected_filename)
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"{bcolors.OKGREEN}[{env_name}] 下載完成: {detected_filename}{bcolors.ENDC}")

            if not existing_filename:
                log_update_to_file(env_name, "None", detected_filename)

    except Exception as e:
        print(f"{bcolors.FAIL}[{env_name}] 下載處理出錯: {e}{bcolors.ENDC}")


def check_environment(env_name, config):
    print(f"\n--- 檢查環境: {env_name} ---")
    os.makedirs(config["save_dir"], exist_ok=True)
    existing_file = find_existing_apk(config["save_dir"], config["prefix"])

    driver = setup_driver()
    if not driver: return

    try:
        wait = WebDriverWait(driver, 20)
        driver.get(config["url"])

        # 步驟 1: 點擊 Android 下載按鈕 (使用 JS 點擊更穩定)
        btn_xpath = "//a[contains(., 'Android版下載')]"
        android_btn = wait.until(EC.element_to_be_clickable((By.XPATH, btn_xpath)))
        driver.execute_script("arguments[0].click();", android_btn)

        # 步驟 2: 定位彈窗中第一個連結 (根據截圖定位)
        # 修改點：使用 //a[1] 確保選取最上面的最新版本
        link_xpath = "//div[contains(@class, 'modal-body')]//a[1]"
        link_element = wait.until(EC.visibility_of_element_located((By.XPATH, link_xpath)))

        final_url = link_element.get_attribute('href')
        version_name = link_element.text.strip()
        print(f"網頁顯示最新版本: {version_name}")

        if final_url and final_url not in ['#', '']:
            # Dropbox 自動轉直連連結
            if 'dl-web.dropbox.com' in final_url:
                final_url = final_url.replace('dl-web.dropbox.com', 'dl.dropboxusercontent.com')

            download_and_compare(env_name, final_url, config["save_dir"], existing_file)
        else:
            print(f"{bcolors.FAIL}無法獲取有效的下載連結。{bcolors.ENDC}")

    except Exception as e:
        print(f"{bcolors.FAIL}環境 {env_name} 執行異常: {e}{bcolors.ENDC}")
    finally:
        driver.quit()


def main():
    print("=" * 60)
    print(f"{bcolors.BOLD}icash Pay APK 監控啟動中...{bcolors.ENDC}")
    print(f"檢查頻率: 每 {CHECK_INTERVAL_SECONDS / 60} 分鐘一次")
    print("=" * 60)

    while True:
        now = datetime.now().strftime('%H:%M:%S')
        print(f"\n{bcolors.HEADER}[{now}] 開始巡檢所有環境...{bcolors.ENDC}")

        for env, cfg in ENVIRONMENTS.items():
            check_environment(env, cfg)
            time.sleep(3)  # 環境切換間隔

        print(f"\n{bcolors.OKGREEN}輪詢結束。{bcolors.ENDC}")
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n使用者停止程式。")