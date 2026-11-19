# EduForge · from @AlStack (https://t.me/AlStack) — AI freebies, abuse schemes, LLM keys & tools.
"""Document generation dispatch + synthetic identity helpers."""
import random
from typing import Tuple, Dict

from .generators import docgen, teacher, psu, names


def make_identity(first: str = None, last: str = None, email: str = None,
                  birth_date: str = None, school_domain: str = "psu.edu") -> Dict:
    n = names.NameGenerator.generate()
    first = first or n["first_name"]
    last = last or n["last_name"]
    if not email:
        try:
            email = psu.generate_psu_email(first, last)
        except Exception:
            email = f"{first.lower()}.{last.lower()}{random.randint(10, 99)}@{school_domain}"
    birth_date = birth_date or names.generate_birth_date()
    return {"first_name": first, "last_name": last, "email": email,
            "birth_date": birth_date, "employee_id": str(random.randint(100000, 999999))}


def generate_doc(doc_type: str, first: str, last: str, school_name: str,
                 dob: str = "", school_id: str = "2565") -> Tuple[bytes, str, str]:
    """Return (payload_bytes, filename, mime_type)."""
    if doc_type == "student_id":
        return docgen.generate_student_id(first, last, school_name), "student_id.png", "image/png"
    if doc_type == "transcript":
        return docgen.generate_transcript(first, last, dob or "2002-05-14", school_name), "transcript.png", "image/png"
    if doc_type == "teacher_badge":
        return docgen.generate_teacher_badge(first, last, school_name), "teacher_badge.png", "image/png"
    if doc_type == "teacher_pdf":
        return teacher.generate_teacher_pdf(first, last), "teacher_certificate.pdf", "application/pdf"
    if doc_type == "teacher_png":
        return teacher.generate_teacher_png(first, last), "teacher_certificate.png", "image/png"
    if doc_type == "psu_card":
        return psu.generate_image(first, last, school_id), "psu_card.png", "image/png"
    raise ValueError(f"unknown doc_type: {doc_type}")


DOC_TYPES = {
    "student_id": {"label": "Student ID card", "mime": "image/png", "engine": "pillow"},
    "transcript": {"label": "Transcript (quick)", "mime": "image/png", "engine": "pillow"},
    "teacher_badge": {"label": "Teacher badge", "mime": "image/png", "engine": "pillow"},
    "teacher_pdf": {"label": "Teacher certificate (PDF)", "mime": "application/pdf", "engine": "xhtml2pdf"},
    "teacher_png": {"label": "Teacher certificate (PNG)", "mime": "image/png", "engine": "playwright"},
    "psu_card": {"label": "PSU LionPATH card", "mime": "image/png", "engine": "playwright"},
    "transcript_studio": {"label": "Transcript Studio (288 schools)", "mime": "image/png", "engine": "browser"},
}