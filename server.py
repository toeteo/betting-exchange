import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel
from matcher import get_num_matched, receive_bet, get_queue_lay, get_queue_back, get_fair_odds, get_liquidity_data
from time import time


app = FastAPI()

class BetRequest(BaseModel):
    is_back: bool # True for BACK, False for LAY
    bet_amount: float
    bet_odds: float

@app.get("/")
async def root():
    return FileResponse("index.html")

@app.post("/bet")
def place_bet(bet: BetRequest):
    ts = time()
    amount_matched = receive_bet(ts, bet.is_back, bet.bet_amount, bet.bet_odds)
    return {"amount_matched": amount_matched}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # push an update every second
            await asyncio.sleep(1)
            num_matched = get_num_matched()
            lay_queue = get_queue_lay()
            back_queue = get_queue_back()
            fair_odds = get_fair_odds()
            odds, liquidity = get_liquidity_data()
            payload = {
                "num_matched": num_matched,
                "lay_queue": lay_queue,
                "back_queue": back_queue,
                "fair_odds": fair_odds,
                "odds": odds,
                "liquidity": liquidity
            }
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        print("Client disconnected")