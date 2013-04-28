import os
import database
import time
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash, make_response, jsonify
from werkzeug import secure_filename
from gevent import monkey
from gevent.event import Event
from gevent.wsgi import WSGIServer
import subprocess
import requests
import servcomm
import threading
import functools
import sys

monkey.patch_all()   

log=open("log","w")
     
# configuration
DATABASE = 'party.db'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'
UPLOAD_FOLDER = 'static/img'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif','JPG'])

     
     
app = Flask(__name__)
app.config.from_object(__name__)


class Votes(object):

    def __init__(self):
        self.event = Event()

    def release(self):
        self.event.set()
        self.event.clear()

    def wait(self):
        self.event.wait()

room = Votes()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def getip(request):
    if not request.headers.getlist("X-Forwarded-For"):
        ip = request.remote_addr
    else:
        ip = request.headers.getlist("X-Forwarded-For")[0]
    return ip

'''database specific calls'''
@app.before_request
def before_request():
    g.db = database.connect_db(app.config['DATABASE'])
    
@app.teardown_request
def teardown_request(exception):
    g.db.close()


@app.route('/')
def home():
    
    imagelist = database.get_published_events(g)
    log.write("GET on /\n")
    log.write(str(imagelist)+"\n")
    log.flush()
    return render_template('index.html', imagelist = imagelist)
            
@app.route('/timeout/<params>')
def timer_expired(params):
    # check db for publish the event
    # release the event here so that everyone receives the message to publish or not publish
    event = params.split(':')[0]
    transid = int(params.split(':')[1])
    ''' get the status of other 2 servers then distribute results about publish or abort '''
    ret1 = database.make_event_status(event,transid,g)
    ret2 = servcomm.make_event_status(SERVER2,SERVER3,event,transid)
    log.write("Time out occurred status is :"+ret1 + ' '+ret2+' '+params+"\n")
    log.flush()
    if(ret1 == 'ignore' or ret2 == 'ignore'):
	log.write("Timeout ignored\n")
    	log.flush()
    elif(ret1 == 'aborted' or ret2 == 'aborted'):
	database.set_event_status(event,transid,'aborted',g)
	servcomm.set_event_status(SERVER2,SERVER3,event,transid,'aborted')
        room.release()
    elif(ret1 == 'published' and ret2 == 'published'):
	database.set_event_status(event,transid,'published',g)
	servcomm.set_event_status(SERVER2,SERVER3,event,transid,'published')
        room.release()
	
    return 'Hello :'+event  

@app.route('/makeeventstatus/<params>')
def make_event_status(params):
	log.write("GET on /makeeventstatus/"+params+"\n")
	log.flush()
	event = params.split(':')[0]
	transid = int(params.split(':')[1])
	ret = database.make_event_status(event,transid,g)	
	log.write('make event status returned:'+ret+'\n')
	log.flush()
	return ret

@app.route('/seteventstatus/<params>')
def set_event_status(params):
	log.write("GET on /seteventstatus/"+params+"\n")
	log.flush()
	event = params.split(':')[0]
	transid = int(params.split(':')[1])
	status = params.split(':')[2]
	ret = database.set_event_status(event,transid,status,g)	
	log.write('set event status returned:'+str(ret)+'\n')
	log.flush()
	if ret != 'ignore':
		room.release()
	return ret

@app.route('/vote/<vote>', methods=['POST'])
def vote(vote):
    log.write("POST on vote/"+vote+"\n")
    log.flush()
    list = vote.split(':')
    if list[0] == 'yes':
        ret = database.register_vote(list[1],request.cookies.get('user'),1,g)
        '''if ret == 0:
            database.add_user_inevent(list[1],request.cookies.get('user'),g)
            ret = database.register_vote(list[1],request.cookies.get('user'),1,g)'''
        log.write("register vote row count is %s\n"%(ret))
        log.flush()
        return jsonify(success=True)
    elif list[0] == 'no':
        ret = database.register_vote(list[1],request.cookies.get('user'),2,g)
        '''if ret == 0:
            database.add_user_inevent(list[1],request.cookies.get('user'),g)
            ret = database.register_vote(list[1],request.cookies.get('user'),2,g)'''
        log.write("register vote row count is %s\n"%(ret))
        log.flush()
        return jsonify(success=True)                
              
