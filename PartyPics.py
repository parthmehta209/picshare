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
            
@app.route('/timeout/<timeout>')
def timer(timeout):
    # check db for publish the event
    # release the event here so that everyone receives the message to publish or not publish
    eventname = timeout.split(':')[0]
    timer = int(timeout.split(':')[1])
    ret = database.make_event_status(eventname,timer,g)
    log.write("Time out occurred status is :"+ret+timeout+"\n")
    log.flush()
    if(ret != 'ignore'):
	log.write("Calling release from time out user:"+timeout+"\n")
    	log.flush()
        room.release()
    return 'Hello :'+eventname  

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
    log.write('The event name created is '+ eventname+' master is '+master+'\n')   
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
            log.write('could not confirm from both servers\n')
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
            ''' add new event to database'''
            database.insert_new_image(event,filename,g)
                                                
            ''' add user to event only when he uploads'''
            if('user' in request.cookies):
                log.write('Cookie found in user ' + request.cookies.get('user')+"\n")
                log.flush()    
                if(database.user_not_in_event(event,request.cookies.get('user'),g)):
                    log.write("Cookie found in user but user not in event adding: " + getip(request)+"\n")
                    log.flush()
                    database.add_user_inevent(event,request.cookies.get('user'),g)

            ''' nullify all the participants votes and then start a new timer by checking the prev
            ious timers number and incrementing it'''
            transaction = database.start_voting(event,g)
            log.write("Start voting returned timer:%s timer started...\n"%(transaction))
            log.flush()
            # start a new timer for end of voting period
            if transaction == 0:
                log.write("Event published cannot upload any more pictures\n")
                log.flush()
            else:
		threading.Timer(10,functools.partial(servcomm.timeout,SERVER1,event+":"+str(transaction))).start()
                #subprocess.Popen(["python", "callee.py",event,str(timer)])
            # wake everyone up and reload images in everyone.
	    log.write("releasing all events now on picture upload :"+request.cookies.get('user')+": " + event)
	    log.flush()
            room.release()
        else:
            log.write("File not accepted bu server name:" + file.filename)
            log.flush()
                
        return redirect('/event/'+event)        
 
@app.route('/newimage/<event>',methods=['POST'])
def new_image(event):
	log.write(request.method+' on /newimage/'+event + " ip: " + getip(request)+"\n")
	log.flush()
	# <event>:<transaction id>:<filename>
	# check own intent and database if transaction number is fine with me if yes respond 
	# positively else respond with failure	
	file = request.files['file']    
	log.write('file name is: '+file.filename)
	log.flush()
	filename = secure_filename(file.filename)
	file.save(os.path.join('server', filename))
	return jsonify(success=True)




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
