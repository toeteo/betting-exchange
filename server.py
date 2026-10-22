import asyncio
import json
import math
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from matcher import (
    get_num_matched,
    receive_bet,
    get_queue_lay,
    get_queue_back,
    get_fair_odds,
    get_liquidity_data,
)
from time import time


app = FastAPI()

app.mount("/images", StaticFiles(directory="images"), name="images")
app.mount("/js", StaticFiles(directory="js"), name="js")
app.mount("/css", StaticFiles(directory="css"), name="css")

EPS = 1e-9


class BetRequest(BaseModel):
    is_back: bool  # True for BACK, False for LAY
    bet_amount: float = Field(..., ge=1.0, description="Minimum stake is 1.0")
    bet_odds: float = Field(
        ..., gt=1.0, description="Odds must be strictly greater than 1.0"
    )

    @field_validator("bet_odds")
    @classmethod
    def validate_odds_tick(cls, v: float) -> float:
        scaled = v * 100
        if not math.isclose(scaled, round(scaled), abs_tol=EPS):
            raise ValueError(f"Odds {v} does not conform to a 0.01 tick size.")
        return round(v, 2)

    @field_validator("bet_amount")
    @classmethod
    def validate_amount_tick(cls, v: float) -> float:
        scaled = v * 2
        if not math.isclose(scaled, round(scaled), abs_tol=EPS):
            raise ValueError(
                f"Stake amount {v} must be an increment of 0.50 (e.g., 1.0, 1.5, 2.0)."
            )
        return round(v, 2)


@app.get("/")
async def root():
    return FileResponse("index.html")


@app.post("/bet")
def place_bet(bet: BetRequest):
    ts = time()
    # The payload is guaranteed valid at this stage by Pydantic
    amount_matched = receive_bet(ts, bet.is_back, bet.bet_amount, bet.bet_odds)
    return {"amount_matched": amount_matched}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # push an update every second
            await asyncio.sleep(0.1)
            num_matched = get_num_matched()
            max_lay = get_queue_lay(1)
            max_lay = max_lay[0][2] if len(max_lay) != 0 else 0
            min_back = get_queue_back(1)
            min_back = min_back[0][2] if len(min_back) != 0 else 0
            fair_odds = get_fair_odds()
            odds, liq_um_lay, liq_um_back, liq_ma = get_liquidity_data()
            payload = {
                "num_matched": num_matched,
                "max_lay": max_lay,
                "min_back": min_back,
                "fair_odds": fair_odds,
                "odds": odds,
                "liq_um_lay": liq_um_lay,
                "liq_um_back": liq_um_back,
                "liq_ma": liq_ma,
            }
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        print("Client disconnected")