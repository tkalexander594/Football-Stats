import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import List, Tuple, Optional
import sys
from urllib.parse import urljoin

sys.path.append("/Users/treveralexander/Library/CloudStorage/OneDrive-EY/Personal/Football-Stats/Fantasy_Football")
import Helper.helper as helper
import Utility.utility as util

async def fetch_page(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()

async def parse_table(html: str) -> Tuple[List[List[str]], List[str]]:
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', {'class': 'd3-o-table'})
    
    if not table:
        return [], []

    headers = [header.text.strip() for header in table.find('thead').find('tr').find_all('th')]
    data = [[col.text.strip() for col in row.find_all('td')] for row in table.find_all('tr')[1:]]
    
    return data, headers

async def get_data(url: str) -> Tuple[List[List[str]], List[str]]:
    all_data = []
    headers = []

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                html = await fetch_page(session, url)
                data, page_headers = await parse_table(html)
                
                if not data:
                    print("Table not found on the page. Final page has been reached!")
                    break
                
                all_data.extend(data)
                if not headers:
                    headers = page_headers

                soup = BeautifulSoup(html, 'html.parser')
                next_page = soup.find('a', {'class': 'nfl-o-table-pagination__next'})
                if next_page:
                    next_cursor = next_page.get('href').split('?aftercursor=')[1]
                    url = urljoin(url, f'?aftercursor={next_cursor}')
                else:
                    break

            except aiohttp.ClientError as e:
                print(f"Error fetching data from {url}: {e}")
                break
            except Exception as e:
                print(f"Unexpected error: {e}")
                break

    return all_data, headers

async def get_stats(category: str, year: int, position: Optional[str] = None) -> Tuple[List[List[str]], List[str]]:
    """
    Retrieves player or team statistics based on the specified category, year, and optional position.

    Args:
        category (str): The category of statistics to retrieve.
        year (int): The year for which to retrieve statistics (1970 - Current Year).
        position (str, optional): The position group for team stats (offense, defense, special-teams).

    Returns:
        A tuple containing the data and headers for player or team stats.

    Raises:
        ValueError: If invalid arguments are provided.
    """
    if position:
        team_stats = util.get_team_category_stats(category, position)
        url = f'https://www.nfl.com/stats/team-stats/{position}/{team_stats}/{year}/reg/all'
    else:
        sort_by = util.get_player_category_stats(category)
        url = f'https://www.nfl.com/stats/player-stats/category/{category}/{year}/reg/all/{sort_by}/desc'
    
    return await get_data(url)

# Example usage
if __name__ == "__main__":
    category = "passing"
    year = 2023

    loop = asyncio.get_event_loop()
    data, headers = loop.run_until_complete(get_stats(category, year))

    print("Headers:", headers)
    print("First few rows of data:", data[:5])