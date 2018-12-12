# -*- coding: utf-8 -*-
"""
===============================================
netmaker python package v0.1
python 3.5
_______________________________________________
NML2JSON()
dict_net = nml2json(netmlFile, configFile=None, writeJson=None)

Features:
- Returns a python dictionary from a NetML file
- Optionally save python dictionary as a json file.
- If NetML file contains errors, the function will print error information to console and continue checking rest of file for errors. No object is return if source nodes are erronerous. Missing target nodes for edges are printed to console and discarded.
- Referenced nodes can be declared both before and after being referenced.

Parameters:
- netmlFile: A NetML file with network information. Can be any text format: txt/md/nml.
- configFile: An optional YAML file to convert abbreviations to full words. See provided template config file. E.g. 'tw' property can be converted to 'twitter_handle'.
- writeJson: False/True
_______________________________________________
JSON2CSV()
df_nodes, df_edges = json2csv(dictObj, csvNodes=None, csvEdges=None, configFile=None):
    
Features:
- Returns two dataframes (nodes, edges) from a python dictionary.
- Optionally save nodes and edges as csv files
- The csv files are configured for Graph Commons import configuration. It entails that edge source and target are stated as the label of node and not and id.

Parameters:
- dictObj: A python dictionary with nodes and edges data.
- configFile: An optional YAML file to enhance data columnwise. E.g. '@maxmunnecke' in twitter handle column may be converted to 'https://twitter.com/maxmunnecke'.   
- csvNodes: Optionally write node data to csv file.    
- csvEdges: Optionally write edge data to csv file.
_______________________________________
EXAMPLES

from netmaker import *

dict_net = nml2json('sample_netml.txt','config_netml.yaml','sample.json')    
df_nodes, df_edges = json2csv(dict_net,'sample_nodes.csv','sample_edges.csv','config_enrich.yaml')

# ... or without any enrichment:

df_nodes, df_edges = json2csv(dict_net,'sample_nodes.csv','sample_edges.csv')

# ... if dict_net is not in memory but saved as a json file, it can be loaded with:

with open('sample.json', 'r') as f:
    dict_net = json.load(f)
_______________________________________
DEV NOTES

Tested with 'mixer/py35' (not tested on any other versions)

Problem: Json is a graph model where elements do not necessarily have the same properties. In a spreadsheet all elements needs a value for all properties.
Solution: 
    1) Make a dictionary for each element and make a dataframe from all those dictionaries. The Pandas will automatically fill in missing values.
    2) Rename columns as needed.
    3) Rearrange (reindex) dataframe columns. Any unknown column names will be add as empty (Useful for 'Reference' column).
==============================================="""  

import yaml
import re
import json
import pandas as pd


