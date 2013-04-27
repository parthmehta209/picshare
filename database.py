#    cur = g.db.execute('select title, text from entries order by id desc')
#    entries = [dict(title=row[0], text=row[1]) for row in cur.fetchall()]
import sqlite3
import random
from contextlib import closing

ABORTED = 0
VOTING = 1
PUBLISHED = 2
INTENDED = 3



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
                    published integer,\
                    timer integer,\
					master text)"
                    )
    db.commit() 

'''This is a table that stores all images with the server'''
def create_image_table(db):
    db.execute("CREATE TABLE IF NOT EXISTS images \
                    (id integer primary key autoincrement,\
                    event text,\
                    image text)"
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
    g.db.execute('INSERT INTO events (event,published,timer,master) VALUES(?,?,?,?)',[eventname,INTENDED,0,master])
    g.db.commit()
    return eventname
    
''' insert half baked event if acceptabe else return fasle'''    
def is_event_acceptable(eventname,master,g):    
    cur = g.db.execute('select * from events where event='+"'"+eventname+"'")
    if(len(cur.fetchall())>0):
        return 'no'
    else:
        g.db.execute('INSERT INTO events (event,published,timer,master) VALUES(?,?,?,?)',[eventname,INTENDED,0,master])
        g.db.commit()
        return 'yes'

''' finalize create'''
def create_new_event(eventname,g):
	cur = g.db.execute('update events set published=? where event=?',[ABORTED,eventname])
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
        
    g.db.execute('INSERT INTO events (event,published,timer) VALUES(?,?,?)',[eventname,ABORTED,0])
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
    
def insert_new_image(event,filename,g):
    g.db.execute('INSERT INTO images (event,image) VALUES(?,?)',[event,filename])
    g.db.commit()    

def get_event_pics(eventname,g):
    cur = g.db.execute('select * from images where event=?',[eventname])
    list1 = [row[2] for row in cur.fetchall()]
    return list1

def get_published_events(g):
    masterlist = []
    cur = g.db.execute('select event from events where published=2')
    publishedevents = [row[0] for row in cur.fetchall()]
    
    for event in publishedevents:
        cur = g.db.execute('select image from images where event=?',[event])
        imglist = [row[0] for row in cur.fetchall()]
        masterlist.append([event,imglist])
    return masterlist

def start_voting(eventname,g):
	#check if the event is in the voting or aborted phase
	cur = g.db.execute('select * from events where event=? and (published=? or published=?)',[eventname,VOTING,ABORTED])
	if(len(cur.fetchall())>0):
                #nullify all previous votes and set the event status to voting
                g.db.execute('update '+eventname+' set vote=0')
		g.db.execute('update events set published=? where event=?',[VOTING,eventname])
		g.db.commit()
                # increment the timer number and return
                cur = g.db.execute('select timer from events where event=?',[eventname])
                timer = [row[0] for row in cur.fetchall()]
                g.db.execute('update events set timer=? where event=?',[timer[0] + 1,eventname])
                g.db.commit()
		return timer[0]+1
	else:
		return 0

def make_event_status(eventname,timer,g):
	#check if the event is in the voting phase or not
	cur = g.db.execute('select * from events where event=? and published=?',[eventname,VOTING])
	if(len(cur.fetchall())>0):
            ## check if the timer is recent else return ignore
            cur = g.db.execute('select timer from events where event=?',[eventname])
            curTimer = [row[0] for row in cur.fetchall()]
            if timer < curTimer[0]:
                return 'ignore'
            ## if there is anyone who voted no or did not vote then abort else publish
            cur = g.db.execute('select * from '+eventname+' where vote=0 or vote=2')
            if len(cur.fetchall()) > 0:
                #abort event
                cur = g.db.execute('update events set published=? where event=?',[ABORTED,eventname])
                g.db.commit()
                return 'aborted'
            else:
                #publish event
		cur = g.db.execute('update events set published=? where event=?',[PUBLISHED,eventname])
		g.db.commit()
		return 'published'
    	else:
		return 'ignore'


def user_not_in_event(event,participant,g):
    cur = g.db.execute('select * from '+event+' where participant=?',[participant])
    if(len(cur.fetchall())>0):
        return False
    else:
        return True

def get_event_status(eventname,g):
	cur = g.db.execute('select published from events where event=?',[eventname])
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



    
