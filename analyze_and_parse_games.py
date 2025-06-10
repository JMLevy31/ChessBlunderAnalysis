import os
import chess
import chess.pgn
import chess.engine
import math
import csv
import re
import io
import requests
from bs4 import BeautifulSoup
import asyncio

async def analyze_game(game, stockfish_path):
    """
    Analyzes a chess game from a PGN file using Stockfish.
    
    Args:
        game (game from python-chess): game type object resulting from python-chess' chess.pgn.read_game()
        stockfish_path (str): string containing the path of local stockfish executable

    Returns:
        white_mistakes (list): list containing the move numbers where white made mistakes
        white_blunders (list): list containing the move numbers where white blundered
        black_mistakes (list): list containing the move numbers where black made mistakes
        black_blunders (list): list containing the move numbers where black blundered
        move_num (int): the total number of moves in the game
    """
    mistake = 100
    blunder = 300

    board = game.board()
    transport, engine = await chess.engine.popen_uci(stockfish_path)

    await engine.configure({"Threads": 10})

    print(f"Analyzing game: {game.headers['Event']} - {game.headers['White']} vs {game.headers['Black']}")

    combined_move_num = 1
    black_mistakes = []
    black_blunders = []
    white_mistakes = []
    white_blunders = []

    for move in game.mainline_moves():
        board.push(move)
        info = await engine.analyse(board, chess.engine.Limit(depth=18))

        try:
            old_score = score
        except UnboundLocalError:
            old_score = info["score"].white().score(mate_score=1000)

        move_num = int(math.ceil(combined_move_num / 2)) #this is how I'm handling the fact that in chess the move number technically doesn't increase until both players have moved. 

        score = info["score"].white().score(mate_score=1000)
 
        if score - old_score >= blunder:
            black_blunders.append(move_num)
        elif score - old_score >= mistake: 
            black_mistakes.append(move_num)
        elif score - old_score <= 0 - blunder:
             white_blunders.append(move_num)
        elif score - old_score <= 0 - mistake:
             white_mistakes.append(move_num)

        combined_move_num += 1

    await engine.quit()

    return white_mistakes, white_blunders, black_mistakes, black_blunders, move_num

def get_opening_name(eco_url):
    """
    Parses opening name from the ECOUrl using a combination of BeautifulSoup and re. 

    Args:
        eco_url (str): the url for the ECO code as provided by PGN
    
    Returns: 
        full_opening_name (str): Full opening name including main name and variation name (e.g. 'Pirc Defense: Classical, Quiet System')
        main_opening_name (str): main opening name (e.g. 'Pirc Defense')
        variation_opening_name (str): variation opening name (e.g. 'Classical, Quiet System')

    """
    eco_url_contents = requests.get(eco_url).text
    soup = BeautifulSoup(eco_url_contents, 'html.parser')
    title = soup.title.string

    full_opening_name = title[:-29] #removes the standard " - Chess Openings - Chess.com'" text from the title to isolate the opening name.
    try: #Need to catch errors when there is no variation listed (e.g. mainline opening was played)
        main_opening_name = re.search(".*?:", full_opening_name).group(0)[:-1]
        variation_opening_name = re.search(":.*", full_opening_name).group(0)[2:]
    except AttributeError:
        main_opening_name = full_opening_name
        variation_opening_name = ""

    return full_opening_name, main_opening_name, variation_opening_name


