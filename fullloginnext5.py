import requests
import json
import base64
import os
import sys
from datetime import datetime
import traceback
import webbrowser

# 確保 pycryptodome 已安裝
try:
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import PKCS1_v1_5, AES
    from Crypto.Hash import SHA256
    from Crypto.Signature import pkcs1_15
    from Crypto.Util.Padding import pad, unpad
except ImportError:
    print("!!! 錯誤: 找不到 pycryptodome 模組。請執行 'pip install pycryptodome' 安裝。 !!!")
    sys.exit(1)


class HtmlReporter:
    """產生並儲存一個 HTML 格式的測試報告。"""

    def __init__(self, report_title):
        self.report_title = report_title
        self.steps = []
        self.start_time = datetime.now()
        self.end_time = None
        self.overall_status = "⏳ 執行中"

    def add_step(self, step_name, status, request_payload=None, decrypted_response=None, error_details=None):
        """新增一個 API 呼叫步驟到報告中。"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        details = {}
        if request_payload:
            # 使用 ensure_ascii=False 來正確顯示中文字元
            details["Request (傳送前)"] = json.dumps(request_payload, indent=2, ensure_ascii=False)
        if decrypted_response:
            details["Response (解密後)"] = json.dumps(decrypted_response, indent=2, ensure_ascii=False)
        if error_details:
            details["Error Info"] = error_details

        self.steps.append({
            "name": step_name,
            "status": status,
            "timestamp": timestamp,
            "details": details
        })
        if "❌" in status:
            self.overall_status = "❌ 失敗"

    def finalize_report(self):
        """設定報告的最終狀態。"""
        self.end_time = datetime.now()
        if self.overall_status == "⏳ 執行中":
            self.overall_status = "✅ 成功"

    def generate_html(self):
        """產生完整的 HTML 報告內容。"""
        if not self.end_time:
            self.finalize_report()

        duration = self.end_time - self.start_time
        status_color = '#28a745' if '✅' in self.overall_status else '#dc3545'

        html = f"""
        <!DOCTYPE html>
        <html lang="zh-Hant">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{self.report_title}</title>
            <style>
                body {{ font-family: 'Segoe UI', 'Microsoft JhengHei', '微軟正黑體', sans-serif; margin: 0; padding: 20px; background-color: #f4f7f6; color: #333; }}
                .container {{ max-width: 1200px; margin: auto; padding: 20px; background-color: #fff; box-shadow: 0 0 15px rgba(0,0,0,0.1); border-radius: 8px; }}
                h1 {{ color: #2c3e50; text-align: center; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                .summary {{ background-color: #ecf0f1; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 5px solid {status_color}; }}
                .summary p {{ margin: 5px 0; font-size: 1.1em;}}
                .summary-status {{ font-size: 1.3em; font-weight: bold; color: {status_color}; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; table-layout: fixed; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; vertical-align: top; word-wrap: break-word; }}
                th {{ background-color: #3498db; color: white; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .status-success {{ color: #28a745; font-weight: bold; }}
                .status-failure {{ color: #dc3545; font-weight: bold; }}
                details {{ cursor: pointer; margin-top: 10px; }}
                summary {{ font-weight: bold; list-style-position: inside; }}
                pre {{ background-color: #2d2d2d; color: #f2f2f2; padding: 10px; border-radius: 5px; white-space: pre-wrap; word-wrap: break-word; font-family: 'Courier New', monospace; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>{self.report_title}</h1>
                <div class="summary">
                    <p><strong>整體狀態:</strong> <span class="summary-status">{self.overall_status}</span></p>
                    <p><strong>開始時間:</strong> {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>結束時間:</strong> {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>總耗時:</strong> {str(duration).split('.')[0]}</p>
                </div>
                <table>
                    <colgroup>
                       <col style="width: 5%;">
                       <col style="width: 25%;">
                       <col style="width: 10%;">
                       <col style="width: 15%;">
                       <col style="width: 45%;">
                    </colgroup>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>執行動作</th>
                            <th>狀態</th>
                            <th>時間戳</th>
                            <th>詳細資料</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        for i, step in enumerate(self.steps, 1):
            status_class = "status-success" if "✅" in step['status'] else "status-failure"
            details_html = "".join(
                [f"<details><summary>{key}</summary><pre><code>{value}</code></pre></details>" for key, value in
                 step['details'].items()])
            html += f"""
            <tr>
                <td>{i}</td>
                <td>{step['name']}</td>
                <td class="{status_class}">{step['status']}</td>
                <td>{step['timestamp']}</td>
                <td>{details_html}</td>
            </tr>
            """
        html += "</tbody></table></div></body></html>"
        return html

    def save_and_open_report(self, base_path="."):
        """儲存報告到檔案並在瀏覽器中開啟。"""
        os.makedirs(base_path, exist_ok=True)
        filename = f"Login_Flow_Report_{self.start_time.strftime('%Y%m%d_%H%M%S')}.html"
        filepath = os.path.join(base_path, filename)
        html_content = self.generate_html()
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"\n📄 報告已成功生成: {filepath}")
            webbrowser.open(f'file://{os.path.realpath(filepath)}')
        except Exception as e:
            print(f"\n❌ 錯誤: 無法儲存或開啟報告: {e}")


class RsaCryptoHelper:
    def __init__(self):
        self._key = None

    def generate_pem_key(self):
        key = RSA.generate(2048)
        private_key_pem = key.export_key(format='PEM', pkcs=8).decode('utf-8')
        public_key_pem = key.publickey().export_key(format='PEM').decode('utf-8')
        return {'private_key': private_key_pem, 'public_key': public_key_pem}

    def import_pem_public_key(self, pem_key):
        if not pem_key.strip().startswith('-----BEGIN'):
            pem_key = f"-----BEGIN PUBLIC KEY-----\n{pem_key}\n-----END PUBLIC KEY-----"
        self._key = RSA.import_key(pem_key)

    def import_pem_private_key(self, pem_key):
        self._key = RSA.import_key(pem_key)

    def encrypt(self, data):
        key_size_bytes = self._key.size_in_bytes()
        max_chunk_size = key_size_bytes - 11
        data_bytes = data.encode('utf-8')
        encrypted_chunks = []
        for i in range(0, len(data_bytes), max_chunk_size):
            chunk = data_bytes[i:i + max_chunk_size]
            encrypted_chunks.append(PKCS1_v1_5.new(self._key).encrypt(chunk))
        return base64.b64encode(b''.join(encrypted_chunks)).decode('utf-8')

    def decrypt(self, enc_data):
        encrypted_bytes = base64.b64decode(enc_data)
        key_size_bytes = self._key.size_in_bytes()
        decrypted_chunks = []
        for i in range(0, len(encrypted_bytes), key_size_bytes):
            chunk = encrypted_bytes[i:i + key_size_bytes]
            decrypted_chunks.append(PKCS1_v1_5.new(self._key).decrypt(chunk, b'error_sentinel'))
        if b'error_sentinel' in decrypted_chunks: raise ValueError("RSA 解密失敗")
        return b''.join(decrypted_chunks).decode('utf-8')

    def sign_data_with_sha256(self, data):
        h = SHA256.new(data.encode('utf-8'))
        return base64.b64encode(pkcs1_15.new(self._key).sign(h)).decode('utf-8')

    def verify_sign_data_with_sha256(self, data, signature):
        h = SHA256.new(data.encode('utf-8'))
        try:
            pkcs1_15.new(self._key).verify(h, base64.b64decode(signature))
            return True
        except (ValueError, TypeError):
            return False


class AesCryptoHelper:
    def __init__(self, key=None, iv=None):
        self.key = key.encode('utf-8') if key else None
        self.iv = iv.encode('utf-8') if iv else None

    def encrypt(self, data):
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        padded_data = pad(data.encode('utf-8'), AES.block_size, style='pkcs7')
        return base64.b64encode(cipher.encrypt(padded_data)).decode('utf-8')

    def decrypt(self, enc_data):
        encrypted_bytes = base64.b64decode(enc_data)
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        decrypted_padded_bytes = cipher.decrypt(encrypted_bytes)
        return unpad(decrypted_padded_bytes, AES.block_size, style='pkcs7').decode('utf-8')


class CertificateApiClient:
    def __init__(self, base_url="https://icp-member-stage.icashpay.com.tw/"):
        self.base_url = base_url
        self.rsa_helper = RsaCryptoHelper()
        self.session = requests.Session()
        self._server_public_key, self._client_private_key = None, None
        self._aes_client_cert_id, self._aes_key, self._aes_iv = -1, None, None

    def _check_timestamp(self, timestamp_str):
        try:
            if not timestamp_str: return
            dt = datetime.strptime(timestamp_str, "%Y/%m/%d %H:%M:%S")
            if abs((datetime.now() - dt).total_seconds()) > 300:
                print(f"警告：API 回應時間戳與本地時間差異過大")
        except (ValueError, TypeError):
            print(f"無法解析時間戳：{timestamp_str}")

    # --- 【***程式碼修改處 1***】: 增加 skip_verification 參數 ---
    def _call_api(self, action, payload, headers, use_aes=True, skip_verification=False):
        """通用內部 API 呼叫方法，包含加解密和簽章。"""
        json_payload = json.dumps(payload, ensure_ascii=False)

        if use_aes:
            enc_data = AesCryptoHelper(self._aes_key, self._aes_iv).encrypt(json_payload)
        else:
            self.rsa_helper.import_pem_public_key(self._server_public_key)
            enc_data = self.rsa_helper.encrypt(json_payload)

        self.rsa_helper.import_pem_private_key(self._client_private_key)
        headers['X-iCP-Signature'] = self.rsa_helper.sign_data_with_sha256(enc_data)

        url = f"{self.base_url}{action}"
        print(f"--- 正在呼叫: {action} ---")
        response = self.session.post(url, data={'EncData': enc_data}, headers=headers)
        response.raise_for_status()

        response_content, response_signature = response.text, response.headers.get('X-iCP-Signature')

        # 只有在 skip_verification 為 False 時才執行自動驗證
        if not skip_verification:
            self.rsa_helper.import_pem_public_key(self._server_public_key)
            if not self.rsa_helper.verify_sign_data_with_sha256(response_content, response_signature):
                raise Exception("API 回應簽章驗證失敗")

        response_json = json.loads(response_content)
        if response_json['RtnCode'] != 1:
            raise Exception(f"{response_json['RtnMsg']} (RtnCode: {response_json['RtnCode']})")

        if use_aes:
            decrypted_data_str = AesCryptoHelper(self._aes_key, self._aes_iv).decrypt(response_json['EncData'])
        else:
            self.rsa_helper.import_pem_private_key(self._client_private_key)
            decrypted_data_str = self.rsa_helper.decrypt(response_json['EncData'])

        print(f"API 回應 (已解密): {decrypted_data_str}")
        decrypted_data = json.loads(decrypted_data_str)
        self._check_timestamp(decrypted_data.get('Timestamp'))

        # 如果跳過了驗證，則回傳額外資訊供手動驗證
        if skip_verification:
            return decrypted_data, response_content, response_signature
        else:
            return decrypted_data

    # --- 【***程式碼修改處 2***】: 調整金鑰初始化流程 ---
    def _initialize_keys(self):
        if self._aes_key: return
        print("--- 開始金鑰初始化流程 ---")
        # 1. GetDefaultPucCert
        url = "api/member/Certificate/GetDefaultPucCert"
        response = self.session.post(f"{self.base_url}{url}").json()
        if response['RtnCode'] != 1: raise Exception(response['RtnMsg'])
        default_cert_id, self._server_public_key = response['DefaultPubCertID'], response['DefaultPubCert']

        # 2. ExchangePucCert
        client_key_pair = self.rsa_helper.generate_pem_key()
        self._client_private_key = client_key_pair['private_key']

        payload_exchange = {
            'ClientPubCert': "".join(client_key_pair['public_key'].splitlines()[1:-1]),
            'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        }
        # 跳過自動驗證，並接收原始回應以供手動驗證
        dec_resp_exchange, raw_content, signature = self._call_api(
            "api/member/Certificate/ExchangePucCert",
            payload_exchange,
            {'X-iCP-DefaultPubCertID': str(default_cert_id)},
            use_aes=False,
            skip_verification=True  # <<<<<< 關鍵修改
        )

        # 手動驗證：先取得新公鑰，再用新公鑰驗證簽章
        self._server_public_key = dec_resp_exchange['ServerPubCert']
        self.rsa_helper.import_pem_public_key(self._server_public_key)
        if not self.rsa_helper.verify_sign_data_with_sha256(raw_content, signature):
            raise Exception("ExchangePucCert 手動簽章驗證失敗")
        print("ExchangePucCert 手動簽章驗證成功。")

        # 3. GenerateAES (此步驟使用新的 server_public_key，可以正常自動驗證)
        payload_aes = {'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S")}
        dec_resp_aes = self._call_api(
            "api/member/Certificate/GenerateAES",
            payload_aes,
            {'X-iCP-ServerPubCertID': str(dec_resp_exchange['ServerPubCertID'])},
            use_aes=False
        )

        self._aes_client_cert_id = dec_resp_aes['EncKeyID']
        self._aes_key = dec_resp_aes['AES_Key']
        self._aes_iv = dec_resp_aes['AES_IV']
        print("--- 金鑰初始化完成 ---")

    def run_complete_flow(self, cellphone, user_code, user_pwd):
        reporter = HtmlReporter(report_title="iCashPay 登入與驗證流程報告(Next5)")
        current_step_name = "準備階段"

        try:
            reporter.add_step(current_step_name, "✅ 成功", request_payload={
                "測試手機": cellphone, "測試帳號": user_code
            })

            # --- 【***程式碼修改處 3***】: 在呼叫金鑰初始化時也加入 try-except ---
            current_step_name = "金鑰初始化"
            self._initialize_keys()
            reporter.add_step(current_step_name, "✅ 成功")

            # 步驟 1: 刷新 AppToken
            current_step_name = "步驟 1: 刷新 AppToken"
            payload1 = {'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S"), 'CellPhone': cellphone}
            dec_resp1 = self._call_api("app/MemberInfo/RefreshLoginToken", payload1,
                                       {'X-iCP-EncKeyID': str(self._aes_client_cert_id)})
            login_token_id = dec_resp1.get("LoginTokenID", "").split(',')[0]
            if not login_token_id: raise Exception("無法提取 LoginTokenID")
            reporter.add_step(current_step_name, "✅ 成功", payload1, dec_resp1)

            # 步驟 2: 發送簡訊
            current_step_name = "步驟 2: 發送簡訊驗證碼"
            payload2 = {"Timestamp": datetime.now().strftime("%Y/%m/%d %H:%M:%S"), "CellPhone": cellphone,
                        "SMSAuthType": 5, "UserCode": "", "LoginTokenID": login_token_id}
            dec_resp2 = self._call_api("app/MemberInfo/SendAuthSMS", payload2,
                                       {'X-iCP-EncKeyID': str(self._aes_client_cert_id)})
            auth_code = dec_resp2.get("AuthCode")
            if not auth_code: raise Exception("無法提取 AuthCode")
            reporter.add_step(current_step_name, "✅ 成功", payload2, dec_resp2)

            # 步驟 3: 會員登入
            current_step_name = "步驟 3: 會員登入"
            payload3 = {"Timestamp": datetime.now().strftime("%Y/%m/%d %H:%M:%S"), "LoginType": "1",
                        "UserCode": user_code, "UserPwd": user_pwd, "SMSAuthCode": auth_code}
            dec_resp3 = self._call_api("app/MemberInfo/UserCodeLogin2022", payload3,
                                       {'X-iCP-EncKeyID': str(self._aes_client_cert_id)})
            reporter.add_step(current_step_name, "✅ 成功", payload3, dec_resp3)

            # 步驟 4: 檢查會員狀態
            current_step_name = "步驟 4: 檢查會員驗證狀態"
            payload4 = {'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S")}
            dec_resp4 = self._call_api("app/MemberInfo/CheckVerifyStatus", payload4,
                                       {'X-iCP-EncKeyID': str(self._aes_client_cert_id)})
            reporter.add_step(current_step_name, "✅ 成功", payload4, dec_resp4)

            # --- 【***程式碼修改處***】: 強化 NextStep 狀態的輸出 ---
            # 從步驟 4 的回應中提取 NextStep 的值
            next_step_status = dec_resp4.get("NextStep")
            # 使用分隔線讓輸出更醒目
            print("\n" + "=" * 25)
            if next_step_status is not None:
                # 在主控台印出 NextStep 的狀態
                print(f"  [狀態檢查] NextStep: {next_step_status}")
            else:
                print("  [狀態檢查] 回應中未找到 NextStep 欄位。")
            print("=" * 25 + "\n")
            # --- 修改結束 ---

            print("\n=== 所有流程執行完畢 ===")

        except Exception as e:
            print(f"\n[執行流程時發生錯誤於 '{current_step_name}']: {e}")
            error_info = f"Error: {e}\n\nTraceback:\n{traceback.format_exc()}"

            failed_payload = "N/A"
            try:
                if "步驟" in current_step_name:
                    step_number = current_step_name.split(' ')[0].replace('步驟', '').replace(':', '')
                    failed_payload = locals().get(f"payload{step_number}", "N/A")
            except (IndexError, KeyError):
                pass

            reporter.add_step(current_step_name, "❌ 失敗", failed_payload, error_details=error_info)

        finally:
            reporter.finalize_report()
            reporter.save_and_open_report(base_path="C:\\icppython\\reports")


if __name__ == '__main__':
    TEST_CELLPHONE = "0978434444"
    TEST_USERCODE = "tester205"
    TEST_PASSWORD = "Aa123456"

    client = CertificateApiClient()
    client.run_complete_flow(
        cellphone=TEST_CELLPHONE,
        user_code=TEST_USERCODE,
        user_pwd=TEST_PASSWORD
    )
