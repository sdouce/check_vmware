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
import atexit
import argparse
import getpass
import csv
# import the VSAN API python bindings
import vsanmgmtObjects
import vsanapiutils


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
    parser.add_argument('-W', '--warning', type=int, action='store', default=100, help='-W: Warning Level %')
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
        if args.verbose > 1:
            debugOut += "\nDEBUG::" + str(e)

        return nagStat

    # for detecting whether the host is VC or ESXi
    aboutInfo = si.content.about
    print aboutInfo

    if aboutInfo.apiType == 'VirtualCenter':
        majorApiVersion = aboutInfo.apiVersion.split('.')[0]
        if int(majorApiVersion) < 6:
            statMsg = "The Virtual Center with version " + \
                aboutInfo.apiVersion+" (lower than 6.0) is not supported."
            nagStat = nagUNKWN
            showStat(nagStat, statMsg)
            return nagStat

        # H Access VC side VSAN Health Service API
        vcMos = vsanapiutils.GetVsanVcMos(si._stub, context=context)
        vst = vcMos['vsan-cluster-space-report-system']

        cluster = getClusterInstance(args.clusterName, si)

        if cluster is None:
            statMsg = "Cluster "+args.clusterName\
                + " is not found for "+args.hostname+"."
            nagStat = nagUNKWN
            showStat(nagStat, statMsg)
            return nagStat

        stockage = vst.QuerySpaceUsage(cluster=cluster)
        primaryCapacityB = 0         
        QUERYSPACEUSAGEDETAILBYOBJECT =  stockage.spaceDetail.spaceUsageByObjectType

        for ITEM in QUERYSPACEUSAGEDETAILBYOBJECT:
            if ITEM.objType == "vmswap" or ITEM.objType == "namespace" or ITEM.objType == "other":
                primaryCapacityB = primaryCapacityB + ITEM.primaryCapacityB

        TotalCap = stockage.totalCapacityB
        provisionCapacityB = int((stockage.spaceOverview.provisionCapacityB/2) + primaryCapacityB )


        Sla_Cap = (float(SLACAP) * float(TotalCap))/100
        AllocVsSLA = round(float(100*float(provisionCapacityB)/float(Sla_Cap)),2)

        status_output = " VM Storage Allocation has reached " + str(AllocVsSLA) + "% SLA Capacity "
        perfdata_output = "| Alloc_pct_SLA=" + str(AllocVsSLA)+"%;"+str(WARNING)+";"+str(WARNING)+";0;1000 Alloc=" + str(provisionCapacityB)+"o;0;0;0;"+str(TotalCap) +" Alloc_SLA=" + str(provisionCapacityB)+"o;0;0;0;"+str(int(Sla_Cap))
 

        if AllocVsSLA >= WARNING:
            print "WARNING :" + str(status_output) + str(perfdata_output)
            sys.exit(1)
        else:
            print "OK :" + str(status_output) + str(perfdata_output)
            sys.exit(0)


# Start program
if __name__ == "__main__":
    exit(main())
