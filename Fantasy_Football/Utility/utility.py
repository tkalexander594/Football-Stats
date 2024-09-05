import sys
sys.path.append("/Users/treveralexander/Library/CloudStorage/OneDrive-EY/Personal/DE Project/Fantasy_Football")
import Fantasy_Football.Helper.extractor as helper


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
    df.write_json(json_path,row_oriented=True)

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

def get_formatted_start_time(start_time):
    from datetime import datetime
    formatted_start_time = datetime.fromtimestamp(start_time).strftime("%Y-%m-%d %H:%M:%S")
    return formatted_start_time

def get_formatted_end_time(end_time):
    from datetime import datetime
    formatted_end_time = datetime.fromtimestamp(end_time).strftime("%Y-%m-%d %H:%M:%S")
    return formatted_end_time


def get_start_time():
    import time
    start_time = time.time()
    return start_time

def get_end_time():
    import time
    start_time = time.time()
    return start_time


def get_valid_player_categories(category):
    category_map = {
        "passing": "passing",
        "rushing": "rushing",
        "receiving": "receiving",
        "fumbles": "fumbles",
        "tackles": "tackles",
        "interceptions": "interceptions",
        "field-goals": "field-goals",
        "kickoffs": "kickoffs",
        "kickoff-returns": "kickoff-returns",
        "punts": "punts",
        "punt-returns": "punt-returns",
    }
    try:
        valid_category = category_map[category]
        return valid_category
    except KeyError:
       return "default_valid_category"


def get_valid_team_categories(category,position):
    position_map = {
        "offense": {
            "passing": "passing",
            "rushing": "rushing",
            "receiving": "receiving",
            "scoring": "scoring",
            "downs": "downs",
        },
        "defense": {
            "passing": "passing",
            "rushing": "rushing",
            "receiving": "receiving",
            "scoring": "scoring",
            "tackles": "tackles",
            "downs": "downs",
            "fumbles": "fumbles",
            "interceptions": "interceptions",
        },
        "special-teams": {
            "field-goals": "field-goals",
            "scoring": "scoring",
            "kickoffs": "kickoffs",
            "kickoff-returns": "kickoff-returns",
            "punts": "punts",
            "punt-returns": "punt-returns",
        },
    }
    try:
        team_stats = position_map[position][category]
        return team_stats 
    except KeyError:
       return "default_team_stats"
    

def ensure_iterable(categories):
    """Ensures that the input is iterable, converting non-iterables to single-item lists."""
    if not isinstance(categories, (list, tuple, set)):
        categories = [categories]  # Convert to a single-item list
    return categories


def current_nfl_regular_season():
  import datetime
  """
  Determines the current NFL season, considering its overlap into the next year.

  Returns:
    A string representing the current NFL season, e.g., "2023-2024".
  """

  today = datetime.date.today()

  # Regular season starts in September and ends in February (including the Super Bowl).
  if today.month == 1 and today.day <= 9:
    # Current year is part of the regular season.
    return int(today.year - 1)
  else:
    # we are now out of the regular season
    return int(today.year)
