import logging
import sys
import time
from enum import Enum
import pickle
from message import Message, MessageType
from pingMessage import pingMessage
from speersmessage import SPeersMessage
from ACKMessage import ACKMessage
from tracker import Tracker
from copy import deepcopy

# NODE que se liga ao bootstrap manda pedido ACK com id , boootstrap manda lista de vizinhos ( NODE(BOOTSTRAP)  = status(CONNECTING) , NODE(NODE) = status(ACK)
# status(CONNECTING) -> RECEIVING ACK -> SEND ACK -> status(CONNECTED) -> status(IDLE) -> status(DISCONNECTED) (BOOTSTRAP)
# SEND ACK(com id) -> RECEIVE ACK ->recebe id e lista vizinhos -> status(CONNECTED) -> status(IDLE) -> status(DISCONNECTED) (NODE)
# NODE connect to lista vizinhos (NODE)

class NodeStatus(Enum):
    ACKSENDING = 1  # Sending ACK
    ACKRECEIVING = 2  # Receiving ACK
    SPEERS = 3  # Sending Peers
    WPEERS = 4  # waiting Peers
    CONNECTED = 5  # Connected
    OFFLINE = 6  # Offline
    FACK = 7  # Final ACK
    WACK = 8  # Waiting final ACK
    NOTCONNECTED = 9  # Not Connected


def handle_RPeers(info):
    """
    Handle para o estado WPEERS , recebe os vizinhos e adiciona-os à lista de nodos do ott(inicia a ligação com eles) , mete o nodo que recebeu esta mensagem no estado FACK(FINAL ACK)
    :param info: info = {ott:ott, node:node , message:message}
    :return:
    """
    message = info['message']
    node = info['node']
    ott = info['ott']
    if message.get_type() != MessageType.SPEERS: return
    node.set_id(message.get_sender_id())
    ott.add_neighbours(message.get_neighbours())
    node.set_status(NodeStatus.FACK)


def handle_SPeers(info):
    """
    Handle para o estado SPEERS, envia os peers ao nodo ,
    se for o bootstrapper envia os nodos do ficheiro se não for não envia nada mas esta mensagem vai nos permitir confirmar o id do server ,
     o status do nodo no final fica em WACK(Waiting for ACK)
    :param info: {ott:ott, node:node}
    :return: A mensagem a enviar já serializada
    """
    node = info['node']
    ott = info['ott']
    if ott.bootstrapper:
        noderepr = ott.get_network_config()[node.get_addr()]
        neighbors = noderepr['neighbors']

        speersmessage = SPeersMessage(ott.get_ott_id(), neighbors)
    else:
        speersmessage = SPeersMessage(ott.get_ott_id(), [])
    node.set_status(NodeStatus.WACK)
    tmp = pickle.dumps(speersmessage)
    return tmp


def handle_AckReceive(info):
    """
     # RECEBE O ACK E METE O NODO EM NodeStatus.SPEERS e atualiza o id do node
    :param info: info = {'node':nodo que recebeu a mensagem , 'message': mensagem ,'ott' : ott}
    :return:
    """
    message = info['message']
    node = info['node']
    if message.get_type() != MessageType.ACK: return
    node.set_id(message.get_sender_id())
    node.set_status(NodeStatus.SPEERS)


def handle_AckSend(info):
    """
    Envia o Ack para o peer e fica a espera de receber os seus vizinhos
    :param info: info = {'node':nodo que recebeu a mensagem , 'message': mensagem ,'ott' : ott}
    :return: mensagem já serializada
    """

    ott = info['ott']
    node = info['node']
    id = ott.get_ott_id()
    message = ACKMessage(id)
    pickled = pickle.dumps(message)
    node.set_status(NodeStatus.WPEERS)
    return pickled


def sendToAllNodes(info):
    """
    Envia para todos os nodos que o ott tem como vizinhos evitando enviar para os que já receberam
    :param info: info = {'node':nodo que recebeu a mensagem , 'message': mensagem ,'ott' : ott}
    :return:
    """
    ott = info['ott']
    message = info['message']
    tracker = message.get_tracker()

    maintracker = tracker.__clone__()
    node_ids = ott.get_neighbours_nodesids()

    maintracker.add_channels_visits(node_ids)
    for node_id in node_ids:
        if tracker.alreadyPassed(node_id):
            continue
        else:
            message.set_tracker(maintracker)
            ott.add_toDispatch(node_id, message)


