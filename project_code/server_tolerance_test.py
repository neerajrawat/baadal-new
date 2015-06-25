if 0:
    from gluon import *  # @UnusedWildImport
    from applications.baadal.models import *
###################################################################################

import sys, math, shutil, paramiko, traceback, libvirt, os, io
import xml.etree.ElementTree as etree
from libvirt import *  # @UnusedWildImport
from helper import *  # @UnusedWildImport
import MySQLdb
import time
from host_helper import *  # @UnusedWildImport
from vm_utilization import *
from nat_mapper import create_mapping, remove_mapping
from vm_helper import *

from server_tolerance import server_fault_tolerance
#############################################################################


host_ip = "10.0.0.6" #SET IP OF HOST WHICH TO BE SHUTDOWN
 
def is_pingable(ip):
	command = "ping -c 1 %s" % ip
	response = os.system(command)
	return not(response)


def get_host_domains_Name(host_ip):
    try:
        conn = libvirt.openReadOnly('qemu+ssh://root@'+host_ip+'/system')
        domains=[]

        for domain_id in conn.listDomainsID():
        	dom_name = conn.lookupByID(domain_id).name()		
		domains.append(str(dom_name))

        conn.close()
        return domains
    except:
        raise

def server_fault_tolerance_test():
	mdb = MySQLdb.connect("localhost","root","baadal","baadal")
	cursor = mdb.cursor()

	execute_remote_cmd(host_ip,'root','shutdown now',None,True)
	
	while True:
		time.sleep(60)
		if not is_pingable(host_ip):
			break;
			
	host_id = current.db(current.db.host.host_ip==host_ip).select().first().id
			
	cursor.execute("select * from vm_data where host_id="+str(host_id))
	vms = cursor.fetchall()
#	vms = current.db(current.db.vm_data.host_id == host_id).select()

	server_fault_tolerance()	
	
	logger.debug("AFTER SERVER TOLERANCE MODULE CALLED")
	
	success=True
	vm_present = False
	
	logger.debug("VMSSSSS %s" %str(vms))
	for vm_name in vms:
		vm_present = True
		hostid = current.db(current.db.vm_data.vm_identity == vm_name[2]).select().first().host_id
		if hostid == host_id:
                        success=False
			break

		hostip = current.db(current.db.host.id == hostid).select().first().host_ip
		logger.debug("VM with name %s redefined on host with IP %s" %(vm_name[2],hostip))
		
		domains = get_host_domains_Name(hostip)
		if vm_name[2] in domains:
			success = True
		
		else:
			success = False	
		
		
		
	if success and vm_present:
		logger.debug("TEST SUCCESSFULL. SERVER FAULT TOLERANCE TOOK PLACE")
	elif success and (not vm_present):
		logger.debug("NO VM present on down host") 
	
	else:
		logger.debug("TEST FAILED. server fault tolerance module failed")
		
		
	
		
	
		
			
	
	
	
	



