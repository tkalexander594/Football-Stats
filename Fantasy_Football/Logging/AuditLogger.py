import csv
import fcntl
import uuid
from pathlib import Path
from typing import Any


class AuditLogger:
    """Singleton audit logger that appends pipeline execution records to a CSV file.

    Only one instance can exist per process.  The CSV file is created with
    headers on first use if it does not already exist.

    CSV columns
    -----------
    ID, Pipeline_Name, Start_Time, End_Time, Source_System,
    Destination_System, Number_of_Records, Processing_Time_Seconds,
    CPU_Usage_Percent, Memory_Usage_MB, Status, Status_Message

    Notes
    -----
    File writes are protected with an exclusive ``fcntl`` lock to support
    concurrent pipeline executions writing to the same log file.

    Raises
    ------
    ValueError
        If a second instantiation is attempted with a different ``log_file_path``
        than the one used for the first instance.
    """

    _instance = None

    def __new__(cls, log_file_path: str) -> "AuditLogger":
        if cls._instance is None:
            cls._instance = super(AuditLogger, cls).__new__(cls)
            cls._instance.log_file_path = Path(log_file_path)
            cls._instance._ensure_headers()
        elif cls._instance.log_file_path != Path(log_file_path):
            raise ValueError(
                f"AuditLogger is already initialised with path "
                f"'{cls._instance.log_file_path}'. Cannot re-initialise with "
                f"'{log_file_path}'."
            )
        return cls._instance

    def _ensure_headers(self) -> None:
        """Write the CSV header row if the log file is new or empty."""
        headers = [
            "ID", "Pipeline_Name", "Start_Time", "End_Time", "Source_System",
            "Destination_System", "Number_of_Records", "Processing_Time_Seconds",
            "CPU_Usage_Percent", "Memory_Usage_MB", "Status", "Status_Message"
        ]
        if not self.log_file_path.exists() or self.log_file_path.stat().st_size == 0:
            with open(self.log_file_path, "w", newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)

    def log(self, **kwargs: Any) -> None:
        """Append a pipeline execution record to the audit log.

        Parameters
        ----------
        pipeline_name : str
        start_time : str
        end_time : str
        source_system : str
        destination_system : str
        num_records : int
        processing_time : float
        cpu_usage : float
        memory_usage : float
        status : str
        status_message : str
        """
        log_data = [
            str(uuid.uuid4()),
            kwargs.get('pipeline_name', ''),
            kwargs.get('start_time', ''),
            kwargs.get('end_time', ''),
            kwargs.get('source_system', ''),
            kwargs.get('destination_system', ''),
            kwargs.get('num_records', 0),
            f"{kwargs.get('processing_time', 0):.2f}",
            f"{kwargs.get('cpu_usage', 0):.2f}",
            f"{kwargs.get('memory_usage', 0):.2f}",
            kwargs.get('status', ''),
            kwargs.get('status_message', '')
        ]

        with open(self.log_file_path, "a", newline='') as csvfile:
            fcntl.flock(csvfile.fileno(), fcntl.LOCK_EX)
            try:
                writer = csv.writer(csvfile)
                writer.writerow(log_data)
            finally:
                fcntl.flock(csvfile.fileno(), fcntl.LOCK_UN)
