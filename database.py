import sqlite3
import hashlib
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "healthify.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER NOT NULL DEFAULT 0,
            phone_number TEXT NOT NULL DEFAULT '',
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('patient', 'doctor', 'admin')),
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'pending', 'rejected')),
            created_at TEXT NOT NULL
        )
    """)

    # Seed admin account if not present
    cursor.execute("SELECT id FROM users WHERE email = 'admin@healthify.com'")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO users (name, age, phone_number, email, password, role, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'admin', 'active', ?)
        """, ("Admin", 0, "", "admin@healthify.com", hash_password("admin123"), datetime.now().isoformat()))

    #create patients table
    cursor.execute("""
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT NOT NULL,
    age INTEGER NOT NULL DEFAULT 0,
    phone_number TEXT NOT NULL DEFAULT '',
    gender TEXT NOT NULL CHECK(gender IN ('Male','Female')),
    hypertension INTEGER NOT NULL DEFAULT 0,
    diabetes INTEGER NOT NULL DEFAULT 0,
    handicap INTEGER NOT NULL DEFAULT 0,
    sms_sent INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
""")

    cursor.execute("PRAGMA table_info(patients)")
    patient_columns = {row[1] for row in cursor.fetchall()}
    if "age" not in patient_columns:
        cursor.execute("ALTER TABLE patients ADD COLUMN age INTEGER NOT NULL DEFAULT 0")
    if "phone_number" not in patient_columns:
        cursor.execute("ALTER TABLE patients ADD COLUMN phone_number TEXT NOT NULL DEFAULT ''")
    if "user_id" not in patient_columns:
        cursor.execute("ALTER TABLE patients ADD COLUMN user_id INTEGER")

    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_patients_user_id ON patients(user_id)")

    cursor.execute("PRAGMA table_info(users)")
    user_columns = {row[1] for row in cursor.fetchall()}
    if "age" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN age INTEGER NOT NULL DEFAULT 0")
    if "phone_number" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN phone_number TEXT NOT NULL DEFAULT ''")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    appointment_date TEXT NOT NULL,
    appointment_time TEXT NOT NULL,
    no_show_probability REAL DEFAULT 0,
    risk_level TEXT DEFAULT 'LOW',
    created_at TEXT NOT NULL,
    FOREIGN KEY(patient_id) REFERENCES patients(id)
)
""")

    # Doctor clinical records (merged from GenAI/clinical-notes feature)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medical_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            patient_name TEXT NOT NULL,
            patient_age TEXT,
            patient_nric TEXT,
            patient_gender TEXT,
            temp TEXT,
            bp TEXT,
            hr TEXT,
            spo2 TEXT,
            symptoms TEXT NOT NULL DEFAULT '',
            patient_complaint TEXT,
            doctor_notes TEXT,
            prediction TEXT,
            icd10 TEXT,
            ai_diagnosis TEXT,
            confirmed_findings TEXT,
            final_clinical_record TEXT,
            treatment TEXT,
            prescription TEXT,
            referral_letter TEXT,
            status TEXT NOT NULL DEFAULT 'Draft'
                CHECK(status IN ('Draft', 'Archived', 'Pending_Review')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(doctor_id) REFERENCES users(id)
        )
    """)

    cursor.execute("PRAGMA table_info(medical_records)")
    medical_record_columns = {row[1] for row in cursor.fetchall()}

    if "patient_age" not in medical_record_columns:
        cursor.execute("ALTER TABLE medical_records ADD COLUMN patient_age TEXT")
    if "patient_nric" not in medical_record_columns:
        cursor.execute("ALTER TABLE medical_records ADD COLUMN patient_nric TEXT")
    if "patient_gender" not in medical_record_columns:
        cursor.execute("ALTER TABLE medical_records ADD COLUMN patient_gender TEXT")

    if "patient_complaint" not in medical_record_columns:
        cursor.execute("ALTER TABLE medical_records ADD COLUMN patient_complaint TEXT")
    if "doctor_notes" not in medical_record_columns:
        cursor.execute("ALTER TABLE medical_records ADD COLUMN doctor_notes TEXT")
    if "ai_diagnosis" not in medical_record_columns:
        cursor.execute("ALTER TABLE medical_records ADD COLUMN ai_diagnosis TEXT")
    if "confirmed_findings" not in medical_record_columns:
        cursor.execute("ALTER TABLE medical_records ADD COLUMN confirmed_findings TEXT")
    if "final_clinical_record" not in medical_record_columns:
        cursor.execute("ALTER TABLE medical_records ADD COLUMN final_clinical_record TEXT")

    conn.commit()
    conn.close()


