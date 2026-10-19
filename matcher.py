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


def get_queue_lay(n:int=5) -> list:
    """Lay orders, lowest odds first (display order)."""
    #bets = sorted((e for e in bet_queue_lay), key=lambda b: (-b.odds, b.ts, b.id))
    if n<1:
        return []
    bets = heapq.nsmallest(n, bet_queue_lay)
    return [(b[3].id, b[3].is_back, b[3].odds, b[3].amount) for b in bets]


def get_queue_back(n:int=5) -> list:
    """Back orders, highest odds first (display order)."""
    if n<1:
        return []
    bets = heapq.nsmallest(n, bet_queue_back)
    return [(b[3].id, b[3].is_back, b[3].odds, b[3].amount) for b in bets]


def get_num_matched() -> int:
    return len(matched_bets_queue)


def get_fair_odds() -> float:
    # TODO instead of fair odds put max lay and min back
    if len(bet_queue_back) == 0 or len(bet_queue_lay) == 0:
        return 0
    
    min_back = bet_queue_back[0][3].odds
    max_lay = bet_queue_lay[0][3].odds
    fair_odds = round((min_back + max_lay)/2, 2)
    
    return fair_odds


def _get_odds_liquidity_from_matched(odd):
    odd_liq = 0
    for m in matched_bets_queue:
        if m[3] == odd:
            odd_liq += m[2]
    return odd_liq


def _get_odds_liquidity_from_queue(odd, q):
    odd_liq = 0
    for b in q:
        if b[2] == odd:
            odd_liq += b[3]
    return odd_liq

def _get_highest_liquidity_odd():
    odds_liq = {}
    for m in matched_bets_queue:
        if m[3] not in odds_liq:
            odds_liq[m[3]] = 0
        odds_liq[m[3]] += m[2]
    if len(odds_liq) == 0:
        return None
    best_odd = max(odds_liq.items(), key=lambda x: x[1])[0]
    return best_odd

def _get_alternative_odd():
    if len(bet_queue_lay) >= 1:
        return abs(bet_queue_lay[0][0])
    if len(bet_queue_back) >= 1:
        return abs(bet_queue_back[0][0])
    if len(matched_bets_queue) >= 1:
        if _get_highest_liquidity_odd() is not None:
            return _get_highest_liquidity_odd()
    return 0

def _get_liability(odds, stake):
    return ((odds - 1) * stake)

def get_liquidity_data(span:int=5):
    # ex: fair_odds=2 span=2 odds_range=[1.98,1.99,2,2.01,2.02]
    # ex: liq_per_odd_um=[0, 1, 0, 0.5, 0] liq_per_odd_ma=...
    fair_odds = get_fair_odds()
    if fair_odds == 0:
        fair_odds = _get_alternative_odd()
        if fair_odds == 0:
            return [0], [0], [0], [0]

    odds_range = [round((x/100 + fair_odds), 2) for x in range(-span, span+1)]

    # get the top of the 2 heaps
    bq = get_queue_back(span)
    lq = get_queue_lay(span)
    
    # for each odd in the range get the corresponding liquidity
    liq_per_odd_um_back = [0 for odd in odds_range]
    liq_per_odd_um_lay = [0 for odd in odds_range]

    for i, odd in enumerate(odds_range):
        # get liquidity from either back or lay queue
        if odd <= fair_odds:
            l = _get_odds_liquidity_from_queue(odd, lq)
            # calculate liability for lay bets
            l = _get_liability(odd, l);
            liq_per_odd_um_lay[i] = l
        if odd >= fair_odds:
            l =_get_odds_liquidity_from_queue(odd, bq)
            liq_per_odd_um_back[i] = l

    liq_per_odd_ma = [_get_odds_liquidity_from_matched(o) for o in odds_range]

    norm_term = max(max(liq_per_odd_um_lay), max(liq_per_odd_um_lay), max(liq_per_odd_ma));
    
    if  norm_term != 0:
        # normalize liquidity to [0,1]
        liq_per_odd_um_lay = [l/norm_term for l in liq_per_odd_um_lay]
        liq_per_odd_um_back = [l/norm_term for l in liq_per_odd_um_back]
        liq_per_odd_ma = [l/norm_term for l in liq_per_odd_ma]

    return odds_range, liq_per_odd_um_lay, liq_per_odd_um_back, liq_per_odd_ma


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
            matched_bets_queue.append((bet.id, top.id, qt + _get_liability(top.odds, qt), top.odds))
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
            matched_bets_queue.append((top.id, bet.id, qt + _get_liability(top.odds, qt), top.odds))
            if top.amount <= EPS:
                heapq.heappop(bet_queue_back)

        if bet.amount > EPS:
            heapq.heappush(bet_queue_lay, (-bet.odds, bet.ts, bet.id, bet))

    return amount_matched