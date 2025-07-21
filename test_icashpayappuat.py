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
    "appium:platformVersion": "14",
    "appium:deviceName": "R5CT925Z7CA",
    "appium:appPackage": "tw.com.icash.a.icashpay.prod",
    "appium:noReset": True,
    "appium:automationName": "UiAutomator2",
    "appium:allowSecureScreenshots": True,
    "appium:autoGrantPermissions": True,
    "appium:adbExecTimeout": 60000,
    "appium:uiautomator2ServerLaunchTimeout": 60000
}

appium_options = UiAutomator2Options().load_capabilities(capabilities)
APPIUM_SERVER_URL = 'http://127.0.0.1:4723'

# --- ✨ 所有函式維持不變 ✨ ---
INFO_FILE_PATH = r"C:\icppython\icashpayappinfouat.txt"
DEFAULT_START_PHONE = "0970000104"


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


# --- ✨ 修正：產生有效的台灣身分證字號 ✨ ---
def generate_taiwan_id():
    """
    根據台灣身分證字號規則產生一組有效的隨機號碼。
    """
    # 縣市代碼與其對應數值的字典
    letter_map = {
        'A': 10, 'B': 11, 'C': 12, 'D': 13, 'E': 14, 'F': 15, 'G': 16, 'H': 17, 'I': 34,
        'J': 18, 'K': 19, 'L': 20, 'M': 21, 'N': 22, 'O': 35, 'P': 23, 'Q': 24, 'R': 25,
        'S': 26, 'T': 27, 'U': 28, 'V': 29, 'W': 32, 'X': 30, 'Y': 31, 'Z': 33
    }

    # 隨機選擇一個縣市開頭字母
    first_letter = random.choice(list(letter_map.keys()))

    # 隨機選擇性別碼 (1=男, 2=女)
    gender_digit = str(random.choice([1, 2]))

    # 產生 7 位隨機數字
    middle_digits = ''.join(random.choices(string.digits, k=7))

    # --- 開始計算校驗碼 ---

    # 將開頭字母轉換為兩位數字
    letter_value = letter_map[first_letter]
    n1 = letter_value // 10
    n2 = letter_value % 10

    # 組合出身分證號的前8碼數字部分 (性別 + 7位隨機數)
    body_digits = gender_digit + middle_digits

    # 根據加權規則計算總和
    # 權重: 1, 9, 8, 7, 6, 5, 4, 3, 2, 1
    total_sum = n1 * 1 + n2 * 9

    # ✨ 修正：補上缺少的加權值 1
    weights = [8, 7, 6, 5, 4, 3, 2, 1]

    for i in range(len(body_digits)):
        total_sum += int(body_digits[i]) * weights[i]

    # 計算校驗碼 (最後一位)
    checksum = (10 - (total_sum % 10)) % 10

    # 組合出完整的身分證字號
    valid_id = f"{first_letter}{body_digits}{checksum}"

    print(f"\n -> 產生有效身分證號: {valid_id}")
    return valid_id


# --- ✨ 滑動手勢輔助函式 (維持不變) ✨ ---
def swipe_by_coordinates(driver, x, start_y, end_y, swipes=1):
    """
    在指定的固定座標區域執行滑動手勢

    :param driver: Appium driver 物件
    :param x: 滑動的 X 軸座標
    :param start_y: 滑動的起始 Y 軸座標
    :param end_y: 滑動的結束 Y 軸座標
    :param swipes: 滑動次數
    """
    # 根據起始和結束Y座標判斷滑動方向
    # 如果 start_y < end_y，代表手指向下移動，內容向上滾動（數字變小）
    direction = 'down' if start_y < end_y else 'up'
    print(f"    -> 在座標 x={x} 從 y={start_y} 滑動到 y={end_y} (方向: {direction})")

    for i in range(swipes):
        try:
            # 使用 ADB shell input swipe 更為直接可靠
            command_args = ['input', 'swipe', str(x), str(start_y), str(x), str(end_y), '300']  # 300ms duration
            driver.execute_script('mobile: shell', {
                'command': command_args[0],
                'args': command_args[1:]
            })
            time.sleep(0.5)  # 每次滑動後停頓更久，確保動畫完成
        except Exception as e:
            print(f"      -> 第 {i + 1} 次滑動時發生錯誤: {e}")
            pass


