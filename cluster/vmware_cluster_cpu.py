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

def get_obj(content, vmname, obj):
    obj = None
    container = content.viewManager.CreateContainerView(content.rootFolder, obj, True)
    for c in container.view:
        if c.name == vmname:
            obj = c
            break
    return obj
def process_datastore_info(content, DSTORE):
    datastore = get_obj(content, DSTORE, [vim.datastore])
    print datastore

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
    parser.add_option("-n", action="store", help="see usage text",
                      dest="name")
    parser.add_option("-W", action="store", help="The Warning threshold (default: %default)",
                      dest="warning", default=90, type=int)
    parser.add_option("-C", action="store", help="The Critical threshold (default: %default)",dest="critical", default=100, type=int)
    parser.add_option("-S", action="store", help="CPU SLA Factor ",dest="SLAFACTOR", default=0.9, type=float)

    (opt, args) = parser.parse_args()

    """
    Required Arguments
    """
    if (opt.hostname is None or opt.authfile is None or opt.name is None):
        return parser.print_help()
    file = open(opt.authfile,"rb")
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
        content = si.RetrieveContent(
            )
        obj_clu = content.viewManager.CreateContainerView(content.rootFolder,[vim.ClusterComputeResource],True)
        obj_res = content.viewManager.CreateContainerView(content.rootFolder,[vim.ResourcePool],True)
       
        cluster_list = obj_clu.view
        resource_list = obj_res.view
        cluster_type = opt.name[:-2] # On enlève les deux derniers digit du nom du cluster pour identifier DRP ou STD 

        CPUSLAFACTOR = opt.SLAFACTOR

        for cluster in cluster_list:
            if str(opt.name) == str(cluster.name):
                numHosts= cluster.summary.numHosts # Recupération Nb Host Total
                RESOURCEPOOL = cluster.resourcePool
                CPUCapacity = cluster.summary.totalCpu # Recupération Capacite total physique du cluster 
                CPUusemhz = RESOURCEPOOL.summary.runtime.cpu.overallUsage # Recuperation Utilisation reel du cluster en MhZ
                if cluster_type.endswith("STD"):
                    numHostssla = float(numHosts-1)/numHosts # Perimetre Ratio du nombre  host sur lequel s applique le SLA 
                    CPU_Capacity_SLA = (CPUCapacity * numHostssla) * CPUSLAFACTOR
                    CPU_use_percent_SLA = ((CPUusemhz*100)/CPU_Capacity_SLA)
                elif cluster_type.endswith("DRP"):
                    
                    CPU_Capacity_SLA = round(((CPUCapacity  /2) * CPUSLAFACTOR),2)
                    
                    CPU_use_percent_SLA = ((CPUusemhz*100)/CPU_Capacity_SLA)


                
                
                
                CPU_use_percent_SLA = round(CPU_use_percent_SLA,2) 
                CPU_Capacity_SLA = int(CPU_Capacity_SLA)
                warn_sla= int((float(CPU_Capacity_SLA)/100) * opt.warning)
                crit_sla=int((float(CPU_Capacity_SLA)/100) * opt.critical)
                #print  CPU_Capacity_SLA, opt.warning , warn_sla

        Output_Message = str(CPU_use_percent_SLA) +"% CPU Usage on Cluster " \
        + str(opt.name)+" |" \
        + " 'CPU_use_percent_SLA'="+str(CPU_use_percent_SLA)+"%;"+str(opt.warning)+";"+str(opt.critical) \
        + " 'CPU_use_Mhz'="+str(CPUusemhz)+"Mhz;"+ str(warn_sla)+";"+ str(crit_sla)+";;"+str(CPU_Capacity_SLA)
        
        if opt.warning > opt.critical:
            print "UNKNOWN ==> Warning level should not be higher than Critical"
            sys.exit(3) 

        if CPU_use_percent_SLA >= opt.critical:
            print "CRITICAL : "+str(Output_Message)
            sys.exit(2)  
        elif CPU_use_percent_SLA >= opt.warning :
            print "WARNING : "+str(Output_Message)
            sys.exit(1)
        else:
            print "OK : "+str(Output_Message)
            sys.exit(0)        

 
        obj_clu.Destroy()
        obj_res.Destroy()
 
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
 