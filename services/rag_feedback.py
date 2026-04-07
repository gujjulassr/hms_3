"""
RAG (Retrieval Augmented Generation) for patient feedback.
Uses ChromaDB as vector store and OpenAI for embeddings + generation.
"""
import os
import chromadb
from openai import OpenAI
from sqlalchemy import select
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
feedback_collection = chroma_client.get_or_create_collection(
    name="patient_feedback",
    metadata={"description": "Patient feedback and ratings for doctors"}
)


def get_embedding(text: str) -> list:
    """Get embedding from OpenAI."""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


def add_feedback_to_store(feedback_id: str, patient_name: str, doctor_name: str,
                          specialization: str, rating: int, feedback_text: str,
                          date: str = ""):
    """Add a feedback entry to the vector store."""
    if not feedback_text:
        feedback_text = f"Rating: {rating}/5 for {doctor_name}"

    document = (
        f"Patient {patient_name} rated {doctor_name} ({specialization}) "
        f"{rating}/5 stars. Feedback: {feedback_text}. Date: {date}"
    )

    metadata = {
        "patient_name": patient_name,
        "doctor_name": doctor_name,
        "specialization": specialization,
        "rating": rating,
        "date": date,
    }

    # Check if already exists
    existing = feedback_collection.get(ids=[feedback_id])
    if existing and existing["ids"]:
        feedback_collection.update(
            ids=[feedback_id],
            documents=[document],
            metadatas=[metadata]
        )
    else:
        feedback_collection.add(
            ids=[feedback_id],
            documents=[document],
            metadatas=[metadata],
            embeddings=[get_embedding(document)]
        )


def search_feedback(query: str, n_results: int = 10, doctor_name: str = "") -> list:
    """Search feedback using semantic similarity."""
    where_filter = None
    if doctor_name:
        where_filter = {"doctor_name": {"$eq": doctor_name}}

    results = feedback_collection.query(
        query_embeddings=[get_embedding(query)],
        n_results=n_results,
        where=where_filter if where_filter else None
    )

    feedbacks = []
    if results and results["documents"]:
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            feedbacks.append({
                "text": doc,
                "doctor": meta.get("doctor_name", ""),
                "rating": meta.get("rating", 0),
                "patient": meta.get("patient_name", ""),
                "date": meta.get("date", ""),
            })
    return feedbacks


def generate_rag_response(query: str, doctor_name: str = "") -> str:
    """RAG: Retrieve relevant feedback → Generate insightful response."""
    # Retrieve
    feedbacks = search_feedback(query, n_results=10, doctor_name=doctor_name)

    if not feedbacks:
        return "No feedback found matching your query."

    # Build context
    context = "\n".join([
        f"- {f['patient']} rated {f['doctor']} {f['rating']}/5: {f['text']}"
        for f in feedbacks
    ])

    # Generate
    prompt = f"""Based on the following patient feedback data, answer this question: "{query}"

Feedback Data:
{context}

Provide a clear, insightful summary. Include:
1. Overall sentiment
2. Key themes or patterns
3. Specific mentions if relevant
4. Average rating if applicable
Keep it concise and professional."""

    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
    )
    return response.choices[0].message.content


async def sync_feedback_to_vectorstore():
    """Sync all ratings from PostgreSQL to ChromaDB vector store."""
    from config.database import AsyncSessionLocal as async_session
    from models.rating import Rating
    from models.patient import Patient
    from models.doctor import Doctor
    from models.user import User

    async with async_session() as db:
        result = await db.execute(
            select(Rating, Patient, User, Doctor)
            .join(Patient, Rating.patient_id == Patient.id)
            .join(User, Patient.user_id == User.id)
            .join(Doctor, Rating.doctor_id == Doctor.id)
        )
        rows = result.all()

        count = 0
        for rating, patient, pat_user, doctor in rows:
            doc_user_r = await db.execute(select(User).where(User.id == doctor.user_id))
            doc_user = doc_user_r.scalars().first()

            add_feedback_to_store(
                feedback_id=str(rating.id),
                patient_name=pat_user.full_name,
                doctor_name=doc_user.full_name if doc_user else "",
                specialization=doctor.specialization or "",
                rating=rating.rating,
                feedback_text=rating.feedback or "",
                date=str(rating.created_at)[:10] if rating.created_at else ""
            )
            count += 1

    return count
