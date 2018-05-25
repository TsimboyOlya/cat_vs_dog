#!/usr/bin/python3

import socket
import threading
from boltons import socketutils
import requests
import io

import keras
from keras.models import load_model
import numpy as np
from PIL import Image

from utils import recv_int, recv_str, TIMEOUT, MAGIC_INIT_BYTES, MAGIC_BYTES
import argparse

def downloadToImage(img_url):
    img_bytes = requests.get(img_url).content
    image = Image.open(io.BytesIO(img_bytes))
    return image


def is_cat(image, model):
    if model is None:
        raise RuntimeError('No model recieved')

    try:
        SAMPLE_SIZE = (128, 128)
        img = image.resize(SAMPLE_SIZE)
        img_arr = np.array(img)
        img_arr = np.expand_dims(img_arr, axis=0)

        result = model.predict(x=img_arr)
        return np.asscalar(result) == 1
    except:
        return False


class CatDogClient:
    def __init__(self, port=17612, addr='localhost'):
        self.host_port = port
        self.host_addr = addr
        self.model = None

    def main_loop(self):
        raw_sock = socket.socket()
        raw_sock.connect((self.host_addr, self.host_port))
        print('connected')
        buf_sock = socketutils.BufferedSocket(raw_sock, timeout=TIMEOUT, maxsize=1024 * 16)

        try:
            assert MAGIC_INIT_BYTES == buf_sock.recv_size(size=len(MAGIC_INIT_BYTES), timeout=None)
            model_size = recv_int(buf_sock)
            print('model size:', model_size)
            model_bytes = buf_sock.recv_size(size=model_size, timeout=TIMEOUT)
            print('model recieved')
            model_file = open('current_model.h5', 'wb')
            model_file.write(model_bytes)
            model_file.close()

            self.model = load_model('current_model.h5')

            while True:
                print('wait task')
                head_bytes = buf_sock.recv_size(size=len(MAGIC_BYTES), timeout=None)
                print('new task')
                assert head_bytes == MAGIC_BYTES

                img_url = recv_str(buf_sock)
                img = downloadToImage(img_url)
                is_img_cat = is_cat(img, self.model)
                print('Result: {} is {} URL'.format(img_url, 'cat' if is_img_cat else 'dog'))
                buf_sock.sendall(b'1' if is_img_cat else b'0', timeout=TIMEOUT)
        except socketutils.ConnectionClosed:
            print('Connection is closed, tear down')
        finally:
            buf_sock.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Executor for cat searcher')

    parser.add_argument('--addr',type=str,
                        required=True,
                        help='Address of server')

    parser.add_argument('--port',type=int,
                        required=True,
                        help='Port of server')

    args = parser.parse_args()

    clt = CatDogClient(
        port=args.port,
        addr=args.addr
    )
    clt.main_loop()

