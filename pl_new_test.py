import threading
import time
import random
import requests
import websocket #websocket-client

#time.sleep(delay)
game_id=str(random.randrange(1,1234))
def play(id):
    response = requests.post('http://localhost:8001/games/'+game_id+'/tokens')
    assert response.status_code == 200
    token = response.json()['token']
    print("Pl"+str(id)+" hello")
    ws=websocket.WebSocket()
    ws.connect( 'ws://localhost:8001/ws/' + game_id, header={'Authorization': token})
    print("Pl"+str(id)+" conn")
    time.sleep(2+id)
    print("Pl" + str(id) + " send")
    ws.send('{"type":"connect","id":"' + str(id) + '"}')
    t=ws.recv()
    print(t)
    time.sleep(2)
    #just new connect !!!
    ws.connect('ws://localhost:8001/ws/' + game_id, header={'Authorization': token})
    time.sleep(2)
    if id==0:
        ws.send('{"type":"move","id":"' + str(id) + '"}')
        move_status = ws.recv()
        print("Status",move_status)
    else:
        ws.send('{"type":"joke","id":"' + str(id) + '"}')
        move_status = ws.recv()
        print("Status",move_status)
    time.sleep(2)


# Create new threads
threading.Thread(target=play,args=[0]).start()
threading.Thread(target=play,args=[1]).start()

