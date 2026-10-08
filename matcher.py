from collections import deque
import heapq

EPS = 1e-9


class Bet:
    def __init__(self, bet_id: int, ts: float, is_back: bool, odds: float, amount: float):
        self.id = bet_id
        self.ts = ts
        self.is_back = is_back
        self.odds = odds
        self.amount = amount


# Heaps are ordered by MATCHING priority (best counterparty for an incoming order first):
# bet_queue_lay:  (-odds, ts, id, bet) -> highest Lay odds on top (best for an incoming Back)
# bet_queue_back: ( odds, ts, id, bet) -> lowest  Back odds on top (best for an incoming Lay)
bet_queue_lay = []
bet_queue_back = []
matched_bets_queue = deque()
next_id = 1


def reset():
    global next_id
    bet_queue_lay.clear()
    bet_queue_back.clear()
    matched_bets_queue.clear()
    next_id = 1


def get_queue_lay() -> list:
    """Lay orders, lowest odds first (display order)."""
    #bets = sorted((e[3] for e in bet_queue_lay), key=lambda b: (-b.odds, b.ts, b.id))
    smallest = heapq.nsmallest(5, bet_queue_lay)
    return [(b[3].id, b[3].is_back, b[3].odds, b[3].amount) for b in smallest]


def get_queue_back() -> list:
    """Back orders, highest odds first (display order)."""
    #bets = sorted((e[3] for e in bet_queue_back), key=lambda b: (-b.odds, b.ts, b.id))
    smallest = heapq.nsmallest(5, bet_queue_back)
    return [(b[3].id, b[3].is_back, b[3].odds, b[3].amount) for b in smallest]


def get_num_matched() -> int:
    return len(matched_bets_queue)


def get_fair_odds() -> float:
    if len(bet_queue_back) == 0 or len(bet_queue_lay) == 0:
        return 0
    
    min_back = bet_queue_back[0][3].odds
    max_lay = bet_queue_lay[0][3].odds
    fair_odds = round((min_back + max_lay)/2, 2)
    
    return fair_odds

def _get_odds_liquidity(odd, q):
    for b in q:
        if b[2] == odd:
            return b[3]
    return 0

def get_liquidity_data():
    fair_odds = get_fair_odds()
    odds = [round((x/100 + fair_odds), 2) for x in range(-5, 6)]
    
    bq = get_queue_back()
    lq = get_queue_lay()

    liquidity = []

    for odd in odds:
        l = _get_odds_liquidity(odd, lq) if odd <= fair_odds else _get_odds_liquidity(odd, bq)
        liquidity.append(l)

    liquidity = [l/max(liquidity) if max(liquidity) != 0 else 0 for l in liquidity]

    return odds, liquidity

def receive_bet(ts: float, is_back: bool, amount: float, odds: float) -> float:
    global next_id
    if amount <= 0 or odds <= 1:
        raise ValueError("amount must be > 0 and odds must be > 1")

    bet = Bet(next_id, ts, is_back, odds, amount)
    next_id += 1
    amount_matched = 0.0

    if is_back:
        # Back wants odds >= bet.odds; match while best Lay odds L >= B
        while bet.amount > EPS and bet_queue_lay:
            top = bet_queue_lay[0][3]
            if top.odds < bet.odds:
                break
            qt = min(bet.amount, top.amount)
            bet.amount -= qt
            top.amount -= qt
            amount_matched += qt
            matched_bets_queue.append((bet.id, top.id, qt, top.odds))
            if top.amount <= EPS:
                heapq.heappop(bet_queue_lay)

        if bet.amount > EPS:
            heapq.heappush(bet_queue_back, (bet.odds, bet.ts, bet.id, bet))

    else:
        # Lay accepts odds <= bet.odds; match while lowest Back odds B <= L
        while bet.amount > EPS and bet_queue_back:
            top = bet_queue_back[0][3]
            if top.odds > bet.odds:
                break
            qt = min(bet.amount, top.amount)
            bet.amount -= qt
            top.amount -= qt
            amount_matched += qt
            matched_bets_queue.append((top.id, bet.id, qt, top.odds))
            if top.amount <= EPS:
                heapq.heappop(bet_queue_back)

        if bet.amount > EPS:
            heapq.heappush(bet_queue_lay, (-bet.odds, bet.ts, bet.id, bet))

    return amount_matched