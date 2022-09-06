import logging
import select
import selectors
import socket
import pickle
import string
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import testes
from dataMessage import DataMessage
from node import Node
import nodeprotocol
import json
import common
from time import sleep
from netifaces import interfaces, ifaddresses, AF_INET
from pingMessage import pingMessage
from tracker import Tracker
from goingOffline import GoingOfflineMessage

HOST = '0.0.0.0'
PORT = 7000
num_of_threads = 2


# https://github.com/eliben/python3-samples/blob/master/async/selectors-async-tcp-server.py

class Ott:

    def __init__(self, bootstrapper_info):
        self.nodes = {}
        self.node_id = {}
        self.addr = self.get_node_ip()
        self.main_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.main_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.main_socket.bind((self.addr, PORT))
        self.main_socket.listen(5)
        self.poll = select.poll()
        self.poll.register(self.main_socket.fileno(), select.POLLIN)
        self.bootstrapper = False
        self.neighbours = []
        self.toDispatch = {}
        self.id = common.generate_id(HOST, PORT)
        self.executor = ThreadPoolExecutor(num_of_threads)
        logging.info(f'Ott id: {self.id}')
        if bootstrapper_info == {}:
            self.bootstrapper = True
            self.network_config = {}
            self.load_network_config()
            self.init_bootstrapper_neighbours()
        else:
            self.connect_to_bootstrapper(bootstrapper_info)

    def get_node_ip(self):
        interf = interfaces()
        tmp = ifaddresses(interf[1]).setdefault(AF_INET, [{'addr': '0.0.0.0'}])
        return tmp[0]['addr']

    def accept_connection(self, key):
        """
        Aceita uma conexao
        :param key:
        :return:
        """
        conn, addr = self.main_socket.accept()
        self.add_node(Node(addr[0], addr[1], conn))

    def add_node(self, nodeconn):
        """
        Adiciona um nodo ao ott e trata de registar o nodo para escuta no selector
        :param nodeconn:
        :return:
        """
        status, node = self.check_node_address(nodeconn.get_addr())
        if status:
            node.received_connection(nodeconn)
        else:
            node = nodeconn
        self.nodes[node.get_id()] = node
        node.set_change_idcallback(self.node_changed_id)
        node.set_nodeofflinecallback(self.nodeIsOffline)
        self.node_id[node.get_socket().fileno()] = node.get_id()
        self.poll.register(node.get_socket().fileno(), select.POLLIN | select.POLLOUT)

    def node_changed_id(self, id, newid):
        """
        Callback para quando recebemos uma mensagem com um id para atualizarmos
        :param id: id temporario
        :param newid: id a atualizar
        :return:
        """
        node = None
        if newid in self.nodes.keys():  # No caso de um node que se conecta e ja esta na rede ja o conhecemos
            node = self.nodes[newid]  # O que nós já temos
            newconnnode = self.nodes.pop(id)  # O do node que está a tentar se conectar
            self.poll.unregister(node.get_socket().fileno())  # Tiramos do selector o nodo com a ligaçao antiga
            node.set_socket(newconnnode.get_socket())  # Atualizamos o socket do node que já temos
            node.set_addr(
                newconnnode.get_addr())  # Atualizamos o endereço no caso do endereço do nodo estar a usar uma interface diferente para se conectar
            node.set_change_idcallback(None)  # Se nao fizemos isto entravamos num loop a seguir com o node.set_id
            node.set_id(newid)  # Mudamos o id do nodo para o id que recebemos
            node.set_change_idcallback(self.node_changed_id)
            self.remove_node(newconnnode)
        else:
            node = self.nodes.pop(id)
        dispatcher_oldid = self.toDispatch.pop(id, [])
        dispatcher_newid = self.toDispatch.pop(newid, [])
        dispatcher_newid.extend(dispatcher_oldid)
        self.toDispatch[newid] = dispatcher_newid
        self.node_id[node.get_socket().fileno()] = newid
        self.nodes[newid] = node

    def connect_to_node(self, addr, port):
        """
        Faz um pedido para ligar a um nodo
        :param addr:
        :param port:
        :return:
        """
        logging.debug(f'Connecting to {addr}:{port}')
        node = Node(addr, port)
        self.add_node(node)
        return

    def remove_node(self, node):
        del self.nodes[node.get_id()]

    def get_nodes(self):
        return self.nodes.values()

    def handle_node_event(self, key, event):
        """
        Tendo em conta o status do event(se lê , escreve ou erro) passa a respetiva funçao para uma pool de threads
        :param key: descritor de ficheiro
        :param event: POLLIN | POLLOUT | POLLHUP
        :return:
        """
        # if node is not self.neighbours
        try:
            id = self.node_id.get(key, None)
            node = self.nodes.get(id, None)
            if node is None or node.get_status() == nodeprotocol.NodeStatus.OFFLINE:
                self.poll.unregister(key)
                return

            if event & select.POLLIN:
                message = node.receive()
                self.executor.submit(self.handleRead, (node, message))
            if event & select.POLLOUT:
                self.executor.submit(self.handleWrite, node)

            if event & select.POLLHUP:
                node = self.getNodeByfileno(key)
                self.poll.unregister(key)
                if node is not None:
                    node.get_socket().close()
                del self.node_id[key]
        except Exception as e:
            return

    def getNodeByfileno(self, fileno):
        """
        Recebe um descritor de ficheiro e retorna o id associado ao descritor
        :param fileno:
        :return:
        """
        nodeid = self.node_id.get(fileno, None)
        return self.nodes.get(nodeid, None)

    def nodeIsOffline(self, node):
        """
        Callback para quando um nodo fica offline
        :param node:
        :return:
        """
        if node.get_socket().fileno() != -1:
            self.poll.unregister(node.get_socket().fileno())
            self.node_id.pop(node.get_socket().fileno())
            node.close_socket()

    def handleRead(self, info):
        """
        Passa a mensagem a função correspondente ao status em que o nodo está
        :param info: tuple (node,message)
        :return:
        """
        node, message = info
        if node is None:
            return
        if message:
            # logging.debug(f'Received from {node.get_id()} : {message}')
            message = pickle.loads(message)
            status = node.get_status()
            handler = nodeprotocol.get_handler(status, True)
            if handler is None: return
            info = {'node': node, 'message': message, 'ott': self}
            handler(info)

    def get_ott_id(self):
        """
        Retorna o id do ott
        :return: str
        """
        return self.id

    def handleWrite(self, node):
        """
        Trata de escrever para o nodo tendo em conta o status em que o nodo está
        :param node:
        :return:
        """
        if node is None: return
        status = node.get_status()
        tosend = None
        handler = nodeprotocol.get_handler(status, False)
        if handler is None: return None
        info = {'node': node, 'ott': self}
        tosend = handler(info)
        if tosend:
            # logging.debug(f'Sending to {node.get_id()} : {tosend}')
            node.send(tosend)
        # return tosend

    def serve_forever(self):
        """
        Mantém o ott a funcionar ativamente, procurando por eventos no selector
        :return:
        """
        try:
            while True:
                sleep(0.01)
                events = self.poll.poll(1)
                # For each new event, dispatch to its handler
                for key, event in events:
                    self.handler(key, event)
        finally:
            self.warnImGoingOffline()
            self.poll.unregister(self.main_socket.fileno())
            self.main_socket.close()

    def warnImGoingOffline(self):
        """
        Envia um warning para todos os nodos da rede
        :return:
        """
        for node in self.nodes.values():
            if node.get_status() == nodeprotocol.NodeStatus.CONNECTED:
                go = GoingOfflineMessage(self.get_ott_id(), tracker=Tracker([self.get_ott_id(), node.get_id()],
                                                                            destination=[node.get_id()]))
                sndgo = pickle.dumps(go)
                node.send(sndgo)
                node.close()

    def handler(self, key, event):
        """
        Se o descritor do ficheiro (key) for o do main socket do ott então aceitamos a conexão , senão passamos o tipo de evento e o descritor ao handler
        :param key:
        :param event:
        :return:
        """
        if key == self.main_socket.fileno():
            self.accept_connection(key)
        else:
            self.handle_node_event(key, event)

    def connect_to_bootstrapper(self, bootstrapper_info):
        """
        Trata de iniciar a ligação ao bootstrapper
        :param bootstrapper_info:
        :return:
        """
        addr = bootstrapper_info['addr']
        port = bootstrapper_info['port']
        self.connect_to_node(addr, port)

    def get_offline_nodes_addr(self):
        """
        Retorna os nodos que estão online
        :return:
        """
        return [node.get_addr() for node in self.nodes.values() if node.get_status() == nodeprotocol.NodeStatus.OFFLINE]

    def get_online_nodes_addr(self):
        """
        Retorna os nodos que estão online
        :return:
        """
        tmp = [node.get_addr() for node in self.nodes.values() if
               node.get_status() == nodeprotocol.NodeStatus.CONNECTED or node.get_status() == nodeprotocol.NodeStatus.NOTCONNECTED]
        tmp.append(self.addr)
        return tmp

    def check_node_address(self, node_addr):
        """
            # Checks if we already have a connection with the node by his address

        :param node_addr: str
        :return: (bool,node)
        """
        for node in self.nodes.values():
            if node.get_addr() == node_addr:
                return True, node
        return False, None

    def load_network_config(self):
        """
        Lê a config da network para no futuro enviar aos peers
        :return:
        """
        with open(common.pathToNetworkConfig, 'r') as f:
            self.network_config = json.load(f)

    def check_id(self, id):
        """
        Verifica se o id existe
        :param id:
        :return:
        """
        return self.nodes.get(id) is None

    def get_network_config(self):
        return self.network_config

    def get_selector(self):
        return self.poll

    def is_bootstrapper(self):
        """
        Se o ott é o bootstrapper
        :return:
        """
        return self.bootstrapper

    def add_neighbours(self, neighbours):
        """
        Adiciona os vizinhos que recebeu do bootstrapper
        :param neighbours:
        :return:
        """
        self.neighbours.extend(neighbours)
        for node in neighbours:
            self.connect_to_node(node, 7000)

    def get_neighbours(self):
        """
        Retorna a lista de vizinhos.
        :return:
        """
        return self.neighbours

    def init_bootstrapper_neighbours(self):
        if len(self.neighbours) == 0 and self.bootstrapper:
            noderepr = self.network_config[self.addr]
            neighbors = noderepr['neighbors']
            self.add_neighbours(neighbors)

    def get_neighbours_nodesids(self):
        """
        Função usada pela inundação controlada para enviar aos nodos vizinhos
        :return: lista de ids dos nodos vizinhos
        """
        res = []
        tmp = self.get_addr_to_id()
        for neig in self.get_neighbours():
            res.append(tmp[neig])
        return res

    def add_toDispatch(self, id, message):
        """
         Adiciona ao dispatcher a entrada {id:Lista de mensagens a enviar para o nodo} sendo que o dispatcher tem um formato {id:[mensagens]}
        """
        node = self.nodes.get(id, None)
        if node is None:
            return False
        elif node.isOffline():
            node.reconnect()
            if node.isOffline():
                return False
        dispatcher = self.toDispatch.get(id, [])
        #  if dispatcher:
        #    self.poll.modify(node.get_socket().fileno(), select.POLLOUT)
        dispatcher.append(message)
        self.toDispatch[id] = dispatcher
        return True

    def set_node_offline(self, node_id):
        """
        Set o nodo offline
        :param node_id:
        :return:
        """
        node = self.nodes.get(node_id, None)
        if node is None:
            return
        node.setOffline()

    def add_toDispatchByAddr(self, addr, message):
        """
        Função que dá dispatch através do id , só quando conhecemos o nodo
        :param addr:
        :param message:
        :return:
        """
        id = self.get_addr_to_id().get(addr, None)
        if id is not None:
            self.add_toDispatch(id, message)
        else:
            logging.debug('Node not found')  ## Envia para todos?

    def get_toDispatch(self, id):
        """
        Retorna um item que o nodo[id] tenha para enviar  , não era de todo mau este dispatch retornar a lista com X itens
        :param id:
        :return: Item a dar dispatch
        """
        tmp = self.toDispatch.get(id, [])
        ret = None
        if len(tmp) > 0:
            ret = tmp.pop(0)
        # if len(tmp) == 0:
        # self.poll.modify(self.nodes.get(id).get_socket().fileno(),select.POLLIN)
        return ret

    def get_addr_to_id(self):
        """
        Gera um dicionario de {address:id}
        :return: {address:id}
        """
        addrToId = {}
        for node in self.nodes.values():
            addrToId[node.get_addr()] = node.get_id()
        if self.bootstrapper:
            addrToId[self.addr] = self.id
        return addrToId

    # Adiciona uma stream a transmitir pelo nosso path
    def send_data(self, packet, addrs, path):
        """
        Adiciona uma stream a transmitir pelo nosso path
        :param packet: packet rdp encapsulado pelo dataMessage
        :param addrs: [endereços dos destinos]
        :param path: [Caminho de endereços]
        :return:
        """
        addr_dic = self.get_addr_to_id()
        path_id = self.convertPathToId(path)
        logging.debug(f'path_id: {path_id}')
        if None not in path_id:
            ids = list(map(lambda a: addr_dic.get(a, None), addrs))
            if None not in ids:
                tracker = Tracker(path_id, destination=ids)
                datapacket = DataMessage(id, tracker, packet)
                self.add_toDispatch(tracker.get_next_channel(self.get_ott_id()), datapacket)
        else:
            logging.debug('Client not found')

    def send_ping(self, addrs, path):
        addr_dic = self.get_addr_to_id()
        path_id = self.convertPathToId(path)
        logging.debug(f'path_id: {path_id}')
        if None not in path_id:
            ids = list(map(lambda a: addr_dic.get(a, None), addrs))
            if None not in ids:
                tracker = Tracker(path_id, destination=ids)
                ping = pingMessage(self.get_ott_id(), tracker)

                self.add_toDispatch(tracker.get_next_channel(self.get_ott_id()), ping)

    def convertPathToId(self, l):
        """
        Funçao que converte o path em addr para path id
        :param l:
        :return:
        """
        tmp = []
        addr_dic = self.get_addr_to_id()
        for p in l:
            if isinstance(p, list):
                tmp.append(self.convertPathToId(p))
            else:
                tmp.append(addr_dic.get(p, p))
        return tmp

    def broadcast_message(self, addr):
        """
        Envia mensagem para um endereço sem saber o caminho(Inundação controlada)
        :param addr:
        :return:
        """
        info = {'ott': self}
        status, node = self.check_node_address(addr)
        if status:
            id = node.get_id()
            if id is not None:
                tracker = Tracker([-1], destination=id)
                datapacket = pingMessage(id, tracker)
                info['message'] = datapacket
                nodeprotocol.sendToAllNodes(info)

    def setDataCallback(self, callback):
        """
        Set do callback do cliente para ser notificado que chegou data para ele
        :param callback:
        :return:
        """
        self.dataCallback = callback

    def checkIfNodeIsNeighbour(self, node):
        """
        Verifica se o nodo é vizinho
        :param node:
        :return:
        """
        for neighbour in self.get_neighbours():
            if node.get_addr() == neighbour:
                return True
        return False


def initOtt():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(filename)s:%(funcName)s - %(message)s')
    asd = {}
    if len(sys.argv) > 1:
        hostip = sys.argv[1]
        asd = {'addr': hostip, 'port': 7000}

    ott_manager = Ott(asd)
    ott_manager.serve_forever()


if __name__ == '__main__':
    initOtt()
