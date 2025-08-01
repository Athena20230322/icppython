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

# --- ✨ Capabilities 設定 (已修改為無頭模式) ---
capabilities = {
    "platformName": "Android",
    "appium:platformVersion": "14",
 Updated upstream
    "appium:deviceName": "R5CR517P4XL",


    # --- ✨ 無頭模式 (Headless Mode) 設定 ✨ ---
    # 說明：無頭模式僅適用於「Android 模擬器」，不適用於真實手機。
    # Appium 會在背景幫您啟動並運行指定的模擬器，但不會顯示其視窗。

    # 1. 註解或刪除您原本的實體手機 deviceName
    # "appium:deviceName": "R5CR517P4XL",

    # 2. 指定您要使用的模擬器名稱 (此名稱需與您在 AVD Manager 中建立的相符)
    "appium:avd": "My_Emulator_34",  # <-- !! 請務必換成您自己的模擬器(AVD)名稱 !!

    # 3. 啟用無頭模式
    "appium:isHeadless": True,

    Stashed changes
    "appium:appPackage": "tw.com.icash.a.icashpay.debuging",
    "appium:noReset": True,
    "appium:automationName": "UiAutomator2",
    "appium:allowSecureScreenshots": True,
    "appium:autoGrantPermissions": True,
    "appium:adbExecTimeout": 60000,
    "appium:uiautomator2ServerLaunchTimeout": 60000
}


appium_options = UiAutomator2Options().load_capabilities(capabilities)
APPIUM_SERVER_URL = 'http://127.0.0.1:4723'

# --- ✨ 全域變數 ---
INFO_FILE_PATH = r"C:\icppython\icashpayappinfo.txt"
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
        print(f"\n -> 已成功將本次資料預先寫入: {file_path}")
    except Exception as e:
        print(f"\n -> 寫入檔案時發生錯誤: {e}")


def generate_taiwan_id():
    letter_map = {
        'A': 10, 'B': 11, 'C': 12, 'D': 13, 'E': 14, 'F': 15, 'G': 16, 'H': 17, 'I': 34,
        'J': 18, 'K': 19, 'L': 20, 'M': 21, 'N': 22, 'O': 35, 'P': 23, 'Q': 24, 'R': 25,
        'S': 26, 'T': 27, 'U': 28, 'V': 29, 'W': 32, 'X': 30, 'Y': 31, 'Z': 33
    }
    first_letter = random.choice(list(letter_map.keys()))
    gender_digit = str(random.choice([1, 2]))
    middle_digits = ''.join(random.choices(string.digits, k=7))
    letter_value = letter_map[first_letter]
    n1 = letter_value // 10
    n2 = letter_value % 10
    body_digits = gender_digit + middle_digits
    weights = [8, 7, 6, 5, 4, 3, 2, 1]
    total_sum = n1 * 1 + n2 * 9
    for i in range(len(body_digits)):
        total_sum += int(body_digits[i]) * weights[i]
    checksum = (10 - (total_sum % 10)) % 10
    valid_id = f"{first_letter}{body_digits}{checksum}"
    print(f"\n -> 產生有效身分證號: {valid_id}")
    return valid_id


def swipe_by_coordinates(driver, x, start_y, end_y, swipes=1):
    direction = 'down' if start_y < end_y else 'up'
    print(f"    -> 在座標 x={x} 從 y={start_y} 滑動到 y={end_y} (方向: {direction})")
    for i in range(swipes):
        try:
            command_args = ['input', 'swipe', str(x), str(start_y), str(x), str(end_y), '300']
            driver.execute_script('mobile: shell', {
                'command': command_args[0],
                'args': command_args[1:]
            })
            time.sleep(0.5)
        except Exception as e:
            print(f"      -> 第 {i + 1} 次滑動時發生錯誤: {e}")
            pass


def enter_pin_by_keycode(driver, pin):
    keycode_map = {str(i): i + 7 for i in range(10)}
    print(f"    -> 準備使用 Keycode 輸入 PIN: {pin}")
    for digit in pin:
        if digit in keycode_map:
            driver.press_keycode(keycode_map[digit])
            print(f"      -> 已輸入數字: {digit}")
            time.sleep(0.2)
        else:
            print(f"      -> 警告：字元 '{digit}' 不是有效的數字，已略過。")


