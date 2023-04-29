import json
import threading
import time
import random
import requests
import websocket #websocket-client
import json


#time.sleep(delay)
game_id=str(100)#str(random.randrange(1,1234))
names= ['alg1','alg2']

def ai(chess_message):
    board=chess_message["board"]
    legal_moves=chess_message["legal_moves"]
    halfmove_clock=chess_message["halfmove_clock"]
    last_move=chess_message["last_move"]
    print(board)
    print(legal_moves)
    return legal_moves[-1]

def play(player_id,sever_talker):
    print("Pl" + str(id) + " hello")
    res=sever_talker('{"type":"connect","id":"' + str(player_id) + '"}')
    print(player_id,">",res)

    playing=True
    move_num=0
    print("Enter game",player_id)
    while playing:
        while True:
            can_move=sever_talker('{"type":"can_move","id":"' + str(player_id) + '"}')=='True'
            print("can_move",can_move)
            if not can_move:
                sever_talker('{"type":"wait","id":"' + str(player_id) + '"}')
            else:
                break
        if move_num==5:
            break
        json_message=sever_talker('{"type":"board_info","id":"' + str(player_id) + '"}')
        chess_message = {}
        while True:
            try:
                chess_message:dict=json.loads(json_message)
                if "board" in chess_message.keys():
                    break
            except:
                print("$$$$$ERROR$$$$$$$$")
                print(json_message)
                print("$$$$$ERROR$$$$$$$$")
                json_message=sever_talker('{"type":""}')


        if len(chess_message['outcome'])>6:
            print(chess_message['outcome'])
            print("END")
            playing=False
            break
        move:str=ai(chess_message)
        print("MOVE",player_id,move)
        if move_num<20:
            time.sleep(1)#decision time
        move_status = sever_talker(json.dumps({
            "type":"move",
            "id":str(player_id),
            "move":move,
        }))
        if not move_status == 'success':
            assert(False)
        sever_talker('{"type":"wait","id":"' + str(player_id) + '"}')

def start_play(id):
    name=names[id]
    response = requests.post('http://localhost:8001/register/'+name+'/owner1')
    response = requests.post('http://localhost:8001/games/'+game_id+'/tokens/'+str(response.json()['id']))
    assert response.status_code == 200
    token = response.json()['token']
    print(response.json()['status'])
    ws = websocket.WebSocket()
    ws.connect('ws://localhost:8001/ws/' + game_id, header={'Authorization': token}),
    sever_talker=lambda message:[
            print(message),
            ws.send(message),
            ws.recv(),
            print("END",message)][-2]
    play(id,sever_talker)




# Create new threads
threading.Thread(target=start_play,args=[0]).start()
threading.Thread(target=start_play,args=[1]).start()

