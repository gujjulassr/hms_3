from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from agent.patient_agent import patient_app
from agent.doctor_agent import doctor_app
from agent.staff_agent import staff_app
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage


memory = MemorySaver()


class SupervisorState(TypedDict):
    messages: Annotated[list, add_messages]
    role: str
    user_info: str


async def route_to_agent(state: SupervisorState):
    role = state.get("role", "patient")
    messages = state["messages"]
    user_info = state.get("user_info", "")

    if role == "doctor":
        result = await doctor_app.ainvoke({"messages": messages, "user_info": user_info})
    elif role in ["nurse", "staff", "admin"]:
        result = await staff_app.ainvoke({"messages": messages, "user_info": user_info})
    else:
        result = await patient_app.ainvoke({"messages": messages, "user_info": user_info})

    return {"messages": result["messages"]}


graph = StateGraph(SupervisorState)
graph.add_node("supervisor", route_to_agent)
graph.set_entry_point("supervisor")
graph.add_edge("supervisor", END)

app = graph.compile(checkpointer=memory)


async def get_response(message: str, user: dict) -> str:
    """Route a chat message to the appropriate agent and return the text response."""
    role = user.get("role", "patient")
    name = user.get("name", "Unknown")
    email = user.get("email", "")

    # Build user_info string for agent context
    user_info = f"Name: {name}, Email: {email}, Role: {role}"

    # Add UHID for patients
    if role == "patient":
        from sqlalchemy import select
        from config.database import AsyncSessionLocal as async_session
        from models.patient import Patient
        from models.user import User
        async with async_session() as db:
            result = await db.execute(
                select(Patient, User).join(User, Patient.user_id == User.id)
                .where(User.email == email)
            )
            row = result.first()
            if row:
                patient, u = row
                user_info += f", UHID: {patient.uhid}"

    # Use email as thread_id for conversation memory
    thread_id = email or "default"
    config = {"configurable": {"thread_id": thread_id}}

    result = await app.ainvoke(
        {"messages": [HumanMessage(content=message)], "role": role, "user_info": user_info},
        config=config
    )

    # Extract the last AI message
    messages = result.get("messages", [])
    for msg in reversed(messages):
        if hasattr(msg, "content") and msg.content and not hasattr(msg, "tool_calls"):
            return msg.content
        if hasattr(msg, "content") and msg.content and hasattr(msg, "tool_calls") and not msg.tool_calls:
            return msg.content

    return "I couldn't process that request. Please try again."
