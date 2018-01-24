#!/usr/bin/python2.7
# coding: utf-8

__author__ = "Sébastien DOUCE"
__version__ = "0.1"
import csv
import ssl
import sys
import json

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

def get_all_vm_snapshots(self, snapshots=None):
    found_snapshots = []

    if not snapshots:
        snapshots = vm.snapshot.rootSnapshotList

    for snapshot in snapshots:
        if snapshot.childSnapshotList:
            found_snapshots += get_all_vm_snapshots(snapshot.childSnapshotList)
        found_snapshots += [snapshot]
    return found_snapshots
def sizeof_fmt(num):
    """
    Returns the human readable version of a file size
    :param num:
    :return:
    """
    for item in ['bytes', 'KB', 'MB', 'GB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, item)
        num /= 1024.0
    return "%3.1f%s" % (num, 'TB')


def print_fs(host_fs):
    """
    Prints the host file system volume info
    :param host_fs:
    :return:
    """
    print("{}\t{}\t".format("Datastore:     ", host_fs.volume.name))
    print("{}\t{}\t".format("UUID:          ", host_fs.volume.uuid))
    print("{}\t{}\t".format("Capacity:      ", sizeof_fmt(
        host_fs.volume.capacity)))
    print("{}\t{}\t".format("VMFS Version:  ", host_fs.volume.version))
    print("{}\t{}\t".format("Is Local VMFS: ", host_fs.volume.local))
    print("{}\t{}\t".format("SSD:           ", host_fs.volume.ssd))


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
    parser.add_option('-j', '--json', default=False, action='store_true',
                        dest="json", help='Output to JSON')
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
        obj_host = content.viewManager.CreateContainerView(content.rootFolder, [vim.HostSystem], True)
        obj_vm = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)

        esxi_hosts = obj_host.view
        host_list = obj_host.view
        vm_list = obj_vm.view
        obj_host.Destroy()
        #print vm_list
 
        count=0
        for vm in vm_list:
            powerState = vm.runtime.powerState
            if powerState == "poweredOn":
                #print vm.name
                vmlist = vm.name
                count = count +1
            else:
                count = count
        print count

        
        datastores = {}
        for esxi_host in esxi_hosts:
            if not opt.json:
                print("{}\t{}\t\n".format("ESXi Host:    ", esxi_host.name))

            # All Filesystems on ESXi host
            storage_system = esxi_host.configManager.storageSystem
            host_file_sys_vol_mount_info = \
                storage_system.fileSystemVolumeInfo.mountInfo

            datastore_dict = {}
            # Map all filesystems
            for host_mount_info in host_file_sys_vol_mount_info:
                # Extract only VMFS volumes
                if host_mount_info.volume.type == "VMFS":

                    extents = host_mount_info.volume.extent
                    if not opt.json:
                        print_fs(host_mount_info)
                    else:
                        datastore_details = {
                            'uuid': host_mount_info.volume.uuid,
                            'capacity': host_mount_info.volume.capacity,
                            'vmfs_version': host_mount_info.volume.version,
                            'local': host_mount_info.volume.local,
                            'ssd': host_mount_info.volume.ssd
                        }

                    extent_arr = []
                    extent_count = 0
                    json = opt.json
                    for extent in extents:
                        if not opt.json:
                            print("{}\t{}\t".format(
                                "Extent[" + str(extent_count) + "]:",
                                extent.diskName))
                            extent_count += 1
                        else:
                            # create an array of the devices backing the given
                            # datastore
                            extent_arr.append(extent.diskName)
                            # add the extent array to the datastore info
                            datastore_details['extents'] = extent_arr
                            # associate datastore details with datastore name
                            datastore_dict[host_mount_info.volume.name] = \
                                datastore_details
                    if not json:
                        print

            # associate ESXi host with the datastore it sees
            datastores[esxi_host.name] = datastore_dict

        #if opt.json:
            #print(json.dumps(datastores))

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        sys.exit(2)
        return -1
    except IOError, e:
        print "Could not connect to %s. Connection Error" % opt.hostname
        sys.exit(2)
        return -1

    return 0

        # for host in host_list:
        #     overallCpuUsage = float(host.summary.quickStats.overallCpuUsage)
        #     cpuMhz = float(host.summary.hardware.cpuMhz)
        #     numCpuCores = float(host.summary.hardware.numCpuCores)

        #     percent = round(
        #         (overallCpuUsage / (numCpuCores * cpuMhz) * 100), 2)

        # output = str(percent)+"% | cpu_usage="+str(percent)+";"+str(warning)+";"+str(critical)+";0;100"

        # if percent >= int(critical):
        #     print "CRITICAL - " + str(output)
        #     sys.exit(2)
        # elif percent >= int(warning):
        #     print "WARNING - " + str(output)
        #     sys.exit(1)
        # else:
        #     print "OK - " + str(output)
        #     sys.exit(0)
        # obj_host.Destroy()


if __name__ == "__main__":
    main()
