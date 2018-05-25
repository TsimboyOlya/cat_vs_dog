#!/usr/bin/python3

import socket
import threading
from boltons import socketutils
import queue
from utils import send_int, send_str, TIMEOUT, MAGIC_INIT_BYTES, MAGIC_BYTES

from bs4 import BeautifulSoup
import urllib.request
from urllib.parse import urlparse, urlunparse, urljoin
import requests
import os
import argparse
import time


def get_links(url):
    try:
        resp = urllib.request.urlopen(url)
        soup = BeautifulSoup(resp, "lxml", from_encoding=resp.info().get_param('charset'))

        def fix_url(u):
            if 'http' not in u:
                u = urljoin(url, u)
            parse_result = urlparse(u, scheme='https')
            return urlunparse(parse_result)

        return [fix_url(link['href']) for link in soup.find_all('a', href=True)]
    except Exception as a:
        print('Exception!', a)
        return []

def get_img_links(url):
    try:
        import re
        p = re.compile(r'(.*(jpg).*)$')

        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, "lxml")
        srcs = []
        for img in soup.findAll('img'):
            srcs.append(img['src'])
            if 'srcset' in img:
                srcs.extend(img['srcset'].split(','))
        srcs = map(lambda s: urljoin(url, s) if 'http' not in s else s, filter(p.match, srcs))
        return list(srcs)

    except Exception as a:
        print('Exception!', a)
        return []


class Task:
    def __init__(self, image_url):
        self.url = image_url
        self.result = None

    def is_ready(self):
        return self.result is not None

    def answer(self):
        if self.result is not None:
            return self.result
        else:
            raise RuntimeError('task is not ready')


class Worker:
    def __init__(self, sock, addr):
        self.sock = sock
        self.addr = addr
        self.thread = None

    def process(self, task):
        self.sock.send(MAGIC_BYTES, timeout=TIMEOUT)
        send_str(self.sock, task.url)
        answer = self.sock.recv_size(size=1, timeout=10)
        task.result = 'cat' if answer == b'1' else 'dog'

    def send_model(self, model_path):
        print('send_model')
        with open(model_path, 'rb') as model_file:
            model_bytes = model_file.read()

        self.sock.send(MAGIC_INIT_BYTES, timeout=TIMEOUT)
        model_size = len(model_bytes)
        send_int(self.sock, model_size)
        self.sock.send(model_bytes)
        print('model sended')


class CatDogServer:
    def __init__(self, server_port=17612, model_path='cats_vs_dogs/cats_vs_dogs.h5'):
        self.model_path = model_path

        self.srv_sock = socket.socket()
        self.srv_sock.bind(('', server_port))
        self.srv_sock.listen()

        self.WORKERS = []
        self.TASK_QUEUE = queue.Queue()
        self.RESULT_QUEUE = queue.Queue()

    def task_handler(self, worker):
        try:
            print('task_handler')
            worker.send_model(self.model_path)
            while True:
                task = self.TASK_QUEUE.get()
                if task is None:
                    break

                print('new task:', task.url)
                worker.process(task)
                print('task processed')
                print(task.url, '->', task.result)

                self.RESULT_QUEUE.put(task)

                self.TASK_QUEUE.task_done()
        except Exception as e:
            print('Exception in worker thread: {}'.format(e))
        finally:
            print('worker socket close')
            worker.sock.close()


    def workers_handler(self):
        print('workers_handler')
        #self.srv_sock.settimeout(5.0)
        while self.working:
            try:
                raw_worker_sock, addr = self.srv_sock.accept()
                print('New worker from:', addr)
                worker_sock = socketutils.BufferedSocket(raw_worker_sock, timeout=5, maxsize=16384)
                worker = Worker(worker_sock, addr)
                self.WORKERS.append(worker)
                print('create thread')
                worker_thread = threading.Thread(target=self.task_handler, args=[worker])
                worker.thread = worker_thread
                worker.thread.start()
                print('worker thread started')

            except Exception as e:
                print('Exception {} in workers_handler, break'.format(e))
                break
        print('workers handler tear down')
        self.srv_sock.close()


    def start(self):
        print('start')
        self.workers_handling_thread = threading.Thread(target=self.workers_handler, args=[])
        self.working = True
        self.workers_handling_thread.start()

    def get_results(self, num_results):
        results = {}

        for _ in range(num_results):
            if not self.RESULT_QUEUE.empty():
                res = self.RESULT_QUEUE.get()
                results[res.url] = res.answer()
                if res.answer() is 'cat':
                    print('New cat URL: <{}>'.format(res.url))
                self.RESULT_QUEUE.task_done()

        return results

    def append_task(self, url):
        self.TASK_QUEUE.put(Task(url))

    def tear_down(self):
        for _ in range(len(self.WORKERS)):
            self.TASK_QUEUE.put(None)

        for worker in self.WORKERS:
            worker.thread.join()

        self.working = False
        self.workers_handling_thread.join()


# python3 server.py --model=./cats_vs_dogs/cats_vs_dogs.h5 --port=23452 --urls=https://pixabay.com/en/photos/?q=cat+%2B+dog&image_type=photo&cat=&min_height=&min_width=&order=upcoming&pagi=3^C

if __name__ == '__main__':
    #u = 'https://en.wikipedia.org/wiki/Cat'

    #ll = get_img_links(u)
    #for l in ll:
    #    print(l)
    #exit(0)

    parser = argparse.ArgumentParser(description='Find cat images by URL')

    parser.add_argument('--model',type=str,
                        required=True,
                        help='Path to file with model')

    parser.add_argument('--port',type=int,
                        required=True,
                        help='Port for server')

    parser.add_argument('--urls',
                        required=True,
                        help='URLs for searching, comma-separated')


    parser.add_argument('--workers', type=int,
                        default=1,
                        help='Wait for certain num of workers')

    args = parser.parse_args()


    srv = CatDogServer(
        server_port=args.port,
        model_path=args.model
    )
    try:
        srv.start()

        print('Wait for all workers')

        while len(srv.WORKERS) < args.workers:
            time.sleep(1.0)

        print('Start sending tasks')

        urls_count = 0
        cats_count = 0
        for page_url in args.urls.split(','):
            urls_to_check = get_img_links(page_url)
            urls_count += len(urls_to_check)
            for url in urls_to_check:
                srv.append_task(url)

        time.sleep(5.0)

        while urls_count > 0:
            res = srv.get_results(num_results=5)
            urls_count -= len(res)

            for url, _ in filter(lambda item: item[1] == 'cat', res.items()):
                cats_count += 1
                print('Download cat image #{} from {}'.format(cats_count, url))
                with open('cat_{}.jpg'.format(cats_count), 'wb') as cat_img:
                    cat_img.write(requests.get(url).content)
            time.sleep(1.0)

    except Exception as e:
        print('Exception during fetching results: {}'.format(e))
    finally:
        srv.tear_down()
        exit(0)
