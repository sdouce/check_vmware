#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

"""
Nagios Style plugin to check the VSAN Utilisation of a vsan cluster.
Based on VMware Python API sample code.
"""

__author__ = 'sdouce@gmail.com'

''' VSAN_UTILISATION'''
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import json
import sys
import ssl
import atexit
import argparse
import getpass
import csv
# import VSAN API bidings
import vsanmgmtObjects
import vsanapiutils
from operator import itemgetter, attrgetter
nagOK=0
nagWARN=1
nagCRIT=2
nagUNKWN=3

def GetArgs():
    """
    Supports the command-line arguments listed below.
    """
    parser = argparse.ArgumentParser(
        description='Process args for VSAN SDK sample application')
    parser.add_argument('-H', '--hostname', required=True,
                        action='store', help='Remote host to connect to')
    parser.add_argument('-o', '--port', type=int, default=443,
                        action='store', help='Port to connect on')
    parser.add_argument('-A', '--authfile', required=False,
                        action='store',
                        help='Password to use when connecting to host')
    parser.add_argument('-c', '--cluster', dest='clusterName', metavar="CLUSTER", default='VSAN-Cluster')
    parser.add_argument('-C', '--group', dest='group', metavar="CLASS", default='VSAN-Cluster')
    listgroup=("Network" ,"Physical disk " ,"Data " ,"Stretched cluster" ,"Limits " ,"Hardware compatibility " ,"Performance service " ,"vSAN Build Recommendation " ,"Online health skipped")

    parser.add_argument('-O', '--object', dest='object', metavar="OBJECT", default='VSAN-Cluster')
    parser.add_argument('-v', '--verbose', action='count', default=1,help='-v: verbose output, -vv: debug output')    
    args = parser.parse_args()
    return args



def getClusterInstance(clusterName, serviceInstance):
    content = serviceInstance.RetrieveContent()
    searchIndex = content.searchIndex
    datacenters = content.rootFolder.childEntity
    for datacenter in datacenters:
        cluster = searchIndex.FindChild(datacenter.hostFolder, clusterName)
        if cluster is not None:
            return cluster
    return None

def CollectMultiple(content, objects, parameters, handleNotFound=True):
    if len(objects) == 0:
        return {}
    result = None
    pc = content.propertyCollector
    propSet = [vim.PropertySpec(
        type=objects[0].__class__,
        pathSet=parameters
    )]

    while result == None and len(objects) > 0:
        try:
            objectSet = []
            for obj in objects:
                objectSet.append(vim.ObjectSpec(obj=obj))
            specSet = [vim.PropertyFilterSpec(objectSet=objectSet, propSet=propSet)]
            result = pc.RetrieveProperties(specSet=specSet)
        except vim.ManagedObjectNotFound as ex:
            objects.remove(ex.obj)
            result = None

    out = {}
    for x in result:
        out[x.obj] ={}
        for y in x.propSet:
            out[x.obj][y.name] = y.val
    return out
# Start program

def showStat( stat, msg, extended ):
    if stat == nagOK:
        print"OK: " + msg
        print str(extended)
    elif stat == nagWARN:
        print"Warning: " + msg
        print str(extended)
    elif stat == nagCRIT:
        print"Critical: " + msg
        print str(extended)
    else:
        print"Unknown: " + msg
        print str(extended)


def main():
    args = GetArgs()
    group=args.group
    obj=args.object


    nagStat = nagOK
    statMsg = ""
    numHealthyObjs = 0
    debugOut = ""
    
    WARNING = ""

    file = open(args.authfile, "rb")
    try:
        reader = csv.reader(file)
        for row in reader:
            LIGNE = row[0]
            if LIGNE.startswith("CSV_ENTRY"):
                username = LIGNE.split(';')[1]
                password = LIGNE.split(';')[2]
    finally:
        file.close()

    context = None
    if sys.version_info[:3] > (2, 7, 8):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    try:
        si = SmartConnect(host=args.hostname,
                          user=username,
                          pwd=password,
                          port=int(args.port),
                          sslContext=context)
        atexit.register(Disconnect, si)
    except Exception, e:
        statMsg = "Connection failure."
        if args.verbose > 1:
            debugOut += "\nDEBUG::" + str(e)
            nagStat = nagUNKWN
            showStat(nagStat,statMsg+debugOut)
        return nagStat


   #for detecting whether the host is VC or ESXi
    aboutInfo = si.content.about
       
    if aboutInfo.apiType == 'VirtualCenter':
        majorApiVersion = aboutInfo.apiVersion.split('.')[0]
        if int(majorApiVersion) < 6:
            statMsg = "The Virtual Center with version "+aboutInfo.apiVersion+" (lower than 6.0) is not supported."
            nagStat = nagUNKWN
            showStat(nagStat,statMsg)
            return nagStat
        #H Access VC side VSAN Health Service API
        vcMos = vsanapiutils.GetVsanVcMos(si._stub, context=context)
        # Get vsan health system
        vhs = vcMos['vsan-cluster-health-system']
        for i in vcMos:
            print i

        cluster = getClusterInstance(args.clusterName, si)

        if cluster is None:
            statMsg = "Cluster "+args.clusterName+" is not found for "+args.host+"."
            nagStat = nagUNKWN
            showStat(nagStat,statMsg)
            return nagStat
       
             # We need to fetch results from cache otherwise the checks timeout.
                   
        healthSummary = vhs.QueryClusterHealthSummary(cluster=cluster, includeObjUuids=True, fetchFromCache=True )

        #print healthSummary.groups
        if group == "Disk":
            group =="Physical disk"
        elif  group == "Stretched":
            group ="Stretched cluster"
        elif  group == "hw_compatibility":
            group="Hardware compatibility" 
        elif  group == "Perfs":
            group="Performance service"
        elif  group == "vSAN_Build_Recommendation":
           group = "vSAN Build Recommendation"
        elif  group == "Online_health ":
            group = "Online health"
      
        for grp in healthSummary.groups:
            groupname = grp.groupName
            grouptest=grp.groupTests
            if groupname == "Cluster":
                for test in grouptest:
                 
                    if test.testName == obj:
                        print "     ",test.testName, test.testHealth
                        status=test.testHealth
                        extended=test.testDescription
                        if str(status) =="green":
                            nagStat=nagOK


       
        # statMsg += " Healthy: " + str(numHealthyObjs)
        showStat(nagStat, status, extended)

       
        # return nagStat



# Start program
if __name__ == "__main__":
    main()