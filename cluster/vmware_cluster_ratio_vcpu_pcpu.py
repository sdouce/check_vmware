#!/usr/bin/python2.7
# coding: utf-8

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
    parser.add_option("-P", action="store",
                      help="vCenter Port (default: %default)",
                      dest="port", default=443, type=int)
    parser.add_option("-A", action="store", help="Authfile",
                      dest="authfile")
    parser.add_option("-c", action="store", help="see usage text",
                      dest="name")
    parser.add_option("-W", action="store", help="The Warning threshold (default: %default)",
                      dest="warning", default=4.5, type=float)
    parser.add_option("-C", action="store", help="The Critical threshold (default: %default)",
                      dest="critical", default=5, type=float)
    parser.add_option("-T", action="store", help="STD/DRP/HYB (default: %default)",
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
                #print cluster.summary
                numCpuCores = cluster.summary.numCpuCores
                numHosts= cluster.summary.numHosts

                if cluster_type.endswith("STD"):
                    nbrphyscpucoressla =  ((numHosts-1) * numCpuCores)/numHosts
                elif cluster_type.endswith("DRP"):
                    nbrphyscpucoressla =  int(numCpuCores) /  2
                elif cluster_type.endswith("HYB"):
                    Percent_cpu_failover = int(cluster.configuration.dasConfig.admissionControlPolicy.cpuFailoverResourcesPercent)
                    nbrphyscpucoressla =  float(numCpuCores*(100-Percent_cpu_failover))/100
                else:
                    if opt.type == "STD":
                        nbrphyscpucoressla =  ((numHosts-1) * numCpuCores)/numHosts
                    elif opt.type == "DRP":
                        nbrphyscpucoressla =  int(numCpuCores) /  2
                    elif opt.type == "HYB":
                        Percent_cpu_failover = int(cluster.configuration.dasConfig.admissionControlPolicy.cpuFailoverResourcesPercent)
                        nbrphyscpucoressla =  float(numCpuCores*(100-Percent_cpu_failover))/100                  
                    
                esx_list =()
                    

                for esx in cluster.host:
                    esx_list += (esx,)

        tot_vcpu  = 0
        for vm in vm_list:


           
            if vm.summary.runtime.host in esx_list:
                numCPU = vm.config.hardware.numCPU
                vcpu = numCPU
                powerState = vm.runtime.powerState

                
                if powerState == "poweredOn":
                   # print vm,  vcpu , numCPU, numCoresPerSocket
                    tot_vcpu = int(tot_vcpu) + int(vcpu)

        Ratio_Vcpu_Pcpu = round( float(tot_vcpu) / float(nbrphyscpucoressla),1)





        if opt.warning > opt.critical:
            print "UNKNOWN ==> Warning level should not be higher than Critical"
            sys.exit(3) 


        status_information = str(tot_vcpu) +" vCPU configured on cluster "+ str(opt.name)+" Ratio vcpu/pcpu="+str(Ratio_Vcpu_Pcpu) + " (SLA Max ratio=5)"
        perfdata = "| ratio="+str(Ratio_Vcpu_Pcpu)+";"+str(opt.warning)+";"+str(opt.critical)+";0;10 nbhost=" +str(numHosts)

        if Ratio_Vcpu_Pcpu >= opt.critical:
            print "CRITICAL : " + status_information + perfdata
            sys.exit(2)  
        elif Ratio_Vcpu_Pcpu >= opt.warning :
            print "WARNING : "+ status_information + perfdata
            sys.exit(1)
        else:
            print "OK : "+ status_information + perfdata
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
 
