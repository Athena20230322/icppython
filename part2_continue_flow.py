# 檔名: part2_continue_flow.py
import requests
import json
import base64
import os
import sys
from datetime import datetime
import random
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

# --- 全域設定 ---
BASE_PATH = "C:\\icppython"
REGISTRATION_LOG_FILE = os.path.join(BASE_PATH, "registration_log_foreigner.txt")
SESSION_DATA_FILE = os.path.join(BASE_PATH, "session_data.json")


# --- HTML 報告產生類別 ---
class HtmlReporter:
    """產生並儲存一個 HTML 格式的測試報告。"""

    def __init__(self, report_title):
        self.report_title = report_title
        self.steps = []
        self.start_time = datetime.now()
        self.end_time = None
        self.overall_status = "⏳ 執行中"

    def add_step(self, step_name, status, request_payload, decrypted_response=None, error_details=None):
        """新增一個 API 呼叫步驟到報告中。"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        details = {}
        if request_payload:
            payload_to_log = {k: v for k, v in request_payload.items() if not isinstance(v, tuple)}
            details["Request (解密後)"] = json.dumps(payload_to_log, indent=2, ensure_ascii=False)
        if decrypted_response:
            details["Response (解密後)"] = json.dumps(decrypted_response, indent=2, ensure_ascii=False)
        if error_details:
            details["Error Info"] = error_details
        self.steps.append({"name": step_name, "status": status, "timestamp": timestamp, "details": details})
        if "❌" in status:
            self.overall_status = "❌ 失敗"

    def finalize_report(self):
        """設定報告的最終狀態。"""
        self.end_time = datetime.now()
        if self.overall_status == "⏳ 執行中": self.overall_status = "✅ 成功"

    def generate_html(self):
        """產生完整的 HTML 報告內容。"""
        if not self.end_time: self.finalize_report()
        duration = self.end_time - self.start_time
        status_color = '#28a745' if '✅' in self.overall_status else '#dc3545'
        html = f"""
        <!DOCTYPE html><html lang="zh-Hant"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{self.report_title}</title>
        <style>
            body {{ font-family: 'Segoe UI', 'Microsoft JhengHei', '微軟正黑體', sans-serif; margin: 0; padding: 0; background-color: #f4f7f6; color: #333; }}
            .container {{ max-width: 1200px; margin: 20px auto; padding: 20px; background-color: #fff; box-shadow: 0 0 15px rgba(0,0,0,0.1); border-radius: 8px; }}
            h1 {{ color: #2c3e50; text-align: center; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            .summary {{ background-color: #ecf0f1; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 5px solid {status_color}; }}
            .summary p {{ margin: 5px 0; font-size: 1.1em;}} .summary-status {{ font-size: 1.3em; font-weight: bold; color: {status_color}; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; table-layout: fixed; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; vertical-align: top; word-wrap: break-word; }}
            th {{ background-color: #3498db; color: white; }} tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .status-success {{ color: #28a745; font-weight: bold; }} .status-failure {{ color: #dc3545; font-weight: bold; }}
            details {{ cursor: pointer; margin-top: 10px; }} summary {{ font-weight: bold; list-style-position: inside; }}
            pre {{ background-color: #2d2d2d; color: #f2f2f2; padding: 10px; border-radius: 5px; white-space: pre-wrap; word-wrap: break-word; font-family: 'Courier New', Courier, monospace; font-size: 0.9em; }}
        </style></head><body><div class="container"><h1>{self.report_title}</h1><div class="summary">
        <p><strong>整體狀態:</strong> <span class="summary-status">{self.overall_status}</span></p><p><strong>開始時間:</strong> {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>結束時間:</strong> {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}</p><p><strong>總耗時:</strong> {str(duration).split('.')[0]}</p></div><table>
        <colgroup><col style="width: 5%;"><col style="width: 25%;"><col style="width: 10%;"><col style="width: 15%;"><col style="width: 45%;"></colgroup>
        <thead><tr><th>#</th><th>執行動作</th><th>狀態</th><th>時間戳</th><th>詳細資料</th></tr></thead><tbody>
        """
        for i, step in enumerate(self.steps, 1):
            status_class = "status-success" if "✅" in step['status'] else "status-failure"
            details_html = "".join(
                [f"""<details><summary>{key}</summary><pre><code>{value}</code></pre></details>""" for key, value in
                 step['details'].items()])
            html += f"""<tr><td>{i}</td><td>{step['name']}</td><td class="{status_class}">{step['status']}</td><td>{step['timestamp']}</td><td>{details_html}</td></tr>"""
        html += """</tbody></table></div></body></html>"""
        return html

    def save_and_open_report(self, base_path):
        os.makedirs(base_path, exist_ok=True)
        filename = f"Registration_Report_Foreigner_{self.start_time.strftime('%Y%m%d_%H%M%S')}_Part2.html"
        filepath = os.path.join(base_path, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.generate_html())
            print(f"\n📄 報告已成功生成: {filepath}")
            webbrowser.open(f'file://{os.path.realpath(filepath)}')
        except Exception as e:
            print(f"\n❌ 錯誤: 無法儲存或開啟報告: {e}")


# --- 加密/解密輔助類別 (合併版) ---
class RsaCryptoHelper:
    def __init__(self):
        self._key = None

    def import_pem_public_key(self, pem_key):
        if not pem_key.strip().startswith(
                '-----BEGIN'): pem_key = f"-----BEGIN PUBLIC KEY-----\n{pem_key}\n-----END PUBLIC KEY-----"
        self._key = RSA.import_key(pem_key)

    def import_pem_private_key(self, pem_key):
        self._key = RSA.import_key(pem_key)

    # === START: ADDED MISSING METHODS ===
    def encrypt(self, data):
        key_size_bytes = self._key.size_in_bytes()
        max_chunk_size = key_size_bytes - 11
        data_bytes = data.encode('utf-8')
        encrypted_chunks = []
        for i in range(0, len(data_bytes), max_chunk_size):
            chunk = data_bytes[i:i + max_chunk_size]
            cipher_rsa = PKCS1_v1_5.new(self._key)
            encrypted_chunks.append(cipher_rsa.encrypt(chunk))
        return base64.b64encode(b''.join(encrypted_chunks)).decode('utf-8')

    def decrypt(self, enc_data):
        encrypted_bytes = base64.b64decode(enc_data)
        key_size_bytes = self._key.size_in_bytes()
        decrypted_chunks = []
        for i in range(0, len(encrypted_bytes), key_size_bytes):
            chunk = encrypted_bytes[i:i + key_size_bytes]
            cipher_rsa = PKCS1_v1_5.new(self._key)
            decrypted_chunks.append(cipher_rsa.decrypt(chunk, b'error_sentinel'))
        if b'error_sentinel' in decrypted_chunks:
            raise ValueError("RSA 解密失敗。")
        return b''.join(decrypted_chunks).decode('utf-8')

    def sign_data_with_sha256(self, data):
        h = SHA256.new(data.encode('utf-8'))
        return base64.b64encode(pkcs1_15.new(self._key).sign(h)).decode('utf-8')

    # === END: ADDED MISSING METHODS ===

    def verify_sign_data_with_sha256(self, data, signature):
        h = SHA256.new(data.encode('utf-8'))
        if signature is None: return False
        try:
            pkcs1_15.new(self._key).verify(h, base64.b64decode(signature))
            return True
        except (ValueError, TypeError):
            return False


class AesCryptoHelper:
    def __init__(self, key, iv):
        self.key, self.iv = key.encode('utf-8'), iv.encode('utf-8')

    def encrypt(self, data):
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        padded_data = pad(data.encode('utf-8'), AES.block_size, style='pkcs7')
        return base64.b64encode(cipher.encrypt(padded_data)).decode('utf-8')

    def decrypt(self, enc_data):
        encrypted_bytes = base64.b64decode(enc_data)
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        decrypted_padded_bytes = cipher.decrypt(encrypted_bytes)
        return unpad(decrypted_padded_bytes, AES.block_size, style='pkcs7').decode('utf-8')


# --- 主要 API 客戶端類別 ---
class FullFlowApiClient:
    def __init__(self, base_url="https://icp-member-stage.icashpay.com.tw/"):
        self.base_url = base_url
        self.rsa_helper = RsaCryptoHelper()
        self.session = requests.Session()
        self._server_public_key, self._client_private_key, self._aes_key_id, self._aes_key, self._aes_iv, self._login_token_id = (
                                                                                                                                     None,) * 6
        self.cell_phone = None
        self.common_device_info = None

    def _call_api(self, endpoint, payload, files=None, use_aes=True, skip_verification=False):
        print(f"\n--- 步驟: 呼叫 {endpoint} ---")
        json_payload = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
        if use_aes:
            if not all([self._aes_key, self._aes_iv, self._aes_key_id]): raise Exception("AES 金鑰尚未初始化…")

            aes_helper = AesCryptoHelper(self._aes_key, self._aes_iv)
            enc_data = aes_helper.encrypt(json_payload)

            headers = {'X-iCP-EncKeyID': str(self._aes_key_id)}
        else:
            self.rsa_helper.import_pem_public_key(payload['ServerPubKey'])
            enc_data = self.rsa_helper.encrypt(json_payload)
            headers = {'X-iCP-DefaultPubCertID': str(payload['CertID'])}
        self.rsa_helper.import_pem_private_key(self._client_private_key)
        # This line was causing the error, it will now work
        signature = self.rsa_helper.sign_data_with_sha256(enc_data)
        headers['X-iCP-Signature'] = signature
        url = f"{self.base_url}{endpoint}"
        print(f"Request Payload (加密前): {json_payload}")
        if files:
            print(f"附加檔案: {list(files.keys())}")
            response = self.session.post(url, data={'EncData': enc_data}, files=files, headers=headers)
        else:
            response = self.session.post(url, data={'EncData': enc_data}, headers=headers)
        response.raise_for_status()
        response_content = response.text
        print(f"API 原始回應: {response_content}")
        response_signature = response.headers.get('X-iCP-Signature')
        if not skip_verification:
            self.rsa_helper.import_pem_public_key(self._server_public_key)
            if not self.rsa_helper.verify_sign_data_with_sha256(response_content, response_signature): raise Exception(
                f"{endpoint} 的回應簽章驗證失敗。")
            print("回應簽章驗證成功。")
        response_json = json.loads(response_content)
        if response_json.get('RtnCode') not in [1, 100001]:
            raise Exception(f"API 返回錯誤 (RtnCode {response_json.get('RtnCode')}): {response_json.get('RtnMsg')}")
        if 'EncData' in response_json and response_json['EncData']:
            if use_aes:
                decrypted_data_str = AesCryptoHelper(self._aes_key, self._aes_iv).decrypt(response_json['EncData'])
            else:
                self.rsa_helper.import_pem_private_key(self._client_private_key)
                decrypted_data_str = self.rsa_helper.decrypt(response_json['EncData'])
            print(f"回應 (已解密): {decrypted_data_str}")
            decrypted_json = json.loads(decrypted_data_str)
        else:
            decrypted_json = response_json
            print(f"回應 (無加密): {json.dumps(decrypted_json, ensure_ascii=False, indent=2)}")
        return decrypted_json, response_content, response_signature

    def load_session_data(self):
        """從檔案中讀取並恢復流程所需的所有關鍵資訊"""
        try:
            with open(SESSION_DATA_FILE, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            self.cell_phone = session_data["cell_phone"]
            self._login_token_id = session_data["login_token_id"]
            self.common_device_info = session_data["common_device_info"]
            self._server_public_key = session_data["server_public_key"]
            self._client_private_key = session_data["client_private_key"]
            self._aes_key_id = session_data["aes_key_id"]
            self._aes_key = session_data["aes_key"]
            self._aes_iv = session_data["aes_iv"]
            print(f"✅ 成功從 {SESSION_DATA_FILE} 載入流程狀態。")
            print(f"   將對手機號碼 {self.cell_phone} 繼續執行操作。")
            return True
        except FileNotFoundError:
            print(f"❌ 錯誤: 找不到 session 檔案: {SESSION_DATA_FILE}")
            print("   請先執行 part1_register.py 來產生 session 檔案。")
            return False
        except Exception as e:
            print(f"❌ 錯誤: 載入 session 檔案時發生問題: {e}")
            return False

    def continue_part2_flow(self):
        """執行註冊流程的後半部分 (步驟 6-7)"""
        if not self.load_session_data():
            return
        reporter = HtmlReporter(report_title="iCashPay API 外國人註冊流程報告 (Part 2)")
        current_step = "開始接續流程"
        log_data = {}
        try:
            # === 步驟 6: 檢查是否為OP會員 (CheckIsOP) ===
            current_step = "步驟 6: 檢查是否為OP會員 (CheckIsOP)"
            payload6 = {**self.common_device_info, 'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
                        'CellPhone': self.cell_phone}
            result6, _, _ = self._call_api("app/MemberInfo/CheckIsOP", payload6)
            reporter.add_step(current_step, "✅ 成功", payload6, result6)
            print("檢查OP會員狀態成功。")

            # === 步驟 7: 註冊為OP會員 (RegisterOpMember) ===
            current_step = "步驟 7: 註冊為OP會員 (RegisterOpMember)"
            payload7 = {**self.common_device_info, 'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
                        'CellPhone': self.cell_phone, 'Birthday': "20000101"}
            result7, _, _ = self._call_api("app/MemberInfo/RegisterOpMember", payload7)
            reporter.add_step(current_step, "✅ 成功", payload7, result7)
            print("註冊OP會員成功。")

            print("\n======= ✅ 全部 7 個步驟流程執行成功！ ✅ =======")
        except Exception as e:
            print(f"\n======= ❌ 流程執行失敗於: {current_step} ❌ =======")
            print(f"錯誤訊息: {e}")
            error_info = f"Error: {e}\n\nTraceback:\n{traceback.format_exc()}"
            failed_payload = locals().get(f'payload{current_step[3].replace(":", "")}',
                                          None) if current_step.startswith("步驟") else log_data
            reporter.add_step(current_step, "❌ 失敗", failed_payload, error_details=error_info)
            print(f"====================================")
        finally:
            reporter.finalize_report()
            reporter.save_and_open_report(BASE_PATH)


if __name__ == '__main__':
    print("--- iCashPay 註冊流程 Part 2 (步驟 6-7) ---")
    input("請確認後台審核已通過，按 Enter 鍵繼續執行...")
    print("--------------------")

    api_client = FullFlowApiClient()
    api_client.continue_part2_flow()