# --- ✨ 新增：透過 Keycode 輸入 PIN 碼的輔助函式 ✨ ---
def enter_pin_by_keycode(driver, pin):
    """
    使用 Android Keycode 來輸入數字 PIN 碼。

    :param driver: Appium driver 物件
    :param pin: 要輸入的 PIN 碼字串, e.g., "246790"
    """
    # Android 數字 Keycode 對照表
    # KEYCODE_0=7, KEYCODE_1=8, ..., KEYCODE_9=16
    keycode_map = {str(i): i + 7 for i in range(10)}

    print(f"    -> 準備使用 Keycode 輸入 PIN: {pin}")
    for digit in pin:
        if digit in keycode_map:
            driver.press_keycode(keycode_map[digit])
            print(f"      -> 已輸入數字: {digit}")
            time.sleep(0.2)  # 模擬輸入間隔
        else:
            print(f"      -> 警告：字元 '{digit}' 不是有效的數字，已略過。")


# --- ✨ 在執行測試前，就先產生並寫入新資料 (維持不變) ✨ ---
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
        # --- ✨ 7.1 修正：調整操作順序 ✨ ---
        # 步驟 7.1: 輸入姓名
        name_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((AppiumBy.ID, "tw.com.icash.a.icashpay.prod:id/et_user_name"))
        )
        name_field.send_keys("測試一")
        print(" -> 已輸入姓名: 測試一")

        # 步驟 7.2: 處理出生年月日
        print(" -> 處理出生年月日...")
        dob_target_id = "tw.com.icash.a.icashpay.prod:id/textView13"
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

        submit_button_locator = (AppiumBy.ID, "tw.com.icash.a.icashpay.prod:id/btnSubmit")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(submit_button_locator)
        )
        print("    -> 日期選擇器已出現")

        # --- ✨ 終極修正：精準調整滑動次數 ✨ ---
        # 說明：Y 軸座標從 1000 (上方) -> 1200 (下方)，模擬手指向下滑動，讓滾輪向上滾動（數字變小）。

        # 滾動年份 (X座標約在 210 附近)
        # 計算方式：從民國100年滾動到89年，約需 11 年，每次滑動約 4 年，11 / 4 ≈ 3 次。
        print("    -> 開始滾動年份...")
        swipe_by_coordinates(driver, x=210, start_y=1000, end_y=1200, swipes=3)

        # 滾動月份 (X座標約在 555 附近)
        # 假設預設是 7 月，目標是 1 月，約需滑動 6 次。
        print("    -> 開始滾動月份...")
        swipe_by_coordinates(driver, x=555, start_y=1000, end_y=1200, swipes=8)

        # 滾動日期 (X座標約在 885 附近)
        # 假設預設是 20 日，目標是 1 日，約需滑動 19 次。
        print("    -> 開始滾動日期...")
        swipe_by_coordinates(driver, x=885, start_y=1000, end_y=1200, swipes=25)

        # 點擊確定按鈕 (改用最可靠的 ADB Tap)
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

        # 步驟 7.3: 最後才輸入身分證號
        id_no_field = driver.find_element(by=AppiumBy.ID, value="tw.com.icash.a.icashpay.prod:id/et_id_no")
        id_no_field.send_keys(new_id_card)
        print(f" -> 已輸入身分證號: {new_id_card}")

        # 步驟 7.4: 處理身分證發證日期 (不滾動，直接確定)
        print(" -> 處理身分證發證日期...")
        issue_date_target_id = "tw.com.icash.a.icashpay.prod:id/textView43"
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

        submit_button_locator = (AppiumBy.ID, "tw.com.icash.a.icashpay.prod:id/btnSubmit")
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

        # 步驟 7.5: 處理身分證發證地點
        print(" -> 處理身分證發證地點...")
        issue_location_id = "tw.com.icash.a.icashpay.prod:id/tv_issue_loc"
        print(f"    -> 點擊 '{issue_location_id}'")
        driver.find_element(by=AppiumBy.ID, value=issue_location_id).click()
        time.sleep(1)  # 等待彈窗

        new_taipei_xpath = "//android.widget.TextView[@text='北縣 / 新北市']"
        print(f"    -> 選擇 '{new_taipei_xpath}'")
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((AppiumBy.XPATH, new_taipei_xpath))
        ).click()
        print(" -> 已選擇發證地點: 北縣 / 新北市")

        # 步驟 7.6: 選擇領補換類別
        print(" -> 選擇領補換類別...")
        first_issue_id = "tw.com.icash.a.icashpay.prod:id/rb_register_id_issued_first"
        print(f"    -> 點擊 '{first_issue_id}' (初發)")
        driver.find_element(by=AppiumBy.ID, value=first_issue_id).click()
        print(" -> 已選擇領補換類別: 初發")

        # --- ✨ 7.7 新增：向上滑動頁面以顯示「下一步」按鈕 ✨ ---
        print(" -> 向上滑動頁面...")
        # 獲取螢幕尺寸以進行相對滑動，從螢幕80%高度滑動到20%高度
        window_size = driver.get_window_size()
        start_x = window_size['width'] // 2
        start_y = int(window_size['height'] * 0.8)
        end_y = int(window_size['height'] * 0.2)

        command_args = ['input', 'swipe', str(start_x), str(start_y), str(start_x), str(end_y), '500']  # 500ms duration
        driver.execute_script('mobile: shell', {
            'command': command_args[0],
            'args': command_args[1:]
        })
        time.sleep(1)  # 等待滑動完成
        print(" -> 頁面已向上滑動")

        # 步驟 7.8: 點擊最後的「下一步」
        print(" -> 點擊最後的下一步按鈕...")
        final_next_button_id = "tw.com.icash.a.icashpay.prod:id/leftButton"
        print(f"    -> 點擊 '{final_next_button_id}'")
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((AppiumBy.ID, final_next_button_id))
        ).click()
        print(" -> 已點擊最後的下一步")

        # 步驟 7.9: 點擊資料確認頁的「確認」按鈕
        print(" -> 點擊資料確認頁的「確認」按鈕...")
        confirm_data_button_id = "tw.com.icash.a.icashpay.prod:id/leftButton"
        print(f"    -> 等待並點擊 '{confirm_data_button_id}'")
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((AppiumBy.ID, confirm_data_button_id))
        ).click()
        print(" -> 已點擊「確認」")

        # --- ✨ 步驟 8: 設定安全密碼 ✨ ---
        print("\n步驟 8: 設定安全密碼...")
        security_pin = "246790"

        # 等待「請輸入安全密碼」的標題出現，確保頁面已載入
        pin_description_id = "tw.com.icash.a.icashpay.prod:id/security_password_description"
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((AppiumBy.ID, pin_description_id))
        )
        print(" -> 安全密碼頁面已載入")

        # 點擊第一個密碼輸入區以觸發鍵盤
        first_pin_area_id = "tw.com.icash.a.icashpay.prod:id/nativeKeyboardPasswordLayout"
        print(f"    -> 點擊第一個密碼輸入區 '{first_pin_area_id}'")
        driver.find_element(AppiumBy.ID, first_pin_area_id).click()
        time.sleep(1)

        # 輸入第一組 PIN
        enter_pin_by_keycode(driver, security_pin)

        # 點擊第二個密碼輸入區
        second_pin_area_id = "tw.com.icash.a.icashpay.prod:id/doubleConfirmNativeKeyboardPasswordLayout"
        print(f"    -> 點擊第二個密碼輸入區 '{second_pin_area_id}'")
        driver.find_element(AppiumBy.ID, second_pin_area_id).click()
        time.sleep(1)

        # 輸入第二組 PIN
        enter_pin_by_keycode(driver, security_pin)
        print(" -> 已完成兩次密碼輸入")

        # --- ✨ 步驟 8.1: 點擊最後的「確認」按鈕 ✨ ---
        print(" -> 點擊最後的「確認」按鈕...")
        final_confirm_button_id = "tw.com.icash.a.icashpay.prod:id/tvConfirm"
        print(f"    -> 等待並點擊 '{final_confirm_button_id}'")
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((AppiumBy.ID, final_confirm_button_id))
        ).click()
        print(" -> 已點擊最終「確認」")

        # --- ✨ 步驟 9: 點擊最後的「下一步」按鈕 ✨ ---
        print("\n步驟 9: 點擊最後的「下一步」按鈕...")
        final_step_button_id = "tw.com.icash.a.icashpay.prod:id/leftButton"
        print(f"    -> 等待並點擊 '{final_step_button_id}'")
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((AppiumBy.ID, final_step_button_id))
        ).click()
        print(" -> 已點擊最後的「下一步」")

        print("\n註冊流程已全部完成！ ✅")
        time.sleep(5)

    except TimeoutException as e:
        print(f"\n錯誤：在指定時間内找不到元素，請檢查定位條件是否正確。 錯誤訊息: {e}")
    except Exception as e:
        print(f"\n發生未預期的錯誤: {e}")