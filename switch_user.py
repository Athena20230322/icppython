import json
import os

# 定義四組帳號資料
users = [
    {"UserCode": "i1753422584", "CellPhone": "0950001657"},
    {"UserCode": "i1753424540", "CellPhone": "0950001658"},
    {"UserCode": "i1753424931", "CellPhone": "0950001659"},
    {"UserCode": "i1753669507", "CellPhone": "0950001660"}
]


def switch():
    print("=== iCashPay 測試帳號切換器 ===")
    for i, user in enumerate(users):
        print(f"[{i}] UserCode: {user['UserCode']} | CellPhone: {user['CellPhone']}")

    try:
        choice = int(input("\n請輸入欲切換的帳號編號 (0-3): "))
        if 0 <= choice < len(users):
            selected = users[choice]
            # 寫入 current_user.json
            with open("C:\\icppython\\current_user.json", "w") as f:
                json.dump(selected, f)
            print(f"\n✅ 已成功切換至: {selected['CellPhone']}")
        else:
            print("❌ 編號超出範圍")
    except ValueError:
        print("❌ 請輸入數字")


if __name__ == "__main__":
    switch()