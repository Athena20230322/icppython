import base64
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

with open('C:/IcashPost/NEWICPAPI/NewLogin/ML203/ConsoleApp1/bin/Debug/keyiv1.txt', 'r') as f:
    key_iv = json.load(f)

with open('C:/Lenc.txt', 'r') as f:
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