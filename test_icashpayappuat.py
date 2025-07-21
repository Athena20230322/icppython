import time
import os
import random
import string
from datetime import datetime
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- ✨ Capabilities 設定 (維持不變) ✨ ---
capabilities = {
    "platformName": "Android",
    "appium:platformVersion": "11",
    "appium:deviceName": "emulator-5554",
    "appium:appPackage": "tw.com.icash.a.icashpay.prod",
    "appium:noReset": True,
    "appium:automationName": "UiAutomator2",
    "appium:allowSecureScreenshots": True,
    "appium:autoGrantPermissions": True,
}

appium_options = UiAutomator2Options().load_capabilities(capabilities)
APPIUM_SERVER_URL = 'http://127.0.0.1:4723'

# --- ✨ 所有函式維持不變 ✨ ---
INFO_FILE_PATH = r"C:\icppython\icashpayappinfouat.txt"
DEFAULT_START_PHONE = "0960000102"


def get_next_registration_info(file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    last_phone = DEFAULT_START_PHONE
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if lines:
                last_line = lines[-1].strip()
                if last_line:
                    last_phone = last_line.split(',')[0].strip()
    except FileNotFoundError:
        print(f"找不到紀錄檔 {file_path}，將使用預設起始門號。")
    except Exception as e:
        print(f"讀取檔案時發生錯誤: {e}，將使用預設起始門號。")
    next_phone_number = str(int(last_phone) + 1).zfill(10)
    timestamp = datetime.now().strftime("%m%d%H%M%S")
    new_account_name = f"ic{timestamp}"
    return next_phone_number, new_account_name


def write_registration_info(file_path, phone, account, id_card):
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"{phone},{account},{id_card}\n")
        print(f"\n -> 已成功將資料寫入: {file_path}")
    except Exception as e:
        print(f"\n -> 寫入檔案時發生錯誤: {e}")


def generate_taiwan_id():
    first_letter = random.choice(string.ascii_uppercase)
    rest_numbers = ''.join(random.choices(string.digits, k=9))
    return f"{first_letter}{rest_numbers}"


next_phone, new_account = get_next_registration_info(INFO_FILE_PATH)
new_id_card = generate_taiwan_id()
# ----------------------------------------------------

