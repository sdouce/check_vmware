#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
__author__ = "Sébastien DOUCE"
__version__ = "0.1"
import csv
import re
import ssl
import sys
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
from optparse import OptionParser


def main():
    global opt
    global parser

    help_text = """
    This is a bigger help with actions separated by mode

    """
    parser = OptionParser(usage=help_text, version="%prog 1.0 beta")
    parser.add_option("-H", action="store", help="vCenter Hostname/IP",
                      dest="hostname")
    parser.add_option("-P", action="store", help="vCenter Port (default: %default)",
                      dest="port", default=443, type=int)
    parser.add_option("-A", action="store", help="Authfile", dest="authfile")
    parser.add_option("-c", action="store", help="see usage text", dest="name")
    parser.add_option("-W", action="store", help="The Warning threshold (default: %default)",
                      dest="warning", default=90, type=int)
    parser.add_option("-C", action="store", help="The Critical threshold (default: %default)",
                      dest="critical", default=95, type=int)
    parser.add_option("-T", action="store", help="Choice STD/HYB/DRP  (default: %default)",
                      dest="type", default="STD", type=str)

    (opt, args) = parser.parse_args()

    """
    Required Arguments
    """
    if (opt.hostname is None or opt.authfile is None or opt.name is None):
        return parser.print_help()
    file = open(opt.authfile,"rb")
    ''' Context DEFINITION for Python2.7.9'''
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    context.verify_mode = ssl.CERT_NONE

    try:
        reader = csv.reader(file)
        for row in reader:
            LIGNE=row[0]
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
        #print content 
        obj_clu = content.viewManager.CreateContainerView(content.rootFolder,[vim.ClusterComputeResource],True)
        obj_vm = content.viewManager.CreateContainerView(content.rootFolder,[vim.VirtualMachine],True)
        obj_host = content.viewManager.CreateContainerView(content.rootFolder,[vim.HostSystem],True)


        vm_list = obj_vm.view
        cluster_list = obj_clu.view
        host_list = obj_host.view
        #print vm_list
        cluster_type = opt.name[:-2] # On enlève les deux derniers digit du nom du cluster pour identifier DRP ou STD 


        for cluster in cluster_list:


            if cluster.name == opt.name:
                totalMemory = int(cluster.summary.totalMemory)
                numHosts= cluster.summary.numHosts

                if cluster_type.endswith("STD"):
                    total_sla_memory =  ((numHosts-1) * totalMemory)/numHosts
                    #print  opt.name, totalMemory, numHosts, total_sla_memory
                elif cluster_type.endswith("DRP"):
                    total_sla_memory =  int(totalMemory) /  2
                elif cluster_type.endswith("HYB"):
                    Percent_mem_failover = int(cluster.configuration.dasConfig.admissionControlPolicy.memoryFailoverResourcesPercent)
                    total_sla_memory =  int(totalMemory*(100-Percent_mem_failover)) / 100   
                else:
                    if opt.type =="STD":
                        total_sla_memory =  ((numHosts-1) * totalMemory)/numHosts
                    elif opt.type =="DRP":
                        total_sla_memory =  int(totalMemory) /  2
                    elif opt.type == "HYB":
                        Percent_mem_failover = int(cluster.configuration.dasConfig.admissionControlPolicy.memoryFailoverResourcesPercent)
                        total_sla_memory =  int(totalMemory*(100-Percent_mem_failover)) / 100   
                                           
                esx_list =()
                    

                for esx in cluster.host:
                    esx_list += (esx,)
                

        tot_mem  = 0
        for vm in vm_list:

           
            if vm.summary.runtime.host in esx_list:
               
                memoryMB = vm.config.hardware.memoryMB*1024*1024

                powerState = vm.runtime.powerState

                
                if powerState == "poweredOn":
                    tot_mem = float(tot_mem) + float(memoryMB)



        Percent_Sla_MEM = round(float(tot_mem/total_sla_memory)*100,2)
        #print total_sla_memory


        Output_status = str(Percent_Sla_MEM) +" %  memory allocated to VMs on cluster’s SLA perimeter " \
        + str(opt.name)+" Mem allocation="+str(total_sla_memory) 
        Output_perfdata = "|ratio="+str(Percent_Sla_MEM)+";"+str(opt.warning)+";"+str(opt.critical)+";0;200 " \
        +"mem_use="+str(int(tot_mem))+";;;;"+str(int(total_sla_memory)) 
        #print Output_status , Output_perfdata
        

        if opt.warning > opt.critical:
            print "UNKNOWN ==> Warning level should not be higher than Critical"
            sys.exit(3)
        if Percent_Sla_MEM >= opt.critical:
            #print "CRITICAL : "+str(Percent_Sla_MEM) +" %  memory allocated to VMs on cluster’s SLA perimeter "+ str(opt.name)+" Mem allocation="+str(total_sla_memory) + " (SLA Max ratio=95)| ratio="+str(Percent_Sla_MEM)+"; 90;95;0;200 "
            print "CRITICAL : "+str(Output_status) + str(Output_perfdata)
            sys.exit(2)   
        elif Percent_Sla_MEM >= opt.warning :
            #print "WARNING : "+str(Percent_Sla_MEM) +" %  memory allocated to VMs on cluster’s SLA perimeter "+ str(opt.name)+" Mem allocation="+str(total_sla_memory) + " (SLA Max ratio=95)| ratio="+str(Percent_Sla_MEM)+"; 90;95;0;200 "
            print "WARNING : "+str(Output_status) + str(Output_perfdata)
            sys.exit(1)
        else:
            #print "OK : "+str(Percent_Sla_MEM) +" %  memory allocated to VMs on cluster’s SLA perimeter "+ str(opt.name)+" Mem allocation="+str(total_sla_memory) + " (SLA Max ratio=95)| ratio="+str(Percent_Sla_MEM)+";90;95;0;200 "
            print "OK : "+str(Output_status) + str(Output_perfdata)
            sys.exit(0)      

    except vmodl.MethodFault, e:
        print "Caught vmodl fault : " + e.msg
        sys.exit(3)
        return -1
    except IOError, e:
        print "Could not connect to %s. Connection Error" % opt.hostname
        sys.exit(3)
        return -1
    return 0


if __name__ == "__main__":
    main()
 
