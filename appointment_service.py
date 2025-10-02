# app/services/appointment_service.py
import random, time
from prompt import (
    doctor_appointment_patient_data_extraction_prompt,
    doctor_appointment_patient_data_extraction__cancel_prompt,
    doctor_appointment_patient_data_extraction__rescheduled_prompt,
)
from db_utils import push_patient_information_data_to_db, push_patient_chat_data_to_db, update_appointment_status
from logger import setup_logging



# Initialize logging first
logger = setup_logging()

async def handle_booking_flow(llm_result, last_msg, llm):
    patient_data = doctor_appointment_patient_data_extraction_prompt(llm).invoke(str(llm_result['messages']))
    patient_data['appointment_status'] = 'Pending'
    safe_username = (patient_data.get('username') or 'USER')[:4]
    appointment_id = f"APT-{safe_username}-{int(time.time())}{random.randint(1000,9999)}"
    appointment = {"appointment_id": appointment_id, **patient_data}
    chat_df = {'patient_name': patient_data.get('username'), 'chat_history': last_msg}

    push_patient_information_data_to_db(appointment)
    push_patient_chat_data_to_db(chat_df)

    appointment_msg = f"""
Hello {patient_data.get('username', 'Patient')},

Your appointment has been successfully booked ✅.

📅 Date & Time: {appointment.get('appointment_booking_date', 'To be confirmed')}, {appointment.get('appointment_booking_time', 'To be confirmed')}
🏥 Hospital: {appointment.get('hospital_name', 'To be confirmed')}
👨‍⚕️ Specialization: {appointment.get('specialization', 'Assigned shortly')}
📍 Location: {appointment.get('location', 'Assigned shortly')}

Your Appointment ID: {appointment.get('appointment_id', 'N/A')}

You will receive a confirmation call or SMS shortly.

Thank you for choosing our Azentyk AI service!
"""
    return appointment_msg

async def handle_cancel_flow(llm_result, last_msg, llm):
    patient_data = doctor_appointment_patient_data_extraction__cancel_prompt(llm).invoke(str(llm_result['messages']))
    update_appointment_status(patient_data['appointment_id'], patient_data['appointment_status'])
    push_patient_chat_data_to_db({'patient_name': patient_data.get('username'), 'chat_history': last_msg})
    cancel_msg = f"""
Hello {patient_data.get('username')},

Your appointment has been successfully cancelled 🛑.

Appointment ID: {patient_data.get('appointment_id', 'N/A')}

If you wish to book a new appointment, please contact us or visit our portal.

Thank you for choosing our Azentyk AI service!
"""
    return cancel_msg

async def handle_reschedule_flow(llm_result, last_msg, llm):
    patient_data = doctor_appointment_patient_data_extraction__rescheduled_prompt(llm).invoke(str(llm_result['messages']))
    print("patient_data - reschuled :",patient_data)
    update_appointment_status(patient_data['appointment_id'], patient_data['appointment_status'], patient_data.get('new_date'), patient_data.get('new_time'))
    push_patient_chat_data_to_db({'patient_name': patient_data.get('username'), 'chat_history': last_msg})
    reschedule_msg = f"""
Hello {patient_data.get('username')},

Your appointment has been successfully rescheduled 🔄.

Appointment ID: {patient_data.get('appointment_id', 'N/A')}

Thank you for choosing our Azentyk AI service!
"""
    return reschedule_msg
