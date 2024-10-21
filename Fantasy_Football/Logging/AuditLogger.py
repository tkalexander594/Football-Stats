import csv
import uuid
from typing import Any
from pathlib import Path
import fcntl

class AuditLogger:
    _instance = None

    def __new__(cls, log_file_path: str):
        if cls._instance is None:
            cls._instance = super(AuditLogger, cls).__new__(cls)
            cls._instance.log_file_path = Path(log_file_path)
            cls._instance._ensure_headers()
        return cls._instance

    def _ensure_headers(self) -> None:
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
        execution_id = str(uuid.uuid4())
        log_data = [
            execution_id,
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