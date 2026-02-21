import os
import sys
import json
import time
import threading
import requests
import random
from websocket import WebSocket
from keep_alive import keep_alive

# --- UPDATED CONFIGURATION ---
GUILD_ID = "1474464326051172418"
CHANNEL_ID = "1474495027223855104"
OWNER_ID = "1407866476949536848"

SELF_MUTE = False
SELF_DEAF = False

should_be_in_vc = False 
current_status = "online" 

usertoken = os.getenv("TOKEN")
if not usertoken:
    print("[ERROR] TOKEN not found in environment variables.")
    sys.exit()

headers = {"Authorization": usertoken, "Content-Type": "application/json"}

def stealth_delete(channel_id, message_id):
    # Wait a moment so it looks like a manual delete
    time.sleep(random.uniform(1.5, 3.0))
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}"
    try: 
        requests.delete(url, headers=headers)
    except: 
        pass

def heartbeat_loop(ws, interval):
    while True:
        time.sleep(interval)
        try: 
            ws.send(json.dumps({"op": 1, "d": None}))
        except: 
            break

def joiner(token):
    global should_be_in_vc, current_status
    
    ws = WebSocket()
    ws.connect("wss://gateway.discord.gg/?v=9&encoding=json")

    hello = json.loads(ws.recv())
    heartbeat_interval = hello["d"]["heartbeat_interval"] / 1000

    # 1. Identify
    auth = {
        "op": 2,
        "d": {
            "token": token,
            "properties": {"$os": "windows", "$browser": "chrome", "$device": "pc"},
            "presence": {"status": current_status, "afk": False}
        }
    }
    ws.send(json.dumps(auth))

    # 2. Re-join on startup if the script was previously in 'join' mode
    if should_be_in_vc:
        time.sleep(2) # Vital delay to ensure gateway is ready
        ws.send(json.dumps({
            "op": 4,
            "d": {
                "guild_id": GUILD_ID,
                "channel_id": CHANNEL_ID,
                "self_mute": SELF_MUTE,
                "self_deaf": SELF_DEAF
            }
        }))

    threading.Thread(target=heartbeat_loop, args=(ws, heartbeat_interval), daemon=True).start()

    while True:
        response = ws.recv()
        if not response: 
            break
            
        try:
            event = json.loads(response)
            if event.get("t") == "MESSAGE_CREATE":
                data = event.get("d", {})
                if data.get("author", {}).get("id") == OWNER_ID:
                    content = data.get("content")
                    chan_id = data.get("channel_id")
                    m_id = data.get("id")
                    
                    # --- JOIN COMMAND ---
                    if content == ",j":
                        should_be_in_vc = True
                        current_status = "dnd"
                        
                        # Join VC
                        ws.send(json.dumps({
                            "op": 4,
                            "d": {"guild_id": GUILD_ID, "channel_id": CHANNEL_ID, "self_mute": SELF_MUTE, "self_deaf": SELF_DEAF}
                        }))
                        
                        time.sleep(0.7) # Delay between packets
                        
                        # Change Status
                        ws.send(json.dumps({
                            "op": 3, 
                            "d": {"status": "dnd", "afk": False, "since": 0, "activities": []}
                        }))
                        
                        print("✓ Joined VC & Status set to DnD")
                        threading.Thread(target=stealth_delete, args=(chan_id, m_id)).start()

                    # --- LEAVE COMMAND ---
                    elif content == ",l":
                        should_be_in_vc = False
                        current_status = "online"
                        
                        # Leave VC
                        ws.send(json.dumps({
                            "op": 4,
                            "d": {"guild_id": GUILD_ID, "channel_id": None, "self_mute": SELF_MUTE, "self_deaf": SELF_DEAF}
                        }))
                        
                        time.sleep(0.7) # Delay between packets
                        
                        # Change Status
                        ws.send(json.dumps({
                            "op": 3, 
                            "d": {"status": "online", "afk": False, "since": 0, "activities": []}
                        }))
                        
                        print("✓ Left VC & Status set to Online")
                        threading.Thread(target=stealth_delete, args=(chan_id, m_id)).start()
                        
        except Exception as e:
            print(f"Connection error: {e}")
            break

def run_joiner():
    print(f"Logged in. Use ,j to join and ,l to leave.")
    while True:
        try:
            joiner(usertoken)
        except Exception:
            time.sleep(5)

keep_alive()
run_joiner()