@app.route('/poll/<event>', methods=['POST'])
def poll(event):
    log.write("POST on /poll/"+event+"\n")
    log.flush()
    
    room.wait()
    statuslist = []
    status = database.get_event_status(event,g)    
    statuslist.append(status)
    imagelist = []
    
    imagelist = database.get_event_pics(event,g)
        
    statuslist.append(imagelist)
    log.write("The database returned :" + str(statuslist)+ "\n");    
    log.write("Wait over for user:"+request.cookies.get('user')+" /poll/"+event+" status is:"+status+"\n")
    log.flush()
    
    return jsonify(status=statuslist)



@app.route('/event/<event>', methods=['POST','GET'])
def get_event(event):
    log.write(request.method+' on /event/'+event + " ip: " + getip(request)+"\n")
    log.flush()
    if request.method == 'GET':
        eventlink = event
        eventname = event.split('_')[0]
        
        '''get the images from the database'''
        imagelist = database.get_event_pics(eventlink,g)
        log.write('Images for event:'+eventlink+' are:\n'+str(imagelist)+"\n")
        log.flush()
        
        status = database.get_event_status(eventlink,g)
        
        '''generate the html page with the images found'''
        response = make_response(render_template('event.html',
                    url='http://128.237.228.158:5000/event/' + eventlink,
                    eventname = eventname, eventlink = eventlink,
                    imagelist = imagelist,status=status))
                                
        '''Putting a cookie if one was not found'''
        if('user' not in request.cookies):
            log.write("No cookie found in user adding cookie for " + getip(request)+"\n")
            log.flush()
            response.set_cookie('user', getip(request))
            ret = database.add_user_inevent(event,getip(request),g)
        return response    

@app.route('/acceptevent/<event>')
def accept_event(event):
    log.write(request.method+' on /acceptevent/'+event+'\n')
    log.flush()
    eventname = event.split(':')[0]
    intent  = event.split(':')[1]
    master  = event.split(':')[2]
    if intent == 'intent':
        ret = database.is_event_acceptable(eventname,master,g)
        log.write('Intent for new event:'+eventname +' ret:'+ ret + '\n')
        log.flush()
        return ret
    if intent == 'confirm':
        ret = database.create_new_event(eventname,g)
        log.write('Confirm creation of event:'+eventname+' ret:'+ret + '\n')
        log.flush()
        return ret


@app.route('/addevent',methods=['POST'])
def add_event():
    log.write(request.method+' on /addevent ip: ' + getip(request)+"\n")
    log.flush()
    ''' creating a new event ''' 
    master = SERVER1.split(':')[2][:-1]
    eventname = request.form['event_name']
    eventlink = database.get_new_event_name(eventname,master,g)
    if eventlink == '':
        log.write('Event creation failed'+"\n")
        log.flush()
        return redirect(url_for('home'))
    log.write('The event name created is '+ eventlink +' master is '+master+'\n')   
    log.flush()	
    ret1 = servcomm.accept_new_event(SERVER2,eventlink,'intent',master)
    ret2 = servcomm.accept_new_event(SERVER3,eventlink,'intent',master)
    
    if ret1=='yes' and ret2 == 'yes':
        log.write('Event accepted now distributing results\n')
        ret1 = servcomm.accept_new_event(SERVER2,eventlink,'confirm',master)
        ret2 = servcomm.accept_new_event(SERVER3,eventlink,'confirm',master)
        if ret1=='yes' and ret2 == 'yes':
            database.create_new_event(eventlink,g)
            log.write('Event created:'+eventlink+'\n')
        else:
            log.write('could not confirm from both servers ' + ret1 + ret2 +'\n')
            log.flush()
            return redirect('/')
    else:
        log.write('could not get intent from both servers\n')
        log.flush()
        return redirect('/')
            
    log.write('Event '+eventlink+'created'+"\n")
    log.flush()
    return redirect('/event/'+eventlink)


