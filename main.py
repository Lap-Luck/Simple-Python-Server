import asyncio
import time
import websocket
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
import secrets
import json
import chess

app = FastAPI()
security = HTTPBearer()

class ServerData:
    def __init__(self):
        self.games = {}
        self.player_next_id=0
        self.players = {}

serverData=ServerData()

@app.post('/register/{name}/{owner}')
async def register(name: str, owner: str):
    id=serverData.player_next_id
    serverData.player_next_id+=1
    serverData.players[id]={"name":name,"owner":str}
    return {'id': str(id)}

@app.post('/token/game/{game_id}/player/{player_id}')
async def get_token(game_id: str, player_id: str):
    token = secrets.token_hex(16)
    if not serverData.games.get(game_id):
        serverData.games[game_id] = {
            'board': chess.Board(),
            'last_move': '',
            'turn': 0,
            'players': [],
            'subscribers': {},
            'player_waiting':{0:False,1:False},
            #TODO TIME
            #'player_time':{0:0.2,1:0.2},
            #'time_stamp':None

        }
    if len(serverData.games[game_id]['players'])<2:
        serverData.games[game_id]['players']+=[{'token': token, 'ws': None, 'id': player_id},]
    else:
        return {}
    return {'token': token}


async def websocket_on_msg(message,game_id:int,white_black_id:int):
    def game_state(game_id: str):
        game=serverData.games[game_id]
        return {
        'last_move':game['last_move'],
        'board':str(game['board']),
        'legal_moves':[str(move) for move in game['board'].legal_moves],
        'halfmove_clock':game['board'].halfmove_clock,
        'can_claim_draw':game['board'].can_claim_draw(),
        'outcome':str(game['board'].outcome()),
        }
    game = serverData.games[game_id]
    ws:WebSocket=game['players'][white_black_id]['ws']
    #print("message",message['type'] ,game['players'][white_black_id]["id"])
    if message['type'] == 'wait':
        game['player_waiting'][white_black_id]=True
    elif message['type'] == 'move and wait':
        def make_move(move):
            board: chess.Board = serverData.games[game_id]['board']
            #print("PUSH",move)
            board.push_uci(move)
            serverData.games[game_id]['turn']=1-serverData.games[game_id]['turn']
            serverData.games[game_id]['player_waiting'][white_black_id] = True
            #print("MOVE:",move," in game= ",game_id)
        #print(white_black_id ,"move",message['move'])
        if white_black_id==serverData.games[game_id]['turn']:
            if message['move'] in [str(move) for move in game['board'].legal_moves]:
                make_move(message['move'])
        else:
            print("error")
            print("cid=",white_black_id)
            print("player with move", game['players'][game['turn']])
            print("/error")
            return

    player_to_wake=serverData.games[game_id]['turn']
    #print(serverData.games[game_id]['player_waiting'])
    if serverData.games[game_id]['player_waiting'][player_to_wake]:
        while len(serverData.games[game_id]['players'])!=2:
            #print("waiting..")
            time.sleep(0.1)
        ws_wake: WebSocket = serverData.games[game_id]['players'][player_to_wake]['ws']
        #print("WAKE:",white_black_id," in game= ",game_id)
        await ws_wake.send_json(game_state(game_id))

@app.websocket('/ws/{game_id}')
async def websocket_endpoint(game_id: str, ws: WebSocket):
    global wait
    #print("accepting...")
    await ws.accept()
    game_players=serverData.games[game_id]['players']
    white_black_id=-1
    while True:
        try:
            token = ws.headers['Authorization']
            for player_id in range(len(game_players)):
                player=game_players[player_id]
                if player['token'] == token:
                    serverData.games[game_id]['players'][player_id]['ws'] = ws
                    white_black_id=player_id
            #print("Hello",white_black_id)
            message = await ws.receive_json()
            await websocket_on_msg(message,game_id,white_black_id)
        except WebSocketDisconnect:
            for player_id in range(len(game_players)):
                player=game_players[player_id]
                if player['ws'] == ws:
                    player['ws'] = None
            break

uvicorn.run(app, host='127.0.0.1', port=8001)


