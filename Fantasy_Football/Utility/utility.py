import datetime
import logging
import os
from typing import List, Optional, Union

import polars as pl

# ---------------------------------------------------------------------------
# Module-level constants — single source of truth for category/position data
# ---------------------------------------------------------------------------

_PLAYER_CATEGORY_SORT_BY: dict = {
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

_TEAM_POSITION_MAP: dict = {
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


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def write_json(path: str, df: pl.DataFrame) -> None:
    """Save a Polars DataFrame to a JSON file.

    Parameters
    ----------
    path : str
        Destination file path.
    df : pl.DataFrame
        DataFrame to write.
    """
    df.write_json(path)
    logging.info("JSON file successfully created: %s", path)


def write_delta(path: str, df: pl.DataFrame) -> None:
    """Save a Polars DataFrame as a Delta Lake table.

    Parameters
    ----------
    path : str
        Destination directory path for the Delta table.
    df : pl.DataFrame
        DataFrame to write.
    """
    df.write_delta(path)
    logging.info("Delta file successfully created: %s", path)


def write_csv(path: str, df: pl.DataFrame) -> None:
    """Save a Polars DataFrame to a CSV file.

    Parameters
    ----------
    path : str
        Destination file path.
    df : pl.DataFrame
        DataFrame to write.
    """
    df.write_csv(path)
    logging.info("CSV file successfully created: %s", path)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def get_valid_player_categories(categories: Union[str, List[str]]) -> Union[str, List[str]]:
    """Validate and return only known player stat categories.

    Parameters
    ----------
    categories : str or list of str
        One or more player stat category names.

    Returns
    -------
    str or list of str
        The validated category name(s), unchanged.

    Raises
    ------
    ValueError
        If any category is not a recognised player stat category.
    TypeError
        If ``categories`` is not a string or list of strings.
    """
    if isinstance(categories, str):
        if categories not in _PLAYER_CATEGORY_SORT_BY:
            raise ValueError(
                f"Invalid player category '{categories}'. "
                f"Valid options: {sorted(_PLAYER_CATEGORY_SORT_BY)}"
            )
        return categories
    elif isinstance(categories, list):
        invalid = [c for c in categories if c not in _PLAYER_CATEGORY_SORT_BY]
        if invalid:
            raise ValueError(
                f"Invalid player categories {invalid}. "
                f"Valid options: {sorted(_PLAYER_CATEGORY_SORT_BY)}"
            )
        return categories
    else:
        raise TypeError("Categories must be a string or a list of strings")


def get_valid_team_categories(category: str, position: str) -> str:
    """Validate a team stat category and position combination.

    Parameters
    ----------
    category : str
        The team stat category name.
    position : str
        The position group (``"offense"``, ``"defense"``, or ``"special-teams"``).

    Returns
    -------
    str
        The validated category name, unchanged.

    Raises
    ------
    ValueError
        If the position or category/position combination is not recognised.
    """
    if position not in _TEAM_POSITION_MAP:
        raise ValueError(
            f"Invalid position '{position}'. Valid options: {sorted(_TEAM_POSITION_MAP)}"
        )
    if category not in _TEAM_POSITION_MAP[position]:
        raise ValueError(
            f"Invalid category '{category}' for position '{position}'. "
            f"Valid options: {sorted(_TEAM_POSITION_MAP[position])}"
        )
    return _TEAM_POSITION_MAP[position][category]


def ensure_iterable(categories: Union[str, list, tuple, set]) -> Union[list, tuple, set]:
    """Ensure the input is iterable, converting scalars to a single-item list.

    Parameters
    ----------
    categories : str, list, tuple, or set
        Input value to normalise.

    Returns
    -------
    list, tuple, or set
        The original value if already iterable, otherwise ``[categories]``.
    """
    if not isinstance(categories, (list, tuple, set)):
        categories = [categories]
    return categories


# ---------------------------------------------------------------------------
# Season helpers
# ---------------------------------------------------------------------------

def current_nfl_regular_season() -> int:
    """Return the current NFL regular season year.

    The NFL regular season starts in September and ends in February
    (including the Super Bowl). Calls made in January on or before the 9th
    return the prior calendar year as the season identifier.

    Returns
    -------
    int
        The four-digit NFL season year, e.g. ``2023``.
    """
    today = datetime.date.today()
    if today.month == 1 and today.day <= 9:
        return today.year - 1
    return today.year


# ---------------------------------------------------------------------------
# Category/URL parameter lookups
# ---------------------------------------------------------------------------

def get_player_category_stats(category: str) -> str:
    """Return the NFL.com ``sort_by`` URL parameter for a player stat category.

    Parameters
    ----------
    category : str
        A player stat category (e.g. ``"passing"``, ``"rushing"``).

    Returns
    -------
    str
        The corresponding ``sort_by`` slug used in NFL.com player stat URLs.

    Raises
    ------
    ValueError
        If ``category`` is not a recognised player stat category.
    """
    if category not in _PLAYER_CATEGORY_SORT_BY:
        raise ValueError(
            f"Invalid player category '{category}'. "
            f"Valid options: {sorted(_PLAYER_CATEGORY_SORT_BY)}"
        )
    return _PLAYER_CATEGORY_SORT_BY[category]


def get_team_category_stats(category: str, position: str) -> str:
    """Return the NFL.com URL slug for a team stat category and position.

    Parameters
    ----------
    category : str
        The team stat category. Valid values depend on ``position``:

        - Offense: ``"passing"``, ``"rushing"``, ``"receiving"``,
          ``"scoring"``, ``"downs"``
        - Defense: ``"passing"``, ``"rushing"``, ``"receiving"``,
          ``"scoring"``, ``"tackles"``, ``"downs"``, ``"fumbles"``,
          ``"interceptions"``
        - Special Teams: ``"field-goals"``, ``"scoring"``,
          ``"kickoffs"``, ``"kickoff-returns"``, ``"punts"``,
          ``"punt-returns"``
    position : str
        The position group: ``"offense"``, ``"defense"``, or
        ``"special-teams"``.

    Returns
    -------
    str
        The URL slug for the category/position combination.

    Raises
    ------
    ValueError
        If the position or category/position combination is not recognised.
    """
    if position not in _TEAM_POSITION_MAP:
        raise ValueError(
            f"Invalid position '{position}'. Valid options: {sorted(_TEAM_POSITION_MAP)}"
        )
    if category not in _TEAM_POSITION_MAP[position]:
        raise ValueError(
            f"Invalid category '{category}' for position '{position}'. "
            f"Valid options: {sorted(_TEAM_POSITION_MAP[position])}"
        )
    return _TEAM_POSITION_MAP[position][category]


# ---------------------------------------------------------------------------
# File utilities
# ---------------------------------------------------------------------------

def _extract_year(filename: str) -> Optional[int]:
    """Extract the year from a filename like ``passing_2023.json``.

    Parameters
    ----------
    filename : str
        The filename to parse.

    Returns
    -------
    int or None
        The extracted four-digit year, or ``None`` if parsing fails.
    """
    try:
        return int(filename.split("_")[-1].split(".")[0])
    except (ValueError, IndexError):
        return None


def concatenate_json_files(directory_path: str) -> pl.DataFrame:
    """Read all JSON files in a directory and concatenate them into one DataFrame.

    A ``Season`` column (``int``) is added to each file's rows, parsed from
    the filename (e.g. ``passing_2023.json`` → ``Season = 2023``).  Files are
    processed in sorted order for deterministic output.

    Parameters
    ----------
    directory_path : str
        Path to the directory containing ``*.json`` files.

    Returns
    -------
    pl.DataFrame
        Concatenated DataFrame with a ``Season`` column appended.
    """
    all_dfs = []
    for filename in sorted(os.listdir(directory_path)):
        if filename.endswith(".json"):
            file_path = os.path.join(directory_path, filename)
            year = _extract_year(filename)
            df = pl.read_json(file_path)
            df = df.with_columns(Season=pl.lit(year))
            all_dfs.append(df)
    return pl.concat(all_dfs)
