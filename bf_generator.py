import requests
from random import randint, uniform
from time import sleep
import pandas as pd
import sys

bet_link = "http://localhost:8000/bet"
df = None

def post_bet(is_back, bet_amount, bet_odds):
    print(f"Placing bet: is_back={is_back}, amount={bet_amount}, odds={bet_odds}")
    bet_data = {
        "is_back": is_back,
        "bet_amount": bet_amount,
        "bet_odds": bet_odds
    }
    response = requests.post(bet_link, json=bet_data)
    return response.json()

def place_bets(n=100):
    i = 0

    for index, row in df.iterrows():
        is_back = row["IS_BACK"]
        bet_amount = row["STAKE"]
        bet_odds = row["ODDS"]
        result = post_bet(is_back, bet_amount, bet_odds)
        print(f"Response: {result}")
        i += 1
        if i >= n:
            break
        sleep(0.1)

# get the file name as an argument from the command line

def main():
    if len(sys.argv) <= 2:
        print("Usage: python script.py <events.csv> <number_of_bets>")
        sys.exit(1)

    global df
    df = pd.read_csv(sys.argv[1])

    place_bets(int(sys.argv[2]))

if __name__ == "__main__":
    main()