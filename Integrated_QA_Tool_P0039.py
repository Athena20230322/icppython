import requests
import json
import base64
import os
import re
from datetime import datetime
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
from Crypto.Util.Padding import pad, unpad


# --- 1. 加密輔助類別 ---
class CryptoHelper:
    def __init__(self):
        self._rsa_private_key = None
        self._rsa_public_key = None

    def generate_rsa_key(self):
        key = RSA.generate(2048)
        return {
            'private_key': key.export_key(format='PEM', pkcs=8).decode('utf-8'),
            'public_key': key.publickey().export_key(format='PEM').decode('utf-8')
        }

    def import_rsa_public(self, pem_key):
        if not pem_key.strip().startswith('-----BEGIN'):
            pem_key = f"-----BEGIN PUBLIC KEY-----\n{pem_key}\n-----END PUBLIC KEY-----"
        self._rsa_public_key = RSA.import_key(pem_key)

    def import_rsa_private(self, pem_key):
        if not pem_key.strip().startswith('-----BEGIN'):
            pem_key = f"-----BEGIN PRIVATE KEY-----\n{pem_key}\n-----END PRIVATE KEY-----"
        self._rsa_private_key = RSA.import_key(pem_key)

    def rsa_encrypt_with_public(self, data):
        key_size = self._rsa_public_key.size_in_bytes()
        max_chunk = key_size - 11
        data_bytes = data.encode('utf-8')
        cipher = PKCS1_v1_5.new(self._rsa_public_key)
        chunks = [cipher.encrypt(data_bytes[i:i + max_chunk]) for i in range(0, len(data_bytes), max_chunk)]
        return base64.b64encode(b''.join(chunks)).decode('utf-8')

    def rsa_decrypt_with_private(self, enc_data):
        encrypted_bytes = base64.b64decode(enc_data)
        key_size = self._rsa_private_key.size_in_bytes()
        cipher = PKCS1_v1_5.new(self._rsa_private_key)
        decrypted_chunks = [cipher.decrypt(encrypted_bytes[i:i + key_size], b'error_sentinel')
                            for i in range(0, len(encrypted_bytes), key_size)]
        return b''.join(decrypted_chunks).decode('utf-8')

    def sign_sha256(self, data, private_key=None):
        target_key = self._rsa_private_key
        if private_key:
            target_key = RSA.import_key(private_key)
        h = SHA256.new(data.encode('utf-8'))
        signature = pkcs1_15.new(target_key).sign(h)
        return base64.b64encode(signature).decode('utf-8')

    @staticmethod
    def aes_encrypt(data, key, iv):
        cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
        padded = pad(data.encode('utf-8'), AES.block_size, style='pkcs7')
        return base64.b64encode(cipher.encrypt(padded)).decode('utf-8')

    @staticmethod
    def aes_decrypt(enc_data, key, iv):
        try:
            cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
            decrypted = unpad(cipher.decrypt(base64.b64decode(enc_data)), AES.block_size, style='pkcs7')
            text = decrypted.decode('utf-8')
            match = re.search(r'\{.*\}', text, re.DOTALL)
            return match.group() if match else text
        except:
            return None


