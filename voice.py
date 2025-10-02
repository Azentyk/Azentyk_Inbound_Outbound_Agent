# app/routes/voice.py
from fastapi import APIRouter, Request, Response, HTTPException
from twilio.twiml.voice_response import VoiceResponse, Gather
import uuid, time, random
from session_manager import conversation_state, user_sessions, cleanup_session
from ai_service import generate_ai_response
from twilio_service import send_sms
from appointment_service import handle_booking_flow, handle_cancel_flow, handle_reschedule_flow
from date_utils import get_formatted_date
from model import llm_model
from prompt import (
    doctor_appointment_patient_data_extraction_prompt,
    doctor_appointment_patient_data_extraction__cancel_prompt,
    doctor_appointment_patient_data_extraction__rescheduled_prompt,
    bot_receptionist_doctor_appointment_patient_data_extraction
)
from db_utils import load_users_appointment_details, push_patient_information_data_to_db, push_patient_chat_data_to_db, load_users_df
from config import PUBLIC_URL, VOICE_VOICE
from logger import setup_logging

# Initialize logging first
logger = setup_logging()
router = APIRouter()

llm = llm_model()

@router.post("/incoming_call")
async def incoming_call(request: Request):
    form_data = await request.form()
    caller_number = form_data.get("From", "")
    session_id = str(uuid.uuid4())

    conversation_state[caller_number] = {"counter": 0}
    logger.info("Incoming call from %s session %s", caller_number, session_id)

    user_details = str(load_users_df(str(caller_number)))
    user_appointment_details = load_users_appointment_details(str(caller_number))

    print("user_details :",user_details)
    print("user_appointment_details :",user_appointment_details)

    if len(user_appointment_details) > 0:
        user_sessions[session_id] = {
            "configurable": {
                "patient_data": f"{user_details} - Incoming caller {caller_number}",
                "current_date": get_formatted_date(),
                "user_appointment_details": user_appointment_details,
                "thread_id": str(uuid.uuid4()),
            }
        }
    else:
        user_sessions[session_id] = {
            "configurable": {
                "patient_data": f"Incoming caller {caller_number} at {get_formatted_date()}",
                "user_appointment_details": "",
                "thread_id": str(uuid.uuid4()),
            }
        }

    resp = VoiceResponse()
    resp.say("Hello! I am Azentyk AI, Please wait while I check your details.", voice=VOICE_VOICE)

    result = await generate_ai_response(f"Hello! Patient details: Incoming caller {caller_number}", user_sessions[session_id])
    logger.debug("LLM result: %s", result)

    # Guard in case result shape differs
    try:
        last_msg = result["messages"][-1].content.replace("<END_OF_TURN>", "").strip()
    except Exception:
        last_msg = "Sorry, I couldn't process your request right now."

    gather = Gather(
        input="speech",
        action=f"{PUBLIC_URL}/process_incoming?session_id={session_id}",
        method="POST",
        language="en-us",
        speech_timeout="auto",
        timeout=20,
        enhanced=True,
        speech_model="googlev2_long",
        hints="yes, no, confirm, cancel, reschedule, appointment",
    )
    gather.say(last_msg, voice=VOICE_VOICE)
    resp.append(gather)
    return Response(content=str(resp), media_type="text/xml")


@router.post("/process_incoming")
async def process_incoming(request: Request):
    form_data = await request.form()
    caller_number = form_data.get("From", "")
    session_id = request.query_params.get("session_id")
    user_speech = form_data.get("SpeechResult", "").lower().strip()

    print("user_speech :",user_speech)

    resp = VoiceResponse()
    state = conversation_state.get(caller_number, {"counter": 0})
    state["counter"] += 1

    # Exit phrases
    if any(phrase in user_speech for phrase in ["thawnk..... you", "thasdswnks", "twhat's all"]):
        resp.say("You're welcome! Goodbye!", voice=VOICE_VOICE)
        cleanup_session(caller_number, session_id)
        return Response(content=str(resp), media_type="text/xml")

    user_config = user_sessions.get(session_id)
    if not user_config:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        result = await generate_ai_response(user_speech, user_config)
        last_msg = result["messages"][-1].content.replace("<END_OF_TURN>", "").replace("**", "").strip()
        print("AI Message :",last_msg)
    except Exception as e:
        logger.exception("Error during LLM/db call: %s", e)
        resp.say("Sorry, we are experiencing a temporary error. Please call again later.", voice=VOICE_VOICE)
        resp.hangup()
        return Response(content=str(resp), media_type="text/xml")

    # Booking flow
    if any(p in last_msg.lower() for p in ["we are booking an appointment","successfully booked","booked successfully","scheduling is in progress","processing your request"]):
        try:
            # Use appointment service to create and persist appointment and chat
            resp.say("Thank you! We are processing your appointment. You will receive confirmation shortly.", voice=VOICE_VOICE)
            resp.hangup()
            appointment_msg = await handle_booking_flow(result, last_msg, llm)
            # send SMS (non-blocking could be used later)
            send_sms(appointment_msg, caller_number)
            cleanup_session(caller_number, session_id)
            return Response(content=str(resp), media_type="text/xml")
        except Exception as e:
            logger.exception("Booking error: %s", e)

    # Cancel flow
    if any(p in last_msg.lower() for p in ["cancelled successfully","cancelled","canceled"]):
        try:
            resp.say("Your appointment has been cancelled successfully. Thank you.", voice=VOICE_VOICE)
            resp.hangup()
            cancel_msg = await handle_cancel_flow(result, last_msg, llm)
            send_sms(cancel_msg, caller_number)
            cleanup_session(caller_number, session_id)
            return Response(content=str(resp), media_type="text/xml")
        except Exception as e:
            logger.exception("Cancel error: %s", e)

    # Reschedule flow
    if any(p in last_msg.lower() for p in ["successfully rescheduled","rescheduled"]):
        try:
            resp.say("Your appointment has been rescheduled successfully. Thank you.", voice=VOICE_VOICE)
            resp.hangup()
            reschedule_msg = await handle_reschedule_flow(result, last_msg, llm)
            send_sms(reschedule_msg, caller_number)
            cleanup_session(caller_number, session_id)
            return Response(content=str(resp), media_type="text/xml")
        except Exception as e:
            logger.exception("Reschedule error: %s", e)

    # Continue conversation
    gather = Gather(
        input="speech",
        action=f"{PUBLIC_URL}/process_incoming?session_id={session_id}",
        method="POST",
        language="en-us",
        speech_timeout="auto",
        timeout=20,
        enhanced=True,
        speech_model="googlev2_long",
        hints="yes, no, confirm, cancel, reschedule, appointment",
    )
    gather.say(last_msg, voice=VOICE_VOICE)
    resp.append(gather)

    conversation_state[caller_number] = state
    return Response(content=str(resp), media_type="text/xml")
