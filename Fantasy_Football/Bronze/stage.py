"""Bronze staging pipeline.

Reads all per-season JSON files from a Raw directory, concatenates them into a
single Polars DataFrame (with a ``Season`` column), and writes the result as a
Delta Lake table.

Usage (command line)
--------------------
Set ``read_path`` and ``write_path`` at the bottom of this file and run::

    python stage.py

Usage (import)
--------------
::

    from Bronze.stage import write_bronze, read_delta

    write_bronze(
        read_path="Storage/Raw/Player_Stats/passing",
        write_path="Storage/Bronze/player_stats/passing",
        mode="overwrite",
    )
"""
import logging

import polars as pl

import Utility.utility as util


def write_bronze(read_path: str, write_path: str, mode: str = "overwrite") -> None:
    """Concatenate Raw JSON files and write to a Bronze Delta Lake table.

    Parameters
    ----------
    read_path : str
        Directory containing the raw ``*.json`` season files.
    write_path : str
        Destination path for the Delta Lake table.
    mode : str, optional
        Delta write mode (default ``"overwrite"``).
    """
    df = util.concatenate_json_files(read_path)
    try:
        df.write_delta(write_path, mode=mode)
        logging.info("Delta table successfully created: %s", write_path)
    except Exception as e:
        logging.error("Failed to write Delta table to %s: %s", write_path, e)
        raise


def read_delta(path: str) -> pl.DataFrame:
    """Read a Delta Lake table into a Polars DataFrame.

    Parameters
    ----------
    path : str
        Path to the Delta Lake table directory.

    Returns
    -------
    pl.DataFrame
    """
    df = pl.read_delta(path)
    logging.info("Delta table successfully read: %s", path)
    return df


def read_csv(path: str) -> pl.DataFrame:
    """Read a CSV file into a Polars DataFrame.

    Parameters
    ----------
    path : str
        Path to the CSV file.

    Returns
    -------
    pl.DataFrame
    """
    df = pl.read_csv(path)
    logging.info("CSV successfully read: %s", path)
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Edit these paths before running
    read_path = "Storage/Raw/Player_Stats/passing"
    write_path = "Storage/Bronze/player_stats/passing"

    write_bronze(read_path=read_path, write_path=write_path, mode="overwrite")
