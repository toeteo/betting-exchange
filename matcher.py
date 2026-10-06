from collections import deque
import heapq


class Bet:
    def __init__(self, ts: int, type: bool, bet_odds: float, bet_amount: float):
        self.ts = ts
        self.type = type    
        self.odds = bet_odds
        self.amount = bet_amount


bet_queue_lay = []
bet_queue_back = []
matched_bets_queue = deque()
id = 0


def receive_bet(ts,type,amount,odds) -> float:
    bet = Bet(ts, type, odds, amount)
    amount_matched = 0.0

    if type: # Back bet
        while bet.amount > 0 and bet_queue_lay:
             top = bet_queue_lay[0][2]  # I pick the bet object inside the tuple with the min odds
             if(bet.odds > top.odds):  # La quota è compatibile
                 break

             qt = min(bet.amount, top.amount)
             bet.amount -= qt
             top.amount -= qt
             amount_matched += qt
             matched_bets_queue.append((bet.ts, top.ts, qt, top.odds))
             
            # TODO: quanto abbino? (pensa a min)
            # TODO: aggiorna bet.amount, best.amount, amount_matched
            # TODO: salva l'abbinamento in matched_bets_queue
            # TODO: se la scommessa in coda è esaurita → heappop
            pass
        # TODO: se resta qualcosa di bet.amount → inseriscilo nella coda BACK

    else:           # LAY in arrivo → specchio esatto del ramo sopra
        # TODO
        pass

    return amount_matched

