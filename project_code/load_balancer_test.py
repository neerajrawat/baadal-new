
import sys, math, shutil, paramiko, traceback, libvirt, os, io
import xml.etree.ElementTree as etree
import MySQLdb
from libvirt import *  # @UnusedWildImport
from helper import *  # @UnusedWildImport

from host_helper import *  # @UnusedWildImport
from vm_utilization import *
from nat_mapper import create_mapping, remove_mapping
from vm_helper import *
from load_balancer import load_balance
#############################################################################



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


def load_balance_test():
	mdb = MySQLdb.connect("localhost","root","baadal","baadal")
	cursor = mdb.cursor()
	cursor.execute("select * from host where status=1")
	hosts = cursor.fetchall()

	hostMAX=None
	hostMIN=None
	max_cpu_usage=0
	min_cpu_usage=9999

	for host in hosts:
		host_ip = str(host[1])
		usage = get_host_cpu_usage(host_ip)
		if usage > max_cpu_usage:
			max_cpu_usage = usage
			hostMAX = host
		
		if usage < min_cpu_usage:
			min_cpu_usage = usage
			hostMIN = host
	
	migration_vector = 0
	will_load_balance_take_place = False
	vm_names = None
	if hostMAX[0] != hostMIN[0]:
		migration_vector = float(max_cpu_usage - min_cpu_usage) / 2

		
		cursor.execute("select * from vm_data where host_id="+str(hostMAX[0]))
		vm_names = cursor.fetchall()
	
		conn = libvirt.open("qemu+ssh://root@" + str(hostMAX[1]) + "/system")
	
		vmname=None
		diff_cpu = 999
		vm_host_id=None
		for vm_name in vm_names:
			logger.debug("vm name = %s" %str(vm_name[2]))
			dom = conn.lookupByName(vm_name[2])
			vm_cpu = float(0.33) #get_actual_usage(dom, str(hostMAX[1]))
			#vm_cpu = float(vm_cpu['cpu'])
			diff=abs(migration_vector - vm_cpu)
			if diff < migration_vector and diff < diff_cpu:
				diff_cpu=diff
				vmname = vm_name[2]
				vm_host_id = hostMAX[0]	
				will_load_balance_take_place = True
					
	
		
		conn.close()	

	logger.debug("BEFORE LOAD BALANCING........")
	if will_load_balance_take_place:

		logger.debug("ID of host with MAX cpu load %s" %str(hostMAX[0]))
		logger.debug("ID of host with MIN cpu load %s" %str(hostMIN[0]))
		logger.debug("CPU LOAD of host with MAX cpu load %s" %str(max_cpu_usage))
		logger.debug("CPU LOAD of host with MIN cpu load %s" %str(min_cpu_usage))
		#logger.debug("NAME of VM to be migrated from host with MAX cpu load %s" %str(vmname))
			
	else:	
		logger.debug("NOTHING SHOULD HAPPEND IN LOAD BALANCING")
	

####################
	vm_migrated = load_balance()
#####################
	if vm_migrated == None:
		load_balance_happened = False
	
	else:
		load_balance_happened = True

		if vm_migrated in vm_names:
			load_balance_happened = True
		else:
			load_balance_happened = False

		domains = get_host_domains_Name(str(hostMIN[1]))
		if vm_migrated not in domains:
			load_balance_happened = False	
		else:
			load_balance_happened=True
		


	logger.debug("AFTER LOAD BALANCE........")




	if load_balance_happened:
		logger.debug("ID of host with MAX cpu load %s" %str(hostMAX[0]))
		logger.debug("ID of host with MIN cpu load %s" %str(hostMIN[0]))
		logger.debug("CPU LOAD of host with MAX cpu load %s" %str(get_host_cpu_usage(hostMAX[1])))
		logger.debug("CPU LOAD of host with MIN cpu load %s" %str(get_host_cpu_usage(hostMIN[1])))
		logger.debug("NAME of VM  migrated %s" %str(vm_migrated))
		#logger.debug("IN DATABASE, NEW HOST ID of VM to be migrated %s" %str(vm_new_host_id))
		
	else:
		logger.debug("AFTER load balancing NOTHING HAPPENED")



	if will_load_balance_take_place == load_balance_happened:
		logger.debug("LOAD BALANCING TESTED SUCCESSFULL")
	
	else:
		logger.debug("LOAD BALANCING TESTED FAILED")	
	
		





	
	
	
	


	


		
		
		




	
		

