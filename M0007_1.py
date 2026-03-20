# (前段 RsaCryptoHelper, AesCryptoHelper 類別同上，此處略過以節省空間)

class CertificateApiClient:
    # ... (初始化與金鑰交換邏輯省略) ...

    def send_auth_sms_2023(self):
        """
        M0007_1 發送簡訊驗證_共用 (更新為 2023 版本參數)
        """
        self.generate_aes()

        # 讀取暫存的 LoginTokenID
        token_path = "C:\\icppython\\logintokenid.txt"
        with open(token_path, 'r') as f:
            login_token_id = f.read().strip()

        # 依照指定 Request Json 參數改寫
        url = "app/MemberInfo/SendAuthSMS2023"
        request_payload = {
            "CellPhone": "0979813585",
            "IDNo": "A110731353",
            "LoginTokenID": login_token_id,
            "MID": "10526311",
            "SMSAuthType": 5,
            "UserCode": ""
        }

        print(f"正在發送簡訊驗證... 手機: {request_payload['CellPhone']}")
        decrypted_data, _ = self._call_normal_api(url, request_payload)

        # 提取 AuthCode 並存檔
        auth_code = decrypted_data.get("AuthCode")
        if auth_code:
            with open("C:\\icppython\\authcode.txt", "w") as f:
                f.write(str(auth_code))
            print(f"成功取得 AuthCode: {auth_code}，已存入 authcode.txt")
        else:
            print("API 回應中未包含 AuthCode，請檢查 RtnCode")

if __name__ == '__main__':
    client = CertificateApiClient()
    try:
        # 執行流程：確保已經有 logintokenid.txt
        client.send_auth_sms_2023()
    except Exception as e:
        print(f"發送簡訊失敗：{e}")