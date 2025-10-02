# app/utils/date_utils.py
from datetime import datetime

def get_formatted_date():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
