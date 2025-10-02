from typing import Optional, List, Dict
from datetime import datetime
import hashlib
import pandas as pd
from pymongo import MongoClient
import logging
from typing import Optional, List, Dict,Tuple
from logger import setup_logging

# Initialize MongoDB client
url = r"mongodb://azentyk-doctor-appointment-app-server:ROtcf6VzE2Jj2Etn0D3QY9LbrSTs4MEgld2hynMw3R46gl8cuL1D70qvx4DjQvogoyBDVO2z1MJxACDb04M0BA==@azentyk-doctor-appointment-app-server.mongo.cosmos.azure.com:10255/?ssl=true&retrywrites=false&replicaSet=globaldb&maxIdleTimeMS=120000&appName=@azentyk-doctor-appointment-app-server@"
client = MongoClient(url)
# client = MongoClient("mongodb+srv://azentyk:azentyk123@cluster0.b9aaq47.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["patient_db"]

# Collections
patient_information_details_table_collection = db["patient_information_details_table"]
patient_chat_table_collection = db["patient_chat_table"]
chat_collection = db["patient_each_chat_table"]
patient_credentials_collection = db["patient_credentials"]

# Initialize logging first
logger = setup_logging()


def init_db():
    try:
        collections = db.list_collection_names()
        logger.info(f"MongoDB connected. Existing collections: {collections}")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}", exc_info=True)

    
# --------------------------
# Load Users
# --------------------------
def load_users_df(user_phone_number: str = None) -> pd.DataFrame | str:
    """Load users from MongoDB and optionally filter by phone_number"""
    try:
        cursor = patient_credentials_collection.find({})
        users_data = list(cursor)
        df = pd.DataFrame(users_data)

        if '_id' in df.columns:
            df.drop('_id', axis=1, inplace=True)

        expected_columns = ["firstname", "email", "phone", "country", "state", "location", "city", "password"]
        for col in expected_columns:
            if col not in df.columns:
                df[col] = None

        if user_phone_number:
            filtered_df = df[df["phone"].astype(str).str[-10:] == str(user_phone_number)[-10:]]
            filtered_df = filtered_df[['firstname','email','phone']]
            if filtered_df.empty:
                return "No match found"
            return filtered_df.to_dict(orient="records")

        return df

    except Exception as e:
        print("Error in load_users_df:", e)
        return pd.DataFrame(columns=["firstname", "email", "phone", "country", "state", "location", "city", "password"])


def load_users_appointment_details(phone_number: str = None) -> pd.DataFrame | str:
    """Load users appointment details from MongoDB and optionally filter by phone_number"""
    try:
        cursor = patient_information_details_table_collection.find({})
        users_data = list(cursor)
        df = pd.DataFrame(users_data)

        if '_id' in df.columns:
            df.drop('_id', axis=1, inplace=True)

        expected_columns = [
            "appointment_id", "username", "phone_number", "mail", "location", 
            "hospital_name", "specialization", "appointment_booking_date",
            "appointment_booking_time", "appointment_status"
        ]
        for col in expected_columns:
            if col not in df.columns:
                df[col] = None

        if phone_number:
            filtered_df = df[df["phone_number"].astype(str).str[-10:] == str(phone_number)[-10:]]
            # Filter only pending appointments (case-insensitive)
            filtered_df = filtered_df[filtered_df["appointment_status"].str.lower() == "pending"]
            if filtered_df.empty:
                return "No match found"

            return filtered_df.to_dict(orient="records")

        return df

    except Exception as e:
        print("Error in load_users_appointment_details:", e)
        return pd.DataFrame(columns=expected_columns)
    
def push_patient_information_data_to_db(patient_data: dict):
    """Insert patient information into database"""
    try:
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")

        patient_data['date'] = str(current_date)
        patient_data['time'] = str(current_time)

        insert_result = patient_information_details_table_collection.insert_one(patient_data)
        logger.info(f"Inserted Patient Information Data ID: {insert_result.inserted_id}")
        return insert_result
    except Exception as e:
        logger.error(f"Error inserting patient information: {e}")
        return None

def push_patient_chat_data_to_db(patient_data: dict):
    """Insert patient chat data into database"""
    try:
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")

        patient_data['date'] = str(current_date)
        patient_data['time'] = str(current_time)

        insert_result = patient_chat_table_collection.insert_one(patient_data)
        logger.info(f"Inserted Patient Chat Data ID: {insert_result.inserted_id}")
        return insert_result
    except Exception as e:
        logger.error(f"Error inserting patient chat data: {e}")
        return None

def patient_each_chat_table_collection(message_text: str):
    """Insert individual chat message into database"""
    try:
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")

        patient_data = {
            'date': current_date,
            'time': current_time,
            'message': message_text.strip()
        }

        insert_result = chat_collection.insert_one(patient_data)
        logger.info(f"Inserted Patient Chat Data ID: {insert_result.inserted_id}")
        return insert_result
    except Exception as e:
        logger.error(f"Error inserting chat message: {e}")
        return None

def update_appointment_status(appointment_id: str,new_status: str,new_date: str = None,new_time: str = None) -> dict:
    """
    Update appointment details in MongoDB.
    
    - For booking/cancel: only updates appointment_status
    - For reschedule: updates appointment_status + date + time

    Args:
        appointment_id (str): The appointment ID to match
        new_status (str): The new status ("booking in progress", "confirmed", "pending","rescheduled","cancelled")
        new_date (str, optional): The new appointment date (required if rescheduling)
        new_time (str, optional): The new appointment time (required if rescheduling)

    Returns:
        dict: A summary of the update result
    """

    update_fields = {"appointment_status": new_status}

    # If rescheduling, also update date & time
    if new_status.lower() == "rescheduled":
        if not new_date or not new_time:
            return {
                "success": False,
                "message": "Reschedule requires both date and time."
            }
        update_fields["appointment_booking_date"] = new_date
        update_fields["appointment_booking_time"] = new_time

    result = patient_information_details_table_collection.update_one(
        {"appointment_id": appointment_id},  # filter by appointment_id
        {"$set": update_fields}
    )

    if result.modified_count > 0:
        if new_status.lower() == "rescheduled":
            return {
                "success": True,
                "message": f"Appointment {appointment_id} rescheduled to {new_date} at {new_time}"
            }
        else:
            return {
                "success": True,
                "message": f"Appointment {appointment_id} updated to '{new_status}'"
            }
    elif result.matched_count > 0:
        return {
            "success": False,
            "message": f"Appointment {appointment_id} already has status '{new_status}'"
        }
    else:
        return {
            "success": False,
            "message": f"No appointment found with ID {appointment_id}"
        }

