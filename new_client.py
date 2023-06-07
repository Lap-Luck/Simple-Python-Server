import json
import threading
import time
import random
import requests
import websocket #websocket-client
import json
import chess

CONFIG_MOVE_OLNY=True

#time.sleep(delay)
game_id=str(random.randrange(1,1234))
names= ['alg1','alg2']
full_print=True
def ai(gameState):
    board=gameState["board"]
    legal_moves=gameState["legal_moves"]
    halfmove_clock=gameState["halfmove_clock"]
    last_move=gameState["last_move"]
    #print(board)
    if full_print: print(legal_moves)
    return legal_moves[-1]

def ai2(board:chess.Board):
    legal_moves=[str(m) for m in board.legal_moves]
    return legal_moves[-1]

def play(player_id,sever_talker):
    if not CONFIG_MOVE_OLNY:
        if full_print: print("Pl" + str(player_id) + " hello")
        playing=True
        gameState=sever_talker({"type":"wait"})
        if full_print: print("GET", str(player_id),gameState)

        while playing:
            if len(gameState["legal_moves"])==0:
                print("end outcome", gameState['outcome'])
                break
            if len(gameState['outcome'])>5:
                print("outcome",gameState['outcome'])
                break
            move=ai(gameState)
            #print(move)
            gameState = sever_talker({"type": "move and wait","move":move})
            time.sleep(0.1)
    else:
        if full_print: print("Pl" + str(player_id) + " hello")
        playing=True
        board=chess.Board()
        gameState=sever_talker({"type":"wait"})
        move=gameState["last_move"]
        print(str(player_id), "recivied", gameState)
        print(str(player_id),"recivied",move)
        while playing:
            if move!="":
                board.push_uci(move)
            if len([str(m) for m in board.legal_moves])==0:
                print("end outcome", gameState['outcome'])
                break
            if len(gameState['outcome'])>5:
                print("outcome",gameState['outcome'])
                break
            move=ai2(board)
            board.push_uci(move)
            if board.outcome():
                print(board.result())
                playing=False
            #print(move)
            gameState = sever_talker({"type": "move and wait","move":move})
            move = gameState["last_move"]
            time.sleep(0.1)
def start_play(id):
    name=names[id]
    response = requests.post('http://localhost:8001/register/'+name+'/owner1/'+('move_only' if CONFIG_MOVE_OLNY else ''))
    #print("my_id=",response.json()['id'])
    response = requests.post('http://localhost:8001/token/game/'+game_id+'/player/'+str(response.json()['id']) )
    assert response.status_code == 200
    #print(response.json())
    token = response.json()['token']
    ws = websocket.WebSocket()
    ws.connect('ws://localhost:8001/ws/' + game_id, header={'Authorization': token}),
    sever_talker=lambda message:[
            full_print and print(message),
            ws.send(json.dumps(message)),
            json.loads(ws.recv()),
            full_print and print("END",message)][-2]
    play(id,sever_talker)


# Create new threads
threading.Thread(target=start_play,args=[0]).start()
threading.Thread(target=start_play,args=[1]).start()

