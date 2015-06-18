
###################################################################################

import sys, math, shutil, paramiko, traceback, libvirt, os
import xml.etree.ElementTree as etree
import pika
import MySQLdb
from libvirt import *  # @UnusedWildImport
#from helper import *  # @UnusedWildImport

#from host_helper import *  # @UnusedWildImport
#from vm_utilization import *
#from nat_mapper import create_mapping, remove_mapping
#from vm_helper import *

SNAPSHOT_USER=101
SNAPSHOT_SYSTEM = 102

#############################################################################

db = MySQLdb.connect("localhost","root","baadal","baadal")
cursor = db.cursor()


def is_pingable(ip):
	command = "ping -c 1 %s" % ip
	response = os.system(command)
	return not(response)

def get_datetime():
	#print "inside datetime"
	import datetime
	return datetime.datetime.now()

def delete_snapshot(parameters):
	#print "inside delkete"
	vm_id = parameters['vm_id']
	snapshotid = parameters['snapshot_id']
	cursor.execute("select * from vm_data where id="+str(vm_id))
	vm_details = cursor.fetchone()	

	try:
		host_id=int(vm_details[3])
		cursor.execute("select host_ip from host where id="+str(host_id))
		host_ip=cursor.fetchone()[0]
		connection_object = libvirt.open("qemu+ssh://root@" + str(host_ip) + "/system")
		vm_identity=str(vm_details[2])
		domain = connection_object.lookupByName(vm_identity)
		cursor.execute("select snapshot_name from snapshot where id="+str(snapshotid))	
		snapshot_name = cursor.fetchone()[0]
		
		snapshot = None
		try:
			snapshot=domain.snapshotLookupByName(str(snapshot_name), 0)
			
		except MySQLdb.Error, e:
			print "Error %d: %s" % (e.args[0], e.args[1])
			sys.exit (1)
		
		if snapshot != None:
			snapshot.delete(0)

		connection_object.close()
		
		cursor.execute("delete from snapshot where id="+str(snapshotid))
		db.commit()
		#print "delete sucess"

	except MySQLdb.Error, e:
		print "Error %d: %s" % (e.args[0], e.args[1])
		sys.exit (1)		


def snapshot(parameters):
	print "inside snapshot"
	vm_id = parameters['vm_id']
	snapshot_type = parameters['snapshot_type']
	try:
		cursor.execute("select * from vm_data where id="+str(vm_id))
		vm_details = cursor.fetchone()
		private_ip=str(vm_details[12])
		if True:#is_pingable(private_ip):
			if snapshot_type != SNAPSHOT_USER:
				cursor.execute("select * from snapshot where vm_id="+str(vm_id)+" and " + "type="+str(snapshot_type))
				snapshots=cursor.fetchall()
				for snapshot_cron in snapshots:
					delete_snapshot({'vm_id':vm_id, 'snapshot_id':int(snapshot_cron[0])})
			
			snapshot_name = get_datetime().strftime("%I:%M%p_%B%d,%Y")			
			host_id=int(vm_details[3])
                	cursor.execute("select host_ip from host where id="+str(host_id))
	                host_ip=cursor.fetchone()[0]
			#print "%s" %str(host_ip)
        	        connection_object = libvirt.open("qemu+ssh://root@" + str(host_ip) + "/system")
			#print "%s" %str(connection_object)	
			#print "about ocome"
			vm_identity=str(vm_details[2])
	                domain = connection_object.lookupByName(vm_identity)
			#print "%s" %str(vm_identity)
			#print "%s" %str(domain)
			xmlDesc = "<domainsnapshot><name>%s</name></domainsnapshot>" % (snapshot_name)
			domain.snapshotCreateXML(xmlDesc, 0)
			connection_object.close()		
			
			datastore_id=int(vm_details[15])
			#print "%d" %datastore_id
			cursor.execute("insert into snapshot (vm_id,datastore_id,snapshot_name,type) values("+str(vm_id)+","+str(datastore_id)+",'"+snapshot_name+"',"+str(snapshot_type)+")")
			

			print "snapshot SUCCESFULL"	
			db.commit()

	except MySQLdb.Error, e:
        	print "Error %d: %s" % (e.args[0], e.args[1])
        	sys.exit (1)
	


def callback(ch, method, properties, message):
	dom_name=message.split(' ')[1]
	host_ip=message.split(' ')[0]
	cpu_usage=message.split(' ')[2]
	
	print "Message from host = %s" %str(host_ip)
	print "VM name = %s" %str(dom_name)
	print "CPU usage of the VM =%s" %str(cpu_usage) 
	 
	cursor.execute("select id from vm_data where vm_identity='"+str(dom_name)+"'")
	dom_id = int(cursor.fetchone()[0])
        param={'vm_id': dom_id,'snapshot_type' : SNAPSHOT_SYSTEM}
	
	snapshot(param)
	
		
connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()
channel.queue_declare(queue='baadal')
channel.basic_consume(callback,queue='baadal',no_ack=True)
channel.start_consuming()


