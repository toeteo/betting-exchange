from fastapi import FastAPI
from pydantic import BaseModel
from matcher import get_num_matched, receive_bet, get_queue_lay, get_queue_back
from time import time

app = FastAPI()

class BetRequest(BaseModel):
    is_back: bool # True for BACK, False for LAY
    bet_amount: float
    bet_odds: float

@app.get("/")
async def root():
    num_matched = get_num_matched()
    lay_queue = get_queue_lay()
    back_queue = get_queue_back()
    return {"num_matched": num_matched, "lay_queue": lay_queue, "back_queue": back_queue}

@app.post("/bet")
def place_bet(bet: BetRequest):
    ts = time()
    amount_matched = receive_bet(ts, bet.is_back, bet.bet_amount, bet.bet_odds)
    return {"amount_matched": amount_matched}
