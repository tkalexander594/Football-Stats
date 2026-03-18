"""Bronze pipeline — player receiving stats.

Reads all per-season receiving JSON files from Raw storage, casts columns to
their proper types, and writes the result as a Bronze Delta Lake table.

Usage
-----
Set ``read_path`` and ``write_path`` at the bottom of this file and run::

    python receiving.py
"""
import logging

import polars as pl

import Utility.utility as util


def stage_receiving(read_path: str, write_path: str, mode: str = "overwrite") -> None:
    """Read raw receiving JSON files, cast types, and write to Bronze Delta table.

    Parameters
    ----------
    read_path : str
        Directory containing the raw receiving ``*.json`` season files.
    write_path : str
        Destination path for the Bronze Delta Lake table.
    mode : str, optional
        Delta write mode (default ``"overwrite"``).
    """
    df = util.concatenate_json_files(read_path)

    df = df.with_columns([
        pl.col("Player").cast(pl.Utf8),
        pl.col("Rec").cast(pl.Int32),
        pl.col("Yds").cast(pl.Int32),
        pl.col("TD").cast(pl.Int32),
        pl.col("20+").cast(pl.Int32),
        pl.col("40+").cast(pl.Int32),
        pl.col("LNG").cast(pl.Int32),
        pl.col("Rec 1st").cast(pl.Int32),
        pl.col("1st%").cast(pl.Float64).round(2),
        pl.col("Rec FUM").cast(pl.Int32),
        pl.col("Rec YAC/R").cast(pl.Int32),
        pl.col("Tgts").cast(pl.Int32),
        pl.col("Season").cast(pl.Int32),
    ])

    df.write_delta(write_path, mode=mode, delta_write_options={"schema_mode": "overwrite"})
    logging.info("Delta table successfully created: %s", write_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Edit these paths before running
    read_path = "Storage/Raw/Player_Stats/receiving"
    write_path = "Storage/Bronze/player_stats/receiving"

    stage_receiving(read_path=read_path, write_path=write_path, mode="overwrite")
