#    cur = g.db.execute('select title, text from entries order by id desc')
#    entries = [dict(title=row[0], text=row[1]) for row in cur.fetchall()]
import sqlite3
import random
from contextlib import closing

ABORTED = 0
VOTING = 1
PUBLISHED = 2
INTENDED = 3
iPUBLISHED = 4
TEMP = 0
PERMANENT = 1
NOTASSIGNED = -1

log = open('log','w')

'''This creates a table per event and registers all ip addresses of the participants of 
    the event in this table; the vote can be 3 values 0=not voted,1=for publishing,2=not for publishing'''
def create_event_table(eventlink,g):
    g.db.execute("CREATE TABLE IF NOT EXISTS "+eventlink+
                    "(participant text primary key not null,\
                    vote integer)"
                    )
    g.db.commit() 

'''this is a global event table and it records all the events that exists and '''
def create_events_table(db):
    db.execute("CREATE TABLE IF NOT EXISTS events\
                    (event text primary key,\
                    status integer,\
                    transid integer,\
		    tempid  integer,\
		    master text)"
                    )
    db.commit() 

'''This is a table that stores all images with the server'''
def create_image_table(db):
    db.execute("CREATE TABLE IF NOT EXISTS images \
                    (id integer primary key autoincrement,\
                    event text,\
                    image text,\
		    status integer,\
		    transid integer)"
                    )
    db.commit() 

'''Functions related to single events'''   
''' get a new event name and inserts a half baked entry'''
def get_new_event_name(event,master,g):
    counter = 0
    while 1:
        eventname = event + "_"+str(random.randint(1,5000))
        cur = g.db.execute('select * from events where event='+"'"+eventname+"'")
        if(len(cur.fetchall())>0):
            counter+=1
            if counter>100:
                return ''
            continue
        else:
            break
    g.db.execute('INSERT INTO events (event,status,transid,tempid,master) VALUES(?,?,?,?,?)',[eventname,INTENDED,0,0,master])
    g.db.commit()
    return eventname
    
''' insert half baked event if acceptabe else return fasle'''    
def is_event_acceptable(eventname,master,g):    
    cur = g.db.execute('select * from events where event='+"'"+eventname+"'")
    if(len(cur.fetchall())>0):
        return 'no'
    else:
        g.db.execute('INSERT INTO events (event,status,transid,tempid,master) VALUES(?,?,?,?,?)',[eventname,INTENDED,0,0,master])
        g.db.commit()
        return 'yes'

''' finalize create'''
def create_new_event(eventname,g):
	cur = g.db.execute('update events set status=? where event=?',[ABORTED,eventname])
	g.db.commit()
	create_event_table(eventname,g)
	if cur.rowcount == 1:
		return 'yes'
	return 'no'
    
''' 
def create_new_event(event,g):
    counter = 0
    while 1:
        eventname = event + "_"+str(random.randint(1,5000))
        cur = g.db.execute('select * from events where event='+"'"+eventname+"'")
        if(len(cur.fetchall())>0):
            counter+=1
            if counter>100:
                return ''
            continue
        else:
            break
        
    g.db.execute('INSERT INTO events (event,status,transid) VALUES(?,?,?)',[eventname,ABORTED,0])
    g.db.commit()
    create_event_table(eventname,g)
    return eventname
'''
def add_user_inevent(event,user,g):
    if(len(user) < 1):
        return 0
    cur = g.db.execute('select * from events where event='+"'"+event+"'")
    if(len(cur.fetchall())>0):
        g.db.execute('INSERT OR REPLACE INTO '+ event +' (participant,vote) VALUES(?,?)',[user,0])
        g.db.commit()
        return 1
    else:
        return 0

def register_vote(event,participant,vote,g):
    cur = g.db.execute('select * from events where event=?',[event])
    if(len(cur.fetchall())>0):
        cur = g.db.execute("update '"+event+"' set vote=? where participant=?",[vote,participant])
        g.db.commit()
        return cur.rowcount
    else: 
        return 0

def isfileuploaded(filename,event,g):
    cur = g.db.execute("select * from images where image='"+filename+"'" +" and event='" +event +"'")
    if(len(cur.fetchall())>0):
        return True
    else:
        return False    
    
def insert_new_image(event,filename,transid,g):
    g.db.execute('INSERT INTO images (event,image,status,transid) VALUES(?,?,?,?)',[event,filename,TEMP,transid])
    g.db.commit()    

def get_event_master(event,g):
	try:
		cur = g.db.execute('select master from events where event=?',[event])
		master = [ row[0] for row in cur.fetchall()]
		return master[0]
	except:
		return 'error' 
	
def get_new_transid(event,g):
	''' check if event is already published '''
	cur = g.db.execute('select status from events where event=?',[event])
	status = [row[0] for row in cur.fetchall()][0]
	if status == PUBLISHED:
		return 0
	''' get current intent '''
	cur = g.db.execute('select tempid from events where event=?',[event])
	tempid = [row[0] for row in cur.fetchall()][0]
	tempid += 1
	cur = g.db.execute('update events set tempid=? where event=?',[tempid,event])
	g.db.commit()
	if cur.rowcount == 1:
		return tempid
	else:
		return 0
		
