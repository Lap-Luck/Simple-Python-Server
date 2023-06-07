import asyncio
import time
import websocket
import threading
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
import secrets
import json
import chess


CONFIG_TIME=60.0
CONFIG_TIME_INC=1.0

app = FastAPI()
security = HTTPBearer()

class ServerData:
    def __init__(self):
        self.games = {}
        self.player_next_id=0
        self.players = {}

serverData=ServerData()

@app.get('/register/{name}/{owner}')
@app.post('/register/{name}/{owner}')
@app.get('/register/{name}/{owner}/{mode}')
@app.post('/register/{name}/{owner}/{mode}')
async def register(name: str, owner: str,mode="full_data"):
    if not mode in ["move_only","full_data"]:
        mode="full_data"
    print("NEW PL",name,mode)
    id=serverData.player_next_id
    serverData.player_next_id+=1
    serverData.players[id]={"name":name,"owner":owner,'mode':mode}
    return {'id': str(id)}

@app.get('/token/game/{game_id}/player/{player_id}')
@app.post('/token/game/{game_id}/player/{player_id}')
async def get_token(game_id: str, player_id: str):
    token = secrets.token_hex(16)
    if not serverData.games.get(game_id):
        serverData.games[game_id] = {
            'Lock':asyncio.Lock(),
            'board': chess.Board(),
            'last_move': '',
            'turn': 0,
            'players': [],
            'subscribers': {},
            'player_waiting':{0:False,1:False},
            'player_time':{0:CONFIG_TIME,1:CONFIG_TIME},
            'time_stamp':None,
            'time_out':False,
            'time_winner':'white'

        }
    if len(serverData.games[game_id]['players'])<2:
        serverData.games[game_id]['players']+=[{'token': token, 'ws': None, 'id': int(player_id),
                                                'mode':serverData.players[int(player_id)]['mode']},]

    else:
        return {}
    return {'token': token}


async def websocket_on_msg(message,game_id:int,white_black_id:int):
    def game_state(game_id: str,mode):
        game=serverData.games[game_id]
        if mode=="move_only":
            return {
            'last_move':game['last_move'],
            'outcome':str(game['board'].outcome()) if not game['time_out'] else "Outcome(termination=TIMEOUT)",
            }
        return {
        'last_move':game['last_move'],
        'board':str(game['board']),
        'legal_moves':[str(move) for move in game['board'].legal_moves],
        'halfmove_clock':game['board'].halfmove_clock,
        'can_claim_draw':game['board'].can_claim_draw(),
        'outcome':str(game['board'].outcome()) if not game['time_out'] else "Outcome(termination=TIMEOUT)",
        }
    game = serverData.games[game_id]
    ws:WebSocket=game['players'][white_black_id]['ws']
    #print("message",message['type'] ,game['players'][white_black_id]["id"])
    if message['type'] == 'wait':
        game['player_waiting'][white_black_id]=True
    elif message['type'] == 'move and wait':
        def make_move(move):
            if not game['time_stamp']:
                game['time_stamp']=time.time()
            if not game['time_out']:
                old_time=game['time_stamp']
                new_time=time.time()
                game['time_stamp']=new_time
                tiime_passed=new_time-old_time
                game['player_time'][white_black_id]-=tiime_passed-CONFIG_TIME_INC
                print("\t",game_id,"INFO: time",game['player_time'][white_black_id])
                if game['player_time'][white_black_id]<0.0:
                    print("TIME_OUT",game_id,"player",game['players'][white_black_id])
                    game['time_out']=True
                    winner_id=game['players'][1-white_black_id]['id']
                    winner=serverData.players[winner_id]
                    print(winner)
                    print("RESULT Game",game_id,"wins",winner['name'],"by",winner['owner'])

                board: chess.Board = game['board']
                print("\t",game_id,"PUSH",move)
                board.push_uci(move)
                game["last_move"]=move
                game['turn']=1-game['turn']
                #
                print("WTF",game['player_waiting'])
                game['player_waiting'][white_black_id] = True
            else:
                print("game already timeout")



            #print("MOVE:",move," in game= ",game_id)
        #print(white_black_id ,"move",message['move'])
        if white_black_id==serverData.games[game_id]['turn']:
            if message['move'] in [str(move) for move in game['board'].legal_moves]:
                make_move(message['move'])
        else:
            print("error")
            print("cid=",white_black_id)
            print("correct id=",serverData.games[game_id]['turn'])
            print("player with move", game['players'][game['turn']]['id'])
            print("/error")
            return

    player_to_wake=serverData.games[game_id]['turn']
    #print(serverData.games[game_id]['player_waiting'])
    if serverData.games[game_id]['player_waiting'][player_to_wake]:
        while len(serverData.games[game_id]['players'])!=2:
            print("waiting..")
            time.sleep(0.1)
        ws_wake: WebSocket = serverData.games[game_id]['players'][player_to_wake]['ws']
        print(player_to_wake,"WAKE:",player_to_wake," in game= ",game_id)
        serverData.games[game_id]['player_waiting'][player_to_wake]=False#new
        mode=serverData.games[game_id]['players'][player_to_wake]['mode']
        await ws_wake.send_json(game_state(game_id,mode))

@app.websocket('/ws/{game_id}')
async def websocket_endpoint(game_id: str, ws: WebSocket):
    global wait
    print("accepting...")
    await ws.accept()
    game_players=serverData.games[game_id]['players']
    white_black_id=-1

    #print("_Au__")
    token = ""
    if 'Authorization' in ws.headers:
        token = ws.headers['Authorization']
    else:
        #print("_Aw__")
        try:
            json_token_text = await ws.receive_text()
            print("XXX",json_token_text)
            json_token=json.loads(json_token_text)
            token=json_token["token"]
            print("XXX=", token)
        except WebSocketDisconnect:
            print("WebSocketDisconnect!!!!!!!!!!!!!!!!!")
            return
    #print("_Ao__", token)



    while True:
        try:

            for player_id in range(len(game_players)):
                player=game_players[player_id]
                if player['token'] == token:
                    serverData.games[game_id]['players'][player_id]['ws'] = ws
                    white_black_id=player_id
            #print("Hello",white_black_id)
            message = await ws.receive_json()
            print(white_black_id,message)

            await serverData.games[game_id]['Lock'].acquire()
            await websocket_on_msg(message,game_id,white_black_id)
            serverData.games[game_id]['Lock'].release()




        except WebSocketDisconnect:
            for player_id in range(len(game_players)):
                player=game_players[player_id]
                if player['ws'] == ws:
                    player['ws'] = None
            break

uvicorn.run(app, host='127.0.0.1', port=8001)


