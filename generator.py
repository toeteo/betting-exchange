import requests
from random import randint, uniform
from time import sleep

bet_link = "http://localhost:8000/bet"

total_liquidity = 0

def post_bet(is_back, bet_amount, bet_odds):
    print(f"Placing bet: is_back={is_back}, amount={bet_amount}, odds={bet_odds}")
    bet_data = {
        "is_back": is_back,
        "bet_amount": bet_amount,
        "bet_odds": bet_odds
    }
    response = requests.post(bet_link, json=bet_data)
    return response.json()

def place_bet():
    global total_liquidity
    is_back = bool(randint(0, 1))  # Randomly choose True or False
    bet_amount = round(round(uniform(0, 20), 1) * 5 * 100) # Random bet amount between 0.5 and 100
    bet_odds = round(round(uniform(1.9, 2.1), 2) * 100) # Random odds
    result = post_bet(is_back, bet_amount, bet_odds)
    liability = bet_amount if is_back else (bet_odds - 100) * bet_amount // 100
    total_liquidity += liability
    print(f"Response: {result}")


def main():
    for _ in range(10):  # Place 10 random bets
        place_bet()
        sleep(0.1)  # Wait for 1 second before placing the next bet
        print(total_liquidity)

if __name__ == "__main__":
    main()