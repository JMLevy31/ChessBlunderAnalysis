import requests
import os

def download_pgns(username, email, year, months, output_dir="pgn_downloads"):
    """
    Downloads the PGN and .txt versions of the game data from Chess.com API

    Args:
        username (str): Your Chess.com username.
        email (str): Your Chess.com email
        year (str): The year (e.g., "2024").
        months (list):  list of month (e.g., ['01','02','03]").
        output_dir (str, optional): Directory to save the PGN file. Defaults to "pgn_downloads".

    Returns:
        output_dir (str): Directory where the files were saved. This is outputted so that it can be utilized when running the merge_files function. 
    """
    
    for month in months: #looping through the months list to create unique urls for each month
        txt_url = f"https://api.chess.com/pub/player/{username}/games/{year}/{month}"
        pgn_url = f"https://api.chess.com/pub/player/{username}/games/{year}/{month}/pgn"
        print(f"Attempting to download files for {month} of {year}")

        try:
            #headers are required  on the requests.get or you will get 403 error. This is why email address is a required input.
            pgn_response = requests.get(pgn_url, headers = {'User-Agent': 'username: {username}, email: {email}'}) 
            pgn_response.raise_for_status()  # Raise an exception for bad status codes

            txt_response = requests.get(txt_url, headers = {'User-Agent': 'username: {username}, email: {email}'}) 
            txt_response.raise_for_status()  # Raise an exception for bad status codes

            pgn_content = pgn_response.text
            txt_content = txt_response.text

            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            pgn_filename = f"{username}_{year}_{month}.pgn"
            pgn_filepath = os.path.join(output_dir, pgn_filename)

            with open(pgn_filepath, "w") as f:
                f.write(pgn_content)

            txt_filename = f"{username}_{year}_{month}.txt"
            txt_filepath = os.path.join(output_dir, txt_filename)

            with open(txt_filepath, "w") as f:
                f.write(txt_content)

            print(f"Successfully downloaded PGNs for {year}-{month} to: {pgn_filepath}")

        except requests.exceptions.RequestException as e:
            print(f"Error downloading PGNs: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        
    return output_dir

def get_txt_and_pgn_filenames(path):
    """
    For a given path, returns alist of all .txt files and a second list of all .pgn files

    Args:
        path(str): the path where the .txt and .pgn files are located
    
    Returns:
        txt_file_names (list): list of all .txt files in the path
        pgn_file_names (list): list of all .pgnfiles in the path
    """
    txt_file_names = []
    pgn_file_names = []

    if os.path.exists(path):
        for item in os.listdir(path):
            if os.path.isfile(os.path.join(path,item)):
                if os.path.splitext(item)[1] == '.txt':
                    txt_file_names.append(item)
                elif os.path.splitext(item)[1] == '.pgn':
                    pgn_file_names.append(item)
    else:
        raise FileNotFoundError(f"(The directory {path} was not found.")
    return txt_file_names, pgn_file_names

def merge_files(path, file_list, output_file):
    """
    For a list of files in a path, merges the files into a single combined file.

    Args:
        path (str): the path where the individual files are located
        file_list(list): the list of the individual files
        output_file(str): the name you want to give the final merged file
    """
    with open(output_file, 'w') as outfile:
        for filename in file_list:
            try:
                with open(path + "/" + filename, 'r') as infile:
                    for line in infile:
                        outfile.write(line)
                    outfile.write("\n\n") #want to consistently start the next file with two newlines following the end of the previous file. 
            except FileNotFoundError:
                print(f"File not found: {path + "/" + filename}")
            

if __name__ == "__main__":
    username = "USERNAME"  # Replace with your username
    email = "EMAIL@gmail.com" # Replace with your chess.com email. This is required or you will get a 403 error
    year = "2025"  # Specify the year
    months = ['03','04','05']  # Specify the months (e.g., "01" for January, "05" for May)

    path = download_pgns(username, email, year, months)

    txt_file_names, pgn_file_names = get_txt_and_pgn_filenames(path)

    merge_files(path, txt_file_names, path + "/combined_txt_file.txt")
    merge_files(path, pgn_file_names, path + "/combined_pgn_file.pgn")