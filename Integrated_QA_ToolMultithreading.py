import requests
import json
import base64
import os
import re
import time
from datetime import datetime
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
from Crypto.Util.Padding import pad, unpad
from concurrent.futures import ThreadPoolExecutor

# ================= 設定區 =================
ACCOUNT_FILE = r"C:\icppython\account.txt"
MAX_WORKERS = 5  # 建議維持 5，避免被伺服器封鎖 IP


# ==========================================

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

    def sign_sha256(self, data):
        if not self._rsa_private_key: raise ValueError("尚未匯入私鑰")
        h = SHA256.new(data.encode('utf-8'))
        signature = pkcs1_15.new(self._rsa_private_key).sign(h)
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


class IcashPayClient:
    def __init__(self):
        self.member_url = "https://icp-member-stage.icashpay.com.tw/"
        self.payment_url = "https://icp-payment-stage.icashpay.com.tw/"
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
        enc_data = self.crypto.aes_encrypt(json.dumps(payload, ensure_ascii=False), self.aes_info['key'],
                                           self.aes_info['iv'])
        sig = self.crypto.sign_sha256(enc_data)
        headers = {'X-iCP-EncKeyID': str(self.aes_info['id']), 'X-iCP-Signature': sig}
        try:
            resp = self.session.post(f"{base_url}{action}", data={'EncData': enc_data}, headers=headers,
                                     timeout=15).json()
            if "EncData" in resp and isinstance(resp['EncData'], str):
                decrypted = self.crypto.aes_decrypt(resp['EncData'], self.aes_info['key'], self.aes_info['iv'])
                if decrypted:
                    try:
                        resp['EncData'] = json.loads(decrypted)
                    except:
                        resp['EncData'] = decrypted
            return resp
        except Exception:
            return {"RtnCode": -99, "RtnMsg": "網路連線異常"}


def task_worker(index, acc_row):
    user_code, phone, cur_token, cur_auth, cur_barcode, count_str = acc_row
    client = IcashPayClient()

    try:
        repeat_count = int(count_str) if str(count_str).isdigit() else 1
    except:
        repeat_count = 1

    local_results = []

    try:
        client.handshake()
        # 1~3. 登入流程
        res_token = client.call_api(client.member_url, "app/MemberInfo/RefreshLoginToken",
                                    {"Timestamp": client._get_timestamp(), "CellPhone": phone})
        new_token = res_token.get("EncData", {}).get("LoginTokenID", "").split(',')[0]

        res_sms = client.call_api(client.member_url, "app/MemberInfo/SendAuthSMS",
                                  {"Timestamp": client._get_timestamp(), "CellPhone": phone, "SMSAuthType": 5,
                                   "UserCode": "", "LoginTokenID": new_token})
        new_auth = res_sms.get("EncData", {}).get("AuthCode", "")

        client.call_api(client.member_url, "app/MemberInfo/UserCodeLogin2022",
                        {"Timestamp": client._get_timestamp(), "LoginType": "1", "UserCode": user_code,
                         "UserPwd": "Aa123456", "SMSAuthCode": new_auth})

        res_pay = client.call_api(client.payment_url, "app/Payment/GetMemberPaymentInfo",
                                  {"Timestamp": client._get_timestamp(), "IsAutoPay": "false", "MerchantID": ""})
        p_data = res_pay.get("EncData", {})

        pay_id = None
        for sk in ["AllIcashpayList", "IcashpayList", "PaymentList"]:
            target = p_data.get(sk)
            if not target: continue
            if isinstance(target, list) and len(target) > 0:
                pay_id = target[0].get("PayID")
            elif isinstance(target, dict):
                pay_id = target.get("PayID")
            if pay_id: break

        if pay_id:
            for i in range(repeat_count):
                res_bc = client.call_api(client.payment_url, "app/Payment/CreateBarcode",
                                         {"PayID": pay_id, "PaymentType": "1", "Timestamp": client._get_timestamp()})
                barcode = res_bc.get("EncData", {}).get("Barcode", "")

                if not barcode:
                    barcode = f"FAIL_{res_bc.get('RtnMsg', 'Unknown')}"

                local_results.append([user_code, phone, new_token, new_auth, barcode, str(repeat_count)])
                # 每產一筆稍微停一下，避免請求過快
                time.sleep(0.05)
        else:
            raise ValueError("無法取得 PayID")

    except Exception as e:
        print(f"❌ 手機 {phone} 處理過程出錯: {e}")

    # 強制補齊筆數，確保總筆數與順序對齊
    while len(local_results) < repeat_count:
        local_results.append([user_code, phone, cur_token, cur_auth, "ERROR_筆數補齊", str(repeat_count)])

    return (index, local_results)


def main():
    if not os.path.exists(ACCOUNT_FILE):
        print(f"找不到檔案: {ACCOUNT_FILE}")
        return

    with open(ACCOUNT_FILE, 'r', encoding='utf-8') as f:
        lines = [line.strip().split(',') for line in f.readlines() if line.strip()]

    if len(lines) <= 1: return
    header = "UserCode,CellPhone,LoginTokenID,authcode,Barcode,Count"

    accounts_with_index = []
    for idx, acc in enumerate(lines[1:]):
        while len(acc) < 6: acc.append("")
        accounts_with_index.append((idx, acc))

    total_expected = sum([int(a[1][5]) if str(a[1][5]).isdigit() else 1 for a in accounts_with_index])
    print(f"\n>>> 任務開始：{len(accounts_with_index)} 個帳號，預計產出 {total_expected} 筆條碼")

    start_time = time.time()
    all_results_indexed = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(task_worker, idx, acc) for idx, acc in accounts_with_index]
        for future in futures:
            all_results_indexed.append(future.result())

    # 依原始順序排序
    all_results_indexed.sort(key=lambda x: x[0])

    final_rows = []
    for _, batch in all_results_indexed:
        final_rows.extend(batch)

    duration = time.time() - start_time

    with open(ACCOUNT_FILE, 'w', encoding='utf-8') as f:
        f.write(header + "\n")
        for row in final_rows:
            f.write(",".join(row) + "\n")

    print("\n" + "=" * 40)
    print(f"🏁 處理完成！")
    print(f"⏱️  總執行時間: {duration:.2f} 秒")
    print(f"📊 實際產出筆數: {len(final_rows)} 筆")
    print(f"🚀 平均產出速度: {len(final_rows) / duration:.2f} 筆/秒")
    print("=" * 40)


if __name__ == '__main__':
    main()