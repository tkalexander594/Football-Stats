import requests
from bs4 import BeautifulSoup
from datetime import datetime
#import time

def get_data(url):
    current_url = url
    data = []  # List to store scraped data
    headers = []  # List to store table headers

    while True:
        try:
            response = requests.get(current_url)
            response.raise_for_status()  # Raise error for non-200 status codes
            soup = BeautifulSoup(response.content, 'html.parser')

            table = soup.find('table', {'class': 'd3-o-table'})

            # Check if the table element exists
            if not table:
                print("Table not found on the page. Final page has been reached!")
                break

            # Extract column headers if not already extracted
            if not headers:
                header_row = table.find('thead').find('tr')
                headers = [header.text.strip() for header in header_row.find_all('th')]

            for row in table.find_all('tr')[1:]:  # Skip the header row
                cols = row.find_all('td')
                row_data = [col.text.strip() for col in cols]
                data.append(row_data)

            # Find the link to the next page using the 'aftercursor' parameter
            next_page = soup.find('a', {'class': 'nfl-o-table-pagination__next'})
            if next_page:
                next_cursor = next_page.get('href').split('?aftercursor=')[1]
                current_url = f'{url}?aftercursor={next_cursor}'
            else:
                break  # No more pages, exit the loop

            # Add a delay to avoid overloading the server
            #time.sleep(1)

        except requests.RequestException as e:
            print(f"Error fetching data from {current_url}: {e}")
            break  # Exit the loop on network errors
        except AttributeError as e:
            print(f"Error parsing HTML content: {e}")
            break  # Exit the loop on HTML parsing errors

    return data, headers

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

    Raises:
        ValueError: If an invalid category is provided.
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
    except KeyError:
        raise ValueError(f"Invalid category: {category}")

    return sort_by

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

    Raises:
        ValueError: If an invalid category or position is provided.
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
    except KeyError:
        raise ValueError(f"Invalid category or position: {category}, {position}")

    return team_stats


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
        team_stats = get_team_category_stats(category, position)
        url = f'https://www.nfl.com/stats/team-stats/{position}/{team_stats}/{year}/reg/all'
        data, headers = get_data(url)
    else:     
        sort_by = get_player_category_stats(category)
        url = f'https://www.nfl.com/stats/player-stats/category/{category}/{year}/reg/all/{sort_by}/desc'
        data, headers = get_data(url)
        
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

