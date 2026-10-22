from collections import deque
import heapq

# Internal scale factor: 100 (e.g. odds 2.15 -> 215, amount 10.50 -> 1050)

class Bet:
    def __init__(
        self, bet_id: int, ts: float, is_back: bool, odds: int, amount: int
    ):
        self.id = bet_id
        self.ts = ts
        self.is_back = is_back
        self.odds = odds
        self.amount = amount

bet_queue_lay = []
bet_queue_back = []
odds_liq_dict_ma = {}
odds_liq_dict_lay = {}
odds_liq_dict_back = {}
matched_bets_queue = deque()
next_id = 1

def reset():
    global next_id
    bet_queue_lay.clear()
    bet_queue_back.clear()
    matched_bets_queue.clear()
    odds_liq_dict_lay.clear()
    odds_liq_dict_back.clear()
    odds_liq_dict_ma.clear()
    next_id = 1

def get_queue_lay(n: int = 5) -> list:
    if n < 1:
        return []
    bets = heapq.nsmallest(n, bet_queue_lay)
    return [(b[3].id, b[3].is_back, b[3].odds, b[3].amount) for b in bets]

def get_queue_back(n: int = 5) -> list:
    if n < 1:
        return []
    bets = heapq.nsmallest(n, bet_queue_back)
    return [(b[3].id, b[3].is_back, b[3].odds, b[3].amount) for b in bets]

def get_num_matched() -> int:
    return len(matched_bets_queue)

def get_fair_odds() -> int:
    if len(bet_queue_back) == 0 or len(bet_queue_lay) == 0:
        return 0
    min_back = bet_queue_back[0][3].odds
    max_lay = bet_queue_lay[0][3].odds
    return (min_back + max_lay) // 2

def _get_alternative_odd() -> int:
    if len(bet_queue_lay) >= 1:
        return abs(bet_queue_lay[0][0])
    if len(bet_queue_back) >= 1:
        return abs(bet_queue_back[0][0])
    return max(odds_liq_dict_ma, key=odds_liq_dict_ma.get, default=0)

def _get_liability(odds: int, stake: int) -> int:
    # (odds - 1.00) * stake
    return (odds - 100) * stake // 100

def get_liquidity_data(span: int = 5):
    fair_odds = get_fair_odds()
    if fair_odds == 0:
        fair_odds = _get_alternative_odd()
        if fair_odds == 0:
            return [0], [0], [0], [0]

    # Odds range in integer ticks
    odds_range = [fair_odds + x for x in range(-span, span + 1)]

    liq_per_odd_um_back = [odds_liq_dict_back.get(odd, 0) for odd in odds_range]
    liq_per_odd_um_lay = [odds_liq_dict_lay.get(odd, 0) for odd in odds_range]
    liq_per_odd_ma = [odds_liq_dict_ma.get(o, 0) for o in odds_range]

    return odds_range, liq_per_odd_um_lay, liq_per_odd_um_back, liq_per_odd_ma

def receive_bet(ts: float, is_back: bool, amount: int, odds: int) -> int:
    if odds <= 100:
        raise RuntimeError(f"Engine invariant violated: odds must be > 100, received {odds}")
    
    if amount < 100:
        raise RuntimeError(f"Engine invariant violated: amount must be >= 100, received {amount}")

    # Stake step size (step: 0.50 -> 50)
    if amount % 50 != 0:
        raise RuntimeError(f"Engine invariant violated: amount {amount} must be in steps of 50")

    global next_id
    bet = Bet(next_id, ts, is_back, odds, amount)
    next_id += 1
    amount_matched = 0

    if is_back:
        while bet.amount > 0 and bet_queue_lay:
            top = bet_queue_lay[0][3]
            if top.odds < bet.odds:
                break
            qt = min(bet.amount, top.amount)
            bet.amount -= qt
            top.amount -= qt
            amount_matched += qt
            total_amount = qt + _get_liability(top.odds, qt)
            matched_bets_queue.append((bet.id, top.id, total_amount, top.odds))
            odds_liq_dict_ma[top.odds] = odds_liq_dict_ma.get(top.odds, 0) + total_amount
            odds_liq_dict_lay[top.odds] = odds_liq_dict_lay.get(top.odds, 0) - _get_liability(top.odds, qt)
            
            if top.amount <= 0:
                heapq.heappop(bet_queue_lay)

        if bet.amount > 0:
            odds_liq_dict_back[bet.odds] = odds_liq_dict_back.get(bet.odds, 0) + bet.amount
            heapq.heappush(bet_queue_back, (bet.odds, bet.ts, bet.id, bet))

    else:
        while bet.amount > 0 and bet_queue_back:
            top = bet_queue_back[0][3]
            if top.odds > bet.odds:
                break
            qt = min(bet.amount, top.amount)
            bet.amount -= qt
            top.amount -= qt
            amount_matched += qt
            total_amount = qt + _get_liability(top.odds, qt)
            matched_bets_queue.append((top.id, bet.id, total_amount, top.odds))
            odds_liq_dict_ma[top.odds] = odds_liq_dict_ma.get(top.odds, 0) + total_amount
            odds_liq_dict_back[top.odds] = odds_liq_dict_back.get(top.odds, 0) - qt
            
            if top.amount <= 0:
                heapq.heappop(bet_queue_back)

        if bet.amount > 0:
            odds_liq_dict_lay[bet.odds] = odds_liq_dict_lay.get(bet.odds, 0) + _get_liability(bet.odds, bet.amount)
            heapq.heappush(bet_queue_lay, (-bet.odds, bet.ts, bet.id, bet))

    return amount_matched
