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


def get_player_category_stats(category):
    """
    Determines the appropriate sort_by value based on the provided category for individual player statistics.

    Args:
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

    Returns:
        A tuple containing the sort_by value.

    """

    category_sort_by_map = {
        "passing": "passingyards",
        "rushing": "rushingyards",
        "receiving": "receivingreceptions",
        "fumbles": "defensiveforcedfumble",
        "tackles": "defensivecombinetackles",
        "interceptions": "defensiveinterceptions",
        "field-goals": "kickingfgmade",
        "kickoffs": "kickofftotal",
        "kickoff-returns": "kickreturnsaverageyards",
        "punts": "puntingaverageyards",
        "punt-returns": "puntreturnsaverageyards",
    }
    try:
        sort_by = category_sort_by_map[category]
        return sort_by
    except KeyError:
       return "default_sort_by"

def get_team_category_stats(category, position):
    """
    Determines the appropriate team_stats value based on the provided category and position.

    Args:
        category (str): The category of player statistics you want to retrieve. Choose from the following options:
            - Offense: "passing", "rushing", "receiving", "scoring", "downs"
            - Defense: "passing", "rushing", "receiving", "scoring", "tackles", "downs", "fumbles", "interceptions"
            - Special Teams: "field-goals", "scoring", "kickoffs", "kickoff-returns", "punts", "punt-returns"
        position (str): The position group for which you want to retrieve statistics. Choose from:
            - "offense"
            - "defense"
            - "special-teams"

    Returns:
        A tuple containing the team_stats value.

    """

    # Documentation for categories and position:
    #
    # Categories:
    #   Offense:
    #       - passing: Statistics related to passing plays (passing yards, completions, touchdowns).
    #       - rushing: Statistics related to rushing plays (rushing yards, attempts, touchdowns).
    #       - receiving: Statistics related to receiving plays (receptions, yards, touchdowns).
    #       - scoring: Overall scoring statistics (points scored).
    #       - downs: Down-specific statistics (third-down conversions, other down-related metrics).
    #   Defense:
    #       - passing: Defensive statistics against passing plays (interceptions, sacks, yards allowed).
    #       - rushing: Defensive statistics against rushing plays (tackles for loss, yards allowed, touchdowns allowed).
    #       - receiving: Defensive statistics against receiving plays (pass breakups, yards allowed).
    #       - scoring: Defensive scoring statistics (points allowed).
    #       - tackles: Overall tackling statistics (total tackles, solo tackles, assisted tackles).
    #       - downs: Down-specific defensive statistics (stopping opponents on third or fourth down).
    #       - fumbles: Statistics related to fumbles caused or recovered by the defense.
    #       - interceptions: Statistics related to interceptions made by the defense.
    #   Special Teams:
    #       - field-goals: Statistics related to field goals (made field goals, attempts, percentage).
    #       - scoring: Special teams scoring statistics (points scored from field goals, extra points, returns).
    #       - kickoffs: Statistics related to kickoffs (touchbacks, average distance, returns allowed).
    #       - kickoff-returns: Statistics related to kickoff returns (average yards per return, touchdowns).
    #       - punts: Statistics related to punts (average distance, hang time, punts inside the 20-yard line).
    #       - punt-returns: Statistics related to punt returns (average yards per return, touchdowns).
    #
    # Position:
    #   - 'offense': For offensive statistics.
    #   - 'defense': For defensive statistics.
    #   - 'special-teams': For special teams statistics.

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
