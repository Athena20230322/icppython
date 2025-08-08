import requests
import os
import re
import time
import json
from datetime import datetime, timedelta
from urllib.parse import urljoin

# 匯入 Selenium 相關工具
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
    print("錯誤：缺少 'selenium' 或 'webdriver-manager' 函式庫。")
    print("請執行 'pip install selenium webdriver-manager' 來安裝。")
    exit()

# 檢查是否能匯入 plyer
try:
    from plyer import notification
except ImportError:
    print("警告：'plyer' 函式庫未安裝，將無法使用桌面通知功能。")
    notification = None

# --- (***程式碼修改處***) ---
# 將您的 Slack Webhook URL 貼在此處
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/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"


class bcolors:
    WARNING = '\033[91m'
    ENDC = '\033[0m'


def send_slack_notification(webhook_url, file_type, old_filename, new_filename):
    """發送格式化的通知到 Slack。"""
    if not webhook_url:
        print("警告：未設定 SLACK_WEBHOOK_URL，無法發送 Slack 通知。")
        return

    # 使用 Slack Block Kit 建立美觀的訊息格式
    slack_payload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📢 icash Pay APK 版本更新通知！",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*偵測環境:*\n`{file_type}`"},
                    {"type": "mrkdwn", "text": f"*更新時間:*\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
                ]
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*偵測到新版本，檔案已更新:*"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*舊有檔案:*\n`{old_filename}`"},
                    {"type": "mrkdwn", "text": f"*新版檔案:*\n`{new_filename}`"}
                ]
            }
        ]
    }

    try:
        response = requests.post(
            webhook_url,
            data=json.dumps(slack_payload),
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        if response.status_code == 200:
            print("已成功發送 Slack 通知。")
        else:
            print(f"發送 Slack 通知失敗，狀態碼: {response.status_code}, 回應: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"發送 Slack 通知時發生網路錯誤: {e}")
    except Exception as e:
        print(f"發送 Slack 通知時發生未預期錯誤: {e}")


def find_existing_apk(directory, prefix):
    """在指定目錄中尋找已存在的 APK 檔案。"""
    if not os.path.isdir(directory): return None
    for filename in os.listdir(directory):
        if filename.upper().startswith(prefix.upper()) and filename.lower().endswith('.apk'):
            return filename
    return None


def download_and_compare(file_type, download_url, save_directory, existing_filename_to_compare):
    """(通用函式) 從最終 URL 下載檔案並進行比對。"""
    detected_filename = None
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 從最終連結下載 [{file_type}] 檔案: {download_url}")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        with requests.get(download_url, stream=True, headers=headers, allow_redirects=True, timeout=300) as r:
            r.raise_for_status()
            content_disposition = r.headers.get('content-disposition')
            if content_disposition:
                fname = re.findall('filename="?([^"]+)"?', content_disposition)
                if fname: detected_filename = fname[0]

            if not detected_filename:
                potential_name = download_url.split('/')[-1].split('?')[0]
                if not potential_name.lower().endswith('.apk'):
                    detected_filename = f"{potential_name}.apk" if potential_name else f"{file_type.lower()}.apk"
                else:
                    detected_filename = potential_name

            # --- (***程式碼修改處***) ---
            # 核心邏輯：比對新舊檔名
            if detected_filename and existing_filename_to_compare and detected_filename != existing_filename_to_compare:
                title = f"{file_type.upper()} 版本更新通知！"
                message = f"偵測到新版本！\n現有檔名: {existing_filename_to_compare}\n新版本檔名: {detected_filename}"
                print(f"{bcolors.WARNING}==================== {title} ===================={bcolors.ENDC}")
                print(f"{bcolors.WARNING}警告：{message.replace(chr(10), ' ')}{bcolors.ENDC}")

                # 發送桌面通知 (如果 plyer 存在)
                if notification:
                    notification.notify(title=title, message=message, app_name='icash Pay 監控程式', timeout=20)

                # 發送 Slack 通知
                send_slack_notification(
                    SLACK_WEBHOOK_URL,
                    file_type,
                    existing_filename_to_compare,
                    detected_filename
                )

            # 儲存檔案
            local_filepath = os.path.join(save_directory, detected_filename)
            print(f"檔案將儲存為: {local_filepath}")
            with open(local_filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"[{file_type.upper()}] 檔案下載/更新成功！")
    except requests.exceptions.RequestException as e:
        print(f"[{file_type.upper()}] 檔案下載失敗: {e}")


def process_download_with_selenium(env_type, initial_url, save_directory, existing_filename):
    """
    (通用函式) 使用 Selenium 解析頁面，找到連結後再下載並比對。
    """
    print(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 使用瀏覽器模式解析 [{env_type.upper()}] 頁面: {initial_url}")

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        wait = WebDriverWait(driver, 15)

        driver.get(initial_url)

        print("步驟 1: 正在尋找 'Android版下載' 按鈕...")
        android_button_xpath = "//a[contains(., 'Android版下載')]"
        android_button = wait.until(EC.element_to_be_clickable((By.XPATH, android_button_xpath)))
        android_button.click()
        print("成功點擊按鈕，等待版本選擇視窗...")

        print("步驟 2: 正在等待彈出視窗並尋找最新版本連結...")
        download_link_xpath = "//div[contains(@class, 'modal-body')]//a[1]"
        download_link_element = wait.until(EC.visibility_of_element_located((By.XPATH, download_link_xpath)))

        final_download_url = download_link_element.get_attribute('href')

        if not final_download_url or final_download_url == 'javascript:;':
            print(f"錯誤：在 {env_type.upper()} 的彈出視窗中獲取到的連結無效。")
            return

        if 'dl-web.dropbox.com' in final_download_url:
            original_url = final_download_url
            final_download_url = final_download_url.replace('dl-web.dropbox.com', 'dl.dropboxusercontent.com')
            print(f"偵測到 Dropbox 連結，已自動嘗試轉換為直接下載格式。")
            print(f"  - 原始連結: {original_url}")
            print(f"  - 轉換後: {final_download_url}")

        print(f"成功在頁面中找到下載連結，將開始下載...")
        download_and_compare(env_type.upper(), final_download_url, save_directory, existing_filename)

    except NoSuchElementException as e:
        print(f"錯誤：在 {env_type.upper()} 頁面中無法找到指定的元素。請檢查 XPath 是否仍然有效。錯誤: {e}")
    except TimeoutException:
        print(f"錯誤：等待 {env_type.upper()} 頁面元素載入超時。可能是網路問題或頁面結構已變更。")
    except (WebDriverException) as e:
        print(f"錯誤：瀏覽器自動化 (Selenium) 執行失敗。請確認 Chrome 已安裝。錯誤訊息: {str(e)[:200]}")
    except Exception as e:
        print(f"處理 {env_type.upper()} 時發生未預期錯誤: {e}")
    finally:
        if driver:
            driver.quit()


def run_check():
    """執行一次完整的檢查與下載流程"""
    print("--- 開始處理 SIT ---")
    save_path_sit = r"C:\icppython\sit"
    try:
        os.makedirs(save_path_sit, exist_ok=True)
        existing_sit_filename = find_existing_apk(save_path_sit, "sit")
        if existing_sit_filename:
            print(f"找到現有 SIT 檔案: {existing_sit_filename}")
        else:
            print(f"目錄 [{save_path_sit}] 中未找到現有的 SIT 檔案。")

        process_download_with_selenium(
            "SIT",
            "https://download.icashsys.com.tw/sit",
            save_path_sit,
            existing_sit_filename
        )
    except Exception as e:
        print(f"處理 SIT 時發生未預期錯誤: {e}")

    print("\n" + "=" * 50 + "\n")

    print("--- 開始處理 UAT ---")
    save_path_uat = r"C:\icppython\uat"
    try:
        os.makedirs(save_path_uat, exist_ok=True)
        existing_uat_filename = find_existing_apk(save_path_uat, "UAT")
        if existing_uat_filename:
            print(f"找到現有 UAT 檔案: {existing_uat_filename}")
        else:
            print(f"目錄 [{save_path_uat}] 中未找到現有的 UAT 檔案。")

        process_download_with_selenium(
            "UAT",
            "https://download.icashsys.com.tw/uat",
            save_path_uat,
            existing_uat_filename
        )
    except Exception as e:
        print(f"處理 UAT 時發生未預期錯誤: {e}")


if __name__ == "__main__":
    CHECK_INTERVAL_SECONDS = 60 * 30
    print("=================================================")
    print("= icash Pay APK 監控程式已啟動              =")
    print(f"= 每 {int(CHECK_INTERVAL_SECONDS / 60)} 分鐘會自動檢查一次版本        =")
    print("= 請保持此視窗開啟，可按 Ctrl+C 來中止程式 =")
    print("=================================================")
    while True:
        run_check()
        print("\n--- 本次檢查完成 ---")
        print(
            f"下次檢查時間: {(datetime.now() + timedelta(seconds=CHECK_INTERVAL_SECONDS)).strftime('%Y-%m-%d %H:%M:%S')}")
        time.sleep(CHECK_INTERVAL_SECONDS)