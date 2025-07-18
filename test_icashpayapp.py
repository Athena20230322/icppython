import time
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- ✨ 修改 Capabilities ✨ ---
capabilities = {
    "platformName": "Android",
    "appium:platformVersion": "11",
    "appium:deviceName": "emulator-5554",
    "appium:appPackage": "tw.com.icash.a.icashpay.debuging",
    # 1. 移除 appActivity，讓 App 自行啟動
    # "appium:appActivity": "tw.com.icash.icashpay.framework.home.HomeActivity",
    "appium:noReset": True,
    "appium:automationName": "UiAutomator2",
    "appium:allowSecureScreenshots": True,
    # 2. 新增 autoGrantPermissions，自動處理權限彈窗
    "appium:autoGrantPermissions": True,
}
# -----------------------------

appium_options = UiAutomator2Options().load_capabilities(capabilities)
APPIUM_SERVER_URL = 'http://127.0.0.1:4723'

with webdriver.Remote(APPIUM_SERVER_URL, options=appium_options) as driver:
    try:
        print("連線成功！開始執行測試步驟...")

        # 後續的測試步驟完全不變
        print("步驟 1: 等待並點擊 '付款碼' 按鈕...")
        payment_code_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((AppiumBy.ID, "tw.com.icash.a.icashpay.debuging:id/home_text"))
        )
        payment_code_button.click()
        print(" -> '付款碼' 點擊成功！")

        print("\n步驟 2: 等待並點擊 '登入/註冊' 按鈕...")
        login_register_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((AppiumBy.ID, "tw.com.icash.a.icashpay.debuging:id/text"))
        )
        login_register_button.click()
        print(" -> '登入/註冊' 點擊成功！")

        print("\n步驟 3: 等待並點擊 '註冊icash Pay' 按鈕...")
        register_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((AppiumBy.ID, "tw.com.icash.a.icashpay.debuging:id/btRegister"))
        )
        register_button.click()
        print(" -> '註冊icash Pay' 點擊成功！")

        print("\n步驟 4: 開始填寫註冊資料...")
        phone_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((AppiumBy.ID, "tw.com.icash.a.icashpay.debuging:id/user_phones_text"))
        )
        phone_field.send_keys("0912345678")
        print(" -> 已輸入手機號碼")

        account_field = driver.find_element(by=AppiumBy.ID, value="tw.com.icash.a.icashpay.debuging:id/user_code_text")
        account_field.send_keys("testaccount01")
        print(" -> 已輸入登入帳號")

        password_field = driver.find_element(by=AppiumBy.ID, value="tw.com.icash.a.icashpay.debuging:id/user_pwd_text")
        password_field.send_keys("Aa123456")
        print(" -> 已輸入登入密碼")

        confirm_password_field = driver.find_element(by=AppiumBy.ID,
                                                     value="tw.com.icash.a.icashpay.debuging:id/user_double_confirm_pwd_text")
        confirm_password_field.send_keys("Aa123456")
        print(" -> 已再次輸入密碼")

        checkboxes = driver.find_elements(by=AppiumBy.CLASS_NAME, value="android.widget.CheckBox")
        for checkbox in checkboxes:
            checkbox.click()
        print(f" -> 已勾選 {len(checkboxes)} 個同意條款")

        next_step_button = driver.find_element(by=AppiumBy.XPATH, value="//android.widget.Button[@text='下一步']")
        next_step_button.click()
        print(" -> 已點擊下一步")

        print("\n測試流程執行完畢！ ✅")
        time.sleep(5)

    except TimeoutException:
        print("錯誤：在指定時間內找不到元素，請檢查定位條件是否正確。")
    except Exception as e:
        print(f"發生未預期的錯誤: {e}")