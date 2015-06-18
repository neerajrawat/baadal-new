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
test_vm_usage={}
vector=0
MAXX=0
MINN=0
hostMAX_id=0
hostMIN_id=0
vm_idd=0
vm_cpu_usage=[]
hostMINip=''

def get_host_domains_ID(host_ip):
    try:
        conn = libvirt.openReadOnly('qemu+ssh://root@'+host_ip+'/system')
        domains=[]

        for domain_id in conn.listDomainsID():
	    domains.append(domain_id)

        conn.close()
        return domains
    except:
        raise


def get_migration_vector(HMAX,HMIN):
        vector=(HMAX-HMIN)/2
        return vector



def calculate_load(hosts):
        hostMAX=hosts[0]
        HMAX=0
        HMIN=9999
        minHost=[]
        for host in hosts:
                host_cpu_usage=get_host_cpu_usage(host['host_ip'])
                logger.debug("host %s has cpu usage %s" %(str(host['host_ip']),str(host_cpu_usage)))
                if host_cpu_usage > HMAX:
                        HMAX=host_cpu_usage
                        hostMAX=host
			
                HMIN=host_cpu_usage
                node={}
                node['id']=host['id']
                node['cpu']=HMIN
		node['host_ip']=host['host_ip']	
                minHost.append(node)
                                                              
	return (HMAX,hostMAX,minHost)



def load_balancing_decision(conn,migration_vector,vms,hostMAX,hostMIN):
        HMIN=hostMIN['cpu']
        logger.debug("MAX AND MIN HOSTS ARE %s %s" %(str(hostMAX),str(hostMIN)))
        logger.debug("VMS ARE %s" %(str(vms)))
        dom_id=0
        flag=0
        diff_cpu=999
		
	
        for vm_id in vms:

                dom = conn.lookupByID(vm_id)
                dom_info=dom.info()
                logger.debug("DOM INFO %s" %(str(dom_info)))
                usage=get_actual_usage(dom,hostMAX['host_ip'])

		vm_set={}	
		vm_set['id']=vm_id
		vm_set['cpu']=usage['cpu']
		vm_cpu_usage.append(vm_set)

                logger.debug("ACTUAL USAGE %s" %(str(usage['cpu'])))
                dom_cpu=float(usage['cpu'])

		test_vm_usage[str(vm_id)] = dom_cpu

                diff=abs(migration_vector - dom_cpu)

		vector=migration_vector

                logger.debug("VECTOR and DIFF and dom_cpu %s -- %s -- %s" %(str(migration_vector),str(diff),str(dom_cpu)))

                hostminRam=current.db(current.db.host.id == hostMIN['id']).select().first().RAM * 1024 * 2  #in MB
                logger.debug("host min RAM %s" %(str(hostminRam)))
                domRam=current.db(current.db.vm_data.vm_identity == str(dom.name())).select().first().RAM
                (Ram_used,Cpu_used)=host_resources_used(hostMIN['id'])
                logger.debug("used RAM %s" %(str(Ram_used)))
                isRamAvailabel=False
                if (hostminRam - Ram_used) >= domRam:
                        isRamAvailabel=True

                if diff < migration_vector and diff < diff_cpu and isRamAvailabel:
                        diff_cpu=diff
                        dom_id=vm_id
                        flag=1

        return (flag,dom_id)


def load_balance():
    try:
		
	#files=io.open("load_test_values","a")
        logger.debug("Inside load balancer() function")
        logger.info("LOAD BALANCER")
        hosts=get_active_hosts()
        logger.debug("HOSTS ARE %s" %(str(hosts)))
        flag=0
	ii=0
        while ii<1: #True:
                flag=0

                hostMAX=hosts[0]
                migration_vector=0

                HMAX,hostMAX,minHost=calculate_load(hosts)

		MAXX=HMAX
		hostMAX_id=hostMAX['id']

                minHosts = sorted(minHost, key=lambda x: x['cpu'])
                logger.debug("MIN HOSTS ARE   ++++ %s" %(str(minHosts)))
                vms=get_host_domains_ID(hostMAX['host_ip'])
                conn = libvirt.openReadOnly('qemu+ssh://root@'+hostMAX['host_ip']+'/system')
                for hostMIN in minHosts:
                        flag=0

                        if hostMIN['id'] != hostMAX['id']:
                                HMIN=hostMIN['cpu']
                                logger.debug("MAX AND MIN HOSTS ARE %s %s" %(str(hostMAX),str(hostMIN)))
                                migration_vector=get_migration_vector(HMAX,HMIN)
                                logger.debug("VMS ARE %s" %(str(vms)))
                                (flag,dom_id)=load_balancing_decision(conn,migration_vector,vms,hostMAX,hostMIN)

                        if flag==1:
				MINN=HMIN
                                hostMINid=hostMIN['id']
				hostMINip=hostMIN['host_ip']
                                break


                logger.debug("FLAG == %s" %(str(flag)))
                if flag==1:
                        domm=conn.lookupByID(dom_id)
			vm_idd=dom_id
                        dom_name=domm.name()
                        logger.debug("DOM NAME!! %s" %(str(dom_name)))
                        domo= current.db(current.db.vm_data.vm_identity == str(dom_name)).select().first()
                        logger.debug("DOMOOOOOO and DOM NAME %s----%s" %(str(domo),str(dom_name)))
			dom_id=domo.id
                        logger.debug("DOM NAME and DOM and DOM ID %s  %s  %s" %(str(dom_name),str(domo),str(dom_id)))


			logger.debug("TESTER== migration vector = %s" %str(migration_vector))
			logger.debug("TESTER== host MAX ID = %s" %str(hostMAX_id))
			logger.debug("TESTER== host MIN ID = %s" %str(hostMINid))
			logger.debug("TESTER== host MAX usage = %s" %str(MAXX))
			logger.debug("TESTER== host MIN usage = %s" %str(MINN))
			logger.debug("TESTER== host MAX migrate VM Id= %s" %str(vm_idd))
			logger.debug("TESTER== host MAX migrate VM usage = %s" %str(test_vm_usage[str(vm_idd)]))
		
			logger.debug("TESTER== VMS of MAX HOST = %s" %str(vms))
			logger.debug("TESTER== VMs of MAX host with id and usage = %s" %str(vm_cpu_usage))
			
	
			logger.debug("TESTER== hostsssss %s" %str(minHosts))
			migrate_domain(dom_id,hostMINid,True)

			logger.debug("TESTER== cpu usage of MAX host after migration %s" %str(get_host_cpu_usage(hostMAX['host_ip'])))

			logger.debug("TESTER== cpu usage of MIN host after migration %s" %str(get_host_cpu_usage(hostMINip)))

			logger.debug("TESTER== \n\n\n\n\n\n")

                else:
                        break
	
		ii=ii+1
	#files.close()

    except:
        logger.debug("Task Status: FAILED Error: %s " % log_exception())
        return (current.TASK_QUEUE_STATUS_FAILED, log_exception())
