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
    # parser.add_option("-n", action="store", help="see usage text",
    #                   dest="name")
    # parser.add_option("-c", action="store", help="The Warning threshold (default: %default)",
    #                   dest="count", default=0, type=int)


    (opt, args) = parser.parse_args()

    """
    Required Arguments
    """
    if (opt.hostname is None or opt.authfile is None ):
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
        content = si.RetrieveContent()
        
        obj_vm = content.viewManager.CreateContainerView(content.rootFolder,[vim.VirtualMachine],True)
        obj_host = content.viewManager.CreateContainerView(content.rootFolder,[vim.HostSystem],True)

        vm_list=obj_vm.view
        VM_WITH_ISO=""


        host_list=obj_host.view
        for host in host_list:
            list_vm = host.vm
            for vm in list_vm:
                try:
                    device = vm.config.hardware.device
                    for i in device:
                        iso = i.deviceInfo.summary


                        if iso.startswith("ISO") and i.connectable.connected is True:
                            VM_WITH_ISO += "ISOMOUNTED :" + str(vm.name) + " "
                except:
                    continue

 
        if "ISOMOUNTED" in  VM_WITH_ISO:
            print "CRITICAL - " + str(VM_WITH_ISO)
            sys.exit(2)
        elif VM_WITH_ISO =="":
            print "OK - No ISO "
            sys.exit(0)




 
    except vmodl.MethodFault, e:
        print "Caught vmodl fault : " + e.msg
        return -1
    except IOError, e:
        print "Could not connect to %s. Connection Error" % opt.hostname
        return -1
    return 0


if __name__ == "__main__":
    main()
 