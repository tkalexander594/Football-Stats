import itertools
import os
import time
from typing import Iterable, Union

import polars as pl
import psutil

import Helper.helper as helper
import Utility.utility as util
from Logging.AuditLogger import AuditLogger


def extract_and_save_team_stats(
    categories: Union[str, Iterable[str]],
    years: Union[int, Iterable[int]],
    positions: Union[str, Iterable[str]],
    base_path: str,
    source_system: str,
    destination_system: str,
    audit_logger: AuditLogger,
) -> None:
    """Extract team statistics and save them as JSON files.

    Iterates over every combination of ``categories``, ``years``, and
    ``positions``, fetches data from NFL.com, and writes one JSON file per
    combination under ``base_path/<position>/<category>/<category>_<year>.json``.

    Parameters
    ----------
    categories : str or iterable of str
        Team stat categories (e.g. ``"passing"``, ``"rushing"``).
    years : int or iterable of int
        Season years to extract (1970–current season).
    positions : str or iterable of str
        Position groups: ``"offense"``, ``"defense"``, or ``"special-teams"``.
    base_path : str
        Root directory for saving JSON output files.
    source_system : str
        Label for the data source used in audit logging (e.g. ``"NFL.com"``).
    destination_system : str
        Label for the destination used in audit logging (e.g. ``"Local Storage"``).
    audit_logger : AuditLogger
        Audit logger instance for recording pipeline execution results.
    """
    current_season = util.current_nfl_regular_season()
    categories = util.ensure_iterable(categories)
    years = util.ensure_iterable(years)
    positions = util.ensure_iterable(positions)

    valid_team_positions = {'offense', 'defense', 'special-teams'}

    for category, year, position in itertools.product(categories, years, positions):
        pipeline_name = f"extract_and_save_team_stats({position}:{category})"
        start_time = time.time()
        try:
            _validate_inputs(category, year, position, current_season, valid_team_positions)

            path = os.path.join(base_path, position.lower(), category.lower())
            os.makedirs(path, exist_ok=True)

            data, headers = helper.get_stats(category, year, position)
            df = pl.DataFrame(data, schema=headers)

            file_path = os.path.join(path, f"{category}_{year}.json")
            util.write_json(file_path, df)

            _log_success(
                audit_logger, pipeline_name, start_time,
                source_system, destination_system, len(df), position, category, year,
            )
        except Exception as e:
            _log_failure(
                audit_logger, pipeline_name, start_time,
                source_system, destination_system, str(e),
            )

    print("Pipeline finished executing!")


def _validate_inputs(
    category: str,
    year: int,
    position: str,
    current_season: int,
    valid_team_positions: set,
) -> None:
    if year < 1970 or year > current_season:
        raise ValueError(f"Invalid year provided: {year}")
    if position not in valid_team_positions:
        raise ValueError(f"Invalid position provided: {position}")
    # Raises ValueError if the category/position combo is invalid
    util.get_valid_team_categories(category, position)


def _log_success(
    audit_logger: AuditLogger,
    pipeline_name: str,
    start_time: float,
    source_system: str,
    destination_system: str,
    num_records: int,
    position: str,
    category: str,
    year: int,
) -> None:
    end_time = time.time()
    audit_logger.log(
        pipeline_name=pipeline_name,
        start_time=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time)),
        end_time=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time)),
        source_system=source_system,
        destination_system=destination_system,
        num_records=num_records,
        processing_time=end_time - start_time,
        cpu_usage=psutil.cpu_percent(),
        memory_usage=psutil.virtual_memory().percent,
        status="Success",
        status_message=(
            f"Pipeline execution completed successfully for "
            f"position: {position}, category: {category}, and year: {year}"
        ),
    )


def _log_failure(
    audit_logger: AuditLogger,
    pipeline_name: str,
    start_time: float,
    source_system: str,
    destination_system: str,
    error_message: str,
) -> None:
    end_time = time.time()
    audit_logger.log(
        pipeline_name=pipeline_name,
        start_time=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time)),
        end_time=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time)),
        source_system=source_system,
        destination_system=destination_system,
        num_records=0,
        processing_time=end_time - start_time,
        cpu_usage=psutil.cpu_percent(),
        memory_usage=psutil.virtual_memory().percent,
        status="Failure",
        status_message=f"Error executing pipeline: {error_message}",
    )


if __name__ == "__main__":
    log_file_path = "Storage/Logs/audit_logs.csv"
    audit_logger = AuditLogger(log_file_path)

    extract_and_save_team_stats(
        categories=["passing", "rushing"],
        years=[2023, 2024],
        positions=["offense"],
        base_path="Storage/Raw/Team_Stats",
        source_system="NFL.com",
        destination_system="Local Storage",
        audit_logger=audit_logger,
    )