# --- 2. API 客戶端 ---
class IcashPayClient:
    def __init__(self):
        self.member_url = "https://icp-member-stage.icashpay.com.tw/"
        self.payment_url = "https://icp-plus-stage.icashpay.com.tw/"
        self.crypto = CryptoHelper()
        self.session = requests.Session()
        self.aes_info = {}

    def _get_timestamp(self):
        return datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    def handshake(self):
        resp = self.session.post(f"{self.member_url}api/member/Certificate/GetDefaultPucCert").json()
        kp = self.crypto.generate_rsa_key()
        self.crypto.import_rsa_private(kp['private_key'])
        self.crypto.import_rsa_public(resp['DefaultPubCert'])
        payload = {'ClientPubCert': "".join(kp['public_key'].splitlines()[1:-1]), 'Timestamp': self._get_timestamp()}
        enc_data = self.crypto.rsa_encrypt_with_public(json.dumps(payload, ensure_ascii=False))
        sig = self.crypto.sign_sha256(enc_data)
        resp_exch = self.session.post(f"{self.member_url}api/member/Certificate/ExchangePucCert",
                                      data={'EncData': enc_data},
                                      headers={'X-iCP-DefaultPubCertID': str(resp['DefaultPubCertID']),
                                               'X-iCP-Signature': sig}).json()
        exch_res = json.loads(self.crypto.rsa_decrypt_with_private(resp_exch['EncData']))
        self.crypto.import_rsa_public(exch_res['ServerPubCert'])
        enc_data_aes = self.crypto.rsa_encrypt_with_public(json.dumps({'Timestamp': self._get_timestamp()}))
        sig_aes = self.crypto.sign_sha256(enc_data_aes)
        resp_aes = self.session.post(f"{self.member_url}api/member/Certificate/GenerateAES",
                                     data={'EncData': enc_data_aes},
                                     headers={'X-iCP-ServerPubCertID': str(exch_res['ServerPubCertID']),
                                              'X-iCP-Signature': sig_aes}).json()
        res = json.loads(self.crypto.rsa_decrypt_with_private(resp_aes['EncData']))
        self.aes_info = {'id': res['EncKeyID'], 'key': res['AES_Key'], 'iv': res['AES_IV']}

    def call_api(self, base_url, action, payload):
        # 自動處理多種時間戳格式標籤
        for ts_key in ["Timestamp", "ts"]:
            if ts_key in payload:
                payload[ts_key] = self._get_timestamp()

        enc_data = self.crypto.aes_encrypt(json.dumps(payload, ensure_ascii=False), self.aes_info['key'],
                                           self.aes_info['iv'])
        sig = self.crypto.sign_sha256(enc_data)
        headers = {'X-iCP-EncKeyID': str(self.aes_info['id']), 'X-iCP-Signature': sig}

        try:
            r = self.session.post(f"{base_url}{action}", data={'EncData': enc_data}, headers=headers)
            resp = r.json()
            if "EncData" in resp and isinstance(resp['EncData'], str):
                decrypted = self.crypto.aes_decrypt(resp['EncData'], self.aes_info['key'], self.aes_info['iv'])
                if decrypted:
                    try:
                        resp['EncResult'] = json.loads(decrypted)
                    except:
                        resp['EncResult'] = decrypted
            return resp
        except Exception as e:
            return {"RtnCode": -999, "RtnMsg": str(e)}