def confirm_image_in_event(event,transid,g):
	cur = g.db.execute('update images set status=? where event=? and transid=?',[PERMANENT,event,transid])
	g.db.commit()
	return cur.rowcount


def update_images_transid(event,filename,transid,g):
	transid = int(transid)
	cur = g.db.execute('update images set transid=? where event=? and image=?',[transid,event,filename])
	g.db.commit()
	return cur.rowcount

def get_event_pics(eventname,g):
    cur = g.db.execute('select * from images where event=? and status=?',[eventname,PERMANENT])
    list1 = [row[2] for row in cur.fetchall()]
    return list1

def get_published_events(g):
    masterlist = []
    cur = g.db.execute('select event from events where status=2')
    publishedevents = [row[0] for row in cur.fetchall()]
    
    for event in publishedevents:
        cur = g.db.execute('select image from images where event=?',[event])
        imglist = [row[0] for row in cur.fetchall()]
        masterlist.append([event,imglist])
    return masterlist

def start_voting(eventname,transid,g):
	#check if the event is in the voting or aborted phase
	cur = g.db.execute('select * from events where event=? and (status=? or status=?)',[eventname,VOTING,ABORTED])
	if(len(cur.fetchall())>0):
                #nullify all previous votes and set the event status to voting
                g.db.execute('update '+eventname+' set vote=0')
		g.db.execute('update events set status=? where event=?',[VOTING,eventname])
		g.db.commit()
                # increment the transid number and return
                g.db.execute('update events set transid=? where event=?',[transid,eventname])
                g.db.commit()
		# confirm the image status to be permanent
		cur = g.db.execute('update images set status=? where event=? and transid=?',[PERMANENT,eventname,transid])
		g.db.commit()

		return 'success'
	else:
		return 'fail'


def start_voting_old(eventname,g):
	#check if the event is in the voting or aborted phase
	cur = g.db.execute('select * from events where event=? and (status=? or status=?)',[eventname,VOTING,ABORTED])
	if(len(cur.fetchall())>0):
                #nullify all previous votes and set the event status to voting
                g.db.execute('update '+eventname+' set vote=0')
		g.db.execute('update events set status=? where event=?',[VOTING,eventname])
		g.db.commit()
                # increment the transid number and return
                cur = g.db.execute('select transid from events where event=?',[eventname])
                transid = [row[0] for row in cur.fetchall()]
                g.db.execute('update events set transid=? where event=?',[transid[0] + 1,eventname])
                g.db.commit()
		return transid[0]+1
	else:
		return 0

def make_event_status(eventname,transid,g):
	#check if the event is in the voting phase or not
	cur = g.db.execute('select * from events where event=? and status=?',[eventname,VOTING])
	if(len(cur.fetchall())>0):
            ## check if the transid is recent else return ignore
            cur = g.db.execute('select transid from events where event=?',[eventname])
            curTransid = [row[0] for row in cur.fetchall()]
            if transid < curTransid[0]:
                return 'ignore'
            ## if there is anyone who voted no or did not vote then abort else publish
            cur = g.db.execute('select * from '+eventname+' where vote=0 or vote=2')
            if len(cur.fetchall()) > 0:
                #abort event
                #cur = g.db.execute('update events set status=? where event=?',[ABORTED,eventname])
                #g.db.commit()
                return 'aborted'
            else:
                #publish event
		#cur = g.db.execute('update events set status=? where event=?',[PUBLISHED,eventname])
		#g.db.commit()
		return 'published'
    	else:
		return 'closed'

def set_event_status(eventname,transid,status,g):
	cur = g.db.execute('select * from events where event=? and status=?',[eventname,VOTING])
	if(len(cur.fetchall())>0):
		cur = g.db.execute('select transid from events where event=?',[eventname])
            	curTransid = [row[0] for row in cur.fetchall()]
            	if transid < curTransid[0]:
                	return 'ignore'
		elif status == 'aborted':
                	#abort event
                	cur = g.db.execute('update events set status=? where event=?',[ABORTED,eventname])
                	g.db.commit()
			return 'success'
		elif status == 'published':
                	#publish event
                	cur = g.db.execute('update events set status=? where event=?',[PUBLISHED,eventname])
                	g.db.commit()
			return 'success'
	else:
		return 'closed'
			

def user_not_in_event(event,participant,g):
    cur = g.db.execute('select * from '+event+' where participant=?',[participant])
    if(len(cur.fetchall())>0):
        return False
    else:
        return True

def get_event_status(eventname,g):
	cur = g.db.execute('select status from events where event=?',[eventname])
	list1 = [row[0] for row in cur.fetchall()]
	if len(list1) < 1:
		return ''
	ret = list1[0]
        if ret == ABORTED:
            status='aborted'
        elif ret == VOTING:
            status='voting'
        elif ret == PUBLISHED:
            status='published'
        return status

def connect_db(name):
    return sqlite3.connect(name)

def init_db(databasename):
    with closing(connect_db(databasename)) as db:                                                                                   
        create_events_table(db)
        create_image_table(db)



    
