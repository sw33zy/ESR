import logging
import socket
import sys
import threading
import time

from tkinter import Tk
from ClienteGui import ClienteGUI
from ott import Ott

bootstrapper_info = {'addr': sys.argv[1], 'port': 7000}

def initOtt():
    """
    Initializes the client.
    """

    global ott_manager
    ott_manager = Ott(bootstrapper_info)
    threading.Thread(target=ott_manager.serve_forever).start()
    return

def initClient():

    # Create a new client
    threading.Thread(target=askForStream).start()
    root = Tk()
    app = ClienteGUI(root, ott_manager)
    app.master.title("Cliente")
    root.mainloop()



def askForStream():
    clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientsocket.connect((bootstrapper_info['addr'], 20000))
    try:
        while True:
            time.sleep(5)

    finally:
        clientsocket.close()

    #clientsocket.send("movie.Mjpeg".encode())


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(filename)s:%(funcName)s - %(message)s')
    initOtt()
    initClient()



