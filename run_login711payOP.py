import os, subprocess, datetime, time, sys, json, base64, re
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


def decrypt_request_data(aes_key, aes_iv, enc_data_base64):
    try:
        key_bytes = aes_key.encode('utf-8')
        iv_bytes = aes_iv.encode('utf-8')
        encrypted_bytes = base64.b64decode(enc_data_base64.strip())
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
        decrypted_raw = cipher.decrypt(encrypted_bytes)
        try:
            text = unpad(decrypted_raw, AES.block_size, style='pkcs7').decode('utf-8')
        except:
            text = decrypted_raw.decode('utf-8', errors='ignore')
        match = re.search(r'\{.*\}', text, re.DOTALL)
        return match.group() if match else text
    except Exception as e:
        return f"(解密失敗: {e})"


def format_json_output(text):
    try:
        text = text.strip()
        if text.startswith('{'):
            return json.dumps(json.loads(text), indent=4, ensure_ascii=False)
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.dumps(json.loads(match.group()), indent=4, ensure_ascii=False)
    except:
        pass
    return text


def execute_test_script(script_path, is_pre_test=False):
    start_time = time.time()
    script_name = os.path.basename(script_path)
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        process = subprocess.run(f'python "{script_path}"', shell=True, capture_output=True, text=True,
                                 encoding='utf-8', timeout=60, env=env)
        stdout = process.stdout.strip()
    except Exception as e:
        stdout = f"Error: {e}"

    status = 'PASS' if (is_pre_test or 'RtnCode": 1' in stdout or '成功' in stdout) else 'FAIL'
    print(f"{'=' * 30} {script_name} {'=' * 30}\n狀態: [{status}] | 耗時: {time.time() - start_time:.2f}s")

    if "API 回應 (已解密):" in stdout:
        parts = stdout.split("API 回應 (已解密):")
        for p in parts[1:]:
            print(f"明文結果:\n{format_json_output(p)}")
    else:
        lines = [l for l in stdout.splitlines() if "RtnCode" in l or "RtnMsg" in l]
        print(f"輸出內容:\n" + ("\n".join(lines) if lines else stdout[:200]))
    print(f"{'-' * 60}\n")
    return stdout


def main():
    if os.path.exists("C:\\icppython\\session_cache.json"):
        os.remove("C:\\icppython\\session_cache.json")

    # 注意：請確保 M0005_3_711OP.py 在路徑中
    pre_scripts = ['C:\\icppython\\M0001_1.py', 'C:\\icppython\\M0007_2.py', 'C:\\icppython\\M0005_3_711payOP.py']

    print(f"=== 啟動測試: {datetime.datetime.now():%Y-%m-%d %H:%M:%S} ===\n")
    final_key, final_iv = "", ""

    for s in pre_scripts:
        out = execute_test_script(s, True)
        match = re.search(r'AES_KEY_INFO:(\{.*?\})', out)
        if match:
            aes_data = json.loads(match.group(1))
            final_key = aes_data.get('AES_Key')
            final_iv = aes_data.get('AES_IV')
            print(f">>> 擷取最新 AES 金鑰: {final_key}")

    time.sleep(1)

    print("--- 3. 解密 Request 檔案內容 ---")
    if final_key:
        data_dir = "C:\\icppython\\OpostData"
        # 這裡加入了 postData_M0132.txt
        for f_name in ['postData3.txt', 'postData12.txt', 'postData_M0132.txt']:
            path = os.path.join(data_dir, f_name)
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    parts = f.read().strip().split(',')
                    if len(parts) >= 3:
                        print(f"【檔案: {f_name}】")
                        decrypted = decrypt_request_data(final_key, final_iv, parts[2])
                        print(format_json_output(decrypted))
            print("-" * 40)
    else:
        print("錯誤：無法從 M0005 擷取金鑰資訊。")


if __name__ == '__main__':
    main()