with webdriver.Remote(APPIUM_SERVER_URL, options=appium_options) as driver:
    try:
        print("連線成功！開始執行測試步驟...")
        print(f"本次使用門號: {next_phone}")
        print(f"本次使用帳號: {new_account}")
        print(f"本次使用身分證號: {new_id_card}")

        # --- 步驟 1 到 6 維持不變 ---
        print("\n步驟 1: 等待並點擊 '付款碼' 按鈕...")
        payment_code_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((AppiumBy.ID, "tw.com.icash.a.icashpay.prod:id/home_text"))
        )
        payment_code_button.click()
        print(" -> '付款碼' 點擊成功！")

        print("\n步驟 2: 等待並點擊 '登入/註冊' 按鈕...")
        login_register_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((AppiumBy.ID, "tw.com.icash.a.icashpay.prod:id/text"))
        )
        login_register_button.click()
        print(" -> '登入/註冊' 點擊成功！")

        print("\n步驟 3: 等待並點擊 '註冊icash Pay' 按鈕...")
        register_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((AppiumBy.ID, "tw.com.icash.a.icashpay.prod:id/btRegister"))
        )
        register_button.click()
        print(" -> '註冊icash Pay' 點擊成功！")

        print("\n步驟 4: 開始填寫註冊資料...")
        phone_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((AppiumBy.ID, "tw.com.icash.a.icashpay.prod:id/user_phones_text"))
        )
        phone_field.send_keys(next_phone)
        account_field = driver.find_element(by=AppiumBy.ID, value="tw.com.icash.a.icashpay.prod:id/user_code_text")
        account_field.send_keys(new_account)
        password_field = driver.find_element(by=AppiumBy.ID, value="tw.com.icash.a.icashpay.prod:id/user_pwd_text")
        password_field.send_keys("Aa123456")
        confirm_password_field = driver.find_element(by=AppiumBy.ID,
                                                     value="tw.com.icash.a.icashpay.prod:id/user_double_confirm_pwd_text")
        confirm_password_field.send_keys("Aa123456")
        checkboxes = driver.find_elements(by=AppiumBy.CLASS_NAME, value="android.widget.CheckBox")
        for checkbox in checkboxes:
            checkbox.click()
        next_step_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((AppiumBy.ID, "tw.com.icash.a.icashpay.prod:id/leftButton"))
        )
        next_step_button.click()
        print(" -> 步驟 4 完成！")

        print("\n步驟 5: 等待並點擊 '送出' 按鈕...")
        submit_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((AppiumBy.ID, "tw.com.icash.a.icashpay.prod:id/leftButton"))
        )
        submit_button.click()
        print(" -> '送出' 點擊成功！")

        print("\n步驟 6: 等待並點擊 '國民身分證'...")
        id_card_option = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((AppiumBy.XPATH, "//android.widget.TextView[@text='國民身分證']"))
        )
        id_card_option.click()
        print(" -> '國民身分證' 點擊成功！")

        print("\n步驟 7: 開始填寫身分驗證資料...")
        # 7.1 輸入姓名
        name_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((AppiumBy.ID, "tw.com.icash.a.icashpay.prod:id/et_user_name"))
        )
        name_field.send_keys("測試一")
        print(" -> 已輸入姓名: 測試一")
        # 7.2 輸入身分證號
        id_no_field = driver.find_element(by=AppiumBy.ID, value="tw.com.icash.a.icashpay.prod:id/et_id_no")
        id_no_field.send_keys(new_id_card)
        print(f" -> 已輸入身分證號: {new_id_card}")

        # --- ✨ 7.3 修正：處理滾動式日期選擇器 ✨ ---
        print(" -> 處理發證日期...")
        issue_date_field = driver.find_element(by=AppiumBy.ID, value="tw.com.icash.a.icashpay.prod:id/id_issue_date")
        issue_date_field.click()

        # 等待日期選擇器出現 (以「確定」按鈕作為標的)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((AppiumBy.XPATH, "//*[@text='確定']"))
        )

        # 找到所有滾輪 (它們的 class 通常是 android.widget.NumberPicker)
        pickers = driver.find_elements(by=AppiumBy.CLASS_NAME, value="android.widget.NumberPicker")

        # 設定年、月、日
        # 注意：傳入的文字必須和滾輪上顯示的完全一樣！
        print("    -> 滾動年份...")
        pickers[0].send_keys("民國89年")
        print("    -> 滾動月份...")
        pickers[1].send_keys("01月")
        print("    -> 滾動日期...")
        pickers[2].send_keys("01日")

        # 點擊確定
        driver.find_element(by=AppiumBy.XPATH, value="//*[@text='確定']").click()
        print(" -> 已確認發證日期: 民國89年01月01日")
        # --- (日期處理結束) ---

        # 7.4 點擊發證地點並選擇「北市」
        issue_location_field = driver.find_element(by=AppiumBy.ID,
                                                   value="tw.com.icash.a.icashpay.prod:id/issue_loc_text")
        issue_location_field.click()
        taipei_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((AppiumBy.XPATH, "//android.widget.TextView[@text='北市']"))
        )
        taipei_option.click()
        print(" -> 已選擇發證地點: 北市")

        # 7.5 點擊領補換類別「初發」
        first_issue_button = driver.find_element(by=AppiumBy.XPATH, value="//android.widget.Button[@text='初發']")
        first_issue_button.click()
        print(" -> 已選擇領補換類別: 初發")

        # 7.6 點擊最後的「下一步」
        final_next_button = driver.find_element(by=AppiumBy.XPATH, value="//android.widget.Button[@text='下一步']")
        final_next_button.click()
        print(" -> 已點擊最後的下一步")

        write_registration_info(INFO_FILE_PATH, next_phone, new_account, new_id_card)
        print("\n測試流程執行完畢！ ✅")
        time.sleep(5)

    except TimeoutException as e:
        print(f"錯誤：在指定時間內找不到元素，請檢查定位條件是否正確。 錯誤訊息: {e}")
    except Exception as e:
        print(f"發生未預期的錯誤: {e}")