@app.route('/upload/<event>',methods=['POST'])
def upload_image(event):
    ''' uploading a picture '''    
    if event != 'new' and request.method == 'POST':
        log.write('Uploading a picture The url to redirect to is:'+event+"\n")
        log.write('Request:'+str(request)+'\n')
        log.flush()
        file = request.files['capture']
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            if database.isfileuploaded(file.filename,event,g) == True:
                log.write('Avoiding reupload'+"\n")
                log.flush()
                return redirect('/event/'+event)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                                                         
            ''' add user to event only when he uploads'''
            if('user' in request.cookies):
                log.write('Cookie found in user ' + request.cookies.get('user')+"\n")
                log.flush()    
                if(database.user_not_in_event(event,request.cookies.get('user'),g)):
                    log.write("Cookie found in user but user not in event adding: " + getip(request)+"\n")
                    log.flush()
                    database.add_user_inevent(event,request.cookies.get('user'),g)

	    ''' add new event to database '''
	    log.write('Adding new image ' + filename + ' into database\n')
	    log.flush()
            database.insert_new_image(event,filename,-1,g)

	    ''' send the image to the master and get the new transaction ID then update the TID ''' 
	    master = database.get_event_master(event,g)
	    transid = servcomm.get_new_transid(event,master)
	    if transid == -1:
		log.write('Cannot proceed with upload event closed\n')
		log.flush()
		return redirect('/event/'+event)

	    database.update_images_transid(event,filename,transid,g)
	
	    ''' Send image to remaining servers '''
	    ret = servcomm.send_image_to_servers(event,SERVER2,SERVER3,transid,filename)
	    if ret != 'success':
		log.write('Upload is not accepted everywhere abort ret: '+ret+'\n')
		log.flush()
		return redirect('/event/'+event)

	    ''' Send message to all 3 servers to confirm the TID in events table '''
	    ''' Also confirm the image linked with the ttransaction to be made permanent '''
	    ''' This also nullifies all previous votes and starts a new voting '''
	    ''' check if event is still open before confirming transaction '''
	    ret = servcomm.confirm_transaction(event,SERVER2,SERVER3,transid)
	    if ret != 'success':
		log.write('Upload could not be confirmed so abort\n')
		log.flush()
		return redirect('/event/'+ event)

	    ret = database.start_voting(event,transid,g)	
            ''' nullify all the participants votes and then start a new timer by checking the prev
            ious timers number and incrementing it'''
            #transaction = database.start_voting(event,g)
            log.write("Start voting returned:%s timer started...\n"%(ret))
            log.flush()
            # start a new timer for end of voting period
            if ret == 0:
                log.write("Event published cannot upload any more pictures\n")
                log.flush()
		return redirect('/event'+event)
            else:
                log.write("Start timer here\n")
		log.flush()
		threading.Timer(10,functools.partial(servcomm.timeout,SERVER1,event+":"+str(transid))).start()
                #subprocess.Popen(["python", "callee.py",event,str(timer)])
            # wake everyone up and reload images in everyone.
	    log.write("releasing all events now on picture upload :"+request.cookies.get('user')+": " + event)
	    log.flush()
            room.release()
        else:
            log.write("File not accepted by server name:" + file.filename)
            log.flush()
                
        return redirect('/event/'+event)        
 
@app.route('/newimage/<params>',methods=['POST'])
def new_image(params):
	log.write(request.method+' on /newimage/'+params+"\n")
	log.flush()
	# <event>:<transaction id>
	event = params.split(':')[0]
	transid = int(params.split(':')[1])
	file = request.files['file']    
	log.write('file name is: '+file.filename+'\n')
	log.flush()
	filename = secure_filename(file.filename)
	file.save(os.path.join('static/img/', filename))

	database.insert_new_image(event,filename,transid,g)	
	return 'success'

@app.route('/confirmtrans/<params>')
def confirm_transaction(params):
	log.write(request.method+' on /confirmtrans/'+params+"\n")
	log.flush()
	event = params.split(':')[0]
	transid = int(params.split(':')[1])

	ret = database.start_voting(event,transid,g)
	log.write('Confirming transaction start voting returns :'+ ret+'\n')
	log.flush()
	room.release()
	return ret
	
	

@app.route('/gettransid/<event>')
def get_new_transid(event):
	ret  = database.get_new_transid(event,g)
	log.write('GET on /gettransid/'+event+' database returned '+str(ret)+'\n')
	log.flush()
	return str(ret)

if __name__ == '__main__':
    database.init_db(app.config['DATABASE'])
    #app.run(host='0.0.0.0')#,debug = True)
    if sys.argv[1] == '5000':
	SERVER1 = 'http://localhost:5000/'
	SERVER2 = 'http://localhost:5001/'
	SERVER3 = 'http://localhost:5002/'
    if sys.argv[1] == '5001':
	SERVER1 = 'http://localhost:5001/'
	SERVER2 = 'http://localhost:5000/'
	SERVER3 = 'http://localhost:5002/'
    if sys.argv[1] == '5002':
	SERVER1 = 'http://localhost:5002/'
	SERVER2 = 'http://localhost:5001/'
	SERVER3 = 'http://localhost:5000/'

    WSGIServer(('', int(sys.argv[1])), app.wsgi_app).serve_forever()
