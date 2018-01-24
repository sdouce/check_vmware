#!/usr/bin/python2.7
# coding: utf-8

__author__ = "Sébastien DOUCE"
__version__ = "0.1"
import csv
import ssl
import sys

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
from optparse import OptionParser
from threading import Thread
import datetime

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
            counter_name_RX = 'net.packetsRx.summation'
            counter_name_TX = 'net.packetsTx.summation'
            counterId = perf_dict[counter_name_RX]
            metricId = vim.PerformanceManager.MetricId(counterId=counterId, instance="")
            timenow=datetime.datetime.now()
            startTime = timenow - datetime.timedelta(minutes=10)
            endTime = timenow
            search_index = content.searchIndex
            host = search_index.FindByDnsName(dnsName=vihost, vmSearch=False)
            query = vim.PerformanceManager.QuerySpec(entity=host,metricId=[metricId],intervalId=20,startTime=startTime,endTime=endTime)
            stats=perfManager.QueryPerf(querySpec=[query])
            # print stats
            count=0
            somme=0
            for val in stats[0].value[0].value:
               perfinfo={}

               # val=ib(val/100)
               print val
               perfinfo['timestamp']=stats[0].sampleInfo[count].timestamp
               perfinfo['hostname']=vihost
               perfinfo['value']=val
               output.append(perfinfo)
               somme+=val
               count+=1
            

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

def main():
    global opt
    global parser

    help_text = """
    This is a bigger help with actions separated by mode

    """
    parser = OptionParser(usage=help_text, version="%prog 1.0 beta")
    parser.add_option("-H", action="store", help="ESX Hostname/IP",
                      dest="hostname")
    parser.add_option("-P", action="store",
                      help="ESX Port (default: %default)",
                      dest="port", default=443, type=int)
    parser.add_option("-A", action="store", help="Authfile",
                      dest="authfile")
    parser.add_option("-w", action="store", help="The Warning threshold (default: %default)",
                      dest="warning", default=80, type=str)
    parser.add_option("-c", action="store", help="The Critical threshold (default: %default)",
                          dest="critical", default=90, type=str)

    (opt, args) = parser.parse_args()

    """
    Required Arguments
    """
    if (opt.hostname is None or opt.authfile is None):
        return parser.print_help()
    file = open(opt.authfile, "rb")
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    context.verify_mode = ssl.CERT_NONE

    warning = str(opt.warning).split('%')[0]
    critical = str(opt.critical).split('%')[0]
    

    try:
        reader = csv.reader(file)
        for row in reader:
            LIGNE = row[0]
            if LIGNE.startswith("CSV_ENTRY"):
                username = LIGNE.split(';')[1]
                password = LIGNE.split(';')[2]
    finally:
        file.close()

    try:
        si = connect.SmartConnect(host=opt.hostname,
                                  user=username,
                                  pwd=password,
                                  port=int(opt.port), sslContext=context)

        if not si:
            print("Could not connect to %s using "
                  "specified username and password" % opt.username)
            return -1

        atexit.register(connect.Disconnect, si)

        
        content = si.RetrieveContent()
        perf=perfdata()
        for child in content.rootFolder.childEntity:
            datacenter=child
            hostfolder= datacenter.hostFolder
            hostlist=perf.metricvalue(hostfolder,0)
            print hostfolder

        for hosts in hostlist:
            esxhosts=hosts.host

            for esx in esxhosts:
                summary=esx.summary
                esxname=summary.config.name
                p = Thread(target=perf.run, args=(content,esxname,))
                p.start()


    except vmodl.MethodFault, e:
        print "Caught vmodl fault : " + e.msg
        sys.exit(2)
        return -1
    except IOError, e:
        print "Could not connect to %s. Connection Error" % opt.hostname
        sys.exit(2)
        return -1
    return 0


if __name__ == "__main__":
    main()
