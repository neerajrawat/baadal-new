import libvirt,commands  # @UnusedImport
import pika
import time
from xml.etree import ElementTree


STEP         = 300
cpu_cut_off = 75

connection = pika.BlockingConnection(pika.ConnectionParameters(host='10.0.0.2'))
channel = connection.channel()
channel.queue_declare(queue='baadal')
dom_ids=[]
domains=[]
conn = libvirt.openReadOnly('qemu:///system')


def is_disk_write_increased(dom_id):

	print "inside disk"	
	counter=0
	previous_value=0
	pos_counter=0
	neg_counter=0	
	while counter <= 10:	
		dom_obj=conn.lookupByID(dom_id)
		tree = ElementTree.fromstring(dom_obj.XMLDesc(0))
		bytesr = 0
	        bytesw = 0
        	rreq  = 0
	        wreq  = 0
		for target in tree.findall("devices/disk/target"):
			device = target.get("dev")
			stats  = dom_obj.blockStats(device)
			rreq   += stats[0]
			bytesr += stats[1]
			wreq   += stats[2]
			bytesw += stats[3]
			
		if counter == 0:
			print "%s" %str(bytesw)
			previous_value=bytesw	
		
		counter = counter + 1	
	print "%s .... %s" %(str(bytesw),str(previous_value))
	
	perc_inc=0
	if previous_value != 0:
		perc_inc = ((bytesw - previous_value)/previous_value)
	
	print "counters== %s== %s == %s" %(str(pos_counter),str(neg_counter),str(perc_inc))
	if pos_counter > neg_counter  and perc_inc > 0.4:
		return True
	
	return False	

while True:
	time.sleep(100)
	#conn = libvirt.openReadOnly('qemu:///system')
	for domain_id in conn.listDomainsID():
		message=''
		dom = conn.lookupByID(domain_id)
		dom_name=dom.name()
		
		if domain_id not in dom_ids:
			dom_ids.append(domain_id)
			cputime=float(dom.info()[4])
			cpus=dom.info()[3]
			domain={'id':domain_id,'name':dom_name,'flag': 0 ,'prev_cputime' : cputime, 'prev_cpus':cpus}
			domains.append(domain)
						
		else:
			for domm in domains:
				if domm['id']==domain_id:
					cputime=float(dom.info()[4])
					cpus=dom.info()[3]
					cpu_usage=(cputime - domm['prev_cputime'])/(float(domm['prev_cpus'])*10000000*STEP)
					domm['prev_cputime'] = cputime
					domm['prev_cpus']=cpus
					
				#	print "%s" %str(cpu_usage)			
		
					if cpu_usage > cpu_cut_off:
                                        	message = message + '10.0.0.5 ' + str(domm['name'] + ' ' + str(cpu_usage))
                                      		print "Host IP = 10.0.0.5"
                                                print "VM name =%s" %str(domm['name'])
                                                print "CPU usage of VM %s is %s" %(str(domm['name']),str(cpu_usage))

						channel.basic_publish(exchange='',routing_key='baadal',body=message)

		if is_disk_write_increased(domain_id):
			message = message + '10.0.0.5 ' + str(domm['name']) + ' disk_write'
			print "increases disk writes"
			channel.basic_publish(exchange='',routing_key='baadal',body=message)
					
	
conn.close()
	
	
connection.close()


