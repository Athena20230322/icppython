import hashlib
import urllib.parse
from datetime import datetime

def generate_ecpay_checkout_form(merchant_id, hash_key, hash_iv, server_host):
    """
    Generate the HTML form for ECPay credit card payment with 3D Secure.
    """
    # 綠界科技的測試環境 URL
    # 請注意：這是一個假設的 URL，您需要從 ECPay 的文件中找到正確的 URL
    AIO_CHECK_OUT_URL = "https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5"

    # 訂單資料
    order_params = {
        'MerchantID': merchant_id,
        'MerchantTradeNo': f"test_order_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        'MerchantTradeDate': datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
        'PaymentType': 'aio',
        'TotalAmount': 100,  # 交易金額
        'TradeDesc': 'ECPay 3D Secure Test',
        'ItemName': 'Test Product',
        'ReturnURL': f'{server_host}/ecpay_return',  # 交易結果回傳的 URL
        'ChoosePayment': 'Credit',
        'EncryptType': '1',
        'ClientBackURL': f'{server_host}/client_back',  # 按下「返回商店」後導回的 URL
        'CreditInstallment': '0', #不分期
        'InstallmentAmount': '0',
        'Redeem': 'N',
        'UnionPay': '0',
    }

    # 排序參數
    sorted_params = sorted(order_params.items())

    # 組成查詢字串
    query_string = '&'.join([f"{key}={value}" for key, value in sorted_params])
    query_string = f"HashKey={hash_key}&{query_string}&HashIV={hash_iv}"

    # URL-encode a-z, A-Z, 0-9, !, *, ., (, )
    encoded_string = urllib.parse.quote(query_string).lower()

    # SHA256 加密
    check_mac_value = hashlib.sha256(encoded_string.encode('utf-8')).hexdigest().upper()

    order_params['CheckMacValue'] = check_mac_value

    # 產生 HTML 表單
    form_html = f"<form id='ecpay_form' action='{AIO_CHECK_OUT_URL}' method='post'>"
    for key, value in order_params.items():
        form_html += f"<input type='hidden' name='{key}' value='{value}' />"
    form_html += "</form>"
    form_html += "<script>document.getElementById('ecpay_form').submit();</script>"

    return form_html

if __name__ == '__main__':
    # 您的特店資料 (從 ECPay 文件取得的測試資料)
    MERCHANT_ID = '3002607'
    HASH_KEY = 'pwFHCqoQZGmho4w6'
    HASH_IV = 'EkRm7iFT261dpevs'

    # 您的網站伺服器網址
    # 這個網址是用來接收 ECPay 的回傳結果
    SERVER_HOST = "https://www.your_domain.com" # 請替換成您的網址

    # 產生結帳表單
    checkout_form = generate_ecpay_checkout_form(MERCHANT_ID, HASH_KEY, HASH_IV, SERVER_HOST)

    # 在您的網站後端，將這個 HTML 回傳給使用者的瀏覽器
    # 當瀏覽器載入這個 HTML 後，會自動跳轉到 ECPay 的付款頁面
    print(checkout_form)