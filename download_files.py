# -*- coding: utf-8 -*-
"""
icash Pay APK 版本監控與自動下載腳本

功能：
1. 定期使用 Selenium 瀏覽器自動化技術，訪問指定的下載頁面。
2. 模擬使用者點擊操作，獲取最新的 APK 下載連結。
3. 比較新版本的檔名與本地已存在的檔名。
4. 如果檔名不同（代表有更新），則下載新版 APK。
5. 更新時，可選擇性地發送桌面通知與 Slack 通知。
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
    print("錯誤：缺少 'selenium' 或 'webdriver-manager' 函式庫。")
    print("請執行 'pip install selenium webdriver-manager' 來安裝。")
    exit()

try:
    from plyer import notification
except ImportError:
    print("警告：'plyer' 函式庫未安裝，將無法使用桌面通知功能。")
    print("若需要此功能，請執行 'pip install plyer'。")
    notification = None

try:
    from dotenv import load_dotenv
except ImportError:
    print("錯誤：缺少 'python-dotenv' 函式庫。")
    print("請執行 'pip install python-dotenv' 來安裝，以便從 .env 檔案讀取設定。")
    exit()

# --- (***設定區***) ---
# 載入 .env 檔案中的環境變數 (例如 SLACK_WEBHOOK_URL)
load_dotenv()

# 1. 從環境變數讀取 Slack Webhook URL。程式會自動讀取專案目錄下的 .env 檔案。
#    請建立一個名為 .env 的檔案，並在其中加入一行：
#    SLACK_WEBHOOK_URL="YOUR_WEBHOOK_URL_HERE"
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

# 2. 設定檢查間隔（秒）
CHECK_INTERVAL_SECONDS = 60 * 30  # 預設為 30 分鐘

# 3. 設定要監控的環境
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
    }
    # 若有其他環境 (如 PROD)，可在此處新增
}


# --- (***設定結束***) ---


class bcolors:
    """用於在終端機中顯示彩色文字的類別"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def setup_driver():
    """初始化並返回一個設定好的 Selenium WebDriver"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 無頭模式，不在前景顯示瀏覽器
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--log-level=3")  # 僅顯示嚴重錯誤
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

    # 使用 try-except 確保驅動程式安裝過程更穩定
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        print(f"{bcolors.FAIL}初始化 WebDriver 失敗: {e}{bcolors.ENDC}")
        return None


def send_slack_notification(webhook_url, env_name, old_filename, new_filename):
    """
    發送格式化的通知到 Slack。

    Args:
        webhook_url (str): Slack Webhook URL。
        env_name (str): 環境類型 (e.g., "SIT", "UAT")。
        old_filename (str): 舊的檔案名稱。
        new_filename (str): 新的檔案名稱。
    """
    if not webhook_url:
        print(f"{bcolors.WARNING}警告：未在 .env 檔案中設定 SLACK_WEBHOOK_URL，無法發送 Slack 通知。{bcolors.ENDC}")
        return

    slack_payload = {
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": "📢 icash Pay APK 版本更新通知！", "emoji": True}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*偵測環境:*\n`{env_name}`"},
                {"type": "mrkdwn", "text": f"*更新時間:*\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
            ]},
            {"type": "divider"},
            {"type": "section", "text": {"type": "mrkdwn", "text": "*偵測到新版本，檔案已更新:*"}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*舊有檔案:*\n`{old_filename}`"},
                {"type": "mrkdwn", "text": f"*新版檔案:*\n`{new_filename}`"}
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
    except Exception as e:
        print(f"{bcolors.FAIL}發送 Slack 通知時發生未預期錯誤: {e}{bcolors.ENDC}")


def find_existing_apk(directory, prefix):
    """
    在指定目錄中尋找符合前綴的已存在 APK 檔案。

    Args:
        directory (str): 要搜尋的目錄路徑。
        prefix (str): 檔案名稱的前綴。

    Returns:
        str or None: 如果找到檔案，返回檔名；否則返回 None。
    """
    if not os.path.isdir(directory):
        return None
    for filename in os.listdir(directory):
        if filename.upper().startswith(prefix.upper()) and filename.lower().endswith('.apk'):
            return filename
    return None


def download_and_compare(env_name, download_url, save_directory, existing_filename):
    """
    從給定的 URL 下載檔案，與現有檔案比對，並在需要時觸發通知。

    Args:
        env_name (str): 環境類型 (e.g., "SIT", "UAT")。
        download_url (str): 檔案的直接下載連結。
        save_directory (str): 儲存檔案的目錄。
        existing_filename (str or None): 本地已存在的檔案名稱。
    """
    print(f"正在從最終連結下載 [{env_name}] 檔案: {download_url}")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        with requests.get(download_url, stream=True, headers=headers, allow_redirects=True, timeout=300) as r:
            r.raise_for_status()

            # 從 HTTP 標頭或 URL 中解析檔名
            detected_filename = None
            content_disposition = r.headers.get('content-disposition')
            if content_disposition:
                fname = re.findall('filename="?([^"]+)"?', content_disposition)
                if fname:
                    detected_filename = fname[0]

            if not detected_filename:
                potential_name = download_url.split('/')[-1].split('?')[0]
                if potential_name:
                    detected_filename = f"{potential_name}.apk" if not potential_name.lower().endswith(
                        '.apk') else potential_name

            if not detected_filename:
                detected_filename = f"{env_name.lower()}_downloaded_{int(time.time())}.apk"  # 提供一個唯一的備用檔名

            # 核心邏輯：如果檔名存在且與現有檔名不同，則觸發通知
            if existing_filename and detected_filename != existing_filename:
                title = f"【{env_name}】版本更新通知！"
                message = f"偵測到新版本！\n舊檔名: {existing_filename}\n新檔名: {detected_filename}"
                print(f"\n{bcolors.OKCYAN}{'=' * 20} {title} {'=' * 20}{bcolors.ENDC}")
                print(f"{bcolors.WARNING}{message.replace(chr(10), ' ')}{bcolors.ENDC}\n")

                # 發送桌面通知 (如果 plyer 存在)
                if notification:
                    try:
                        notification.notify(title=title, message=message, app_name='icash Pay 監控程式', timeout=20)
                        print(f"{bcolors.OKGREEN}已發送桌面通知。{bcolors.ENDC}")
                    except Exception as e:
                        print(f"{bcolors.WARNING}發送桌面通知失敗: {e}{bcolors.ENDC}")

                # 發送 Slack 通知
                send_slack_notification(SLACK_WEBHOOK_URL, env_name, existing_filename, detected_filename)

                # 刪除舊檔案
                try:
                    old_filepath = os.path.join(save_directory, existing_filename)
                    if os.path.exists(old_filepath):
                        os.remove(old_filepath)
                        print(f"已刪除舊檔案: {old_filepath}")
                except OSError as e:
                    print(f"{bcolors.WARNING}刪除舊檔案 {existing_filename} 失敗: {e}{bcolors.ENDC}")

            elif existing_filename == detected_filename:
                print(f"[{env_name}] 版本無變化，檔名相同: {detected_filename}")
                return  # 版本相同，無需下載，直接結束

            # 儲存檔案
            local_filepath = os.path.join(save_directory, detected_filename)
            print(f"檔案將儲存至: {local_filepath}")
            with open(local_filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"{bcolors.OKGREEN}[{env_name}] 檔案下載/更新成功！{bcolors.ENDC}")

    except requests.exceptions.RequestException as e:
        print(f"{bcolors.FAIL}[{env_name}] 檔案下載失敗: {e}{bcolors.ENDC}")
    except Exception as e:
        print(f"{bcolors.FAIL}[{env_name}] 處理下載時發生未預期錯誤: {e}{bcolors.ENDC}")


def check_environment(env_name, config):
    """
    對單一環境執行完整的檢查、下載與比對流程。

    Args:
        env_name (str): 環境的名稱 (e.g., "SIT")。
        config (dict): 該環境的設定字典。
    """
    print(f"--- 開始處理 {env_name} ---")
    initial_url = config["url"]
    save_dir = config["save_dir"]
    prefix = config["prefix"]

    # 建立儲存目錄
    os.makedirs(save_dir, exist_ok=True)

    # 尋找現有檔案
    existing_filename = find_existing_apk(save_dir, prefix)
    if existing_filename:
        print(f"找到現有 {env_name} 檔案: {existing_filename}")
    else:
        print(f"目錄 [{save_dir}] 中未找到現有的 {env_name} 檔案。")

    print(f"使用瀏覽器模式解析 [{env_name}] 頁面: {initial_url}")
    driver = None
    try:
        driver = setup_driver()
        if not driver:  # 如果 driver 初始化失敗，則跳過此環境
            return

        wait = WebDriverWait(driver, 20)  # 增加等待時間
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

        if not final_download_url or final_download_url.strip() in ['#', 'javascript:;']:
            print(f"{bcolors.FAIL}錯誤：在 {env_name} 的彈出視窗中獲取到的連結無效。{bcolors.ENDC}")
            return

        # 特殊處理 Dropbox 連結，轉換為直接下載格式
        if 'dl-web.dropbox.com' in final_download_url:
            final_download_url = final_download_url.replace('dl-web.dropbox.com', 'dl.dropboxusercontent.com')
            print("偵測到 Dropbox 連結，已自動轉換為直接下載格式。")

        print("成功在頁面中找到下載連結，將開始下載...")
        download_and_compare(env_name, final_download_url, save_dir, existing_filename)

    except TimeoutException:
        print(f"{bcolors.FAIL}錯誤：等待 {env_name} 頁面元素載入超時。可能是網路問題或頁面結構已變更。{bcolors.ENDC}")
    except NoSuchElementException:
        print(f"{bcolors.FAIL}錯誤：在 {env_name} 頁面中無法找到指定的元素。請檢查 XPath 是否仍然有效。{bcolors.ENDC}")
    except WebDriverException as e:
        print(
            f"{bcolors.FAIL}錯誤：瀏覽器自動化 (Selenium) 執行失敗。請確認 Chrome 已安裝。錯誤: {str(e)[:200]}{bcolors.ENDC}")
    except Exception as e:
        print(f"{bcolors.FAIL}處理 {env_name} 時發生未預期錯誤: {e}{bcolors.ENDC}")
    finally:
        if driver:
            driver.quit()


def main():
    """主執行函式，包含無限迴圈來定期檢查。"""
    print("=" * 60)
    print(f"= {bcolors.BOLD}icash Pay APK 監控程式已啟動{bcolors.ENDC} =")
    print(f"= 每 {int(CHECK_INTERVAL_SECONDS / 60)} 分鐘會自動檢查一次版本        =")
    print(f"= {bcolors.OKCYAN}請保持此視窗開啟，可按 Ctrl+C 來中止程式{bcolors.ENDC}      =")
    print("=" * 60)

    if not SLACK_WEBHOOK_URL:
        print(f"\n{bcolors.WARNING}警告：未在 .env 檔案中找到 'SLACK_WEBHOOK_URL'。")
        print(f"程式將繼續執行，但無法發送 Slack 通知。{bcolors.ENDC}")

    while True:
        print(
            f"\n{bcolors.HEADER}>>> 開始新一輪檢查 @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} <<<{bcolors.ENDC}")
        for env_name, config in ENVIRONMENTS.items():
            check_environment(env_name, config)
            print("-" * 40)
            time.sleep(5)  # 在檢查不同環境之間稍作停頓

        print("\n--- 本次所有環境檢查完成 ---")
        next_check_time = datetime.now() + timedelta(seconds=CHECK_INTERVAL_SECONDS)
        print(f"下次檢查時間: {next_check_time.strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            time.sleep(CHECK_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print(f"\n{bcolors.WARNING}偵測到 Ctrl+C，正在中止程式...{bcolors.ENDC}")
            break


if __name__ == "__main__":
    main()