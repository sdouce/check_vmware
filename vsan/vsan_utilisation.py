#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
 
"""
Nagios Style plugin to check the VSAN Utilisation of a vsan cluster.
Based on VMware Python API sample code.
"""
 
__author__ = 'sdouce@gmail.com'
 
''' VSAN_UTILISATION'''
from pyVim.connect import SmartConnect, Disconnect
import sys
import ssl
import csv
import atexit
import argparse
import getpass
# import the VSAN API python bindings
import vsanmgmtObjects
import vsanapiutils
 
 
def GetArgs():
    """
    Supports the command-line arguments listed below.
    """
    parser = argparse.ArgumentParser(description='Process args for VSAN SDK sample application')
    parser.add_argument('-H', '--hostname', required=True, action='store', help='Remote host to connect to')
    parser.add_argument('-o', '--port', type=int, default=443, action='store', help='Port to connect on')
    parser.add_argument('-A', '--authfile', required=True, action='store', help='Authentification File')
    parser.add_argument('-c', dest='clusterName', metavar="CLUSTER",default='-c: VMWARE ClusterName')
    parser.add_argument('-W', '--warning', type=int, action='store', default=90, help='-W: Warning Level %')    
    parser.add_argument('-C', '--critical', type=int, action='store', default=100, help='-C: Critical Level %')    
    parser.add_argument('-S', '--slacap', type=int, action='store', default=35, help='-C: Critical Level %')    
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
 
 
# Start program
def main():
 
    args = GetArgs()
    WARNING = args.warning
    CRITICAL = args.critical
    SLACAP = args.slacap
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
        sys.exit(3)
 
    # for detecting whether the host is VC or ESXi
    aboutInfo = si.content.about
 
    if aboutInfo.apiType == 'VirtualCenter':
        majorApiVersion = aboutInfo.apiVersion.split('.')[0]
        if int(majorApiVersion) < 6:
            statMsg = "The Virtual Center with version " + \
                aboutInfo.apiVersion+" (lower than 6.0) is not supported."
            print statMsg
            sys.exit(3)            
 
 
        # H Access VC side VSAN space report Service API
        vcMos = vsanapiutils.GetVsanVcMos(si._stub, context=context)
        vst = vcMos['vsan-cluster-space-report-system']
 
        cluster = getClusterInstance(args.clusterName, si)
 
        if cluster is None:
            statMsg = "Cluster "+args.clusterName+" is not found for "+args.hostname+"."
            print statMsg
            sys.exit(3)
 
        stockage = vst.QuerySpaceUsage(cluster=cluster)
        primaryCapacityB = stockage.spaceOverview.primaryCapacityB 
        TotalCap = stockage.totalCapacityB
        freeCapacityB = stockage.freeCapacityB
       
        

        '''Boucle récuperation des  '''
        QUERYSPACEUSAGEDETAILBYOBJECT =  stockage.spaceDetail.spaceUsageByObjectType

        for ITEM in QUERYSPACEUSAGEDETAILBYOBJECT:
            if ITEM.objType == "vmswap" or ITEM.objType == "namespace" or ITEM.objType == "other":
                primaryCapacityB = primaryCapacityB + ITEM.primaryCapacityB
        
        
        if WARNING > CRITICAL:
          print "UNKNOWN ==> Warning level should not be higher than Critical"
          sys.exit(3)  
 

        Used_vs_TotalCAP = round(float(100*float(primaryCapacityB)/float(TotalCap)),2)
        Sla_Cap = (float(SLACAP) * float(TotalCap))/100
        UsedVsSla = round(float(100*float(primaryCapacityB)/float(Sla_Cap)),2)
        warnsla= int((Sla_Cap*WARNING)/100)

        status_output = "Datastore Usage has reached " + str(UsedVsSla) + "% SLA Capacity (" + str(Used_vs_TotalCAP)+"% of Total Datastore Capacity)"
        perfdata_output = "| Used_pct_SLA=" + str(UsedVsSla)+"%;"+str(WARNING)+";"+str(CRITICAL)+";0;150 Usage="+str(primaryCapacityB)+"o;0;0;0;"+str(TotalCap) +" Usage_SLA="+str(primaryCapacityB)+"o;"+str(warnsla)+";0;0;"+str(int(Sla_Cap))
 
        if UsedVsSla >= CRITICAL:
          print "CRITICAL : " + str(status_output) + str(perfdata_output)
          sys.exit(2)
        elif UsedVsSla >= WARNING:
          print "WARNING : " + str(status_output) + str(perfdata_output)
          sys.exit(1)
        else:
          print "OK : " + str(status_output) + str(perfdata_output)
          sys.exit(0)
 
# Start program
if __name__ == "__main__":
    exit(main())

 