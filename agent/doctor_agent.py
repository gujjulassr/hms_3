from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from config.settings import OPENAI_API_KEY
from tools.queue_tools import get_queue, call_next, call_patient, complete_appointment, emergency_book, get_my_patients, get_my_sessions, set_priority
from tools.session_tools import create_session, activate_session, complete_session, extend_session, cancel_session
from tools.appointment_tools import cancel_appointment, reschedule_appointment, book_appointment, check_earliest_slot
from tools.patient_tools import search_patients
from tools.report_tools import generate_session_report


class DoctorState(TypedDict):
    messages: Annotated[list, add_messages]
    user_info: str


doctor_tools = [get_queue, call_next, call_patient, complete_appointment, cancel_appointment, reschedule_appointment, book_appointment, check_earliest_slot, emergency_book, search_patients, get_my_patients, get_my_sessions, set_priority, create_session, activate_session, complete_session, extend_session, cancel_session, generate_session_report]

llm = ChatOpenAI(model="gpt-4o-mini", api_key=OPENAI_API_KEY)
llm_with_tools = llm.bind_tools(doctor_tools)


async def doctor_chatbot(state: DoctorState):
    from datetime import date as _date, timedelta as _td
    today = str(_date.today())
    tomorrow = str(_date.today() + _td(days=1))
    user_info = state.get("user_info", "")
    system_msg = SystemMessage(content=f"""You are a Hospital Management System assistant for DOCTORS.
        TODAY's date is {today}. TOMORROW is {tomorrow}. Always use these when user says 'today' or 'tomorrow'.
        Keep answers SHORT and RELEVANT. Only show what was asked. Do not dump extra data.

        CRITICAL RULES:
        - ALWAYS use tools to fetch real-time data from the database. NEVER use data from previous messages or chat history.
        - Every time the user asks about sessions, patients, queue, or any data — make a FRESH tool call. Do NOT reuse old results.
        - Never make up information. If a tool returns data, use that. If it fails, say so.

        Current logged-in doctor: {user_info}
        Use their name from above. NEVER ask for name.

        Tool selection rules:
        - 'my sessions' / 'active session' / 'session details' → use get_my_sessions. Brief answer.
        - 'my patients' / 'who visited' / 'patient list' → use get_my_patients.
        - 'queue' / 'waiting' / 'who is next' → use get_queue.
        - 'extend' past/completed session → say "Cannot extend completed/past sessions."
        - 'activate' when all completed → say "All sessions completed for today."
        - Use ONLY ONE tool per question. Do not combine tools unless asked.
        - When user says 'cancel appointment' — use cancel_appointment. It works for 'booked' and 'checked_in' statuses. Do NOT confuse with complete_appointment.
        - When user says 'emergency' / 'emergency booking' — use emergency_book. Requires patient UHID and your name. The patient must be registered in the system.
        - When user refers to a patient by name (e.g. 'amit'), first use search_patients to find their UHID, then use that UHID for the action.
        - If search_patients returns MULTIPLE results, ALWAYS list them and ask the user to pick one. NEVER auto-select.
        - 'book appointment' / 'book for patient' → use book_appointment with patient UHID and your name.
        - 'all patients' / 'fetch all patients' / 'list patients' → use search_patients with empty string to list ALL patients.
        - 'my patients' / 'today patients' → use get_my_patients for today's session only.
        - NEVER book, cancel, complete, create, or activate without explicit confirmation. Always describe what you're about to do and ask 'Shall I proceed?' first.

        REGISTRATION: When registering a new patient, collect ALL required fields:
        - Full Name, Email, Phone, Gender (Male/Female/Other), Blood Group (A+/A-/B+/B-/O+/O-/AB+/AB-)
        - Optional: Date of Birth (YYYY-MM-DD), Address, Emergency Contact Name & Phone
        Do NOT call register_patient until you have all required fields.""")
    messages = [system_msg] + state["messages"]
    response = await llm_with_tools.ainvoke(messages)
    if response.tool_calls:
        print(f"[DOCTOR] Tool calls: {[t['name'] for t in response.tool_calls]}")
    return {"messages": [response]}


def doctor_should_continue(state: DoctorState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END


doctor_graph = StateGraph(DoctorState)
doctor_graph.add_node("doctor_chatbot", doctor_chatbot)
doctor_graph.add_node("tools", ToolNode(doctor_tools))
doctor_graph.add_edge("tools", "doctor_chatbot")
doctor_graph.add_conditional_edges("doctor_chatbot", doctor_should_continue, {"tools": "tools", END: END})
doctor_graph.set_entry_point("doctor_chatbot")

doctor_app = doctor_graph.compile()
