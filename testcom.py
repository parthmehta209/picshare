import servcomm

SERVER1 = 'http://localhost:5000/'
SERVER2 = 'http://localhost:5001/'
SERVER3 = 'http://localhost:5002/'

event = 'party_721'
filename = 'images.jpg'
transid = 1

servcomm.send_image_to_servers(event,SERVER2,SERVER3,transid,filename)

