import re
import time
from playwright.sync_api import sync_playwright


def get_mail2000_otp():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print("正在開啟 MailCloud 登入頁面...")
        page.goto("https://vs.mailcloud.com.tw/cgi-bin/login?index=1&user_domain=mailcloud.com.tw")

        # --- 精準定位修改開始 ---

        # 使用更嚴謹的 CSS Selector：指定在 id="stdLogin" 範圍內的 input，且必須是可見的
        # 'id=stdLogin >> input[name="USERID"]' 確保不會抓到外層的 hidden 欄位
        print("等待登入欄位載入...")

        # 1. 填寫帳號 (針對 id="stdLogin" 下的可見輸入框)
        user_input = page.locator('#stdLogin input[name="USERID"]')
        user_input.wait_for(state="visible", timeout=20000)
        user_input.fill("adanyao@mail.icash.com.tw")

        # 2. 填寫密碼
        pass_input = page.locator('#stdLogin input[name="PASSWD"]')
        pass_input.fill("icash@Aa0937818247")

        # 3. 點擊登入按鈕
        print("點擊登入...")
        login_btn = page.locator('#stdLogin input[type="submit"][value="登入"]')
        login_btn.click()

        # --- 精準定位修改結束 ---

        print("等待進入收件匣...")
        try:
            page.wait_for_load_state("networkidle")

            # 4. 尋找 OTP 信件 (使用 text 定位更直觀)
            # 考量到這是在測試流程中，建議增加等待新信出現的邏輯
            target_mail = page.get_by_text("[外部信件]ICP Admin OTP 通知").first
            target_mail.wait_for(state="visible", timeout=15000)
            target_mail.click()

            print("正在讀取信件內容...")
            time.sleep(3)  # 等待內文渲染

            content = page.content()

            # 5. 提取驗證碼
            otp_match = re.search(r'您的驗證碼為\s*[:：]\s*(\d{6})', content)

            if otp_match:
                otp_code = otp_match.group(1)
                print(f"\n✅ 成功取得 OTP: {otp_code}\n")
                time.sleep(5)
                return otp_code
            else:
                print("❌ 找不到驗證碼數字。")

        except Exception as e:
            print(f"❌ 執行過程中發生問題: {e}")

        finally:
            print("關閉瀏覽器...")
            browser.close()


if __name__ == "__main__":
    get_mail2000_otp()