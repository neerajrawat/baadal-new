if 0:
    from gluon import *  # @UnusedWildImport
    from applications.baadal.models import *
###################################################################################

import sys, math, shutil, paramiko, traceback, libvirt, os, io
import xml.etree.ElementTree as etree
from libvirt import *  # @UnusedWildImport
from helper import *  # @UnusedWildImport

from host_helper import *  # @UnusedWildImport
from vm_utilization import *
from nat_mapper import create_mapping, remove_mapping
from vm_helper import *

#############################################################################

def is_pingable(ip):
	command = "ping -c 1 %s" % ip
	response = os.system(command)
	return not(response)
	

def new_host(RAM, vCPU):
    hosts = current.db(current.db.host.status == 1).select()
    hosts = hosts.as_list(True,False) 
    while hosts:
        host = random.choice(hosts)
        logger.debug("Checking host =" + host['host_name'])
        (used_ram, used_cpu) = host_resources_used(host['id'])
        logger.debug("used ram: " + str(used_ram) + " used cpu: " + str(used_cpu) + " host ram: " + str(host['RAM']) + " host cpu "+ str(host['CPUs']))
        host_ram_after_200_percent_overcommitment = math.floor((host['RAM'] * 1024) * 2)
        host_cpu_after_200_percent_overcommitment = math.floor(host['CPUs'] * 2)

        logger.debug("ram available: %s cpu available: %s cpu < max cpu: %s" % ((( host_ram_after_200_percent_overcommitment - used_ram) >= RAM), ((host_cpu_after_200_percent_overcommitment - used_cpu) >= vCPU), (vCPU <= host['CPUs']) ))

        if((( host_ram_after_200_percent_overcommitment - used_ram) >= RAM) and ((host_cpu_after_200_percent_overcommitment - used_cpu) >= vCPU) and (vCPU <= host['CPUs'])) and is_pingable(host['host_ip']):
            return (host['id'],host['host_ip'])
        else:
            hosts.remove(host)
            
    #If no suitable host found
    raise Exception("No new host is available for a new vm.")


def relaunch_vm(vm_name, hostid, host_ip):
	command = "virsh define /mnt/datastore/vm_xmls/" + vm_name + ".xml"
	command_output = execute_remote_cmd(host_ip,'root',command,None,True)
	logger.debug("SERVER FAULT CREATE == %s" %str(command_output))
	if command_output[0] == str('Domain '+vm_name + ' defined from /mnt/datastore/vm_xmls/'+ vm_name + '.xml\n'):
		conn = libvirt.open("qemu+ssh://root@" + host_ip + "/system")
		domain = conn.lookupByName(vm_name)
		domain.create()
		conn.close()
		current.db(current.db.vm_data.vm_identity==vm_name).update(host_id=hostid)
		current.db.commit()
	
	if os.path.exists('/mnt/datastore/vm_snapshots/' + vm_name):
		vm_id = current.db(current.db.vm_data.vm_identity == vm_name).select().first()['id']
		snapshots = current.db(current.db.snapshot.vm_id == vm_id).select()
		for snapshot in snapshots:
			command = 'virsh snapshot-create ' + vm_name + ' /mnt/datastore/vm_snapshots/' + vm_name + '/'  + vm_name + '_' + snapshot['snapshot_name'] + '.xml --redefine'
			execute_remote_cmd(host_ip,'root',command,None,True)

#	raise Exception("VM can not be created on new host")



def server_fault_tolerance():
    try:
		
	logger.debug("Inside server fault tolerance function")
        logger.info("SERVER FAULT TOLERANCE")
        hosts=current.db(current.db.host.status == HOST_STATUS_UP).select(current.db.host.ALL)
        logger.debug("HOSTS ARE %s" %(str(hosts)))
        
        for host in hosts:
		if (not is_pingable(host["host_ip"])):
			current.db(current.db.host.id==host['id']).update(status=0)
			current.db.commit()
		
			vms = current.db(current.db.vm_data.host_id == host["id"]).select()
			vms = vms.as_list(True,False) 	
			for vm in vms:
				RAM = vm["RAM"]
				CPU = vm["vCPU"]
				new_host_id, new_host_ip = new_host(RAM,CPU)
				relaunch_vm(vm['vm_identity'],new_host_id,new_host_ip)
					
	
    except:
	logger.debug("Task Status: FAILED Error: %s " % log_exception())
	return (current.TASK_QUEUE_STATUS_FAILED, log_exception())    					
			
			
			
			
			
			
			
			
			
			
			
			
			
			
			
			
			
			
			
			
			
			
			
    
