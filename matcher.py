from collections import deque
import heapq
from dataclasses import dataclass

# TODO
# dynamic odds step 

# INTERNAL SCALE FACTOR: 100 (e.g. odds 2.15 -> 215, stake 10.50 -> 1050)

@dataclass
class Bet:
    id: int
    ts: float
    is_back: bool
    odds: int
    amount: int

@dataclass
class BackBet(Bet):
    def __lt__(self, other: "BackBet") -> bool:
        # min-heap: lowest odds first, then oldest ts, then lowest id
        return (self.odds, self.id) < (other.odds, other.id)

@dataclass
class LayBet(Bet):
    def __lt__(self, other: "LayBet") -> bool:
        # max-heap for odds (Lay bets): highest odds first, then oldest ts, then lowest id
        return (-self.odds, self.id) < (-other.odds, other.id)


class Market:
    def __init__(self):
        self.bet_queue_lay = []
        self.bet_queue_back = []
        self.matched_bets_queue = deque()
        self.odds_liq_dict_lay = {}
        self.odds_liq_dict_back = {}
        self.odds_liq_dict_ma = {}
        self.next_id = 1

    def reset(self):
        self.bet_queue_lay.clear()
        self.bet_queue_back.clear()
        self.matched_bets_queue.clear()
        self.odds_liq_dict_lay.clear()
        self.odds_liq_dict_back.clear()
        self.odds_liq_dict_ma.clear()
        self.next_id = 1

    def get_queue_lay(self, n: int = 5) -> list:
        if n < 1:
            return []
        bets = heapq.nsmallest(n, self.bet_queue_lay)
        return [(b.id, b.is_back, b.odds, b.amount) for b in bets]

    def get_queue_back(self, n: int = 5) -> list:
        if n < 1:
            return []
        bets = heapq.nsmallest(n, self.bet_queue_back)
        return [(b.id, b.is_back, b.odds, b.amount) for b in bets]

    def get_num_matched(self) -> int:
        return len(self.matched_bets_queue)

    def get_fair_odds(self) -> int:
        if len(self.bet_queue_back) == 0 or len(self.bet_queue_lay) == 0:
            return 0
        min_back = self.bet_queue_back[0].odds
        max_lay = self.bet_queue_lay[0].odds
        return (min_back + max_lay) // 2

    def _get_alternative_odd(self) -> int:
        if len(self.bet_queue_lay) >= 1:
            return self.bet_queue_lay[0].odds
        if len(self.bet_queue_back) >= 1:
            return self.bet_queue_back[0].odds
        return max(self.odds_liq_dict_ma, key=self.odds_liq_dict_ma.get, default=0)

    @staticmethod
    def _get_liability(odds: int, stake: int) -> int:
        return (odds - 100) * stake // 100

    def get_total_liquidity(self) -> int:
        return sum([
            sum(self.odds_liq_dict_ma.values()),
            sum(self.odds_liq_dict_back.values()),
            sum(self.odds_liq_dict_lay.values())
        ])

    def get_liquidity_data(self, span: int = 5):
        fair_odds = self.get_fair_odds()
        if fair_odds == 0:
            fair_odds = self._get_alternative_odd()
            if fair_odds == 0:
                return [0], [0], [0], [0]

        odds_range = [fair_odds + x for x in range(-span, span + 1)]
        liq_per_odd_um_back = [self.odds_liq_dict_back.get(odd, 0) for odd in odds_range]
        liq_per_odd_um_lay = [self.odds_liq_dict_lay.get(odd, 0) for odd in odds_range]
        liq_per_odd_ma = [self.odds_liq_dict_ma.get(o, 0) for o in odds_range]

        return odds_range, liq_per_odd_um_lay, liq_per_odd_um_back, liq_per_odd_ma

    def receive_bet(self, ts: float, is_back: bool, amount: int, odds: int) -> dict:
        if odds <= 100:
            raise RuntimeError(f"Engine invariant violated: odds must be > 100, received {odds}")
        
        if amount < 100:
            raise RuntimeError(f"Engine invariant violated: amount must be >= 100, received {amount}")

        if amount % 50 != 0:
            raise RuntimeError(f"Engine invariant violated: amount {amount} must be in steps of 50")

        if is_back:
            bet = BackBet(self.next_id, ts, is_back, odds, amount)
        else:
            bet = LayBet(self.next_id, ts, is_back, odds, amount)
            
        self.next_id += 1
        
        matched_amounts = {} 

        if bet.is_back:
            while bet.amount > 0 and self.bet_queue_lay:
                top = self.bet_queue_lay[0]
                if top.odds < bet.odds:
                    break
                qt = min(bet.amount, top.amount)
                bet.amount -= qt
                top.amount -= qt
                
                matched_amounts[top.odds] = matched_amounts.get(top.odds, 0) + qt 
                
                total_amount = qt + self._get_liability(top.odds, qt)
                self.matched_bets_queue.append((bet.id, top.id, total_amount, top.odds))
                self.odds_liq_dict_ma[top.odds] = self.odds_liq_dict_ma.get(top.odds, 0) + total_amount
                self.odds_liq_dict_lay[top.odds] = self.odds_liq_dict_lay.get(top.odds, 0) - self._get_liability(top.odds, qt)
                
                if top.amount <= 0:
                    heapq.heappop(self.bet_queue_lay)

            if bet.amount > 0:
                self.odds_liq_dict_back[bet.odds] = self.odds_liq_dict_back.get(bet.odds, 0) + bet.amount
                heapq.heappush(self.bet_queue_back, bet)

        else:
            while bet.amount > 0 and self.bet_queue_back:
                top = self.bet_queue_back[0]
                if top.odds > bet.odds:
                    break
                qt = min(bet.amount, top.amount)
                bet.amount -= qt
                top.amount -= qt
                
                matched_amounts[top.odds] = matched_amounts.get(top.odds, 0) + qt
                
                total_amount = qt + self._get_liability(top.odds, qt)
                self.matched_bets_queue.append((top.id, bet.id, total_amount, top.odds))
                self.odds_liq_dict_ma[top.odds] = self.odds_liq_dict_ma.get(top.odds, 0) + total_amount
                self.odds_liq_dict_back[top.odds] = self.odds_liq_dict_back.get(top.odds, 0) - qt
                
                if top.amount <= 0:
                    heapq.heappop(self.bet_queue_back)

            if bet.amount > 0:
                self.odds_liq_dict_lay[bet.odds] = self.odds_liq_dict_lay.get(bet.odds, 0) + self._get_liability(bet.odds, bet.amount)
                heapq.heappush(self.bet_queue_lay, bet)

        return matched_amounts