# --- 3. 處理邏輯 ---
def process_p0039_flow():
    ACCOUNT_FILE = r"C:\icppython\account.txt"
    print(f"[*] 啟動測試開發工具：同步 P0037 -> P0038 付款 -> P0039 扣款...")

    if not os.path.exists(ACCOUNT_FILE):
        print(f"[!] 錯誤: 找不到檔案 {ACCOUNT_FILE}")
        return

    with open(ACCOUNT_FILE, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    client = IcashPayClient()
    final_output_rows = []
    # 更新標頭，增加 P0039 狀態
    header_str = "UserCode,CellPhone,LoginTokenID,AuthCode,QR_ItemName,QR_BillNo,QR_Amount,SeqNo,Order_Status,TradeNo,P0039_Status"

    try:
        client.handshake()
    except Exception as e:
        print(f"❌ Handshake 失敗: {str(e)}")
        return

    for idx, line in enumerate(lines[1:], 1):
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 2: continue
        user_code, phone = parts[0], parts[1]

        print(f"\n>>> [{idx}] 帳號: {phone}")
        try:
            # 初始化變數
            new_token, new_auth = "", ""
            qr_item_name, qr_bill_no, qr_amount = "N/A", "N/A", "300"
            order_status, trade_no = "Failed", "N/A"
            current_seq = "N/A"
            p0039_status = "N/A"
            dynamic_acq_info = ""

            # --- [Step 1: Refresh Login Token] ---
            res_token = client.call_api(client.member_url, "app/MemberInfo/RefreshLoginToken",
                                        {"Timestamp": "", "CellPhone": phone})
            if res_token.get("RtnCode") != 1:
                print(f"    [!] Token 刷新失敗: {res_token.get('RtnMsg')}")
            else:
                new_token = res_token.get("EncResult", {}).get("LoginTokenID", "").split(',')[0]

                # --- [Step 2: Send Auth SMS] ---
                res_sms = client.call_api(client.member_url, "app/MemberInfo/SendAuthSMS",
                                          {"Timestamp": "", "CellPhone": phone, "SMSAuthType": 5,
                                           "LoginTokenID": new_token})

                if res_sms.get("RtnCode") != 1:
                    print(f"    [!] 簡訊發送失敗: {res_sms.get('RtnMsg')}")
                else:
                    new_auth = res_sms.get("EncResult", {}).get("AuthCode", "")
                    print(f"    └─ 取得 AuthCode: {new_auth}")

                    # --- [Step 3: Login] ---
                    res_login = client.call_api(client.member_url, "app/MemberInfo/UserCodeLogin2022",
                                                {"Timestamp": "", "LoginType": "1", "UserCode": user_code,
                                                 "UserPwd": "Aa123456", "SMSAuthCode": new_auth})

                    if res_login.get("RtnCode") != 1:
                        print(f"    [!] 登入失敗: {res_login.get('RtnMsg')}")
                    else:
                        # --- [Step 4: P0037 ParserQrCode] ---
                        qr_string = "TWQRP%3A%2F%2F462%E8%81%AF%E5%90%88%E5%8B%B8%E5%8B%9FQR+Code%2F158%2F03%2FV1%3FD1%3D30000%26D3%3DAb%2BETKdx%2Bk95%26D12%3D99991231123112%26D10%3D901%26D7%3D0000121277127505%26D11%3D00%2C4624620000057500090575000900057801"
                        res_parser = client.call_api(client.payment_url, "app/Payment/ParserQrCode",
                                                     {"Timestamp": "", "MerchantQRcode": qr_string})

                        if res_parser.get("RtnCode") == 1:
                            enc_res = res_parser.get("EncResult", {})
                            rtn_val = json.loads(enc_res.get("RtnValue", "{}"))
                            qr_item_name = rtn_val.get("ItemName", "無名稱")
                            dynamic_acq_info = rtn_val.get("acqInfo", "")
                            bills = rtn_val.get("Bills", [])
                            if bills:
                                qr_bill_no = str(bills[0].get("BillNo", ""))
                                qr_amount = str(bills[0].get("Amount", "300"))
                                current_seq = str(bills[0].get("SeqNo", "32194"))

                            print(f"    └─ [P0037 成功] SeqNo: {current_seq}")

                            # --- [Step 5: P0038 CreateOrder] ---
                            order_payload = {
                                "Timestamp": "", "Amount": qr_amount, "BillNo": qr_bill_no,
                                "Charge": "0", "SeqNo": current_seq, "acqInfo": dynamic_acq_info, "deadline": ""
                            }
                            res_order = client.call_api(client.payment_url, "app/Fisc/CreateOnlinePaymentOrder",
                                                        order_payload)

                            if res_order.get("RtnCode") == 1:
                                trade_no = res_order.get("EncResult", {}).get("MerchantTradeNo", "N/A")
                                pay_id = res_order.get("EncResult", {}).get("PayID", "")
                                order_status = "Success"
                                print(f"    └─ [P0038 成功] 交易序號: {trade_no}")

                                # --- [Step 6: P0039 ChargeOnlineFISC (新增)] ---
                                charge_payload = {
                                    "AccumulatedPointsType": "1",
                                    "ChargeVersionType": "v2",
                                    "MerchantID": "10523899",
                                    "MerchantTradeNo": trade_no,  # 來自 P0038
                                    "PayID": pay_id,  # 來自 P0038
                                    "PlatformID": "10523899",
                                    "SeqNo": current_seq,  # 來自 P0037/P0038
                                    "UsePoint": "0",
                                    "UsePointType": "1",
                                    "acqInfo": dynamic_acq_info,
                                    "deadline": "",
                                    "ts": ""
                                }
                                res_charge = client.call_api(client.payment_url, "app/Fisc/ChargeOnlineFISC",
                                                             charge_payload)

                                if res_charge.get("RtnCode") == 1:
                                    p0039_status = "Success"
                                    print(f"    └─ [P0039 成功] 扣款完成")
                                else:
                                    p0039_status = f"Failed({res_charge.get('RtnCode')})"
                                    print(f"    └─ [P0039 失敗] 原因: {res_charge.get('RtnMsg')}")

                            else:
                                order_status = f"Failed({res_order.get('RtnCode')})"
                                print(f"    └─ [P0038 失敗] 原因: {res_order.get('RtnMsg')}")
                        else:
                            print(f"    [!] P0037 解析失敗: {res_parser.get('RtnMsg')}")

            final_output_rows.append(
                [user_code, phone, new_token, new_auth, qr_item_name, qr_bill_no, qr_amount, current_seq, order_status,
                 trade_no, p0039_status])

        except Exception as e:
            print(f"❌ 異常: {str(e)}")

    # 寫回檔案 (包含 P0039 結果)
    with open(ACCOUNT_FILE, 'w', encoding='utf-8') as f:
        f.write(header_str + "\n")
        for row in final_output_rows:
            f.write(",".join(row) + "\n")
    print(f"\n[*] 處理完畢，結果已存入 {ACCOUNT_FILE}")


if __name__ == '__main__':
    process_p0039_flow()