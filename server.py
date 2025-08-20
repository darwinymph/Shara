from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import json
from pathlib import Path
import os

app = FastAPI()

# Statik dosyalar
app.mount("/static", StaticFiles(directory="static"), name="static")

chat_clients = []
signal_clients = []

# Persistent chat history
HISTORY_MAX = 500
DATA_DIR = Path('data')
HISTORY_FILE = DATA_DIR / 'chat_history.json'
chat_history = []

# Ensure data dir exists & load history
DATA_DIR.mkdir(exist_ok=True)
if HISTORY_FILE.exists():
    try:
        chat_history = json.loads(HISTORY_FILE.read_text(encoding='utf-8'))
    except Exception:
        chat_history = []

def save_history():
    try:
        HISTORY_FILE.write_text(json.dumps(chat_history[-HISTORY_MAX:], ensure_ascii=False), encoding='utf-8')
    except Exception:
        pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------
# PAGES
# ------------------------

@app.get("/")
async def get_index():
    """Ana chat sayfası (index.html)"""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/login")
async def get_login():
    """Login sayfası (login.html)"""
    with open("static/login.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/history")
async def get_history():
    # Return latest messages
    return JSONResponse(chat_history[-HISTORY_MAX:])

# ------------------------
# WEBSOCKETS - Chat
# ------------------------

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    chat_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Try to parse JSON and store chat messages
            try:
                payload = json.loads(data)
                if isinstance(payload, dict) and payload.get('type') == 'chat':
                    chat_history.append({
                        'type': 'chat',
                        'from': payload.get('from', 'guest'),
                        'text': payload.get('text', ''),
                        'ts': payload.get('ts')
                    })
                    if len(chat_history) > HISTORY_MAX:
                        del chat_history[0:len(chat_history)-HISTORY_MAX]
                    save_history()
            except Exception:
                pass
            # gönderen dışındaki tüm client'lara ilet
            for client in list(chat_clients):
                if client is not websocket:
                    await client.send_text(data)
    except WebSocketDisconnect:
        if websocket in chat_clients:
            chat_clients.remove(websocket)

# ------------------------
# WEBSOCKETS - WebRTC Signaling
# ------------------------

@app.websocket("/signal")
async def signaling(websocket: WebSocket):
    await websocket.accept()
    signal_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            for client in list(signal_clients):
                if client is not websocket:
                    await client.send_text(data)
    except WebSocketDisconnect:
        if websocket in signal_clients:
            signal_clients.remove(websocket)

# ------------------------
# ENTRYPOINT (local)
# ------------------------

if __name__ == "__main__":
    # server.py dosya adı ile uyumlu
    uvicorn.run("server:app", host="0.0.0.0", port=10000, reload=False)
