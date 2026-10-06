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
    biggest = heapq.nlargest(5, bet_queue_back)
    return [(b[3].id, b[3].is_back, b[3].odds, b[3].amount) for b in biggest]


def get_num_matched() -> int:
    return len(matched_bets_queue)


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