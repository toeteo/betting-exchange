import requests
from random import randint, uniform
from time import sleep

bet_link = "http://localhost:8000/bet"

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
    is_back = bool(randint(0, 1))  # Randomly choose True or False
    bet_amount = round(uniform(0.2, 2.0), 1) * 5  # Random bet amount between 1 and 100
    bet_odds = round(uniform(2.0, 2.2), 2)  # Random odds between 1 and 5
    result = post_bet(is_back, bet_amount, bet_odds)
    print(f"Response: {result}")

def main():
    for _ in range(10):  # Place 10 random bets
        place_bet()
        sleep(1)  # Wait for 1 second before placing the next bet

if __name__ == "__main__":
    main()