import threading
import time
import random
import requests
import websocket #websocket-client

#time.sleep(delay)
game_id=str(random.randrange(1,1234))


def play(player_id,sever_talker):
    print("Pl" + str(id) + " hello")
    res=sever_talker('{"type":"connect","id":"' + str(player_id) + '"}')
    print(player_id,">",res)
    play_white =sever_talker('{"type":"play_white","id":"' + str(player_id) + '"}')=='True'
    print(player_id," play white", ">", play_white)
    if play_white:
        time.sleep(5)#decision time
        print(player_id,"move")
        move_status = sever_talker('{"type":"move","id":"' + str(player_id) + '"}')
        if move_status == 'success':
            print(player_id,'move ok')
        time.sleep(1)
    else:
        time.sleep(1)
        print(player_id,"wait")
        move_status = sever_talker('{"type":"wait","id":"' + str(player_id) + '"}')
        print(player_id,"Status", move_status)


def start_play(id):
    response = requests.post('http://localhost:8001/games/'+game_id+'/tokens')
    assert response.status_code == 200
    token = response.json()['token']
    ws = websocket.WebSocket()
    ws.connect('ws://localhost:8001/ws/' + game_id, header={'Authorization': token}),
    sever_talker=lambda message:[
            ws.send(message),
            ws.recv()][-1]
    play(id,sever_talker)




# Create new threads
threading.Thread(target=start_play,args=[0]).start()
threading.Thread(target=start_play,args=[1]).start()

