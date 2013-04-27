import threading
import requests
import pycurl
from time import sleep

def timeout(url):
	r = requests.get('http://localhost:5000/timeout/'+url)
        
def accept_new_event(server,url):
        r = requests.get(server+url)
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
