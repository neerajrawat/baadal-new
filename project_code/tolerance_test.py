import sys, math, shutil, paramiko, traceback, libvirt, os
import xml.etree.ElementTree as etree
import pika
import time
import MySQLdb
from libvirt import *  # @UnusedWildImport


db = MySQLdb.connect("localhost","root","baadal","baadal")
cursor = db.cursor()
connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()
channel.queue_declare(queue='baadal')


VM_NAME = ""   #SET this before testing
HOST_IP = ""   #SET this before testing


cursor.execute("select * from vm_data where vm_name='" + str(VM_NAME) + "'")
VM_NAME = cursor.fetchone()[2]

message=''
message = HOST_IP + ' ' + VM_NAME + ' ' + str(100)


print "%s" %message

connection_object = libvirt.open("qemu+ssh://root@" + str(HOST_IP) + "/system")
dom = connection_object.lookupByName(VM_NAME)

dom.destroy()

connection_object.close()


channel.basic_publish(exchange='',routing_key='baadal',body=message)

time.sleep(100)

print "AFTER Fault TOLERANCE MODULE"

cursor.execute("select * from vm_data where vm_identity='" + str(VM_NAME) + "'")
vm_id = int(cursor.fetchone()[0])

print "vm id == %s" %str(vm_id)

cursor.execute("select * from snapshot where vm_id="+str(vm_id))
snapshot_name = cursor.fetchone()[3]

print "%s" %snapshot_name

connection_object = libvirt.open("qemu+ssh://root@" + str(HOST_IP) + "/system")

dom = connection_object.lookupByName(VM_NAME)

dom.create()

snaps = dom.snapshotLookupByName(snapshot_name,0)

connection_object.close()

if snaps != None:
	print "FAUTL TOLERANCE is successfull"
	
else:
	print "FAUTL TOLERANCE is FAILED"	












