import logging
import csv
import uuid

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create a CSV file handler in append mode
csv_handler = logging.FileHandler("/Users/treveralexander/Library/CloudStorage/OneDrive-EY/Personal/DE_Project/Storage/Logs/audit_logs.csv", mode="a")
csv_formatter = logging.Formatter("%(message)s")
csv_handler.setFormatter(csv_formatter)
logger.addHandler(csv_handler)

def audit_log(pipeline_name,start_time, end_time, source_system, destination_system, num_records, processing_time, cpu_usage, memory_usage, status, status_message):

    # Generate a unique ID for this execution
    execution_id = str(uuid.uuid4())

    # Write CSV headers if the file is empty (using formatted times in headers too)
    with open("/Users/treveralexander/Library/CloudStorage/OneDrive-EY/Personal/DE_Project/Storage/Logs/audit_logs.csv", "r+") as csvfile:
        reader = csv.reader(csvfile)
        if not list(reader):  # Check if the file is empty
            csvfile.seek(0)  # Rewind to the beginning
            writer = csv.writer(csvfile)
            writer.writerow(["ID"
                             ,"Pipeline_Name"
                             ,"Start_Time"
                             ,"End_Time"
                             ,"Source_System"
                             ,"Destination_System"
                             ,"Number_of_Records"
                             ,"Processing Time (seconds)"
                             ,"CPU Usage (%)"
                             ,"Memory Usage (MB)"
                             ,"Status"
                             ,"Status_Message"
                             ])
            
            csvfile.truncate()  # Remove any extra newlines

    # Log execution details with status based on 'successful' flag
    logger.info(f"{execution_id},{pipeline_name},{start_time},{end_time},{source_system},{destination_system},{num_records},{processing_time:.2f},{cpu_usage:.2f},{memory_usage:.2f},{status},{status_message}")

    # Close the CSV handler (optional, but recommended)
    csv_handler.close()