# --- ✨ 在執行測試前，就先產生並寫入新資料 ---
print("步驟 0: 準備新的註冊資料並預先寫入紀錄檔...")
next_phone, new_account = get_next_registration_info(INFO_FILE_PATH)
new_id_card = generate_taiwan_id()
write_registration_info(INFO_FILE_PATH, next_phone, new_account, new_id_card)
# ----------------------------------------------------

with webdriver.Remote(APPIUM_SERVER_URL, options=appium_options) as driver:
    try:
        print("\n連線成功！開始執行測試步驟...")
        print(f"本次使用門號: {next_phone}")
        print(f"本次使用帳號: {new_account}")
        print(f"本次使用身分證號: {new_id_card}")

        # --- 步驟 1 到 3 ---
        print("\n步驟 1: 等待並點擊 '付款碼' 按鈕...")
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((AppiumBy.ID, "tw.com.icash.a.icashpay.debuging:id/home_text"))).click()
        print(" -> '付款碼' 點擊成功！")

        print("\n步驟 2: 等待並點擊 '登入/註冊' 按鈕...")
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((AppiumBy.ID, "tw.com.icash.a.icashpay.debuging:id/text"))).click()
        print(" -> '登入/註冊' 點擊成功！")

        print("\n步驟 3: 等待並點擊 '註冊icash Pay' 按鈕...")
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((AppiumBy.ID, "tw.com.icash.a.icashpay.debuging:id/btRegister"))).click()
        print(" -> '註冊icash Pay' 點擊成功！")

        # --- 步驟 4: 填寫註冊資料 (使用之前正常的勾選邏輯) ---
        print("\n步驟 4: 開始填寫註冊資料...")
        WebDriverWait(driver, 20).until(EC.presence_of_element_located(
            (AppiumBy.ID, "tw.com.icash.a.icashpay.debuging:id/user_phones_text"))).send_keys(next_phone)
        driver.find_element(by=AppiumBy.ID, value="tw.com.icash.a.icashpay.debuging:id/user_code_text").send_keys(
            new_account)
        driver.find_element(by=AppiumBy.ID, value="tw.com.icash.a.icashpay.debuging:id/user_pwd_text").send_keys(
            "Aa123456")
        driver.find_element(by=AppiumBy.ID,
                            value="tw.com.icash.a.icashpay.debuging:id/user_double_confirm_pwd_text").send_keys(
            "Aa123456")

        print(" -> 勾選前兩個同意選項...")
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
            (AppiumBy.ID, "tw.com.icash.a.icashpay.debuging:id/cb_register_policies"))).click()
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
            (AppiumBy.ID, "tw.com.icash.a.icashpay.debuging:id/cb_op_register_policies"))).click()

        print(" -> 向上滑動頁面以顯示所有選項...")
        window_size = driver.get_window_size()
        start_x_swipe = window_size['width'] // 2
        start_y_swipe = int(window_size['height'] * 0.7)
        end_y_swipe = int(window_size['height'] * 0.3)
        swipe_by_coordinates(driver, start_x_swipe, start_y_swipe, end_y_swipe, swipes=1)
        time.sleep(1)

        print(" -> 勾選第三個核取方塊...")
        try:
            cb3_id = "tw.com.icash.a.icashpay.debuging:id/cb_register_policies_2"
            checkbox3 = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((AppiumBy.ID, cb3_id)))
            if not checkbox3.is_selected():
                checkbox3.click()
            print("   -> 已勾選第三個核取方塊。")
        except Exception as e:
            print(f" -> 點擊第三個核取方塊時發生錯誤: {e}")

        print(" -> 為確保 '下一步' 按鈕可見，再次向上滑動...")
        swipe_by_coordinates(driver, start_x_swipe, start_y_swipe, end_y_swipe, swipes=1)
        time.sleep(1)

        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((AppiumBy.ID, "tw.com.icash.a.icashpay.debuging:id/leftButton"))).click()
        print(" -> 步驟 4 完成！")

        # --- 步驟 5 和 6 ---
        print("\n步驟 5: 等待並點擊 '送出' 按鈕...")
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((AppiumBy.ID, "tw.com.icash.a.icashpay.debuging:id/leftButton"))).click()
        print(" -> '送出' 點擊成功！")

        print("\n步驟 6: 等待並點擊 '國民身分證'...")
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((AppiumBy.XPATH, "//android.widget.TextView[@text='國民身分證']"))).click()
        print(" -> '國民身分證' 點擊成功！")

        # =======================================================================
        # --- ✨ 步驟 7: 整合您提供且可正常執行的身分驗證程式碼 ✨ ---
        # =======================================================================
        print("\n步驟 7: 開始填寫身分驗證資料...")
        name_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((AppiumBy.ID, "tw.com.icash.a.icashpay.debuging:id/et_user_name"))
        )
        name_field.send_keys("測試一")
        print(" -> 已輸入姓名: 測試一")

        print(" -> 處理出生年月日...")
        dob_target_id = "tw.com.icash.a.icashpay.debuging:id/textView13"
        print(f"    -> 使用 ID 定位點擊目標 '{dob_target_id}'")
        dob_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((AppiumBy.ID, dob_target_id))
        )
        print("    -> 目標元件已定位")

        location = dob_field.location
        size = dob_field.size
        x = location['x'] + (size['width'] / 2)
        y = location['y'] + (size['height'] / 2)

        print(f"    -> 使用 'mobile: shell' (adb tap) 腳本點擊座標: x={int(x)}, y={int(y)}")
        command_args = ['input', 'tap', str(int(x)), str(int(y))]
        driver.execute_script('mobile: shell', {
            'command': command_args[0],
            'args': command_args[1:]
        })
        print("    -> ADB Tap 動作已執行")
        time.sleep(2)

        submit_button_locator = (AppiumBy.ID, "tw.com.icash.a.icashpay.debuging:id/btnSubmit")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(submit_button_locator)
        )
        print("    -> 日期選擇器已出現")

        print("    -> 開始滾動年份...")
        swipe_by_coordinates(driver, x=210, start_y=1000, end_y=1200, swipes=3)

        print("    -> 開始滾動月份...")
        swipe_by_coordinates(driver, x=555, start_y=1000, end_y=1200, swipes=8)

        print("    -> 開始滾動日期...")
        swipe_by_coordinates(driver, x=885, start_y=1000, end_y=1200, swipes=25)

        submit_button = driver.find_element(*submit_button_locator)
        location = submit_button.location
        size = submit_button.size
        x = location['x'] + (size['width'] / 2)
        y = location['y'] + (size['height'] / 2)
        print(f"    -> 使用 ADB Tap 點擊「確定」按鈕於座標 x={int(x)}, y={int(y)}")
        command_args = ['input', 'tap', str(int(x)), str(int(y))]
        driver.execute_script('mobile: shell', {
            'command': command_args[0],
            'args': command_args[1:]
        })
        print(" -> 已確認出生年月日")

        id_no_field = driver.find_element(by=AppiumBy.ID, value="tw.com.icash.a.icashpay.debuging:id/et_id_no")
        id_no_field.send_keys(new_id_card)
        print(f" -> 已輸入身分證號: {new_id_card}")

        print(" -> 處理身分證發證日期...")
        issue_date_target_id = "tw.com.icash.a.icashpay.debuging:id/textView43"
        print(f"    -> 使用 ID 定位點擊目標 '{issue_date_target_id}'")
        issue_date_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((AppiumBy.ID, issue_date_target_id))
        )
        print("    -> 目標元件已定位")

        location = issue_date_field.location
        size = issue_date_field.size
        x = location['x'] + (size['width'] / 2)
        y = location['y'] + (size['height'] / 2)

        print(f"    -> 使用 'mobile: shell' (adb tap) 腳本點擊座標: x={int(x)}, y={int(y)}")
        command_args = ['input', 'tap', str(int(x)), str(int(y))]
        driver.execute_script('mobile: shell', {
            'command': command_args[0],
            'args': command_args[1:]
        })
        print("    -> ADB Tap 動作已執行")
        time.sleep(2)

        submit_button_locator = (AppiumBy.ID, "tw.com.icash.a.icashpay.debuging:id/btnSubmit")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(submit_button_locator)
        )
        print("    -> 日期選擇器已出現")
        print("    -> 不執行滾動，直接接受預設日期")

        submit_button = driver.find_element(*submit_button_locator)
        location = submit_button.location
        size = submit_button.size
        x = location['x'] + (size['width'] / 2)
        y = location['y'] + (size['height'] / 2)
        print(f"    -> 使用 ADB Tap 點擊「確定」按鈕於座標 x={int(x)}, y={int(y)}")
        command_args = ['input', 'tap', str(int(x)), str(int(y))]
        driver.execute_script('mobile: shell', {
            'command': command_args[0],
            'args': command_args[1:]
        })
        print(" -> 已確認身分證發證日期")

        print(" -> 處理身分證發證地點...")
        issue_location_id = "tw.com.icash.a.icashpay.debuging:id/tv_issue_loc"
        print(f"    -> 點擊 '{issue_location_id}'")
        driver.find_element(by=AppiumBy.ID, value=issue_location_id).click()
        time.sleep(1)

        new_taipei_xpath = "//android.widget.TextView[@text='北縣 / 新北市']"
        print(f"    -> 選擇 '{new_taipei_xpath}'")
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((AppiumBy.XPATH, new_taipei_xpath))
        ).click()
        print(" -> 已選擇發證地點: 北縣 / 新北市")

        print(" -> 選擇領補換類別...")
        first_issue_id = "tw.com.icash.a.icashpay.debuging:id/rb_register_id_issued_first"
        print(f"    -> 點擊 '{first_issue_id}' (初發)")
        driver.find_element(by=AppiumBy.ID, value=first_issue_id).click()
        print(" -> 已選擇領補換類別: 初發")

        print(" -> 向上滑動頁面...")
        window_size = driver.get_window_size()
        start_x = window_size['width'] // 2
        start_y = int(window_size['height'] * 0.8)
        end_y = int(window_size['height'] * 0.2)
        command_args = ['input', 'swipe', str(start_x), str(start_y), str(start_x), str(end_y), '500']
        driver.execute_script('mobile: shell', {
            'command': command_args[0],
            'args': command_args[1:]
        })
        time.sleep(1)
        print(" -> 頁面已向上滑動")

        print(" -> 點擊最後的下一步按鈕...")
        final_next_button_id = "tw.com.icash.a.icashpay.debuging:id/leftButton"
        print(f"    -> 點擊 '{final_next_button_id}'")
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((AppiumBy.ID, final_next_button_id))
        ).click()
        print(" -> 已點擊最後的下一步")

        print(" -> 點擊資料確認頁的「確認」按鈕...")
        confirm_data_button_id = "tw.com.icash.a.icashpay.debuging:id/leftButton"
        print(f"    -> 等待並點擊 '{confirm_data_button_id}'")
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((AppiumBy.ID, confirm_data_button_id))
        ).click()
        print(" -> 已點擊「確認」")

        # --- 步驟 8 和 9 ---
        print("\n步驟 8: 設定安全密碼...")
        security_pin = "246790"
        pin_description_id = "tw.com.icash.a.icashpay.debuging:id/security_password_description"
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((AppiumBy.ID, pin_description_id)))
        print(" -> 安全密碼頁面已載入")

        first_pin_area_id = "tw.com.icash.a.icashpay.debuging:id/nativeKeyboardPasswordLayout"
        driver.find_element(AppiumBy.ID, first_pin_area_id).click()
        time.sleep(1)
        enter_pin_by_keycode(driver, security_pin)

        second_pin_area_id = "tw.com.icash.a.icashpay.debuging:id/doubleConfirmNativeKeyboardPasswordLayout"
        driver.find_element(AppiumBy.ID, second_pin_area_id).click()
        time.sleep(1)
        enter_pin_by_keycode(driver, security_pin)
        print(" -> 已完成兩次密碼輸入")

        final_confirm_button_id = "tw.com.icash.a.icashpay.debuging:id/tvConfirm"
        WebDriverWait(driver, 20).until(EC.element_to_be_clickable((AppiumBy.ID, final_confirm_button_id))).click()
        print(" -> 已點擊最終「確認」")

        print("\n步驟 9: 點擊最後的「下一步」按鈕...")
        final_step_button_id = "tw.com.icash.a.icashpay.debuging:id/leftButton"
        WebDriverWait(driver, 20).until(EC.element_to_be_clickable((AppiumBy.ID, final_step_button_id))).click()
        print(" -> 已點擊最後的「下一步」")

        print("\n註冊流程已全部完成！ ✅")
        time.sleep(5)

    except TimeoutException as e:
        print(f"\n錯誤：在指定時間内找不到元素，請檢查定位條件是否正確。 錯誤訊息: {e}")
    except Exception as e:
        print(f"\n發生未預期的錯誤: {e}")