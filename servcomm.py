import threading
import requests
import pycurl
from time import sleep
import StringIO
import traceback

log = open('log','w')

def timeout(server,event):
	r = requests.get(server+'timeout/'+event)
        
def accept_new_event(server,eventname,intent,master):
	try:
		r = requests.get(server+'acceptevent/'+eventname+':'+intent+':'+master)
	except:
		return 'error'
	return r.text

def get_new_transid(event,master):
	try: 
		r = requests.get('http://localhost:'+master+'/gettransid/'+event)
	except:
		return 0
	log.write('Get new transID returned :'+r.text)
	return int(r.text)	

def send_image_to_servers(event,SERVER2,SERVER3,transid,filename):
	url2 = SERVER2+'newimage/'+event+':'+str(transid)
	url3 = SERVER3+'newimage/'+event+':'+str(transid)
	log.write('Sending image to other two servers\n'+url2+'\n'+url3+'\n')
	log.flush()	
	
	c = pycurl.Curl()
	c.setopt(c.POST, 1)
	c.setopt(c.HTTPPOST, [("file", (c.FORM_FILE, "static/img/"+filename))])
	
	response_func = StringIO.StringIO()
	c.setopt(pycurl.WRITEFUNCTION, response_func.write)
	try: 
		c.setopt(c.URL, str(url2.encode('utf-8')))
		c.perform()
		response = response_func.getvalue()
		log.write('Server '+url2+' replied with '+response+'\n')
		log.flush()	
		
		c.setopt(c.URL, str(url3.encode('utf-8')))
		c.perform()
		response = response_func.getvalue()
		log.write('Server '+url3+' replied with '+response+'\n')
		log.flush()
		c.close()

		ret = 'success'
	except Exception, e:
    		traceback.print_exc()
		ret = 'fail'
	return ret

def confirm_transaction(event,SERVER2,SERVER3,transid):
	url2 = SERVER2+'confirmtrans/'+event+':'+str(transid)
	url3 = SERVER3+'confirmtrans/'+event+':'+str(transid)
	
	try:
		r2 = requests.get(str(url2.encode('utf-8')))
		r3 = requests.get(str(url3.encode('utf-8')))
		if r2.text == 'success' and r3.text == 'success':
			return 'success'
		else:
			return 'fail'
	except:
		return 'fail'


def make_event_status(SERVER2,SERVER3,event,transid):
	url2 = SERVER2+'makeeventstatus/'+event+':'+str(transid)
	url3 = SERVER3+'makeeventstatus/'+event+':'+str(transid)
	
	try:
		r2 = requests.get(str(url2.encode('utf-8')))
		r3 = requests.get(str(url3.encode('utf-8')))
		if r2.text == 'ignore' or r3.text == 'ignore':
			return 'ignore'
		elif r2.text == 'aborted' or r3 == 'aborted':
			return 'aborted'
		elif r2.text == 'published' and r3.text == 'published':
			return 'published'
	except:
		return 'fail'

def set_event_status(SERVER2,SERVER3,event,transid,status):
	url2 = SERVER2+'seteventstatus/'+event+':'+str(transid)+':'+status
	url3 = SERVER3+'seteventstatus/'+event+':'+str(transid)+':'+status
	
	try:
		r2 = requests.get(str(url2.encode('utf-8')))
		r3 = requests.get(str(url3.encode('utf-8')))
		if r2.text == 'ignore' or r3.text == 'ignore':
			return 'ignore'
		elif r2.text == 'closed' or  r3 == 'closed':
			return 'closed'
		elif r2.text == 'success' and r3.text == 'success':
			return 'success'
	except:
		return 'fail'

