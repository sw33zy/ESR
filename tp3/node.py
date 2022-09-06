import logging
import socket
from sre_constants import IN

import nodeprotocol
import common


class Node():

    def __init__(self, addr, port, sock=None, id=None):
        self.addr = addr
        self.port = port
        self.offlinecallback = None
        self.change_idcallback = None
        self.status = nodeprotocol.NodeStatus.OFFLINE
        if sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connect()
        else:
            self.status = nodeprotocol.NodeStatus.ACKRECEIVING
            self.sock = sock
        if id is None:
            self.id = common.generate_id(addr, port)
        else:
            self.id = id
        self.sock.setblocking(False)

    def get_addr(self):
        return self.addr

    def get_socket(self):
        return self.sock

    def set_nodeofflinecallback(self,callback):
        self.offlinecallback = callback

    def set_change_idcallback(self, callback):
        self.change_idcallback = callback

    def connect(self):
        try:
            logging.debug("Connecting to node: " + str(self.addr) + ":" + str(self.port))
            self.sock.connect((self.addr, self.port))
            self.set_status(nodeprotocol.NodeStatus.ACKSENDING)
        except socket.error:
            logging.debug("Could not connect to node %s:%d" % (self.addr, self.port))
            self.set_status(nodeprotocol.NodeStatus.OFFLINE)

    def disconnect(self):
        self.set_status(nodeprotocol.NodeStatus.NOTCONNECTED)
        if self.offlinecallback != None:
            self.offlinecallback(self)


    def reconnect(self):
        self.connect()

    def get_id(self):
        return self.id

    def get_status(self):
        return self.status

    def get_port(self):
        return self.port

    def set_status(self, status):
        tmp_status = self.status
        self.status = status
        if self.status == nodeprotocol.NodeStatus.OFFLINE and tmp_status != nodeprotocol.NodeStatus.OFFLINE:
            if self.offlinecallback is not None:
                self.offlinecallback(self)
                logging.info("Node %s:%d is offline" % (self.addr, self.port))
        elif self.status == nodeprotocol.NodeStatus.CONNECTED:
            logging.info("Node %s:%d is connected" % (self.addr, self.port))
        elif self.status == nodeprotocol.NodeStatus.NOTCONNECTED:
            logging.info("Node %s:%d is not connected" % (self.addr, self.port))
        logging.debug("Node %s:%d status changed to %s" % (self.addr, self.port, status))

    def set_id(self, newid):
        tmp = self.id
        self.id = newid
        self.change_idcallback(tmp, newid)

    def send(self,data):
        if self.status == nodeprotocol.NodeStatus.OFFLINE: return
        try:
            self.sock.send(data)
        except socket.error:
            self.connect()
            #self.sock.send(data)


    def receive(self):
        try:
            data = self.sock.recv(23000)
            if data:
                return data
            else:
                return None
        except socket.error:
            self.reconnect()
            return None

    def close(self):
        self.set_status(nodeprotocol.NodeStatus.OFFLINE)

    def received_connection(self, connnode):
        self.addr = connnode.get_addr()
        self.port = connnode.get_port()
        self.sock = connnode.get_socket()
        self.set_status(nodeprotocol.NodeStatus.ACKRECEIVING)


    def isOffline(self):
        return self.status == nodeprotocol.NodeStatus.OFFLINE

    def setOffline(self):
        self.set_status(nodeprotocol.NodeStatus.OFFLINE)

    def close_socket(self):
        self.sock.close()