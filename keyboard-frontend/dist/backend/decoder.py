
from fastapi import FastAPI, WebSocket
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

@app.get("/")
def home():
    return {"status": "running"}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    print("connected")

    try:
        while True:
            # for c in practice:
            c = input("Enter a command (Uw, Ue, Dn, Ds, Dw, De, DUD, Un, CCW, CW): ")
        
            command = COMMANDS.get(c)

            if command:
                await ws.send_json({"action": command})

            await asyncio.sleep(2)

    except WebSocketDisconnect:
        print("WebSocket client disconnected")


# if __name__ == "__main__":

#     import uvicorn

#     uvicorn.run(app, host="127.0.0.1", port=8000)