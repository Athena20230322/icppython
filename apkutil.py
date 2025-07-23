#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
# 打印 sys.path 以幫助診斷模組搜尋路徑問題
print("--- sys.path when running script ---")
for p in sys.path:
    print(p)
print("------------------------------------")

import requests
import os
from apkutils.apk import ApkInfo # ✨ 修正：從 apkutils.apk 導入 ApkInfo
import tempfile # 用於創建臨時文件

def get_apk_version_from_url(url, output_dir="temp_apks"):
    """
    從給定的 URL 下載 APK 檔案，並解析其版本號。

    Args:
        url (str): APK 檔案的下載 URL。
        output_dir (str): 暫存 APK 檔案的目錄。

    Returns:
        tuple: (version_name, version_code) 如果成功解析，否則返回 (None, None)。
    """
    # 檢查 URL 是否以 .apk 結尾，但即使不是也會嘗試下載和解析
    if not url.endswith('.apk'):
        print(f"警告: 連結 '{url}' 沒有以 '.apk' 結尾。此函數預期直接的 APK 下載連結。")
        print(f"將嘗試下載並解析，但如果內容不是有效的 APK 檔案，將會失敗。")

    # 創建暫存目錄
    os.makedirs(output_dir, exist_ok=True)

    # 從 URL 提取檔名
    # 由於 URL 可能不包含 .apk 結尾，這裡給一個預設的檔名
    file_name = os.path.basename(url)
    if not file_name or '.' not in file_name: # 如果 URL 以 / 結尾或沒有副檔名
        file_name = "downloaded_app.apk" # 給一個預設名稱，確保有副檔名以便 apkutils 識別

    apk_path = os.path.join(output_dir, file_name)

    print(f"開始從 {url} 下載內容到 {apk_path}...")
    try:
        # 設置 stream=True 以便流式下載，適用於大檔案
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status() # 如果請求失敗，拋出 HTTPError
            total_size = int(r.headers.get('content-length', 0))
            downloaded_size = 0
            with open(apk_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): # 每次下載 8KB
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        # 簡單的進度顯示 (可選)
                        # print(f"\r下載進度: {downloaded_size / (1024 * 1024):.2f}MB / {total_size / (1024 * 1024):.2f}MB", end='')
            print(f"\n下載完成: {apk_path}")

    except requests.exceptions.RequestException as e:
        print(f"下載內容時發生錯誤: {e}")
        if os.path.exists(apk_path):
            os.remove(apk_path) # 失敗時清除部分下載的檔案
        return None, None
    except Exception as e:
        print(f"處理下載時發生未知錯誤: {e}")
        if os.path.exists(apk_path):
            os.remove(apk_path)
        return None, None

    try:
        print(f"開始解析 APK: {apk_path} ...")
        apk_info = ApkInfo(apk_path)

        version_name = apk_info.get_manifest().get("version_name")
        version_code = apk_info.get_manifest().get("version_code")

        print(f"解析成功！")
        print(f"  Version Name (版本名稱): {version_name}")
        print(f"  Version Code (版本號): {version_code}")

        # 解析完畢後刪除暫存的 APK 檔案
        os.remove(apk_path)
        print(f"已刪除暫存檔案: {apk_path}")

        return version_name, version_code

    except Exception as e:
        print(f"解析 APK 檔案時發生錯誤: {e}")
        if os.path.exists(apk_path): # 確保即使解析失敗也刪除檔案
            os.remove(apk_path)
            print(f"已刪除暫存檔案 (因解析錯誤): {apk_path}")
        return None, None

# --- 使用範例 ---
if __name__ == "__main__":
    # --- 請將這裡的範例 URL 替換為您的實際 URL ---
    # 由於您提供的連結可能不是直接的 .apk 檔案，此腳本會嘗試下載並解析其內容。
    # 如果內容不是有效的 APK 檔案，解析將會失敗。

    icash_sit_uat_url = "https://download.icashsys.com.tw/sitUAT"
    icash_uat_url = "https://download.icashsys.com.tw/uat"

    print(f"\n--- 嘗試解析 icash sitUAT 連結: {icash_sit_uat_url} ---")
    sit_uat_version_name, sit_uat_version_code = get_apk_version_from_url(icash_sit_uat_url)
    if sit_uat_version_name and sit_uat_version_code:
        print(f"icash sitUAT 最終結果: 版本名稱={sit_uat_version_name}, 版本號={sit_uat_version_code}")
    else:
        print("icash sitUAT 未能成功獲取版本號。")

    print(f"\n--- 嘗試解析 icash UAT 連結: {icash_uat_url} ---")
    uat_version_name, uat_version_code = get_apk_version_from_url(icash_uat_url)
    if uat_version_name and uat_version_code:
        print(f"icash UAT 最終結果: 版本名稱={uat_version_name}, 版本號={uat_version_code}")
    else:
        print("icash UAT 未能成功獲取版本號。")

