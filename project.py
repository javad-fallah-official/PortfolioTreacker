import json
import sys
from pycoingecko import CoinGeckoAPI
import requests 
import math 

PORTFOLIO_FILE = "portfolio.json"
COINGECKO_API = CoinGeckoAPI()
VS_CURRENCY = "usd" 


def load_portfolio(filepath: str) -> dict:
    """
    Loads the portfolio data from a JSON file.

    Args:
        filepath (str): The path to the JSON portfolio file.

    Returns:
        dict: The portfolio data (dictionary mapping coingecko_id to
              {'total_amount': float, 'total_cost_usd': float}).
              Returns an empty dict if the file doesn't exist or is invalid.
    """
    try:
        with open(filepath, 'r') as f:
            # Handle empty file case
            content = f.read()
            if not content:
                return {}
            return json.loads(content)
    except FileNotFoundError:
        return {} # Return empty portfolio if file doesn't exist yet
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {filepath}. Starting with empty portfolio.", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"An unexpected error occurred loading portfolio: {e}", file=sys.stderr)
        return {}

def save_portfolio(filepath: str, portfolio: dict) -> bool:
    """
    Saves the portfolio data to a JSON file.

    Args:
        filepath (str): The path to the JSON portfolio file.
        portfolio (dict): The portfolio data to save.

    Returns:
        bool: True if saving was successful, False otherwise.
    """
    try:
        with open(filepath, 'w') as f:
            json.dump(portfolio, f, indent=4)
        return True
    except IOError as e:
        print(f"Error: Could not write to portfolio file {filepath}: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"An unexpected error occurred saving portfolio: {e}", file=sys.stderr)
        return False

def add_transaction(portfolio: dict) -> dict:
    """
    Prompts the user for transaction details, allows viewing examples or searching for IDs,
    validates the entered CoinGecko ID, and adds it to the portfolio.

    Args:
        portfolio (dict): The current portfolio data.

    Returns:
        dict: The updated portfolio data. Returns the original portfolio if input is invalid.
    """
    print("\n--- Add New Transaction ---")

    # --- Loop for Getting and Validating Coin ID ---
    while True:
        user_input = input("Enter Crypto ID (type 'examples' or 'search' for help): ").strip().lower()

        if not user_input:
            print("Error: Cryptocurrency ID cannot be empty. Please try again.")
            continue # Ask again

        # --- Handle 'examples' input ---
        if user_input == 'examples':
            print("\n--- Show Example Coin IDs ---")
            print("1. Show Top 20 by Market Cap")
            print("2. Show All Supported IDs (Warning: Very long list!)")
            example_choice = input("Choose example type (1 or 2, or press Enter to cancel): ").strip()

            if example_choice == '1':
                try:
                    print("\nFetching Top 20 coins by market cap...")
                    top_coins = COINGECKO_API.get_coins_markets(vs_currency=VS_CURRENCY, order='market_cap_desc', per_page=20, page=1)
                    if top_coins:
                        print("Top 20 CoinGecko IDs:")
                        print(", ".join([coin['id'] for coin in top_coins]))
                    else:
                        print("Could not fetch top coin examples.")
                except Exception as e:
                    print(f"Could not fetch top coin examples: {e}", file=sys.stderr)

            elif example_choice == '2':
                try:
                    print("\nFetching all supported coins (this may take a moment)...")
                    all_coins = COINGECKO_API.get_coins_list()
                    if all_coins:
                        print(f"All Supported CoinGecko IDs ({len(all_coins)} total):")
                        ids = [coin['id'] for coin in all_coins]
                        cols = 8
                        lines = math.ceil(len(ids) / cols)
                        for i in range(lines):
                            print(", ".join(ids[i*cols : (i+1)*cols]))
                    else:
                        print("Could not fetch the list of all coins.")
                except Exception as e:
                    print(f"Could not fetch the list of all coins: {e}", file=sys.stderr)

            elif example_choice == '':
                print("Example display cancelled.")
            else:
                print("Invalid choice for examples.")

            print("-" * 20) # Separator
            continue # Go back to the main ID prompt

        # --- Handle 'search' input ---
        elif user_input == 'search':
            print("\n--- Search Coin IDs ---")
            search_query = input("Enter search term (e.g., 'bitcoin cash', 'doge'): ").strip()

            if not search_query:
                print("Search cancelled.")
                print("-" * 20)
                continue # Go back to the main ID prompt

            try:
                print(f"Searching for '{search_query}'...")
                results = COINGECKO_API.search(query=search_query)
                coins = results.get('coins', [])

                if coins:
                    print(f"Found {len(coins)} matching coin(s) [showing top 10 max]:")
                    # Display results clearly, limiting to first 10
                    for coin in coins[:10]:
                        # Ensure keys exist before accessing
                        coin_id = coin.get('id', 'N/A')
                        name = coin.get('name', 'N/A')
                        symbol = coin.get('symbol', 'N/A')
                        rank = coin.get('market_cap_rank', 'N/A')
                        print(f"  ID: {coin_id:<20} Name: {name:<25} Symbol: {symbol:<8} Rank: {rank}")
                else:
                    print(f"No matching coins found for '{search_query}'.")

            except Exception as e:
                print(f"Error during search: {e}", file=sys.stderr)

            print("-" * 20)
            continue # Go back to the main ID prompt

        # --- If input is not 'examples' or 'search', treat as potential ID ---
        else:
            coin_id = user_input # Use the input as the potential ID
            print(f"Validating ID '{coin_id}' with CoinGecko...")
            if is_coingecko_id_valid(coin_id):
                print(f"ID '{coin_id}' is valid.")
                break # Exit the loop, ID is valid and stored in coin_id
            else:
                # Validation function returned False
                print(f"Error: ID '{coin_id}' seems invalid or could not be verified.")
                print("This could be a typo, a delisted coin, or a network issue during validation.")
                print("Please check the ID or type 'examples' or 'search'.")
                # Continue loop to ask again

    # --- If we reach here, coin_id is validated ---

    # --- Get Amount and Price (with existing validation) ---
    # (This part remains unchanged from the previous version)
    try:
        amount_str = input(f"Enter amount of {coin_id} bought: ").strip()
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError("Amount must be positive.")

        price_per_unit_str = input(f"Enter purchase price per unit (in {VS_CURRENCY.upper()}): ").strip()
        price_per_unit = float(price_per_unit_str)
        if price_per_unit < 0:
             raise ValueError("Purchase price cannot be negative.")

    except ValueError as e:
        print(f"Error: Invalid input for amount or price. Please enter valid numbers. {e}")
        return portfolio # Return original portfolio on error

    # --- Add to Portfolio (existing logic) ---
    # (This part remains unchanged from the previous version)
    transaction_cost = amount * price_per_unit
    if coin_id in portfolio:
        portfolio[coin_id]['total_amount'] += amount
        portfolio[coin_id]['total_cost_usd'] += transaction_cost
    else:
        portfolio[coin_id] = {
            'total_amount': amount,
            'total_cost_usd': transaction_cost
        }

    print(f"Successfully added {amount} {coin_id} to portfolio.")
    return portfolio

def get_current_prices(coin_ids: list) -> dict:
    """
    Fetches current prices for a list of CoinGecko IDs.

    Args:
        coin_ids (list): A list of CoinGecko IDs (strings).

    Returns:
        dict: A dictionary mapping coin_id to its current price in VS_CURRENCY.
              Returns empty dict if API call fails or no IDs provided.
    """
    if not coin_ids:
        return {}

    try:
        # Ping API first to check status (optional but good practice)
        if not COINGECKO_API.ping():
             print("Warning: CoinGecko API seems unreachable.", file=sys.stderr)
             return {}

        prices = COINGECKO_API.get_price(ids=coin_ids, vs_currencies=VS_CURRENCY)
        # Prices dict format: {'bitcoin': {'usd': 60000}, 'ethereum': {'usd': 4000}}
        # Flatten it for easier use: {'bitcoin': 60000, 'ethereum': 4000}
        current_prices = {coin_id: data.get(VS_CURRENCY) for coin_id, data in prices.items() if VS_CURRENCY in data}
        return current_prices

    except requests.exceptions.RequestException as e:
         print(f"Error fetching prices from CoinGecko API (Network Error): {e}", file=sys.stderr)
         return {}
    except Exception as e: # Catch other potential errors from the API wrapper or processing
        print(f"Error fetching or processing prices: {e}", file=sys.stderr)
        return {}

def view_portfolio(portfolio: dict):
    """
    Displays the current state of the portfolio, including changes.
    """
    print("\n--- Portfolio View ---")
    if not portfolio:
        print("Portfolio is empty.")
        return

    coin_ids = list(portfolio.keys())
    current_prices = get_current_prices(coin_ids)

    if not current_prices:
        print("Could not fetch current prices. Displaying holdings without valuation.")

    total_portfolio_value = 0.0
    total_portfolio_cost = 0.0

    print("-" * 70)
    print(f"{'Cryptocurrency':<15} | {'Amount':<15} | {'Total Cost ({})':<15} | {'Current Price ({})':<15} | {'Current Value ({})':<15} | {'Change (%)':<10}".format(VS_CURRENCY.upper(), VS_CURRENCY.upper(), VS_CURRENCY.upper()))
    print("-" * 70)

    for coin_id, data in portfolio.items():
        amount = data['total_amount']
        total_cost = data['total_cost_usd']
        total_portfolio_cost += total_cost

        current_price = current_prices.get(coin_id) # Use .get for safety

        if current_price is not None:
            current_value = amount * current_price
            total_portfolio_value += current_value
            if total_cost > 0: # Avoid division by zero
                change_pct = ((current_value - total_cost) / total_cost) * 100
                change_str = f"{change_pct:+.2f}%"
            else: # If total cost was 0 (e.g., free coins)
                 change_str = "N/A" if current_value == 0 else "+Inf%"

            print(f"{coin_id:<15} | {amount:<15.8f} | {total_cost:<15.2f} | {current_price:<15.2f} | {current_value:<15.2f} | {change_str:<10}")
        else:
            # Handle case where price couldn't be fetched
            print(f"{coin_id:<15} | {amount:<15.8f} | {total_cost:<15.2f} | {'N/A':<15} | {'N/A':<15} | {'N/A':<10}")

    print("-" * 70)
    print(f"Total Portfolio Cost: {total_portfolio_cost:.2f} {VS_CURRENCY.upper()}")
    if total_portfolio_value > 0 or total_portfolio_cost > 0: # Only show value if prices were available
        print(f"Total Portfolio Value: {total_portfolio_value:.2f} {VS_CURRENCY.upper()}")
        if total_portfolio_cost > 0:
            total_change_pct = ((total_portfolio_value - total_portfolio_cost) / total_portfolio_cost) * 100
            print(f"Total Portfolio Change: {total_change_pct:+.2f}%")
        else:
            print("Total Portfolio Change: N/A (Cost was zero)")
    print("-" * 70)

def is_coingecko_id_valid(coin_id: str) -> bool:
    """
    Checks if a given coin ID is recognized by the CoinGecko API.

    Args:
        coin_id (str): The CoinGecko ID to validate (e.g., 'bitcoin').

    Returns:
        bool: True if the ID is valid and returns data, False otherwise.
    """
    if not coin_id: # Basic check if called directly
        return False
    try:
        # Attempt to fetch price data for the entered ID
        # Use global constants COINGECKO_API and VS_CURRENCY
        validation_data = COINGECKO_API.get_price(ids=[coin_id], vs_currencies=[VS_CURRENCY])

        # Check if the API returned data specifically for this ID and currency
        if coin_id in validation_data and VS_CURRENCY in validation_data[coin_id]:
            return True # ID is valid
        else:
            # API call succeeded but didn't return expected data for this ID/currency
            return False # ID is likely invalid or delisted

    except Exception as e:
        # Handle potential errors during the API call (network, truly invalid ID format etc.)
        # You could log the error here if needed: print(f"Validation API error for {coin_id}: {e}", file=sys.stderr)
        return False # Treat API errors as invalid ID for simplicity

def clear_portfolio_history() -> dict:
    """
    Asks the user for confirmation and clears the portfolio data
    by overwriting the portfolio file with an empty dictionary.

    Returns:
        dict: An empty dictionary if clearing was successful and confirmed,
              otherwise None (indicating cancellation or error).
              Returning None prevents the main loop from overwriting the
              in-memory portfolio if the user cancels.
    """
    print("\n--- Clear Portfolio History ---")
    confirm = input("WARNING: This will permanently delete all saved portfolio data!\n"
                    "Are you absolutely sure you want to proceed? (Type 'yes' to confirm): ").strip().lower()

    if confirm == "yes":
        print("Attempting to clear portfolio data...")
        # Save an empty dictionary to overwrite the file
        if save_portfolio(PORTFOLIO_FILE, {}):
            print("Portfolio history cleared successfully.")
            return {} # Return empty dict to signal success
        else:
            # save_portfolio would have printed an error
            print("Failed to clear portfolio history due to a save error.")
            return None # Return None to indicate failure
    else:
        print("Clear operation cancelled.")
        return None # Return None to indicate cancellation


def main():
    """
    Main function to run the portfolio tracker application.
    """
    portfolio = load_portfolio(PORTFOLIO_FILE)

    while True:
        print("\n--- Crypto Portfolio Tracker ---")
        print("1. Add Transaction")
        print("2. View Portfolio")
        print("3. Clear Portfolio History") # New option
        print("4. Exit")                   # Renumbered Exit
        choice = input("Choose an option: ").strip()

        if choice == '1':
            # Make a temporary copy to potentially update
            temp_portfolio = portfolio.copy()
            updated_portfolio = add_transaction(temp_portfolio)
            # Only update and save if add_transaction didn't return the original due to error
            # and the portfolio actually changed (though add_transaction doesn't signal this explicitly)
            # A simple check is if the returned dict is different (e.g., new item added)
            # For simplicity, we assume if it didn't return the exact same object on error, it succeeded.
            # Revisit this if add_transaction needs more robust success signaling.
            portfolio = updated_portfolio # Update in-memory portfolio regardless for now
            if not save_portfolio(PORTFOLIO_FILE, portfolio):
                 print("Warning: Failed to save portfolio update after add.", file=sys.stderr)


        elif choice == '2':
            view_portfolio(portfolio)

        elif choice == '3': # New block for clearing history
            cleared_portfolio = clear_portfolio_history()
            # Only update the in-memory portfolio if clearing was successful
            if cleared_portfolio is not None: # clear_portfolio_history returns {} on success, None on cancel/fail
                portfolio = cleared_portfolio

        elif choice == '4': # Renumbered Exit option
            # Optional: Save one last time before exiting?
            # if not save_portfolio(PORTFOLIO_FILE, portfolio):
            #     print("Warning: Failed to save portfolio before exiting.", file=sys.stderr)
            print("Exiting Portfolio Tracker. Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()