def _insert_patient(cursor, name: str, age: int, phone_number: str, gender: str, hypertension, diabetes, handicap, user_id: int | None = None):
    cursor.execute("""
        INSERT INTO patients
        (user_id, name, age, phone_number, gender, hypertension, diabetes, handicap, sms_sent, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
    """, (
        user_id,
        name.strip().title(),
        int(age),
        phone_number.strip(),
        gender,
        int(hypertension),
        int(diabetes),
        int(handicap),
        datetime.now().isoformat()
    ))


def create_user(name: str, email: str, password: str, role: str, age: int = 0, phone_number: str = '', gender: str | None = None, hypertension=0, diabetes=0, handicap=0) -> tuple[bool, str]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        status = "pending" if role == "doctor" else "active"
        normalized_name = name.strip().title()
        normalized_email = email.strip().lower()
        cursor.execute("""
            INSERT INTO users (name, age, phone_number, email, password, role, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (normalized_name, int(age), phone_number.strip(), normalized_email, hash_password(password), role, status, datetime.now().isoformat()))

        if role == "patient" and gender in ("Male", "Female"):
            _insert_patient(
                cursor,
                normalized_name,
                age,
                phone_number,
                gender,
                hypertension,
                diabetes,
                handicap,
                user_id=cursor.lastrowid,
            )

        conn.commit()
        return True, "Account created successfully."
    except sqlite3.IntegrityError:
        conn.rollback()
        return False, "An account with this email already exists."
    except Exception as exc:
        conn.rollback()
        return False, str(exc)
    finally:
        conn.close()


def authenticate_user(email: str, password: str, role: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    normalized_email = email.strip().lower()
    cursor.execute("""
        SELECT * FROM users WHERE email = ? AND password = ? AND role = ?
    """, (normalized_email, hash_password(password), role))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_users() -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE role != 'admin' ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pending_doctors() -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE role = 'doctor' AND status = 'pending' ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_user_status(user_id: int, status: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = ? WHERE id = ?", (status, user_id))
    conn.commit()
    conn.close()


def delete_user(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def create_patient(name, age, phone_number, gender, hypertension, diabetes, handicap, user_id: int | None = None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        _insert_patient(cursor, name, age, phone_number, gender, hypertension, diabetes, handicap, user_id=user_id)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    conn.close()

def get_all_patients():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT *
        FROM patients
        ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
    
def delete_patient(patient_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
    conn.commit()
    conn.close()


def update_patient_profile(user_id: int, age: int, gender: str, hypertension: bool, diabetes: bool, handicap: bool):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE patients
        SET age = ?, gender = ?, hypertension = ?, diabetes = ?, handicap = ?
        WHERE user_id = ?
        """,
        (int(age), gender, int(bool(hypertension)), int(bool(diabetes)), int(bool(handicap)), user_id)
    )
    cursor.execute(
        """
        UPDATE users
        SET age = ?
        WHERE id = ?
        """,
        (int(age), user_id)
    )
    conn.commit()
    conn.close()


def get_patient_by_id(patient_id):

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT *
        FROM patients
        WHERE id=?
        """,
        (patient_id,)
    )

    row = cursor.fetchone()
    conn.close()
    return row


def get_patient_by_user_id(user_id):

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT *
        FROM patients
        WHERE user_id = ?
        """,
        (user_id,)
    )

    row = cursor.fetchone()
    conn.close()
    return row