# Process configuration file
def nml2json(netmlFile,configFile= None, writeJson = None):
    try:
        with open(configFile, "r") as f:
            look = yaml.load(f)
    except:
        print("No config file")
        look = {}
    look['meta'] = {'m1':'name','m2':'label','m3':'uid','m4':'text'}
    # A function that looks in a dictionary for a key:value. If not found key is returned.
    def lookup(obj,key):
        try:
            return look[obj][key]
        except:
            print("Key not found >> " + key + " not found in " + obj + " : " + line)
            return(key)
    # Process NetML file
    record = {"nodes":[],"edges":[]} # Container for processed information
    linkTopic = []
    linkSection = []
    processing = True
    with open(netmlFile) as fp:           
        for line in fp:
            line = line.strip()
            # Part 1: Initial check of the type of line and eventually add mandatory links
            head = line[:3]
            if not processing:
                # ]++ = start processing and set topic link
                if head == "]++":
                    processing = True
            else:
                # <empty> = remove section link skip
                if len(line.strip())==0:
                    linkTopic = []
                    linkSection = []
                elif head[:2] == "//":
                    continue
                elif head[:2] == "##":
                    # >>> = add section link
                    linkTopic =[]
                    try:
                        links = line[3:].split()
                        if links:
                            for link in links:
                                pair = [x.strip() for x in link.split(":")]
                                if len(head.strip()) < 3: # assuming that '##' will be followed by a space. 
                                    linkTopic.append({'relType':lookup('links',pair[0]),"target":pair[1]})
                                else:
                                    linkSection.append({'relType':lookup('links',pair[0]),"target":pair[1]})
                    except:
                        continue   
                #) ++] = stop processng, remove linkTopic
                elif head == "[--": 
                    processing = False
                    linkTopic = []
                    linkSection = []
                else:
                    # Part 2: If none of above then process the line   
                    tmpObj = {}
                    blocks = line.split("|")
                    # Prevent havock when '|' occurs in text                
                    if (len(blocks)>3):
                        blocks =["|".join(blocks[0:-2])]+ blocks[-2:]  
                    # Meta
                    try:
                        bItems = blocks[0].split(";",2)
                        typeID = re.split('([^a-z].*)', bItems[1].strip(),1)
                        tmpObj[lookup('meta','m2')] = lookup('types',typeID[0])
                        # Make unique id if only one letter type is given
                        if (len(typeID)<2):
                            tmp = re.sub(r'[^a-zA-Z0-9]+','', bItems[0].strip())
                            bItems[1]= bItems[1].strip()+tmp[:3]+tmp[-3:]+str(len(line))
                        sUid = bItems[1].strip() # Needed also for links
                        tmpObj[lookup('meta','m3')]= sUid # this is first in order to stop process if there is not two items in list.
                        tmpObj[lookup('meta','m1')]=bItems[0].strip()
                        if (len(bItems)>2):
                            tmpObj[lookup('meta','m4')]=bItems[2].strip()
                    except:
                        print("Error during node creation >> " + str(line))
                        continue
                    # Properties
                    try:
                        props = re.sub(r" *([:]) *", '\g<1>', blocks[1]).split()
                        if props:
                            for prop in props:
                                pair = prop.split(":",1)
                                if (len(pair)==2 and pair[0] and pair[1]):
                                    tmpObj[lookup('props',pair[0])] = pair[1]
                                else:
                                    print("Property error >> " + line)
                    except:
                        pass
                    # Links
                    try:    
                        links = re.sub(r' *([:]) *','\g<1>', blocks[2]).split()
                        if links:
                            for link in links:
                                pair = link.split(":",1)
                                if (len(pair)==2 and pair[0] and pair[1]):
                                    record["edges"].append({"source":sUid, 'relType':lookup('links',pair[0]),"target":pair[1]})
                                else:
                                    print("Link error >> " + line)
                    except:
                        pass     
                    record["nodes"].append(tmpObj)
                    tmpObj = {}
                    # Part 3: Finally we will add the mandatory links in linkTopic and linkSection that was created in Part 1
                    if linkTopic:
                        for link in linkTopic:
                            # Exclude the topic linking to itself when it is defined below its reference!!!!
                            record["edges"].append(dict(link, **{"source":sUid}))
                    if linkSection:
                        for link in linkSection:
                            record["edges"].append(dict(link, **{"source":sUid}))
    # Check nodes and relations
    lookEdge = {n[lookup('meta','m3')]:{'label':n[lookup('meta','m2')],'name':n[lookup('meta', 'm1')]} for n in record['nodes']}
    #lookEdge = {n['uid']:{'label':n['label'],'name':n['name']} for n in record['nodes']}
    ### Print report of edge data health
    allgood = True
    tmpList = []
    for i,e in enumerate(record['edges']):
        try:
            x={'FromType':lookEdge[e['source']]['label'],'FromName':lookEdge[e['source']]['name'], 'Edge':e['relType'], 'ToType':lookEdge[e['target']]['label'],'ToName':lookEdge[e['target']]['name']}
            tmpList.append(e)
        except:
            allgood = False
            print("Target missing! Edge: " + e['source'] +" >> " +  e['target'] )
            pass
    if not allgood:
        record['edges'] = tmpList
        print("Not all edges could be created because of missing targets" )        
    if writeJson:
        # Print json to file
        with open(writeJson, 'w') as outfile:
            json.dump(record, outfile, sort_keys=True, indent=4)
    return record

def json2csv(net, csvNodes=None, csvEdges=None,configFile=None):
    try:
        with open(configFile, "r") as f:
            look = yaml.load(f)
    except:
        print("No config file")
        
    def lookup(obj,key):
        try:
            return look[obj][key]
        except:
            return('')
    ### Create dataframe from dictionary, rename/rearrange and write
    node_dict = { i:{k:lookup('prop-prefix',k)+v for k,v in n.items()}  for i, n in enumerate(net['nodes'])}
    df_node = pd.DataFrame.from_dict(node_dict, orient = 'index')
    df_node = df_node.rename(columns={"label": "type", 'text':'description'})
    ### Create new columns
    df_node['image'] = [lookup('type-image',x) for x in df_node['type']]
    ### Reorder and enforce new columns and write
    graphcommon = ['type', 'name', 'description', 'image', 'reference', 'uid']
    column_headers = graphcommon + [x for x in df_node.columns.tolist() if x not in graphcommon]
    df_node = df_node.reindex(columns = column_headers)
    ## Edge Export
    lookEdge = {n['uid']:{'label':n['label'],'name':n['name']} for n in net['nodes']}
    ### Print report of edge data health
    edge_dict = {('row'+str(i)):{'FromType':lookEdge[e['source']]['label'],'FromName':lookEdge[e['source']]['name'], 'Edge':e['relType'], 'ToType':lookEdge[e['target']]['label'],'ToName':lookEdge[e['target']]['name']} for i,e in enumerate(net['edges'])}    
    df_edge = pd.DataFrame.from_dict(edge_dict, orient = 'index')
    df_edge = df_edge.reindex(columns = ['FromType', 'FromName', 'Edge', 'ToType', 'ToName'])
    if csvNodes:
        df_node.to_csv(csvNodes, header=True, index=None, mode='w', sep=',', encoding='utf-8') # Graphcommons require UTF-8 encoding. It should be default for "to_csv" but default is producing an import error.
    if csvEdges:
        df_edge.to_csv(csvEdges, header=True, index=None, mode='w', sep=',', encoding='utf-8') 
    return df_node,df_edge
