from collections import deque
import heapq


class Bet:
    def __init__(self, bet_id: int, ts: int, is_back: bool, odds: float, amount: float):
        self.id = bet_id
        self.ts = ts
        self.is_back = is_back
        self.odds = odds
        self.amount = amount


bet_queue_lay = []    # (-odds, id, bet) -> in cima la LAY con quota PIÙ ALTA (minheap)
bet_queue_back = []   # (odds, id, bet)  -> in cima la BACK con quota PIÙ BASSA
matched_bets_queue = deque()   # (back_id, lay_id, importo, quota)
next_id = 0


def receive_bet(ts, is_back, amount, odds) -> float:
    global next_id
    next_id += 1
    bet = Bet(next_id, ts, is_back, odds, amount)
    amount_matched = 0.0

    if is_back:   # BACK in arrivo -> cerco nella coda LAY
        while bet.amount > 0 and bet_queue_lay:
            top = bet_queue_lay[0][2]   # LAY con la quota più alta
            if bet.odds > top.odds:     # quota non compatibile
                break

            qt = min(bet.amount, top.amount)
            bet.amount -= qt
            top.amount -= qt
            amount_matched += qt
            matched_bets_queue.append((bet.id, top.id, qt, top.odds))

            if top.amount <= 0:
                heapq.heappop(bet_queue_lay)

        if bet.amount > 0:
            heapq.heappush(bet_queue_back, (bet.odds, bet.id, bet))

    else:         # LAY in arrivo -> cerco nella coda BACK
        while bet.amount > 0 and bet_queue_back:
            top = bet_queue_back[0][2]  # BACK con la quota più bassa
            if top.odds > bet.odds:     # quota non compatibile
                break

            qt = min(bet.amount, top.amount)
            bet.amount -= qt
            top.amount -= qt
            amount_matched += qt
            matched_bets_queue.append((top.id, bet.id, qt, top.odds))

            if top.amount <= 0:
                heapq.heappop(bet_queue_back)

        if bet.amount > 0:
            heapq.heappush(bet_queue_lay, (-bet.odds, bet.id, bet))

    return amount_matched