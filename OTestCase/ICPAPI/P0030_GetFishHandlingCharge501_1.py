import os
import requests
import base64
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

postData = "C:\\icppython\\OpostData\\postData16.txt"

#postData = os.path.join('C:', os.sep, 'IcashPost', 'ICPAPIVS', 'CreateBarcode', 'icashendurance',
                        #'ConsoleApp1', 'bin', 'Debug', 'postData1.txt')

with open(postData, 'r') as f:
    # Read the contents of the file and split into the three variables
    file_contents = f.read().strip().split(',')
    enc_key_id = file_contents[0]
    signature = file_contents[1]
    enc_data = file_contents[2]


url = 'https://icp-payment-stage.icashpay.com.tw/app/TransferAccount/GetFiscHandlingCharge'


headers = {
    'X-ICP-EncKeyID': enc_key_id,
    'X-iCP-Signature': signature
}


data = {'EncData': enc_data}


response = requests.post(url, headers=headers, data=data, verify=False)
print(response)

# Parse the JSON response and extract RtnCode, RtnMsg, and EncData
response_json = response.json()
rtn_code = response_json['RtnCode']
rtn_msg = response_json['RtnMsg']
enc_text = response_json['EncData']

# Print the values of RtnCode, RtnMsg, and EncData
print(f"RtnCode: {rtn_code}")
print(f"RtnMsg: {rtn_msg}")
#print(f"EncData: {enc_text}")


#enc_text = response.json()["EncData"]

with open("c:\\enc\\Lenc.txt", 'w') as f:
    f.write(enc_text)

# Validate RtnCode value
test_data_file = "C:\\icppython\\OTestData\\ICPAPI\\P0030_GetFishHandlingCharge501_1.txt"
with open(test_data_file, 'r') as f:
    file_contents = f.read()
    expected_rtn_code = None
    expected_rtn_msg = None
    expected_handling_charge = None

    with open('C:/icppython/keyiv1.txt', 'r') as f:
        key_iv = json.load(f)

    with open('C:/enc/Lenc.txt', 'r') as f:
        encrypted_data = f.read()

    aes_key = key_iv['AES_Key']
    aes_iv = key_iv['AES_IV']

    print("AES Key: ", aes_key)
    print("AES IV: ", aes_iv)

    key = aes_key.encode('utf-8')
    iv = aes_iv.encode('utf-8')

    # 解密數據
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decoded_data = base64.b64decode(encrypted_data)
    decrypted_data = cipher.decrypt(decoded_data)
    decrypted_data = unpad(decrypted_data, AES.block_size)
    decrypted_data = decrypted_data.decode('utf-8')
    print(decrypted_data)

# Parse the file contents and extract expected values
for line in file_contents.strip().split('\n'):
    key, value = line.strip().split(',')
    if key == 'RtnCode':
        expected_rtn_code = value
    elif key == 'RtnMsg':
        expected_rtn_msg = value.rstrip(',')  # Remove trailing comma
    elif key == 'HandlingCharge':
        expected_handling_charge = value

# Validate RtnCode and RtnMsg values
if expected_rtn_code == str(rtn_code) and expected_rtn_msg in rtn_msg:
    print("RtnCode and RtnMsg Test Passed")

# Validate HandlingCharge value
expected_handling_charge = str(expected_handling_charge)  # Ensure both are strings for consistent comparison

# Extract the actual handling charge from the decrypted JSON string
actual_handling_charge = json.loads(decrypted_data)["HandlingCharge"]
actual_handling_charge = str(actual_handling_charge).strip()  # Remove extra spaces or characters

if expected_handling_charge == actual_handling_charge:
    print("HandlingCharge Test Passed")
else:
    print("HandlingCharge Test Failed. Expected HandlingCharge: %s, Actual HandlingCharge: %s" % (expected_handling_charge, actual_handling_charge))
