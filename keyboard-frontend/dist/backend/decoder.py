
from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from starlette.websockets import WebSocketDisconnect
import logging
import asyncio
import time

print("Starting now")

app = FastAPI()

COMMANDS = {
    "Uw": "Q_LEFT",
    "Ue": "Q_RIGHT",
    "Dn": "L_UP",
    "Ds": "L_DOWN",
    "Dw": "L_LEFT",
    "De": "L_RIGHT",
    "DUD": "SELECT",
    "Un": "SPACE",
    "CCW": "BACKSPACE",
    "CW": "AUTOFILL",
}



# Real time connection with watch
connected_clients = set()
class GestureMessage(BaseModel):
    gesture: str


@app.get("/")
def home():
    return {"status": "running"}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    # Real time connection with watch
    connected_clients.add(ws)

    print("connected")

    try:
        while True:
            # for c in practice:
            await ws.receive_text()        

    except WebSocketDisconnect:
        print("WebSocket client disconnected")



@app.post("/gesture")
async def receive_gesture(message: GestureMessage):

    gesture = message.gesture

    command = COMMANDS.get(gesture)

    if not command:
        return {
            "status": "ignored",
            "gesture": gesture
        }

    dead_clients = []

    for ws in connected_clients:

        try:
            await ws.send_json({
                "action": command
            })

        except Exception:
            dead_clients.append(ws)

    # NEW:
    # Remove any disconnected frontends
    for ws in dead_clients:
        connected_clients.remove(ws)

    return {
        "status": "sent",
        "gesture": gesture,
        "command": command,
        "clients": len(connected_clients)
    }

# if __name__ == "__main__":

#     import uvicorn

#     uvicorn.run(app, host="127.0.0.1", port=8000)