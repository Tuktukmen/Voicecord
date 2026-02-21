import os
import sys
import json
import time
import threading
import requests
from websocket import WebSocket
from keep_alive import keep_alive

status = "online"  # online / dnd / idle

GUILD_ID = "1474464326051172418"
CHANNEL_ID = "1474495027223855104"
OWNER_ID = "1407866476949536848"  # Only this user can trigger the commands

SELF_MUTE = False
SELF_DEAF = False

# Set to False initially. It will NOT join VC until you type ,j in chat.
should_be_in_vc = False 

usertoken = os.getenv("TOKEN")
if not usertoken:
    print("[ERROR] TOKEN not found in environment variables.")
    sys.exit()

headers = {
    "Authorization": usertoken,
    "Content-Type": "application/json"
}

validate = requests.get(
    "https://canary.discordapp.com/api/v9/users/@me",
    headers=headers
)

if validate.status_code != 200:
    print("[ERROR] Invalid token.")
    sys.exit()

userinfo = validate.json()
username = userinfo["username"]
discriminator = userinfo["discriminator"]
userid = userinfo["id"]

def heartbeat_loop(ws, interval):
    while True:
        time.sleep(interval)
        try:
            ws.send(json.dumps({"op": 1, "d": None}))
        except:
            break

def joiner(token, status):
    global should_be_in_vc
    
    ws = WebSocket()
    ws.connect("wss://gateway.discord.gg/?v=9&encoding=json")

    hello = json.loads(ws.recv())
    heartbeat_interval = hello["d"]["heartbeat_interval"] / 1000

    auth = {
        "op": 2,
        "d": {
            "token": token,
            "properties": {
                "$os": "windows",
                "$browser": "chrome",
                "$device": "pc"
            },
            "presence": {
                "status": status,
                "afk": False
            }
        }
    }

    # Base VC Payload
    vc_payload = {
        "op": 4,
        "d": {
            "guild_id": GUILD_ID,
            "channel_id": CHANNEL_ID,
            "self_mute": SELF_MUTE,
            "self_deaf": SELF_DEAF
        }
    }

    ws.send(json.dumps(auth))
    
    # It checks the variable here. If you haven't typed ,j yet, it skips joining.
    if should_be_in_vc:
        ws.send(json.dumps(vc_payload))

    threading.Thread(
        target=heartbeat_loop,
        args=(ws, heartbeat_interval),
        daemon=True
    ).start()

    while True:
        response = ws.recv()
        if not response:
            break
            
        try:
            event = json.loads(response)
            
            # This is where it listens to your chat messages to trigger the command
            if event.get("t") == "MESSAGE_CREATE":
                msg_data = event.get("d", {})
                author_id = msg_data.get("author", {}).get("id")
                content = msg_data.get("content")
                
                # Verifies it's actually YOU typing the command
                if author_id == OWNER_ID:
                    
                    # The LEAVE command
                    if content == ",l":
                        print("Leave command received. Leaving VC.")
                        should_be_in_vc = False
                        
                        leave_payload = vc_payload.copy()
                        leave_payload["d"]["channel_id"] = None
                        ws.send(json.dumps(leave_payload))
                        
                    # The JOIN command
                    elif content == ",j":
                        print("Join command received. Joining VC.")
                        should_be_in_vc = True
                        
                        join_payload = vc_payload.copy()
                        join_payload["d"]["channel_id"] = CHANNEL_ID
                        ws.send(json.dumps(join_payload))
                        
        except json.JSONDecodeError:
            pass

def run_joiner():
    print(f"Logged in as {username}#{discriminator} ({userid})")
    print("Listening for commands. Type ',j' in any chat to join the VC.")
    while True:
        try:
            joiner(usertoken, status)
        except Exception as e:
            print("Disconnected, reconnecting...", e)
            time.sleep(5)

keep_alive()
run_joiner()
