import logging
import sys
import threading
import time
import socket

import paths
from RtpPacket import RtpPacket
from VideoStream import VideoStream
from ott import Ott

class Server:
    clientInfo = {}

    def __init__(self):
        """
        Initializes the server.
        """
        self.filename = "movie.Mjpeg"
        self.clientInfo['videoStream'] = VideoStream(self.filename)
        self.clientInfo['event'] = threading.Event()
        self.clientInfo['worker'] = threading.Thread(target=self.sendThroughOtt)
        self.clientInfo['pingThread'] = threading.Thread(target=self.sendPingThroughOtt)

        return


    def main(self):
        self.initOtt()
        self.initServer()


    def initOtt(self):
        """
        Initializes the server.
        """
        global ott_manager
        bootstrapper_info = {}
        ott_manager = Ott(bootstrapper_info)
        threading.Thread(target=ott_manager.serve_forever).start()
        self.clientInfo['worker'].start()
        self.clientInfo['pingThread'].start()
        return

    def initServer(self):
        """
        Initializes the server.
        """
        self.clientInfo['videoStream'] = VideoStream(self.filename)
        socketServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socketServer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        socketServer.bind(('10.0.0.10', 20000))
        socketServer.listen(5)
        while True:
            clientSocket, address = socketServer.accept()
            logging.info("Client connected from: %s", address)
            clientsids = self.clientInfo.get('clients',[])
            if self.noClients():
                self.clientInfo['event'].clear()
            clientsids.append(address[0])
            self.clientInfo['clients'] = clientsids
            threading.Thread(target=self.clientWorker,args=(clientSocket,address[0])).start()



    def clientWorker(self,clientSocket, address):
        self.clientInfo['path'] = self.getPathsToGo(self.clientInfo['clients'])

        try:
            message = clientSocket.recv(1024).decode()

        finally:
            if self.noClients():
                self.clientInfo['event'].set()
            self.clientInfo['clients'].remove(address)
            logging.info("Client disconnected from: %s", address)
            clientSocket.close()


    def noClients(self):
        return self.clientInfo.get('clients',[]) == []

    def sendThroughOtt(self):

        while True:
            if self.noClients():
                continue
            if self.clientInfo['event'].isSet():
                logging.debug("Event is set")
                break
            self.sendStream()
            time.sleep(0.05)


    def sendPingThroughOtt(self):
        while True:
            time.sleep(1)
            if self.noClients():
                continue
            if self.clientInfo['event'].isSet():
                logging.debug("Event is set")
                break
            address, paths = self.clientInfo.get('path', (None, []))
            if address is None: return
            ott_manager.send_ping(self.clientInfo['clients'], paths)



    def sendStream(self):
        address, paths = self.clientInfo.get('path', (None, []))
        # logging.debug("Sending to %s", address)
        if address is None: return
        # ott_manager.broadcast_message(address)

        data = self.clientInfo['videoStream'].nextFrame()
        if data:
            frameNumber = self.clientInfo['videoStream'].frameNbr()
            packet = self.makeRtp(data, frameNumber)
            ott_manager.send_data(packet, self.clientInfo['clients'], paths)
        else:
            self.clientInfo['videoStream'] = VideoStream(self.filename)



    def sendPingToAllNodes(self):
        addrlist = ott_manager.get_online_nodes_addr()
        for a in addrlist:
            address, path = self.getPathsToGo(a)
            if address is None : return
            logging.info(f'paths to go {path}')
            ott_manager.send_ping(addrlist, path)



    def getPathToGo(self,addr):
        graph = paths.initGraph()
        path = paths.shortest_path('10.0.0.10',addr,graph)
        return path[1:]

    def getPathsToGo(self,addrs):
        """
        Retorna o primeiro elemento para saber se já pode enviar a mensagem ou nao
        :param addrs:
        :return:
        """
        onlineNodes = ott_manager.get_online_nodes_addr()
        onlineNodes.extend(addrs)
        logging.debug(f'online nodes {onlineNodes}')
        pathlist = paths.multicast_path_list_addOnline("10.0.0.10", addrs,onlineNodes)

        path = paths.multicast_path2(pathlist)
        logging.info("Paths to go: %s", path)
        return path[1],path

    def makeRtp(self, payload, frameNbr):
        """RTP-packetize the video data."""
        version = 2
        padding = 0
        extension = 0
        cc = 0
        marker = 0
        pt = 26  # MJPEG type
        seqnum = frameNbr
        ssrc = 0

        rtpPacket = RtpPacket()

        rtpPacket.encode(version, padding, extension, cc, seqnum, marker, pt, ssrc, payload)
        #print("Encoding RTP Packet: " + str(seqnum))

        return rtpPacket.getPacket()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(filename)s:%(funcName)s - %(message)s')
    server = Server()
    server.main()