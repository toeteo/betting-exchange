from collections import deque
import heapq
import math

EPS = 1e-9


class Bet:
    def __init__(
        self, bet_id: int, ts: float, is_back: bool, odds: float, amount: float
    ):
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
    """Lay orders, highest odds first (display order)."""
    if n < 1:
        return []
    bets = heapq.nsmallest(n, bet_queue_lay)
    return [(b[3].id, b[3].is_back, b[3].odds, b[3].amount) for b in bets]


def get_queue_back(n: int = 5) -> list:
    """Back orders, lowest odds first (display order)."""
    if n < 1:
        return []
    bets = heapq.nsmallest(n, bet_queue_back)
    return [(b[3].id, b[3].is_back, b[3].odds, b[3].amount) for b in bets]


def get_num_matched() -> int:
    return len(matched_bets_queue)


def get_fair_odds() -> float:
    if len(bet_queue_back) == 0 or len(bet_queue_lay) == 0:
        return 0

    min_back = bet_queue_back[0][3].odds
    max_lay = bet_queue_lay[0][3].odds
    fair_odds = round((min_back + max_lay) / 2, 2)

    return fair_odds


def _get_alternative_odd():
    if len(bet_queue_lay) >= 1:
        return abs(bet_queue_lay[0][0])
    if len(bet_queue_back) >= 1:
        return abs(bet_queue_back[0][0])

    best_odd_ma = max(odds_liq_dict_ma, key=odds_liq_dict_ma.get, default=0)
    return best_odd_ma


def _get_liability(odds, stake):
    return (odds - 1) * stake


def get_liquidity_data(span: int = 5):
    # ex: fair_odds=2 span=2 odds_range=[1.98,1.99,2,2.01,2.02]
    # ex: liq_per_odd_um_lay=[0, 1, 0.5, 0, 0] liq_per_odd_ma=...
    fair_odds = get_fair_odds()
    if fair_odds == 0:
        fair_odds = _get_alternative_odd()  # used for the graph
        if fair_odds == 0:
            return [0], [0], [0], [0]

    odds_range = [round((x / 100 + fair_odds), 2) for x in range(-span, span + 1)]

    # for each odd in the range get the corresponding liquidity
    liq_per_odd_um_back = [odds_liq_dict_back.get(odd, 0) for odd in odds_range]
    liq_per_odd_um_lay = [odds_liq_dict_lay.get(odd, 0) for odd in odds_range]
    liq_per_odd_ma = [odds_liq_dict_ma.get(o, 0) for o in odds_range]

    return odds_range, liq_per_odd_um_lay, liq_per_odd_um_back, liq_per_odd_ma


def receive_bet(ts: float, is_back: bool, amount: float, odds: float) -> float:
    # TODO only accept with a 0.01 step (find a good dynamic step)
    # TODO fix EPS, negatives etc...
    # odds -> round(x, 2) amout -> min: 1 step:0.5
    global next_id

    # boundary checks
    if odds <= 1.0:
        raise ValueError("Odds must be greater than 1.0.")
    if amount < 1.0:
        raise ValueError("Stake amount must be at least 1.0.")

    # odds step: 0.01
    scaled_odds = odds * 100
    if not math.isclose(scaled_odds, round(scaled_odds), abs_tol=EPS):
        raise ValueError(f"Invalid odds {odds}: must adhere to a 0.01 tick size.")
    odds = round(odds, 2)

    # stake step: 0.5
    scaled_amount = amount * 2
    if not math.isclose(scaled_amount, round(scaled_amount), abs_tol=EPS):
        raise ValueError(f"Invalid stake amount {amount}: must be in steps of 0.5.")
    amount = round(amount, 2)

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
            total_amount = qt + _get_liability(top.odds, qt)
            matched_bets_queue.append((bet.id, top.id, total_amount, top.odds))
            odds_liq_dict_ma[top.odds] = (
                odds_liq_dict_ma.get(top.odds, 0) + total_amount
            )
            odds_liq_dict_lay[top.odds] = odds_liq_dict_lay.get(
                top.odds, 0.0
            ) - _get_liability(top.odds, qt)
            if top.amount <= EPS:
                heapq.heappop(bet_queue_lay)

        if bet.amount > EPS:
            odds_liq_dict_back[bet.odds] = (
                odds_liq_dict_back.get(bet.odds, 0) + bet.amount
            )
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
            total_amount = qt + _get_liability(top.odds, qt)
            matched_bets_queue.append((top.id, bet.id, total_amount, top.odds))
            odds_liq_dict_ma[top.odds] = (
                odds_liq_dict_ma.get(top.odds, 0) + total_amount
            )
            odds_liq_dict_back[top.odds] = odds_liq_dict_back.get(top.odds, 0.0) - qt
            if top.amount <= EPS:
                heapq.heappop(bet_queue_back)

        if bet.amount > EPS:
            odds_liq_dict_lay[bet.odds] = odds_liq_dict_lay.get(
                bet.odds, 0
            ) + _get_liability(bet.odds, bet.amount)
            heapq.heappush(bet_queue_lay, (-bet.odds, bet.ts, bet.id, bet))

    return amount_matched
