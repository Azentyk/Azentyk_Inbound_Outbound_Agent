# app/utils/session_manager.py
from typing import Dict, Set

conversation_state: Dict[str, dict] = {}  # caller_number -> state
user_sessions: Dict[str, dict] = {}       # session_id -> user config
processed_sessions: Set[str] = set()

def cleanup_session(caller_number: str, session_id: str):
    conversation_state.pop(caller_number, None)
    user_sessions.pop(session_id, None)
    processed_sessions.add(session_id)
