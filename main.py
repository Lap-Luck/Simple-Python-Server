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

# Store the state of the games in a dictionary of dictionaries
games = {}
players = {} #from file

with open("players.json", "r") as fp:
    # load the json data into a dictionary
    players = json.load(fp)

def get_current_game(game_id: str):
    """
    Get the current game based on the game ID.
    """
    game = games.get(game_id)
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Game not found')
    return game

def get_current_player(game_id: str, credentials: str):
    """
    Get the current player based on the token in the authentication header.
    """
    token = credentials
    for player_id, player_info in get_current_game(game_id)['players'].items():
        if player_info['token'] == token:
            return player_id
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token')

async def send_game_state(game_id: str):
    """
    Broadcast the current state of the game to both players.
    """
    try:
        game = get_current_game(game_id)
        send_tasks = []
        for player_id, player_info in game['players'].items():
            ws = player_info['ws']
            if ws:
                print(f'Sending game state to player {player_id}')
                print(ws)
                send_task = asyncio.create_task(ws.send_json({
                    'board': game['board'],
                    'turn': game['turn']
                }))
                send_tasks.append(send_task)
        # Wait for all messages to be sent
        await asyncio.gather(*send_tasks)
        print('All game states sent')
    except Exception as e:
        print(f'An exception occurred: {e}')


@app.post('/games/{game_id}/tokens/{player_id}')
async def get_token(game_id: str, player_id: str):
    """
    Issue a token to the player for the specified game.
    If the game doesn't exist, create a new game.
    """
    registration_status: str
    player = players.get(player_id)

    if player_id == 0:
        registration_status = 'playing as guest'
    elif not player:
        player_id = 0
        registration_status = 'id not found, playing as guest'
    else:
        registration_status = 'playing as ' + player['name']

    game = games.get(game_id)
    if not game:
        game = {
            'board': chess.Board(),
            'last_move':'',
            'turn': 0,
            'players': {
                0: {'token': secrets.token_hex(16), 'ws': None, 'id': player_id},
                1: {'token': None, 'ws': None, 'id' : None}
            },
            'subscribers':{}
        }
        games[game_id] = game
        print("game created: " + game_id)
        return {'token': game['players'][0]['token'], 'status': registration_status}

    elif game['players'][1]['token']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Game is full')

    else:
        token = secrets.token_hex(16)
        game['players'][1]['token'] = token
        game['players'][1]['id'] = player_id
        return {'token': token, 'status': registration_status}


@app.post('/register/{algorithm}/{owner}')
async def register(algorithm: str, owner: str):
    player = {
        'name': algorithm,
        'owner': owner,
        'history' : {}
    }

    '''
    history format: opponent, outcome
    '''
    players['0']['current_id'] += 1
    players[str(players['0']['current_id'])] = player
    with open("players.json", "w") as fp:
        # dump the dictionary to the file
        json.dump(players, fp)

    return {'id': str(players['0']['current_id'])}







wait={}

def encode(board:chess.Board,last_move):
    data={
        'last_move':last_move,
        'board':str(board),
        'legal_moves':[str(move) for move in board.legal_moves],
        'halfmove_clock':board.halfmove_clock,
        'can_claim_draw':board.can_claim_draw(),
        'outcome':str(board.outcome()),
    }
    return json.dumps(data)



@app.websocket('/ws/{game_id}')
async def websocket_endpoint(game_id: str, ws: WebSocket):
    global wait
    print("accepting...")
    await ws.accept()
    while True:
        try:
            # Authenticate the player
            token = ws.headers['Authorization']

            for player_id, player_info in get_current_game(game_id)['players'].items():
                if player_info['token'] == token:
                    get_current_game(game_id)['players'][player_id]['ws'] = ws
                    #await send_game_state(game_id)
                    break
                #else:
                    #raise WebSocketDisconnect()

            message =await ws.receive_json()
            print("recived:",message)
            if message['type'] == 'can_move':
                current_player = get_current_player(game_id, token)
                if current_player == get_current_game(game_id)['turn']:
                    print("$",get_current_game(game_id)['turn'])
                    print("$",current_player)
                    await ws.send_text("True")
                else:
                    print("#$", current_player)
                    await ws.send_text("False")
            if message['type'] == 'board_info':
                current_game=get_current_game(game_id)
                await ws.send_text(encode(current_game['board'],current_game['last_move']))

            if message['type'] == 'move':
                    print("PLAYER:move")
                    # Check if it is the player's turn
                    current_player = get_current_player(game_id, token)
                    print("B1")
                    if current_player != get_current_game(game_id)['turn']:
                        print("B2#")
                        print(get_current_game(game_id)['turn'])
                        print(current_player)
                        #raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Not your turn')
                        await ws.send_text("not your move")
                        continue
                    print("B2")
                    # Update the game state with the move
                    #move = message['move']
                    #get_current_game(game_id)['board'].make_move(move)
                    board=get_current_game(game_id)['board']
                    if not message['move'] in [str(move) for move in board.legal_moves]:
                        print("ERROR illegal move",message['move'])
                        await ws.send_text("fail")
                        continue
                    get_current_game(game_id)['board'].push_uci(message['move'])#make move


                    # Switch to the other player's turn
                    get_current_game(game_id)['turn'] = 1 - get_current_game(game_id)['turn']
                    print("B3")
                    # Broadcast the new state of the game to both players
                    print("Send")
                    await ws.send_text("success")
                    if game_id in wait:
                        for wait_dict in wait[game_id]:
                            if wait_dict["active"]:
                                wait_dict["active"]=False
                                ws2=wait_dict["ws"]
                                print("Trully Send")
                                await ws2.send_text("your move")
                    #await send_game_state(game_id)
            elif message['type'] == 'test':
                await ws.send_text("test_successful")
                print(message['type'])
            elif message['type'] == 'connect':
                print(message['type'])
                await ws.send_text("You are conncted")
            elif message['type'] == 'wait':
                print(message['type'])
                wait[game_id]=wait.get(game_id,[])+[{"ws":ws,"active":True}]
        except WebSocketDisconnect:
            print("error...")
            # Remove the player from the game
            for player_id, player_info in get_current_game(game_id)['players'].items():
                if player_info['ws'] == ws:
                    get_current_game(game_id)['players'][player_id]['ws'] = None
            break

    # Broadcast the new state of the game to both players


@app.websocket('/ws/{game_id}/spectate')
async def websocket_endpoint(game_id: str, ws: WebSocket):
    global wait
    print("accepting...")
    await ws.accept()
    get_current_game(game_id)['subscribers'][str(len(get_current_game(game_id)['subscribers']))] = ws
    while True:
        try:
            await ws.send_json({'board': get_current_game(game_id)['board'], 'turn':get_current_game(game_id)['turn']})
        except WebSocketDisconnect:
                for subscriber in get_current_game(game_id)['subscribers'].items():
                    if subscriber == ws:
                        subscriber = None
                break



uvicorn.run(app, host='127.0.0.1', port=8001)

