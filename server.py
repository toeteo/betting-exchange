from fastapi import FastAPI
from pydantic import BaseModel
from time import time

app = FastAPI()
num_matched = 0

class BetRequest(BaseModel):
    bet_type: bool
    bet_amount: float
    bet_odds: float

@app.get("/")
async def root():
    # num_matched = exchange.get_num_matched()
    return {"num_matched": num_matched}

@app.post("/bet")
def place_bet(bet: BetRequest):
    global num_matched
    num_matched += 1
    ts = time()
    # exchange.receive_bet(ts, bet.bet_type, bet.bet_amount, bet.bet_odds)
    return {"message": "Bet placed", "ts": ts}
