import os
import requests
import base64
import json
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# Disable SSL warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Read post data from file
post_data_file = "C:\\icppython\\OpostData\\postData55.txt"
with open(post_data_file, 'r') as f:
    file_contents = f.read().strip().split(',')
    enc_key_id = file_contents[0]
    signature = file_contents[1]
    enc_data = file_contents[2]

# API request
url = 'https://icp-member-stage.icashpay.com.tw/app/ChatMember/QueryTransferInfoByCellPhoneOrIcpmid'
headers = {
    'X-ICP-EncKeyID': enc_key_id,
    'X-iCP-Signature': signature
}
data = {'EncData': enc_data}

# Send POST request
response = requests.post(url, headers=headers, data=data, verify=False)
print(response)

# Parse JSON response
response_json = response.json()
rtn_code = response_json['RtnCode']
rtn_msg = response_json['RtnMsg']
enc_text = response_json['EncData']

# Print response details
print(f"RtnCode: {rtn_code}")
print(f"RtnMsg: {rtn_msg}")
print(f"EncData: {enc_text}")

# Save encrypted data to file
enc_output_file = "c:\\enc\\Lenc.txt"
with open(enc_output_file, 'w') as f:
    f.write(enc_text)

# Validate RtnCode
test_data_file = "C:\\icppython\\OTestData\\ICPAPI\\M0104_QueryTransferInfoByCellPhoneOrIcpmid_1.txt"
with open(test_data_file, 'r') as f:
    file_contents = f.read()
    expected_rtn_code = file_contents.strip().split(',')[1]

if expected_rtn_code == str(rtn_code):
    print("Test Passed")
else:
    print(f"Test Failed. Expected RtnCode: {expected_rtn_code}. Actual RtnCode: {rtn_code}")

# Read key and IV for decryption
with open('C:/icppython/keyiv1.txt', 'r') as f:
    key_iv = json.load(f)

# Read encrypted data
with open('C:/enc/Lenc.txt', 'r') as f:
    encrypted_data = f.read()

# Extract AES key and IV
aes_key = key_iv['AES_Key']
aes_iv = key_iv['AES_IV']
print("AES Key:", aes_key)
print("AES IV:", aes_iv)

# Decrypt data
key = aes_key.encode('utf-8')
iv = aes_iv.encode('utf-8')
cipher = AES.new(key, AES.MODE_CBC, iv)
decoded_data = base64.b64decode(encrypted_data)
decrypted_data = cipher.decrypt(decoded_data)
decrypted_data = unpad(decrypted_data, AES.block_size)
decrypted_data = decrypted_data.decode('utf-8')
print("Decrypted Data:", decrypted_data)