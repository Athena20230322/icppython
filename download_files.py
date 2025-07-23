import requests
import os
import re


# 用於在終端機中顯示彩色文字
class bcolors:
    WARNING = '\033[91m'  # 紅色
    ENDC = '\033[0m'  # 重設顏色


def find_existing_uat_apk(directory):
    """在指定目錄中尋找現有的 UAT APK 檔案。"""
    # 確保目錄存在，避免錯誤
    if not os.path.isdir(directory):
        return None
    # 遍歷目錄下的所有檔案
    for filename in os.listdir(directory):
        # 根據您的範例，我們尋找以 'UAT' 開頭且以 '.apk' 結尾的檔案
        if filename.startswith('UAT') and filename.endswith('.apk'):
            return filename  # 找到後立即返回檔名
    return None  # 如果沒找到，返回 None


def download_file(url, save_directory, output_filename=None, existing_filename_to_compare=None):
    """
    從 URL 下載檔案，並與現有檔名進行比對。

    :param url: 要下載的檔案網址
    :param save_directory: 儲存檔案的資料夾路徑
    :param output_filename: 指定的檔案名稱。若為 None，則嘗試自動偵測。
    :param existing_filename_to_compare: (可選) 本機現有的檔名，用於比對。
    """
    detected_filename = None

    print(f"準備下載來源: {url}")

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        with requests.get(url, stream=True, headers=headers, allow_redirects=True) as r:
            r.raise_for_status()

            if not output_filename:
                content_disposition = r.headers.get('content-disposition')
                if content_disposition:
                    fname = re.findall('filename="?([^"]+)"?', content_disposition)
                    if fname:
                        detected_filename = fname[0]

                if not detected_filename:
                    detected_filename = url.split('/')[-1]

                final_filename_to_save = detected_filename
            else:
                final_filename_to_save = output_filename

            # --- 主要修改：檔名驗證邏輯 ---
            # 檢查是否有傳入 "現有檔名" 且 "偵測到的新檔名" 與它不同
            if existing_filename_to_compare and detected_filename and detected_filename != existing_filename_to_compare:
                print(f"{bcolors.WARNING}==================== 通知 ====================")
                print(f"警告：新下載的 UAT 版本檔名與現有檔案不同！")
                print(f"現有檔名: {existing_filename_to_compare}")
                print(f"新版本檔名: {detected_filename}")
                print(f"============================================{bcolors.ENDC}")

            local_filepath = os.path.join(save_directory, final_filename_to_save)
            print(f"檔案將儲存為: {local_filepath}")

            with open(local_filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"下載成功！檔案已儲存至 {local_filepath}")
            return True

    except requests.exceptions.RequestException as e:
        print(f"下載失敗: {e}")
        return False


if __name__ == "__main__":
    save_path = r"C:\icppython\uat"

    try:
        os.makedirs(save_path, exist_ok=True)
        print(f"儲存路徑 '{save_path}' 已確認。")
    except OSError as e:
        print(f"建立資料夾失敗: {e}")
        exit()

    # --- 主要修改：在下載前，先尋找本機資料夾中現有的 UAT 檔名 ---
    existing_uat_filename = find_existing_uat_apk(save_path)
    if existing_uat_filename:
        print(f"在目錄中找到現有 UAT 檔案: {existing_uat_filename}")
    else:
        print("目錄中未找到現有的 UAT 檔案，將直接下載。")

    files_to_download = [
        {
            "url": "https://download.icashsys.com.tw/sit",
            "filename": "sitUAT.apk",
            "compare_with": None  # SIT 版本不需要比對
        },
        {
            "url": "https://dl-web.dropbox.com/s/m9j2pf9l2bkjkri/icash_Pay_UAT.apk",
            "filename": None,  # 維持自動偵測
            "compare_with": existing_uat_filename  # 將找到的現有檔名傳入，用於比對
        }
    ]

    print("-" * 30)
    for file_info in files_to_download:
        download_file(
            file_info["url"],
            save_path,
            file_info["filename"],
            file_info["compare_with"]
        )
        print("-" * 30)