import base64

from Crypto import Random
from Crypto.Cipher import AES

BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
unpad = lambda s : s[0:-ord(s[-1])]


class AESCipher:

    def __init__( self, key, iv ):
        self.key = key
        self.iv = iv

    def encrypt( self, raw ):
        raw = pad(raw)
        cipher = AES.new( self.key, AES.MODE_CBC, self.iv )
        return base64.b64encode( self.iv + cipher.encrypt( raw ) )

