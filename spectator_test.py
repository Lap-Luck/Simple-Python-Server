import threading
import time
import random
import requests
import websocket  # websocket-client

# time.sleep(delay)
game_id = str(100)

def start_spectate(id):
    ws = websocket.WebSocket()
    ws.connect('ws://localhost:8001/ws/' + game_id + '/spectate', header=None),

    while True:
        print("spectator" +str(id)+" "+ws.recv())
        time.sleep(10)


# Create new threads
threading.Thread(target=start_spectate, args=[0]).start()
threading.Thread(target=start_spectate, args=[1]).start()
