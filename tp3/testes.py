# envia ping
import json
import logging
import pickle

import common
import nodeprotocol
import paths
from common import create_tracker
from pingMessage import pingMessage
from tracker import Tracker


def pingTeste(info):
    ott = info['ott']
    tracker = create_tracker(info, ['10.0.0.1', '10.0.1.2'])
    message = pingMessage(ott.get_ott_id(), tracker=tracker)
    return message


def checkPathNodeConnected(path, nodedic):
    for p in path:
        tmp = nodedic.get(p, None)
        if tmp is None:
            return False
        else:
            if tmp.get_status() != nodeprotocol.NodeStatus.CONNECTED:
                return False
    return True


def trackerteste():
    pathlist = paths.multicast_path_list("10.0.0.10", ["10.0.3.20", "10.0.4.20"])
    path = paths.multicast_path2(pathlist)
    tracker = Tracker(path)
    trackers = []
    tracker.get_next_channel("sad")
    tracker.get_next_channel("asdasd")
    tmp = tracker.get_next_channel("asd")
    multicastsd = dropMulticastPath(path, tmp)
    if isinstance(tmp, list):
        for l in tmp:
            pathToTracker = multicastsd + l
            nt = Tracker(pathToTracker)
            trackers.append(nt)
    else:
       print(path)

    return trackers

def separateMulticast(s):
        tmp_jump_counts = 0
        trackers = []
        channel = s.get_path()[-1]
        if isinstance(channel, list):
            alreadyvisited = dropMulticastPath(s.get_path(), channel)
            dst = 0
            for l in channel:
                pathToTracker = alreadyvisited + l
                nt = s.__clone__()
                nt.set_destination([s.destination[dst]])
                nt.set_path(pathToTracker)
                trackers.append(nt)
                dst += 1
        else:
            tmp_jump_counts += 1

        return trackers


def dropMulticastPath(path, drop_list):
    lsts = list(path)
    lsts.remove(drop_list)
    return lsts


def convertPathToId(l):
    tmp = []
    addr_dic = {"10.0.0.10" : "0000" , "10.0.0.1" : "1111" , "10.0.1.2" : "2222", "10.0.3.20":"33333", "10.0.2.2" : "44444" , "10.0.4.20" : "55555"}
    for p in l:
        if isinstance(p, list):
            tmp.append(convertPathToId(p))
        else:
            tmp.append(addr_dic[p])

    return tmp

def multicast_path_list_tmp(src, dests,nodes_online):
    graph = {}
    addNodesn(graph,nodes_online)
    logging.info(f'graph: {graph}')
    pathlist = []
    for dest in dests:
        p = paths.shortest_path(src, dest, graph)
        pathlist.append(p)
    logging.info("pathlist: %s", pathlist)
    pathlist = sorted(pathlist, key=len)
    return pathlist

def addNodesn (graph , nodes):
    f = open(common.pathToNetworkConfig, 'r')
    network_config = json.load(f)
    for node in nodes:
        graph[node] = []
        ncl = network_config.get(node,{})['neighbors']
        for n in ncl:
            if n in nodes:
                tmp = graph.get(node)
                tmp.append(n)
                tmp2 = graph.get(n,[])
                if node not in tmp2:
                    tmp2.append(node)
                    graph[n] = tmp2
                graph[node] = tmp

    print(graph)

if __name__ == '__main__':
    addNodesn({},['10.0.0.10','10.0.0.1','10.0.5.2', '10.0.12.2','10.0.10.2'])
    #pathlist = multicast_path_list_tmp("10.0.0.10", ["10.0.3.20"],['10.0.0.10','10.0.0.1','10.0.5.2', '10.0.12.2','10.0.10.2'])
    #path = paths.multicast_path2(pathlist)
    #print(path)
    #tmp = convertPathToId(path)
    #print(tmp)
   # track = Tracker(tmp, destination=['3','5'])
    #tracker_nxt_channel = track.get_next_channel('0')
    #trackers = separateMulticast(track)
   # for t in trackers:
    #   print(t.get_path())
     #  print(t.get_next_channel('0'))
