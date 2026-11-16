"""EduForge configuration — programs, schools, API endpoints.

Program IDs below were live-checked against services.sheerid.com (HTTP 200).
Dead programs are kept in PROGRAMS_DEAD for reference only.
"""

SHEERID_BASE = "https://services.sheerid.com"
MY_SHEERID = "https://my.sheerid.com"
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1 MB upload cap

# kind: student | teacher | military
PROGRAMS = {
    "student": {
        "programId": "67c8c14f5f17a83b745e3f82",
        "title": "An Exclusive Student Offer",
        "kind": "student",
        "infoStep": "collectStudentPersonalInfo",
        "docTypes": ["student_id", "transcript"],
        "note": "Generic student offer (Google / Spotify / YouTube style flows).",
    },
    "student_alt": {
        "programId": "681d40e03e7a8077098cb1b6",
        "title": "Verify Student Status",
        "kind": "student",
        "infoStep": "collectStudentPersonalInfo",
        "docTypes": ["student_id", "transcript"],
        "note": "Alternate student verification program.",
    },
    "student_br": {
        "programId": "623e8edc19a65d5a7db2969a",
        "title": "Oferta exclusiva para estudantes (PT)",
        "kind": "student",
        "infoStep": "collectStudentPersonalInfo",
        "docTypes": ["student_id", "transcript"],
        "note": "Portuguese-language student offer.",
    },
    "teachers": {
        "programId": "68d47554aa292d20b9bec8f7",
        "title": "Special Offer Just For Teachers",
        "kind": "teacher",
        "infoStep": "collectTeacherPersonalInfo",
        "docTypes": ["teacher_badge", "teacher_pdf"],
        "note": "K-12 teacher offer. Vendor may gate on school email domain before SheerID.",
    },
    "veterans": {
        "programId": "690415d58971e73ca187d8c9",
        "title": "Honoring All Who Served",
        "kind": "military",
        "infoStep": "collectMilitaryPersonalInfo",
        "docTypes": ["student_id"],
        "note": "Military / veteran offer.",
    },
    "generic": {
        "programId": "5b0721a52094bf13b4024c5d",
        "title": "SheerID Verification",
        "kind": "student",
        "infoStep": "collectStudentPersonalInfo",
        "docTypes": ["student_id", "transcript"],
        "note": "Generic verification entry.",
    },
}

PROGRAMS_DEAD = {
    "68cc6a2e64f55220de204448": "Bolt.new (404)",
    "67c88d2e0536336550bc3bd6": "Google One legacy (404)",
    "681044b7729fba7beccd3565": "Cursor student (404, program closed 2026-06-25)",
}

# Penn State multi-campus registry (id / idExtended used by SheerID organization).
SCHOOLS = {
    "2565": {"id": 2565, "idExtended": "2565", "name": "Pennsylvania State University-Main Campus",
             "city": "University Park", "state": "PA", "country": "US", "domain": "PSU.EDU"},
    "651379": {"id": 651379, "idExtended": "651379", "name": "Pennsylvania State University-World Campus",
               "city": "University Park", "state": "PA", "country": "US", "domain": "PSU.EDU"},
    "8387": {"id": 8387, "idExtended": "8387", "name": "Pennsylvania State University-Penn State Harrisburg",
             "city": "Middletown", "state": "PA", "country": "US", "domain": "PSU.EDU"},
    "8382": {"id": 8382, "idExtended": "8382", "name": "Pennsylvania State University-Penn State Altoona",
             "city": "Altoona", "state": "PA", "country": "US", "domain": "PSU.EDU"},
}
DEFAULT_SCHOOL_ID = "2565"

# currentStep -> normalized status (mirrors the public SheerID widget mapping)
STEP_STATUS = {
    "success": "verified",
    "docUpload": "document_required",
    "sso": "sso_required",
    "emailLoop": "email_required",
    "pending": "pending",
    "error": "rejected",
    "collectStudentPersonalInfo": "validation_failed",
    "collectTeacherPersonalInfo": "validation_failed",
}

SUBMISSION_OPT_IN = (
    "By submitting the personal information above, I acknowledge that my personal "
    "information is being collected under the privacy policy of the business from "
    "which I am seeking a discount"
)

FLAGS = (
    '{"collect-info-step-email-first":"default","doc-upload-considerations":"default",'
    '"doc-upload-may24":"default","doc-upload-redesign-use-legacy-message-keys":false,'
    '"docUpload-assertion-checklist":"default","font-size":"default",'
    '"include-cvec-field-france-student":"not-labeled-optional"}'
)