#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
# Version : 1.0
# On import les modules nécessaires
__author__ = "Sébastien Douce <sebastien.douce@cheops.fr>"
__version__ = "1.0"


#from __future__ import print_function
#from __future__ import division
import argparse
import MySQLdb
import sys
from datetime import timedelta, datetime
from os import path
import pytz
import re
import csv
import ssl
from text_unidecode import unidecode
import datetime

try:
    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        from pyVim import connect
        from pyVmomi import vmodl
        from pyVmomi import vim
except ImportError as e:
    raise(e)

import atexit
warning_age = 7


class db():

    def __init__(self, host, user, password, base):
        dbcnx = MySQLdb.connect(host=host, user=user, passwd=password, db=base)
        self.cur = dbcnx.cursor()

    def req_glpi(self, server):
        self.cur.execute("""SELECT
                glpi_plugin_customfields_computers.vm_name,
                glpi_dropdown_plugin_customfields_cluster_icod.comments
                FROM glpi_computers 
                LEFT JOIN glpi_plugin_customfields_computers ON glpi_computers.ID = glpi_plugin_customfields_computers.id
                LEFT JOIN glpi_dropdown_plugin_customfields_cluster_icod ON glpi_plugin_customfields_computers.cluster_icod = glpi_dropdown_plugin_customfields_cluster_icod.id
                WHERE glpi_computers.name = %s
                AND glpi_computers.is_template ='0' 
                AND glpi_computers.deleted ='0'""", (server,))
        self.result = self.cur.fetchone()
        return self.result
def GetArgs():
    parser = argparse.ArgumentParser(
        description='''Ce plugin génère un audit du host supervisé.''')
    parser.add_argument("-H", "--host", action="store",
                        help="Le serveur à controller")
    parser.add_argument("-p", "--port", action="store",
                        help="Le port a controler")
    args = parser.parse_args()
    return args

#
# Classe de connexion pour  MYSQL CHEOPS
#


class perfdata():
    def metricvalue(self,item,depth):
        maxdepth=10
        if hasattr(item, 'childEntity'):
            if depth > maxdepth:
                return 0
            else:
                item = item.childEntity
                item=self.metricvalue(item,depth+1)
        return item

    def run(self,content,vihost):
        output=[]
        try:
            perf_dict = {}
            perfManager = content.perfManager
            perfList = content.perfManager.perfCounter
            for counter in perfList: #build the vcenter counters for the objects
                counter_full = "{}.{}.{}".format(counter.groupInfo.key,counter.nameInfo.key,counter.rollupType)
                perf_dict[counter_full] = counter.key
                print counter_full
            # counter_name_RX = 'net.packetsRx.summation'
            # counter_name_TX = 'net.packetsTx.summation'
            # counterId = perf_dict[counter_name_RX]
            # metricId = vim.PerformanceManager.MetricId(counterId=counterId, instance="")
            # timenow=datetime.datetime.now()
            # startTime = timenow - datetime.timedelta(minutes=10)
            # endTime = timenow
            # search_index = content.searchIndex
            # host = search_index.FindByDnsName(dnsName=vihost, vmSearch=False)
            # query = vim.PerformanceManager.QuerySpec(entity=host,metricId=[metricId],intervalId=20,startTime=startTime,endTime=endTime)
            # stats=perfManager.QueryPerf(querySpec=[query])
            # # print stats
            # count=0
            # somme=0
            # for val in stats[0].value[0].value:
            #    perfinfo={}

            #    # val=ib(val/100)
            #    print val
            #    perfinfo['timestamp']=stats[0].sampleInfo[count].timestamp
            #    perfinfo['hostname']=vihost
            #    perfinfo['value']=val
            #    output.append(perfinfo)
            #    somme+=val
            #    count+=1
            

            # print count, somme
            # test = somme/count
            # print test

            # for out in output:
            #     print "Hostname: {}  TimeStamp: {} Usage: {}".format (out['hostname'],out['timestamp'],out['value'])

    
        except vmodl.MethodFault as e:
            print("Caught vmodl fault : " + e.msg)
            return 0
        except Exception as e:
            print("Caught exception : " + str(e))
    
        return 0   