def update_sms_sent(patient_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE patients
        SET sms_sent = 1
        WHERE id = ?
    """, (patient_id,))

    conn.commit()
    conn.close()


def create_appointment(appointment):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO appointments
            (
                patient_id,
                appointment_date,
                appointment_time,
                created_at
            )

            VALUES
            (?, ?, ?, ?)
            """,
            (
                appointment["patient_id"],
                appointment["date"].isoformat() if hasattr(appointment["date"], "isoformat") else str(appointment["date"]),
                appointment["time"].isoformat() if hasattr(appointment["time"], "isoformat") else str(appointment["time"]),
                datetime.now().isoformat()
            )
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ==================================================
# Doctor clinical record CRUD
# ==================================================
def save_medical_record(
    record_id,
    doctor_id,
    patient_name,
    patient_age,
    patient_nric,
    patient_gender,
    temp,
    bp,
    hr,
    spo2,
    patient_complaint,
    doctor_notes,
    prediction,
    icd10,
    ai_diagnosis,
    confirmed_findings,
    final_clinical_record,
    treatment,
    prescription,
    referral_letter,
    status,
):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    # Keep the legacy symptoms column populated for backward compatibility.
    legacy_symptoms = patient_complaint or ""

    try:
        if record_id is None:
            cursor.execute(
                """
                INSERT INTO medical_records
                (
                    doctor_id,
                    patient_name,
                    patient_age,
                    patient_nric,
                    patient_gender,
                    temp,
                    bp,
                    hr,
                    spo2,
                    symptoms,
                    patient_complaint,
                    doctor_notes,
                    prediction,
                    icd10,
                    ai_diagnosis,
                    confirmed_findings,
                    final_clinical_record,
                    treatment,
                    prescription,
                    referral_letter,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doctor_id,
                    patient_name,
                    patient_age,
                    patient_nric,
                    patient_gender,
                    temp,
                    bp,
                    hr,
                    spo2,
                    legacy_symptoms,
                    patient_complaint,
                    doctor_notes,
                    prediction,
                    icd10,
                    ai_diagnosis,
                    confirmed_findings,
                    final_clinical_record,
                    treatment,
                    prescription,
                    referral_letter,
                    status,
                    now,
                    now,
                ),
            )
        else:
            cursor.execute(
                """
                UPDATE medical_records
                SET
                    patient_name=?,
                    patient_age=?,
                    patient_nric=?,
                    patient_gender=?,
                    temp=?,
                    bp=?,
                    hr=?,
                    spo2=?,
                    symptoms=?,
                    patient_complaint=?,
                    doctor_notes=?,
                    prediction=?,
                    icd10=?,
                    ai_diagnosis=?,
                    confirmed_findings=?,
                    final_clinical_record=?,
                    treatment=?,
                    prescription=?,
                    referral_letter=?,
                    status=?,
                    updated_at=?
                WHERE id=? AND doctor_id=?
                """,
                (
                    patient_name,
                    patient_age,
                    patient_nric,
                    patient_gender,
                    temp,
                    bp,
                    hr,
                    spo2,
                    legacy_symptoms,
                    patient_complaint,
                    doctor_notes,
                    prediction,
                    icd10,
                    ai_diagnosis,
                    confirmed_findings,
                    final_clinical_record,
                    treatment,
                    prescription,
                    referral_letter,
                    status,
                    now,
                    record_id,
                    doctor_id,
                ),
            )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_records_by_doctor_and_status(doctor_id: int, status: str) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM medical_records
        WHERE doctor_id = ? AND status = ?
        ORDER BY updated_at DESC
        """,
        (doctor_id, status),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_medical_record(record_id: int, doctor_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM medical_records WHERE id = ? AND doctor_id = ?",
        (record_id, doctor_id),
    )
    conn.commit()
    conn.close()


def update_record_status(record_id: int, new_status: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE medical_records SET status = ?, updated_at = ? WHERE id = ?",
        (new_status, datetime.now().isoformat(), record_id),
    )
    conn.commit()
    conn.close()