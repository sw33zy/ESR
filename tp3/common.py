import hashlib
import logging
import random
from tracker import Tracker


pathToNetworkConfig = "networkconfigotim.json"

def generate_id(addr, port):
    """Generates a unique ID for each node."""
    id = hashlib.sha512()
    t = addr + str(port) + str(random.randint(1, 99999999))
    id.update(t.encode('ascii'))
    tmp_id = id.hexdigest()
    return tmp_id


def create_tracker(info, channels):
    ott = info['ott']
    #addr_to_id = ott.get_addr_to_id()
    #path = list(map(lambda x: addr_to_id.get(x,None), channels))
    tracker = Tracker(channels)
    return tracker

"""
 # teste += 7
            # if teste%10 == 0:
            #     testelista = list(map(lambda node: (node.get_addr(),node.get_status()), self.nodes.values()))
            #    print(f'node status {testelista}')
            if self.bootstrapper and count == 0:
                msg = testes.pingTeste(info)
                addr_to_id = self.get_addr_to_id()
                channels = msg.get_tracker().get_channels()
                path = list(map(lambda x: addr_to_id.get(x, None), channels))
                if None not in path:
                    if testes.checkPathNodeConnected(path, self.nodes):
                        msg.get_tracker().set_path(path)
                        nxt = msg.get_tracker().get_next_channel()
                        # logging.debug('Dispatching ping to ' + str(nxt))
                        self.add_toDispatch(nxt, msg)
                        count += 1"""