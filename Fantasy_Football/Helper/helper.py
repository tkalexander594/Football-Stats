import logging
from typing import List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

import Utility.utility as util


def get_data(url: str, session: Optional[requests.Session] = None) -> Tuple[List[List[str]], List[str]]:
    """Paginate through an NFL.com stat table and return all rows.

    Parameters
    ----------
    url : str
        The base NFL.com stats URL (without ``?aftercursor``).
    session : requests.Session, optional
        An existing session to reuse for all page requests.  If not provided,
        a temporary session is created internally.

    Returns
    -------
    tuple[list[list[str]], list[str]]
        A tuple of ``(data, headers)`` where ``data`` is a list of rows
        (each row is a list of cell strings) and ``headers`` is a list of
        column name strings.
    """
    _session = session or requests.Session()
    current_url = url
    data: List[List[str]] = []
    headers: List[str] = []

    while True:
        try:
            response = _session.get(current_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            table = soup.find('table', {'class': 'd3-o-table'})
            if not table:
                logging.info("Table not found — final page reached.")
                break

            if not headers:
                header_row = table.find('thead').find('tr')
                headers = [th.text.strip() for th in header_row.find_all('th')]

            for row in table.find_all('tr')[1:]:
                row_data = [col.text.strip() for col in row.find_all('td')]
                data.append(row_data)

            next_page = soup.find('a', {'class': 'nfl-o-table-pagination__next'})
            if next_page:
                next_cursor = next_page.get('href').split('?aftercursor=')[1]
                current_url = f'{url}?aftercursor={next_cursor}'
            else:
                break

        except requests.RequestException as e:
            logging.error("Network error fetching %s: %s", current_url, e)
            break
        except AttributeError as e:
            logging.error("HTML parsing error: %s", e)
            break

    return data, headers


def get_stats(category: str, year: int, position: Optional[str] = None) -> Tuple[List[List[str]], List[str]]:
    """Retrieve player or team statistics from NFL.com.

    Parameters
    ----------
    category : str
        The stat category to retrieve.

        Player categories: ``"passing"``, ``"rushing"``, ``"receiving"``,
        ``"fumbles"``, ``"tackles"``, ``"interceptions"``, ``"field-goals"``,
        ``"kickoffs"``, ``"kickoff-returns"``, ``"punts"``, ``"punt-returns"``.

        Team categories vary by position — see :func:`get_team_category_stats`.
    year : int
        The NFL season year (1970–current).
    position : str, optional
        Position group for team stats: ``"offense"``, ``"defense"``, or
        ``"special-teams"``.  Omit for player stats.

    Returns
    -------
    tuple[list[list[str]], list[str]]
        A tuple of ``(data, headers)``.

    Raises
    ------
    ValueError
        If an invalid category or position is provided.
    """
    with requests.Session() as session:
        if position:
            team_stats = util.get_team_category_stats(category, position)
            url = f'https://www.nfl.com/stats/team-stats/{position}/{team_stats}/{year}/reg/all'
        else:
            sort_by = util.get_player_category_stats(category)
            url = f'https://www.nfl.com/stats/player-stats/category/{category}/{year}/reg/all/{sort_by}/desc'

        return get_data(url, session=session)
