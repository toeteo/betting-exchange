from collections import deque
import heapq

def get_queue_lay() -> list:
    return [(bet.id, bet.odds, bet.amount) for _, _, bet in bet_queue_lay]

def get_queue_back() -> list:
    return [(bet.id, bet.odds, bet.amount) for _, _, bet in bet_queue_back]

def get_num_matched() -> int:
    return len(matched_bets_queue)


class Bet:
    def __init__(self, bet_id: int, ts: int, is_back: bool, odds: float, amount: float):
        self.id = bet_id
        self.ts = ts
        self.is_back = is_back
        self.odds = odds
        self.amount = amount


bet_queue_lay = []    # (odds, id, bet) -> in cima la LAY con quota PIÙ BASSA (minheap)
bet_queue_back = []   # (-odds, id, bet)  -> in cima la BACK con quota PIÙ ALTA
matched_bets_queue = deque()   # (back_id, lay_id, importo, quota)
next_id = 0


def receive_bet(ts: float, is_back: bool, amount: float, odds: float) -> float:
    global next_id
    bet = Bet(next_id, ts, is_back, odds, amount)
    next_id += 1
    amount_matched = 0.0

    if is_back:
        # BACK wants the lowest available lay price (lowest ask)
        while bet.amount > 0 and bet_queue_lay:
            top = bet_queue_lay[0][2]
            # If the lowest Lay price in the book is higher than what Backer accepts: stop
            if top.odds > bet.odds:
                break

            qt = min(bet.amount, top.amount)
            bet.amount -= qt
            top.amount -= qt
            amount_matched += qt
            # Execution price is the resting order's odds (price improvement for Backer)
            matched_bets_queue.append((bet.id, top.id, qt, top.odds))

            if top.amount <= 0:
                heapq.heappop(bet_queue_lay)

        # Unmatched Back bet joins book: sorted highest odds first
        if bet.amount > 0:
            heapq.heappush(bet_queue_back, (-bet.odds, bet.id, bet))

    else:
        # LAY wants the highest available back price (best payout terms)
        while bet.amount > 0 and bet_queue_back:
            top = bet_queue_back[0][2]
            # If the best Back price is lower than the minimum odds Layer accepts: stop
            if top.odds < bet.odds:
                break

            qt = min(bet.amount, top.amount)
            bet.amount -= qt
            top.amount -= qt
            amount_matched += qt
            # Execution price is the resting order's odds
            matched_bets_queue.append((top.id, bet.id, qt, top.odds))

            if top.amount <= 0:
                heapq.heappop(bet_queue_back)

        # Unmatched Lay bet joins book: sorted lowest odds first
        if bet.amount > 0:
            heapq.heappush(bet_queue_lay, (bet.odds, bet.id, bet))

    return amount_matched

    