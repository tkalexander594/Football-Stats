def get_data(url):
    import requests
    from bs4 import BeautifulSoup

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


def get_stats(category, year, position=None):
    import sys
    sys.path.append("/Users/treveralexander/Library/CloudStorage/OneDrive-EY/Personal/Football-Stats/Fantasy_Football")
    import Helper.helper as helper
    import Utility.utility as util

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
        team_stats = util.get_team_category_stats(category, position)
        url = f'https://www.nfl.com/stats/team-stats/{position}/{team_stats}/{year}/reg/all'
        data, headers = helper.get_data(url)
    else:     
        sort_by = util.get_player_category_stats(category)
        url = f'https://www.nfl.com/stats/player-stats/category/{category}/{year}/reg/all/{sort_by}/desc'
        data, headers = helper.get_data(url)
        
    return data, headers
