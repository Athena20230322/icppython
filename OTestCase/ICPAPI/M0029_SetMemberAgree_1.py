import os
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

postData = "C:\\icppython\\OpostData\\postData23.txt"

#postData = os.path.join('C:', os.sep, 'IcashPost', 'ICPAPIVS', 'CreateBarcode', 'icashendurance',
                        #'ConsoleApp1', 'bin', 'Debug', 'postData1.txt')

with open(postData, 'r') as f:
    # Read the contents of the file and split into the three variables
    file_contents = f.read().strip().split(',')
    enc_key_id = file_contents[0]
    signature = file_contents[1]
    enc_data = file_contents[2]


url = 'https://icp-member-stage.icashpay.com.tw/app/MemberInfo/SetMemberAgree'


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




# Print the values of RtnCode RtnMsg and EncData

print(f"RtnCode: {rtn_code}")
print(f"RtnMsg: {rtn_msg}")
#print(f"EncData: {enc_text}")


#enc_text = response.json()["EncData"]

with open("c:\\enc\\Lenc.txt", 'w') as f:
    f.write(enc_text)

# Validate RtnCode value
test_data_file = "C:\\icppython\\OTestData\\ICPAPI\\M0029_SetMemberAgree_1.txt"
with open(test_data_file, 'r') as f:
    file_contents = f.read()
    expected_rtn_code = file_contents.strip().split(',')[1]

if expected_rtn_code == str(rtn_code):
    print("Test Passed")
else:
    print("Test Failed. Expected RtnCode: %s. Actual RtnCode: %s" % (expected_rtn_code, rtn_code))



