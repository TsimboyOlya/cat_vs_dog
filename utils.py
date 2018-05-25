

TIMEOUT = 5.0
MAGIC_INIT_BYTES = b'\x7a\xc5\xfc\xa6\x5b\x7d\xe1\xff'
MAGIC_BYTES = bytes([0x7f, 0x45, 0x4c, 0x46, 0x51, 0x76, 0x31, 0xff])

def send_int(sock, value, timeout=TIMEOUT):
    #print('send_int')
    sock.send(value.to_bytes(4, byteorder='big'), timeout=timeout)

def send_str(sock, value, timeout=TIMEOUT):
    #print('send_str')
    value_bytes = value.encode()
    sock.send((len(value_bytes)).to_bytes(4, byteorder='big'), timeout=timeout)
    sock.send(value_bytes, timeout=timeout)

def recv_int(sock, timeout=TIMEOUT):
    #print('recv_int')
    int_bytes = sock.recv_size(size=4, timeout=timeout)
    return int.from_bytes(int_bytes, byteorder='big')    

def recv_str(sock, timeout=TIMEOUT):
    #print('recv_str')
    str_size_bytes = sock.recv_size(size=4, timeout=timeout)
    str_size = int.from_bytes(str_size_bytes, byteorder='big')
    
    str_bytes = sock.recv_size(size=str_size, timeout=timeout)
    return str_bytes.decode()
