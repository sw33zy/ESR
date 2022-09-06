import json
import logging
from os import read

import common


def read_json(jsonfile,graph):
    f= open(jsonfile, 'r')
    network_config = json.load(f)  
    for i in network_config:
        for nodelist in network_config[i].values():
            for node in nodelist:
                if i in graph:
                    graph[i].append(node)
                else:
                    graph[i] = [node]


def BFS_SP(graph, start, goal):
    explored = []
     
    # Queue for traversing the
    # graph in the BFS
    queue = [[start]]
     
    # If the desired node is
    # reached
    if start == goal:
        print("Same Node")
        return
     
    # Loop to traverse the graph
    # with the help of the queue
    while queue:
        path = queue.pop(0)
        node = path[-1]
         
        # Condition to check if the
        # current node is not visited
        if node not in explored:
            neighbours = graph[node]
             
            # Loop to iterate over the
            # neighbours of the node
            for neighbour in neighbours:
                new_path = list(path)
                new_path.append(neighbour)
                queue.append(new_path)
                 
                # Condition to check if the
                # neighbour node is the goal
                if neighbour == goal:
                    #print("Shortest path = ", *new_path)
                    return new_path
            explored.append(node)
        
    # Condition when the nodes
    # are not connected
    print(goal, " is not reachable from ", start)
    print("So sorry, but a connecting"\
                "path doesn't exist :(")
    return
     

def initGraph():
    graph = {}

    read_json(common.pathToNetworkConfig, graph)
    return graph
    

# src : string 
# dest : string 
# graph : dictionary
def shortest_path(src,dest, graph):

    list = BFS_SP(graph, src, dest)
    return list


# graph : dictionary
# nodes : List<String>
def removeNodes(graph, nodes):
    for node in nodes:

        if node in graph:
            graph.pop(node)

        for key, value in graph.items():
            if node in value:
                value.remove(node)
    

# graph : dictionary
# nodes : List<String>
def addNodes(graph, nodes):
    f = open(common.pathToNetworkConfig, 'r')
    network_config = json.load(f)
    for node in nodes:
        for i in network_config:
            if i == node:
                graph[i] = []

                for nlist in network_config[i].values():

                    for nnlist in nlist:
                        if nnlist in graph:
                            graph[i].append(nnlist)
            
            else:
                for nlist in network_config[i].values():
                    if node in nlist:
                        if i in graph:
                            if node not in graph[i]:
                                graph[i].append(node)

def addNodesn (graph , nodes):
    f = open(common.pathToNetworkConfig, 'r')
    network_config = json.load(f)
    for node in nodes:
        ncl = network_config.get(node,{}).values()
        for n in ncl:
            if n in nodes:
                graph.get(node,[]).append(n)

    print(graph)




        

#graph = initGraph()
#print(graph)
#print("------------------------------------------------------------------------")
#shortest_path("10.0.0.10","10.0.3.20", graph)
#removeNodes(graph,['10.0.3.20', '10.0.2.2', '10.0.4.20'])
#print(graph)
#print("------------------------------------------------------------------------")
#addNodes(graph,['10.0.2.2','10.0.4.20'])
#print(graph)


def multicast_path_list(src,dests):
    graph = initGraph()

    pathlist =[]
    for dest in dests:
        p = shortest_path(src,dest, graph)
        pathlist.append(p)
    pathlist=sorted(pathlist, key=len)
    return pathlist


def multicast_path_list_removeOffline(src, dests,nodes_to_remove):
    graph = initGraph()
    removeNodes(graph,nodes_to_remove)
    pathlist = []
    for dest in dests:
        p = shortest_path(src, dest, graph)
        pathlist.append(p)
    pathlist = sorted(pathlist, key=len)
    return pathlist

def multicast_path_list_addOnline(src, dests,nodes_online):
    graph = {}
    addNodes(graph,nodes_online)
    logging.info(f'graph: {graph}')
    pathlist = []
    for dest in dests:
        p = shortest_path(src, dest, graph)
        pathlist.append(p)
    logging.info("pathlist: %s", pathlist)
    pathlist = sorted(pathlist, key=len)
    return pathlist

def Extract(lst,index):
    return [item[index] for item in lst]

def subLists(lst, x):
    lists = []
    for i in lst:
        if x in i:
            lists.append(i)

    return lists

def remMerge(lst,elem):
    lst = [[i for i in nested if i != elem] for nested in lst]
    lst = [j for i in lst for j in i]
    return lst

def multicast_path2(pathlist):
    path = []
    index=0
    elems= Extract(pathlist,index)
    while elems.count(elems[0]) == len(elems):
        path.append(elems[0])
        pathlist = [[j for j in nested if j != elems[0]] for nested in pathlist]
        if pathlist[0]:
            elems = Extract(pathlist,index)
        else:
            break
    
    sub = []
    if pathlist[0]:
        for p in pathlist:
            elem = p[index]
            if any(elem in i for i in pathlist):
                lst = subLists(pathlist,elem)
                lst = remMerge(lst,elem)
                lst.insert(0,elem)
                sub.append(lst)
        res = []
        for i in sub:
            if i not in res:
                res.append(i)
        path.append(res)
    return path
    #print(path)
    
#pathlist=multicast_path_list("10.0.0.10",["10.0.4.20","10.0.3.20"])
#multicast_path2(pathlist)