def handle_connectedR(info):
    """
    Trata de ler as mensagens e coloca-las no dispatcher associado ao id a enviar (id este obtido atraves do tracker)
    :param info: info = {'node':nodo que recebeu a mensagem , 'message': mensagem ,'ott' : ott}
    :return:
    """
    node = info['node']
    ott = info['ott']
    message: Message = info['message']
    tracker = message.get_tracker()
    reached_destination = tracker.reach_destination(ott.get_ott_id())
    if not reached_destination:
        tracker_nxt_channel = tracker.get_next_channel(ott.get_ott_id())
        if message.get_type() == MessageType.PING:
            logging.info(f'Received PING from {node.get_addr()} sending to {tracker_nxt_channel}')
        if tracker_nxt_channel == -1:
            sendToAllNodes(info)
        elif isinstance(tracker_nxt_channel, list):
            trackers = tracker.separateMulticast()
            for t in trackers:
                tmpmessage = deepcopy(message)
                tmpmessage.set_tracker(t)
                tmp_nxt_channel = t.get_next_channel(ott.get_ott_id())
                if not ott.add_toDispatch(tmp_nxt_channel, tmpmessage):
                    info['message'] = tmpmessage
                    sendToAllNodes(info)
        else:
            if not ott.add_toDispatch(tracker_nxt_channel, message):
                sendToAllNodes(info)


    else:
        if message.get_type() == MessageType.DATA:
            logging.debug(f'Received data from {message.get_sender_id()}')
            ott.dataCallback(message.get_rtppacket())
        elif message.get_type() == MessageType.PING:
            if (ott.bootstrapper):
                delay = message.ping()
                logging.info(f'Received ping with delay: {delay}')
            else:
                logging.info("Received ping from server with delay: " + str(message.ping()))
                tracker.send_back(message.get_sender_id())
                # logging.debug(f'Path after receiving ping from bootstrap: {tracker.get_path()}')
                nextdestination_id = tracker.get_next_channel()
                ott.add_toDispatch(nextdestination_id, message)
        elif message.get_type() == MessageType.GOINGOFFLINE:
            logging.info(f'Received going offline from {message.get_sender_id()}')
            ott.set_node_offline(message.get_sender_id())


def handle_connectedW(info):
    """
    Trata de enviar as mensagens do Dispatcher
    :param info: info = {'node':nodo que recebeu a mensagem , 'message': mensagem ,'ott' : ott}
    :return: Mensagem a enviar , serializada
    """
    node = info['node']
    ott = info['ott']
    toTransmit = ott.get_toDispatch(node.get_id())
    if toTransmit:
        logging.debug(f'Received message to transmit {toTransmit}  to {node.get_id()}')
        pickled = pickle.dumps(toTransmit)
        return pickled
    else:
        return None


def handle_AckConfirmation(info):
    """
    Confirma que ambas as partes sabem o id associado a cada
    Se for o bootstrap desliga-se de todos os nodos a seguir ao handshake, exceto se forem seus vizinhos
    :param info: info = {'node':nodo que recebeu a mensagem , 'message': mensagem ,'ott' : ott}
    :return:
    """
    node = info['node']
    ott = info['ott']
    message = info['message']
    if message.get_type() != MessageType.ACK: return
    if message.get_sender_id() == node.get_id():
        node.set_status(NodeStatus.CONNECTED)
        if ott.is_bootstrapper() and not ott.checkIfNodeIsNeighbour(node):
            node.disconnect()


def handle_AckConfirmationSend(info):
    """
    Envia a primeira parte da confirmação do Ack das duas partes
    :param info:
    :return: mensagem, ja serializada
    """
    node = info['node']
    ott = info['ott']
    id = ott.get_ott_id()
    message = ACKMessage(id)
    pickled = pickle.dumps(message)
    node.set_status(NodeStatus.CONNECTED)
    return pickled


def get_handler(status, read):
    """
    Retorna o handler tendo em conta o tipo de evento(ler ou escrever) e o status do peer
    :param status:
    :param read:
    :return:
    """
    if read:
        dic = {
            NodeStatus.WACK: handle_AckConfirmation,
            NodeStatus.ACKRECEIVING: handle_AckReceive,
            NodeStatus.WPEERS: handle_RPeers,
            NodeStatus.CONNECTED: handle_connectedR
        }
    else:
        dic = {
            NodeStatus.FACK: handle_AckConfirmationSend,
            NodeStatus.ACKSENDING: handle_AckSend,
            NodeStatus.SPEERS: handle_SPeers,
            NodeStatus.CONNECTED: handle_connectedW
        }

    tmp = dic.get(status, None)
    # logging.debug(f'handler: {tmp}')
    return tmp

