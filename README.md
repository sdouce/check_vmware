# check_vmware
Monitoring Plugins for VMWARE/VSAN written with Python . 

Plugins for monitoring system nagios-like : Icinga/Shinken/naemon/nagios...... etc 

Every plugins use for authentification a local csv based file :

     CSV_ENTRY;username;password
     

     ./check_xxx.py -A /path/auth.csv -H VCENTER/ESX 
     
I prefer separate action plugins by plugins . 


    define service{
            use                     generic-service
            name                    TPL-CLUSTER-VSAN-HEALTH
            check_command           CHK_CLUSTER_VSAN_HEALTH
            register                0
    }
    define command{
            command_name    CHK_CLUSTER_VSAN_HEALTH
            command_line    $USER1$/vsan/vsan_cluster_health.py -H $_HOSTVCENTER$ -A $_HOSTAUTH$ -c $_HOSTCLUSTER$ -C $_SERVICEGROUP$ -O '$_SERVICEHEALTHTEST$'
    }

