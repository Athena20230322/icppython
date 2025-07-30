import requests
import os
import re
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin

# 匯入 Selenium 相關工具
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
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


class bcolors:
    WARNING = '\033[91m'
    ENDC = '\033[0m'


def find_existing_apk(directory, prefix):
    """在指定目錄中尋找已存在的 APK 檔案。"""
    if not os.path.isdir(directory): return None
    for filename in os.listdir(directory):
        # 使用 upper() 進行不分大小寫的比對
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
        # 使用 requests 下載檔案，設定超時為 300 秒
        with requests.get(download_url, stream=True, headers=headers, allow_redirects=True, timeout=300) as r:
            r.raise_for_status()
            # 從 HTTP 標頭中嘗試取得檔案名稱
            content_disposition = r.headers.get('content-disposition')
            if content_disposition:
                fname = re.findall('filename="?([^"]+)"?', content_disposition)
                if fname: detected_filename = fname[0]

            # 如果標頭中沒有檔名，則從 URL 中推斷
            if not detected_filename:
                potential_name = download_url.split('/')[-1].split('?')[0]
                if not potential_name.lower().endswith('.apk'):
                    detected_filename = f"{potential_name}.apk" if potential_name else f"{file_type.lower()}.apk"
                else:
                    detected_filename = potential_name

            # 核心邏輯：比對新舊檔名
            if detected_filename and existing_filename_to_compare and detected_filename != existing_filename_to_compare:
                title = f"{file_type.upper()} 版本更新通知！"
                message = f"偵測到新版本！\n現有檔名: {existing_filename_to_compare}\n新版本檔名: {detected_filename}"
                print(f"{bcolors.WARNING}==================== {title} ===================={bcolors.ENDC}")
                print(f"{bcolors.WARNING}警告：{message.replace(chr(10), ' ')}{bcolors.ENDC}")
                # 如果 plyer 成功匯入，則發送桌面通知
                if notification:
                    notification.notify(title=title, message=message, app_name='icash Pay 監控程式', timeout=20)

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
    此函式現在可同時處理 SIT 和 UAT。
    """
    print(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 使用瀏覽器模式解析 [{env_type.upper()}] 頁面: {initial_url}")

    # 設定 Chrome 瀏覽器選項 (無頭模式)
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

    driver = None
    try:
        # 自動下載並設定 ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.get(initial_url)
        time.sleep(5)  # 等待頁面 JavaScript 可能的加載

        # --- (***程式碼修改處***) 使用通用的新版 XPath 定位 <a> 標籤 ---
        # 調整後的 XPath 直接指向 <a> 標籤以獲取 href
        target_xpath = "//*[@id='app']/div[1]/div[4]/div/div[2]/div[4]/div[2]/a"
        print(f"正在使用更新後的 XPath 嘗試定位: {target_xpath}")
        target_link = driver.find_element(By.XPATH, target_xpath)

        # 取得 <a> 標籤的 'href' 屬性，即為下載連結
        final_download_url = target_link.get_attribute('href')

        # --- 針對 Dropbox 連結進行特殊處理 ---
        # 這個修改是為了繞過 Dropbox 的直接下載限制
        if 'dl-web.dropbox.com' in final_download_url:
            original_url = final_download_url
            final_download_url = final_download_url.replace('dl-web.dropbox.com', 'dl.dropboxusercontent.com')
            print(f"偵測到 Dropbox 連結，已自動嘗試轉換為直接下載格式。")
            print(f"  - 原始連結: {original_url}")
            print(f"  - 轉換後: {final_download_url}")

        print(f"成功在頁面中找到下載連結，將開始下載...")

        # 呼叫通用下載與比對函式
        download_and_compare(env_type.upper(), final_download_url, save_directory, existing_filename)

    except NoSuchElementException:
        print(f"錯誤：使用 XPath '{target_xpath}' 無法在 {env_type.upper()} 頁面中找到指定的下載連結元素。")
    except (TimeoutException, WebDriverException) as e:
        print(f"錯誤：瀏覽器自動化 (Selenium) 執行失敗。請確認 Chrome 已安裝。錯誤訊息: {str(e)[:200]}")
    except Exception as e:
        print(f"處理 {env_type.upper()} 時發生未預期錯誤: {e}")
    finally:
        # 確保瀏覽器在結束時關閉
        if driver:
            driver.quit()


def run_check():
    """執行一次完整的檢查與下載流程"""
    # --- UAT 處理區塊 ---
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

    print("\n" + "=" * 50 + "\n")

    # --- SIT 處理區塊 ---
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


if __name__ == "__main__":
    CHECK_INTERVAL_SECONDS = 60 * 30  # 檢查間隔 (30分鐘)
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
