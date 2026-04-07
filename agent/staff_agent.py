from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from config.settings import OPENAI_API_KEY
# from tools.queue_tools import checkin_patient, get_queue, call_next, call_patient, complete_appointment, emergency_book, set_priority, get_audit_log, get_my_patients
# from tools.patient_tools import search_patients, get_patient_details, register_patient
from tools.patient_tools import search_patients, get_patient_details, register_patient, update_patient, add_beneficiary, get_my_beneficiaries                             
from tools.doctor_tools import search_doctors
# from tools.session_tools import check_availability, create_session, activate_session, complete_session, extend_session, cancel_session
from tools.session_tools import check_availability, create_session, activate_session, complete_session, extend_session, cancel_session                                    
# from tools.appointment_tools import book_appointment, get_my_appointments,cancel_appointment
from tools.appointment_tools import book_appointment, get_my_appointments, cancel_appointment, reschedule_appointment, check_earliest_slot                                                        
from tools.rating_tools import submit_rating, get_doctor_ratings, search_feedback                                                                                         
from tools.report_tools import generate_patient_report, generate_session_report
from tools.rag_tools import query_feedback_rag, sync_feedback_store
from tools.queue_tools import checkin_patient, get_queue, call_next, call_patient, complete_appointment, emergency_book, set_priority, get_audit_log, get_my_patients,get_my_sessions  


class StaffState(TypedDict):
    messages: Annotated[list, add_messages]
    user_info: str


# staff_tools = [checkin_patient, get_queue, call_next, call_patient, complete_appointment, emergency_book, set_priority, get_audit_log, get_my_patients, search_patients, get_patient_details, register_patient, search_doctors, check_availability, book_appointment, get_my_appointments, create_session, activate_session, complete_session, extend_session, cancel_session,cancel_appointment]

staff_tools = [checkin_patient, get_queue, call_next, call_patient, complete_appointment, emergency_book, set_priority, get_audit_log, get_my_patients, get_my_sessions,  
  search_patients, get_patient_details, register_patient, update_patient, add_beneficiary, get_my_beneficiaries, search_doctors, check_availability, check_earliest_slot,   
  book_appointment, get_my_appointments, cancel_appointment, reschedule_appointment, create_session, activate_session, complete_session, extend_session, cancel_session, submit_rating,
  get_doctor_ratings, search_feedback, generate_patient_report, generate_session_report, query_feedback_rag, sync_feedback_store]


llm = ChatOpenAI(model="gpt-4o-mini", api_key=OPENAI_API_KEY)
llm_with_tools = llm.bind_tools(staff_tools)


async def staff_chatbot(state: StaffState):
    user_info = state.get("user_info", "")
    from datetime import date as _date, timedelta as _td
    today = str(_date.today())
    tomorrow = str(_date.today() + _td(days=1))
    system_msg = SystemMessage(content=f"""You are a Hospital Management System assistant for STAFF and ADMIN.
        You can help with checking in patients, managing queues, emergency bookings, setting priorities, searching patients, booking appointments, and managing sessions.
        TODAY's date is {today}. TOMORROW is {tomorrow}. Always use these when user says 'today' or 'tomorrow'.
        CRITICAL RULES:
        - ALWAYS use tools to fetch real-time data from the database. NEVER use data from previous messages or chat history.
        - Every time the user asks about patients, queue, sessions, or any data — make a FRESH tool call. Do NOT reuse old results.
        - Never make up information. If a tool returns data, use that. If it fails, say so.
        When asking about a doctor's patients, use get_my_patients with the doctor's name.
        When passing doctor names to tools, use only the last name without 'Dr.' prefix.
        CRITICAL: complete_session and cancel_session are DESTRUCTIVE actions. ONLY use them when explicitly asked to 'complete session', 'end session', or 'cancel session'.     
        NEVER use them when asked about overtime, details, or info.
                               
       CRITICAL: emergency_book creates a new emergency appointment. Only use it when explicitly asked to 'book emergency', 'create emergency', or 'add emergency'. If asked 'is there any emergency' or 'show emergency', use get_queue instead.
                               

        Tool selection rules:
            - 'all patients' or 'list patients' → use search_patients with empty string.
            - 'patient details' with name/UHID → use get_patient_details.
            - 'all doctors' or 'list doctors' → use search_doctors with empty string.
            - 'doctor sessions' → use get_my_sessions with doctor name.
            - 'schedule session' / 'create session' → use create_session with doctor name, date (YYYY-MM-DD), start_time (HH:MM), end_time (HH:MM). You CAN create sessions for ANY doctor.
            - 'extend session' → use extend_session. Pass total overtime minutes from original end time, not extra minutes.
            - 'show queue' → use get_queue with doctor name.
            - When passing doctor/patient names to tools, use only last name without 'Dr.' prefix.
            - If search_patients or search_doctors returns MULTIPLE results, ALWAYS list ALL of them and ask the user to pick one. NEVER auto-select.
            - NEVER book, cancel, complete, create, or activate without explicit confirmation from the user. Always describe what you're about to do and ask 'Shall I proceed?' before taking any action.
            - Always use 24-hour format for time (e.g., '22:00' not '10:00 PM').
            - When user says 'schedule a session for tomorrow for X', use create_session. Ask for start time and end time if not provided.

                               
        Book an appointment for a patient with a doctor. Set confirm=True only after patient confirms.
        When checking in a patient by name, first use search_patients to find their UHID, then use checkin_patient with the UHID.

        REGISTRATION: When registering a new patient, you MUST collect ALL required fields before calling register_patient:
        - Full Name (required)
        - Email (required)
        - Phone (required)
        - Gender: Male/Female/Other (required)
        - Blood Group: A+/A-/B+/B-/O+/O-/AB+/AB- (required)
        - Date of Birth: YYYY-MM-DD (optional)
        - Address (optional)
        - Emergency Contact Name (optional)
        - Emergency Contact Phone (optional)
        Ask for ALL required fields first. Do NOT call register_patient until you have all required fields.
        When searching patients, use only first name or last name, not full name.
        Current logged-in user: {user_info}""")
    messages = [system_msg] + state["messages"]
    response = await llm_with_tools.ainvoke(messages)
    if response.tool_calls:
        print(f"[STAFF] Tool calls: {[t['name'] for t in response.tool_calls]}")
    return {"messages": [response]}


def staff_should_continue(state: StaffState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END


staff_graph = StateGraph(StaffState)
staff_graph.add_node("staff_chatbot", staff_chatbot)
staff_graph.add_node("tools", ToolNode(staff_tools))
staff_graph.add_edge("tools", "staff_chatbot")
staff_graph.add_conditional_edges("staff_chatbot", staff_should_continue, {"tools": "tools", END: END})
staff_graph.set_entry_point("staff_chatbot")

staff_app = staff_graph.compile()
