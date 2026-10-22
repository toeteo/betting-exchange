import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from matcher import Market
from time import time

app = FastAPI()

m = Market()

app.mount("/images", StaticFiles(directory="images"), name="images")
app.mount("/js", StaticFiles(directory="js"), name="js")
app.mount("/css", StaticFiles(directory="css"), name="css")

class BetRequest(BaseModel):
    is_back: bool
    bet_amount: int = Field(..., ge=100, description="Minimum stake is 100 (1.00)")
    bet_odds: int = Field(..., gt=100, description="Odds must be strictly greater than 100 (1.00)")

    @field_validator("bet_amount")
    @classmethod
    def validate_amount_tick(cls, v: int) -> int:
        if v % 50 != 0:
            raise ValueError(f"Stake amount {v} must be an increment of 50 (0.50).")
        return v

@app.get("/")
async def root():
    return FileResponse("index.html")

@app.get("/test")
async def test():
    return {"total_liquidity": m.get_total_liquidity()}

@app.post("/bet")
def place_bet(bet: BetRequest):
    ts = time()
    
    amounts_matched = m.receive_bet(ts, bet.is_back, bet.bet_amount, bet.bet_odds)
    
    return {"amounts_matched": amounts_matched}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await asyncio.sleep(0.1)
            num_matched = m.get_num_matched()
            
            max_lay = m.get_queue_lay(1)
            max_lay_val = max_lay[0][2] if len(max_lay) != 0 else 0
            
            min_back = m.get_queue_back(1)
            min_back_val = min_back[0][2] if len(min_back) != 0 else 0
            
            fair_odds_val = m.get_fair_odds()
            
            odds_int, liq_um_lay_int, liq_um_back_int, liq_ma_int = m.get_liquidity_data()
            
            payload = {
                "num_matched": num_matched,
                "max_lay": max_lay_val,
                "min_back": min_back_val,
                "fair_odds": fair_odds_val,
                "odds": odds_int,
                "liq_um_lay": liq_um_lay_int,
                "liq_um_back": liq_um_back_int,
                "liq_ma": liq_ma_int,
            }
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        print("Client disconnected")
