from cryptography.fernet import Fernet
import os


key = Fernet.generate_key()
with open("secret.key", "wb") as key_file:
    key_file.write(key)
print(f"Generated key: {key.decode()}")

def encrypt_file(filename, key):
    fernet = Fernet(key)
    with open(filename, "rb") as file:
        original = file.read()
    encrypted = fernet.encrypt(original)
    with open(filename + ".encrypted", "wb") as encrypted_file:
        encrypted_file.write(encrypted)

encrypt_file("tst.xlsx", key)
os.remove("tst.xlsx")  # Remove the original file after encryption

with open("secret.key", "rb") as key_file:
    key = key_file.read()
def decrypt_file(filename, key):
    fernet = Fernet(key)
    with open(filename, "rb") as encrypted_file:
        encrypted = encrypted_file.read()
    decrypted = fernet.decrypt(encrypted)
    with open(filename.replace(".encrypted", ""), "wb") as decrypted_file:
        decrypted_file.write(decrypted)

decrypt_file("tst.xlsx.encrypted", key)
os.remove("tst.xlsx.encrypted")  # Remove the encrypted file after decryption
os.remove("secret.key")

