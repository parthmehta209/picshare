import threading
import requests
import pycurl
from time import sleep

def timeout(event):
	r = requests.get(server+'timeout/'+event)
        
def accept_new_event(server,eventname,intent,master):
	try:
		r = requests.get(server+'acceptevent/'+eventname+':'+intent+':'+master)
	except:
		return 'error'
	return r.text

def uploadFile(url,filename):
	c = pycurl.Curl()
	c.setopt(c.POST, 1)
	c.setopt(c.URL, url)
	c.setopt(c.HTTPPOST, [("file", (c.FORM_FILE, "static/img/"+filename))])
	try: 
		ret = 'success'
		c.perform()
		c.close()
	except:
		ret = 'fail'
	return ret
