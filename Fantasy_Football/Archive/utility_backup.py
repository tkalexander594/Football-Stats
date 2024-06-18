from datetime import datetime
import sys
sys.path.append("/Users/treveralexander/Library/CloudStorage/OneDrive-EY/Personal/DE Project/Fantasy_Football")
import Helper.helpers as helper

def get_stats(category, year, position=None):
    """
    Retrieves player or team statistics based on the specified category, year, and optional position.

      Args (get_player_category_stats):
        category (str): The category of player statistics you want to retrieve. Choose from the following options:
            - "passing"
            - "rushing"
            - "receiving"
            - "fumbles"
            - "tackles"
            - "interceptions"
            - "field-goals"
            - "kickoffs"
            - "kickoff-returns"
            - "punts"
            - "punt-returns"

      Args (get_team_category_stats):
        category (str): The category of player statistics you want to retrieve. Choose from the following options:
            - Offense: "passing", "rushing", "receiving", "scoring", "downs"
            - Defense: "passing", "rushing", "receiving", "scoring", "tackles", "downs", "fumbles", "interceptions"
            - Special Teams: "field-goals", "scoring", "kickoffs", "kickoff-returns", "punts", "punt-returns"
        position (str): The position group for which you want to retrieve statistics. Choose from:
            - "offense"
            - "defense"
            - "special-teams"
     Args:
        Year (1970 - Current Year)

    Returns:
        A tuple containing the data and headers for player stats.

    Raises:
        ValueError: If an invalid Args is provided.
    """

    # Get the current year from the datetime object:
    current_year = datetime.now().year

    if year < 1970 or year > current_year:
        raise ValueError("Invalid year provided. Please enter a year between 1970 and the current year.")

    if position:
        team_stats = helper.get_team_category_stats(category, position)
        url = f'https://www.nfl.com/stats/team-stats/{position}/{team_stats}/{year}/reg/all'
        data, headers = helper.get_data(url)
    else:     
        sort_by = helper.get_player_category_stats(category)
        url = f'https://www.nfl.com/stats/player-stats/category/{category}/{year}/reg/all/{sort_by}/desc'
        data, headers = helper.get_data(url)
        
    return data, headers

def write_json(path,df):
    # Directory path
    json_path = path

    # Create the Delta table
    df.write_json(json_path)

    print(f"json file has successfully been created in: {path}")

def write_delta(path,df):
    # Directory path
    delta_path = path

    # Create the Delta table
    df.write_delta(delta_path)

    print(f"delta file has successfully been created in: {path}")

def write_csv(path,df):
    # Directory path
    csv_path = path

    # Create the Delta table
    df.write_csv(csv_path)

    print(f"csv file has successfully been created in: {path}")


def get_current_year():
    from datetime import datetime
    current_year = datetime.now().year
    return current_year