def get_obj(content, vimtype, name):
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj
def main():
    args = GetArgs()
    server = str(args.host)
    port = str(args.port)
    port=443
    # CONNEXIONS MYSQL
    dbglpi = db("infvip-my", "info_read_only", "vdAoxUzsBTJtTR", "glpi")
    glpivalue = dbglpi.req_glpi(server)
    vmname = str(glpivalue[0])    
    VCID = str(glpivalue[1])
    vCenter = str(glpivalue[1])

    PassFile = "/products/icinga/libexec/authfiles/" + str(vCenter)
    file = open(PassFile, "rb")
    try:
        reader = csv.reader(file)
        for row in reader:
            LIGNE = row[0]
            if LIGNE.startswith("CSV_ENTRY"):
                username = LIGNE.split(';')[1]
                password = LIGNE.split(';')[2]

    except:
        print "Le fichier :" + str(file) + " n'existe pas ou n'est pas rempli correctement !!"
    finally:
        file.close()
    python_test_context = "YES"

    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        context.verify_mode = ssl.CERT_NONE
    except:
        python_test_context = "NO"
    try:
        if python_test_context == "NO":
            si = connect.SmartConnect(
                host=vCenter, user=username, pwd=password, port=int(port))
        else:
            si = connect.SmartConnect(
                host=vCenter, user=username, pwd=password, port=int(port), sslContext=context)
        if not si:
            print("Could not connect to %s using "
                  "specified username and password" % username)
            return -1
        atexit.register(connect.Disconnect, si)
        # Get vCenter date and time for use as baseline when querying for
        # counter
        content = si.RetrieveContent()
        # vm = get_obj(content, [vim.VirtualMachine], vmname)
        # print vm
        perfManager = content.perfManager
        perfList = content.perfManager.perfCounter
       
        # container = content.rootFolder
        # viewType = [vim.VirtualMachine]
        # recursive = True

        # containerView = content.viewManager.CreateContainerView(container, 
        #                                                         viewType,
        #                                                         recursive)
        # #print containerView.summary

        counter_name = 'cpu.ready.summation'
        
        #children = containerView.view
        obj_VM = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)

        # Loop through all the VMs
        for child in obj_VM.view:
            #print child.name
            if child.name == str(vmname):
                vm = child.summary.vm
                nbcpu = child.summary.config.numCpu
                perf_dict = {}
                for counter in perfList:
             
                    #build the vcenter counters for the objects
                    counter_full = "{}.{}.{}".format(counter.groupInfo.key,counter.nameInfo.key,counter.rollupType)
                    
                    perf_dict[counter_full] = counter.key

                    #print counter_full
            
                counterId = perf_dict[counter_name]
               
                
                metricId = vim.PerformanceManager.MetricId(counterId=counterId, instance="")

                timenow=datetime.datetime.now()
                startTime = timenow - datetime.timedelta(minutes=5)
                endTime = timenow # + datetime.timedelta(seconds=300)
                #search_index = content.searchIndex
                query = vim.PerformanceManager.QuerySpec(entity=vm,metricId=[metricId],intervalId=20,startTime=startTime,endTime=endTime)
                stats=perfManager.QueryPerf(querySpec=[query])
                counter=0
                somme=0.0

                for val in stats[0].value[0].value:
                    val = int(val)
                    somme = somme + val
                    print somme
                    counter= counter+1
                    print "VALEUR ", val ,"SOMME " , somme , "COUNTER ",counter
                     
                # print "COUNTER ==>", counter
                average = somme/counter
                percent = somme / 3000
                percent = percent / nbcpu


                print "POURCENTAGE OBTENU :",  percent
    except vmodl.MethodFault, e:
        print "Caught vmodl fault : " + e.msg
        return -1
    # except IOError, e:
    #   print "Could not connect to %s. Connection Error" % server
    #   return -1
    return 0

if __name__ == "__main__":
    main()
