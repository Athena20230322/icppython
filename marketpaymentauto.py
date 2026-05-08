import json
import base64
import requests
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256

# --- 配置區 ---
AES_KEY = "VhoGVCInVF2UJ1cQBVZCF48lGUVIoCng"
AES_IV = "z3P4Se8qTFE0F1xI"
BARCODE_PATH = r'C:\icppython\barcode.txt'
CLIENT_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEowIBAAKCAQEA0hXyO7E10c4WR/S1XUFUyvlLS8wX/3RoL9nE4kwWJC+nTy8AFSVBgNz2KPnv3If+q8lG3bqq6TCiBmZxP33hbQH1H/cZPHag644nHlHc0/ZSunXB92jprH4xf96wfev12wqrMbCnYKytInEJnuHN+n3eq0LuyQ/WRcPVROJWxYFUO+uGLbFohtmppb0f/cSKOr0hVP15qZAEVSQwYHhu1CJAI/XoRLkZd87A2KHzvVJ2qkbjRbzXemRToE0v3GrWoUoBIMW3cJxgKieMW/HhQHfnz8njTf4nYlA4OSi2U43OA3Z9T+9gB5I8FvfOokt/LfhvO5q/l7QWB+yaX2hvuQIDAQABAoIBAAd57PYnWws1mpDiej7Ql6AmiYGvyG3YmmmThiBohUQx5vIYMdhOzFs14dO4+0p9k3hRECLNZQ4p4yY3qJGSHP7YWj0SOdVvQlBHrYg0cReg9TY6ARZZJzGyhvfuOJkul7/9C/UXfIlh88JdQ/KhxgcDSjSNi/pfRCiU7MbICD78h/pCS1zIWHaICZ2aL5rV2o5JwCcvDP8p3F+LFW/5u5kK0D0Pd29FXhf5MKHC4Mgrn2I44Uyhdud2Mf7wdvYvvcv2Nzn/EvM7uYZpkEyC3Y1Ow037fZjO3pVCVRt8Mbo4B75ORqXQnr1SbKXWXM/unUEIfMhsBRhx/diDCO8xyiECgYEA8UXIvYWREf+EN5EysmaHcv1jEUgFym8xUiASwwAv+LE9jQJSBiVym13rIGs01k1RN9z3/RVc+0BETTy9qEsUzwX9oTxgqlRk8R3TK7YEg6G/W/7D5DDM9bS/ncU7PlKA/FaEasHCfjs0IY5yJZFYrcA2QvvCl1X1NUZ4Hyumk1ECgYEA3ujTDbDNaSy/++4W/Ljp5pIVmmO27jy30kv1d3fPG6HRtPvbwRyUk/Y9PQpVpd7Sx/+GN+95Z3/zy1IHrbHN5SxE+OGzLrgzgj32EOU+ZJk5uj9qNBkNXh5prcOcjGcMcGL9OAC2oaWaOxrWin3fAzDsCoGrlzSzkVANnBRB6+kCgYEA2EaA0nq3dxW/9HugoVDNHCPNOUGBh1wzLvX3O3ughOKEVTF+S2ooGOOQkGfpXizCoDvgxKnwxnxufXn0XLao+YbaOz0/PZAXSBg/IlCwLTrBqXpvKM8h+yLCHXAeUhhs7UW0v2neqX7ylR32bnyirGW/fj3lyfjQrKf1p6NeV3ECgYB2X+fspk5/Iu+VJxv3+27jLgLg6UE1BPONbx8c4XgPsYB+/xz1UWsppCNjLgDLxCflY7HwNHEhYJakC5zeRcUUhcze6mTQU6uu556r3EGlBKXeXVzV69Pofngaef3Bpdu6NydHvUE/WIUuDBOQmkV7GVjQP4pTEv6lFYEUuMFFOQKBgHfINuaiIlITl/u59LPrvhTZoq6qg7N/3wVeAjYvbpv+b2cFgvOMQAr+S8eCDzijy2z4MENBTr/q6mkKe4NHFGtodP+bjSYEG+GnBEG+EUpAx3Wh/BL2f/sIiSOH9ODB6B847F+apa0OTawmslgGna9/985egGMto9g16EQ4ib1M
-----END PRIVATE KEY-----"""


# --- 核心邏輯 ---

def encrypt_aes_cbc_256(data, key, iv):
    cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
    ct_bytes = cipher.encrypt(pad(data.encode('utf-8'), AES.block_size))
    return base64.b64encode(ct_bytes).decode('utf-8')


def decrypt_aes_cbc_256(enc_data, key, iv):
    enc_bytes = base64.b64decode(enc_data)
    cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
    pt_bytes = unpad(cipher.decrypt(enc_bytes), AES.block_size)
    return pt_bytes.decode('utf-8')


def sign_data(data, private_key_pem):
    key = RSA.import_key(private_key_pem)
    h = SHA256.new(data.encode('utf-8'))
    signature = pkcs1_15.new(key).sign(h)
    return base64.b64encode(signature).decode('utf-8')


def get_current_time():
    now = datetime.now()
    return {
        "tradeNo": f"Sample{now.strftime('%Y%m%d%H%M%S')}",
        "tradeDate": now.strftime('%Y/%m/%d %H:%M:%S')
    }


def main():
    try:
        # 讀取檔案
        with open(BARCODE_PATH, 'r', encoding='utf-8') as f:
            input_barcode = f.read().strip()
        print(f"已讀取條碼: {input_barcode}")

        time_info = get_current_time()

        data = {
            "PlatformID": "10000266",
            "MerchantID": "10000266",
            "Ccy": "TWD",
            "TxAmt": "1",
            "NonRedeemAmt": "",
            "NonPointAmt": "",
            "StoreId": "217477",
            "StoreName": "見晴_QA",
            "PosNo": "01",
            "OPSeq": time_info["tradeNo"],
            "OPTime": time_info["tradeDate"],
            "ReceiptNo": "",
            "ReceiptReriod": "",
            "TaxID": "",
            "CorpID": "22555003",
            "Vehicle": "",
            "Donate": "",
            "ItemAmt": "1",
            "UtilityAmt": "",
            "CommAmt": "",
            "ExceptAmt1": "",
            "ExceptAmt2": "",
            "BonusType": "ByWallet",
            "BonusCategory": "",
            "BonusID": "",
            "PaymentNo": "038",
            "Remark": "123456",
            "ReceiptPrint": "N",
            "Itemlist": [{}],
            "BuyerID": input_barcode,
        }

        # 加密與簽章
        json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        enc_data = encrypt_aes_cbc_256(json_str, AES_KEY, AES_IV)
        signature = sign_data(enc_data, CLIENT_PRIVATE_KEY)

        # 發送請求
        url = "https://icp-payment-stage.icashpay.com.tw/api/V2/Payment/Pos/SETPay"
        headers = {
            'X-iCP-EncKeyID': '288768',
            'X-iCP-Signature': signature,
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        payload = {'EncData': enc_data}

        response = requests.post(url, data=payload, headers=headers)
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")

        if response.status_code == 200:
            res_json = response.json()
            if "EncData" in res_json:
                decrypted_res = decrypt_aes_cbc_256(res_json["EncData"], AES_KEY, AES_IV)
                print(f"Decrypted Response Data: {decrypted_res}")

                res_data = json.loads(decrypted_res)
                log_content = (f"BuyerID: {input_barcode}\n"
                               f"OPSeq: {res_data.get('OPSeq')}\n"
                               f"BankSeq: {res_data.get('BankSeq')}\n")

                with open('marketpaymentrefund.txt', 'w', encoding='utf-8') as f_out:
                    f_out.write(log_content)
                print("Data saved to marketpaymentrefund.txt")

    except Exception as e:
        print(f"發生錯誤: {e}")


if __name__ == "__main__":
    main()