def parse_pgn_to_csv(pgn_path, txt_path, user_name, stockfish_path, csv_path="chess_games_data.csv"):
    """
    Parses a PGN file and .txt file, extracts game metadata, and saves it to a CSV file.

    Args:
        pgn_path (str): The path to the input .pgn file.
        txt_path (str): The path to the input .txt file.
        user_name (str): Needed for win/loss/draw column. 
        csv_path (str, optional): The path to the output CSV file. Defaults to "chess_games_data.csv".
    """

    try:
        # Ensure the output directory exists if the CSV path includes one
        output_dir = os.path.dirname(csv_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(txt_path, 'r', encoding='utf-8') as txt_file:
            games_data = re.findall(r"\"pgn\":.*?eco\":", txt_file.read(), flags = re.DOTALL) 

        # Open the PGN for reading and the CSV file for writing
        with open(pgn_path, 'r', encoding='utf-8') as pgn_file, \
             open(csv_path, 'w', newline='', encoding='utf-8') as csv_file: 

            writer = csv.writer(csv_file)

            # Define the headers for your CSV file
            headers = [
                "Event", "Site", "Date", "Round", "White", "Black", "Result", "CurrentPosition", "TimeZone", "ECO", "ECOUrl", "UTCDate", "UTCTime", "WhiteElo", "BlackElo",
                "TimeControl", "Termination", "StartTime", "EndDate", "EndTime", "Link", "Full Opening Name", "Main Opening Name", "Variation Opening Name", "Win-Loss-Draw", "Total Moves",
                "White Accuracy", "Black Accuracay", "Black Total Blunders", "Black Total Mistakes", "White Total Blundres", "White Total Mistakes", "Black First Blunder",
                "Black First Mistake", "White First Blunder", "White First Mistake" 
                ]
            writer.writerow(headers) # Write the header row to the CSV

            game_count = 0 # Read games one by one from the PGN file
            while True:
                game = chess.pgn.read_game(pgn_file) 
            
                if game is None:
                    break # No more games in the PGN file
                
                try:
                    accuracies = re.search("\"accuracies\":{\"white\":.*?}", games_data[game_count]).group(0)
                    white_accuracy = re.search("\"white\":.*?,", accuracies).group(0)[8:-1]
                    black_accuracy = re.search("\"black\":.*?}", accuracies).group(0)[8:-1]
                except AttributeError:
                    white_accuracy = ""
                    black_accuracy = ""

                white_mistakes, white_blunders, black_mistakes, black_blunders, move_num = asyncio.run(analyze_game(game, stockfish_path))

                headers = game.headers # Get the game's headers

                # Create a list for the current row's data
                row_data = []
                for header_name in headers:
                    # Get the header value, use an empty string if missing
                    value = headers.get(header_name, "")
                    row_data.append(value)     
                
                full_opening_name, main_opening_name, variation_opening_name = get_opening_name(row_data[10])

                row_data.extend([full_opening_name, main_opening_name, variation_opening_name])

                if row_data[6] == "1-0" and row_data[4] == user_name:
                    row_data.append("Win")
                elif row_data[6] == "1-0" and row_data[5] == user_name:
                    row_data.append("Loss")
                elif row_data[6] == "0-1" and row_data[5] == user_name:
                    row_data.append("Win")
                elif row_data[6] == "0-1" and row_data[4] == user_name:
                    row_data.append("Loss")
                elif row_data[6] == "1/2-1/2" and (row_data[4] == user_name or row_data[5] == user_name):
                    row_data.append("Draw")
                else:
                    "uhhh you didn't play in this game..."

                
                row_data.extend([move_num, white_accuracy, black_accuracy, len(black_blunders), len(black_mistakes), len(white_blunders), len(white_mistakes)])

                try:
                    row_data.append(black_blunders[0])
                except IndexError:
                    row_data.append('')
            
                try:
                    row_data.append(black_mistakes[0])
                except IndexError:
                    row_data.append('')
            
                try:
                    row_data.append(white_blunders[0])
                except IndexError:
                    row_data.append('')
                
                try:
                    row_data.append(white_mistakes[0])
                except IndexError:
                    row_data.append('')

                writer.writerow(row_data)
                game_count += 1

        print(f"Successfully parsed {game_count} games from '{txt_path}' and saved to '{csv_path}'")

    except FileNotFoundError:
        print(f"Error: PGN file not found at '{txt_path}'")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    input_txt_file = "pgn_downloads/combined_txt_file.txt" #default file location, update if necessary. need the .txt version as it has the acurracies while the .pgn doesn't...
    input_pgn_file = "pgn_downloads/combined_pgn_file.pgn" #default file location, update if necessary. need the .pgn version in order to utilize chess.engine...
    user_name = "FreakWhenSee" #update for your username. 
    stockfish_path = "C:/stockfish/stockfish-windows-x86-64-avx2.exe" #update for your local stockfish path.
    output_csv_file = "Chess_database.csv"

    parse_pgn_to_csv(input_pgn_file, input_txt_file, user_name, stockfish_path, output_csv_file) # Run the parser 