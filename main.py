from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import json
from datetime import datetime

app = FastAPI(title="Hệ thống Quản lý Lớp học - LMS")

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    if not DATABASE_URL:
        raise Exception("Chưa cấu hình DATABASE_URL trong biến môi trường!")
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    if not DATABASE_URL:
        return
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(255) UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role VARCHAR(50) NOT NULL DEFAULT 'student',
        visit_count INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS students (
        id SERIAL PRIMARY KEY,
        student_code VARCHAR(100) UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        dob TEXT,
        status VARCHAR(50) DEFAULT 'Active'
    );
    CREATE TABLE IF NOT EXISTS attendance (
        id SERIAL PRIMARY KEY,
        student_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        status VARCHAR(50) NOT NULL,
        UNIQUE(student_id, date)
    );
    CREATE TABLE IF NOT EXISTS videos (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        youtube_id TEXT NOT NULL,
        description TEXT,
        order_index INTEGER DEFAULT 0,
        drive_url TEXT DEFAULT '',
        chapter VARCHAR(100) DEFAULT 'Chương 1',
        category VARCHAR(100) DEFAULT 'Bài 1'
    );
    CREATE TABLE IF NOT EXISTS documents (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        drive_url TEXT NOT NULL,
        chapter VARCHAR(100) DEFAULT 'Chương 1',
        category VARCHAR(100) DEFAULT 'Bài 1',
        doc_date TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS assignments (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        pdf_url TEXT DEFAULT '',
        due_date TEXT,
        mc_count INTEGER DEFAULT 0,
        tf_count INTEGER DEFAULT 0,
        sa_count INTEGER DEFAULT 0,
        answer_key TEXT DEFAULT '{}',
        mc_score_per_q NUMERIC(4, 2) DEFAULT 0.25,
        tf_score_1 NUMERIC(4, 2) DEFAULT 0.10,
        tf_score_2 NUMERIC(4, 2) DEFAULT 0.25,
        tf_score_3 NUMERIC(4, 2) DEFAULT 0.50,
        tf_score_4 NUMERIC(4, 2) DEFAULT 1.00,
        sa_score_per_q NUMERIC(4, 2) DEFAULT 0.50
    );
    CREATE TABLE IF NOT EXISTS submissions (
        id SERIAL PRIMARY KEY,
        assignment_id INTEGER NOT NULL,
        student_name TEXT NOT NULL,
        answer_text TEXT NOT NULL,
        raw_score NUMERIC(5, 2) DEFAULT 0,
        max_score NUMERIC(5, 2) DEFAULT 0,
        score NUMERIC(5, 2) DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS exams (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        pdf_url TEXT DEFAULT '',
        content TEXT DEFAULT '',
        question_mathml TEXT DEFAULT '',
        due_date TEXT DEFAULT '',
        duration_minutes INTEGER DEFAULT 60,
        mc_count INTEGER DEFAULT 0,
        tf_count INTEGER DEFAULT 0,
        sa_count INTEGER DEFAULT 0,
        answer_key TEXT DEFAULT '{}',
        mc_score_per_q NUMERIC(4, 2) DEFAULT 0.25,
        tf_score_1 NUMERIC(4, 2) DEFAULT 0.10,
        tf_score_2 NUMERIC(4, 2) DEFAULT 0.25,
        tf_score_3 NUMERIC(4, 2) DEFAULT 0.50,
        tf_score_4 NUMERIC(4, 2) DEFAULT 1.00,
        sa_score_per_q NUMERIC(4, 2) DEFAULT 0.50
    );
    CREATE TABLE IF NOT EXISTS exam_submissions (
        id SERIAL PRIMARY KEY,
        exam_id INTEGER NOT NULL,
        student_name TEXT NOT NULL,
        answer_text TEXT NOT NULL,
        raw_score NUMERIC(5, 2) DEFAULT 0,
        max_score NUMERIC(5, 2) DEFAULT 0,
        score NUMERIC(5, 2) DEFAULT 0,
        time_taken INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS visit_count INTEGER DEFAULT 1;")
    cursor.execute("ALTER TABLE assignments ADD COLUMN IF NOT EXISTS pdf_url TEXT DEFAULT '';")
    cursor.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS raw_score NUMERIC(5, 2) DEFAULT 0;")
    cursor.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS max_score NUMERIC(5, 2) DEFAULT 0;")
    
    cursor.execute("ALTER TABLE videos ADD COLUMN IF NOT EXISTS drive_url TEXT DEFAULT '';")
    cursor.execute("ALTER TABLE videos ADD COLUMN IF NOT EXISTS chapter VARCHAR(100) DEFAULT 'Chương 1';")
    cursor.execute("ALTER TABLE videos ADD COLUMN IF NOT EXISTS category VARCHAR(100) DEFAULT 'Bài 1';")

    cursor.execute("ALTER TABLE exams ADD COLUMN IF NOT EXISTS pdf_url TEXT DEFAULT '';")
    cursor.execute("ALTER TABLE exams ADD COLUMN IF NOT EXISTS content TEXT DEFAULT '';")
    cursor.execute("ALTER TABLE exams ADD COLUMN IF NOT EXISTS due_date TEXT DEFAULT '';")
    cursor.execute("ALTER TABLE exams ADD COLUMN IF NOT EXISTS duration_minutes INTEGER DEFAULT 60;")
    cursor.execute("ALTER TABLE exams ADD COLUMN IF NOT EXISTS mc_count INTEGER DEFAULT 0;")
    cursor.execute("ALTER TABLE exams ADD COLUMN IF NOT EXISTS tf_count INTEGER DEFAULT 0;")
    cursor.execute("ALTER TABLE exams ADD COLUMN IF NOT EXISTS sa_count INTEGER DEFAULT 0;")
    cursor.execute("ALTER TABLE exams ADD COLUMN IF NOT EXISTS answer_key TEXT DEFAULT '{}';")
    cursor.execute("ALTER TABLE exams ADD COLUMN IF NOT EXISTS mc_score_per_q NUMERIC(4, 2) DEFAULT 0.25;")
    cursor.execute("ALTER TABLE exams ADD COLUMN IF NOT EXISTS tf_score_1 NUMERIC(4, 2) DEFAULT 0.10;")
    cursor.execute("ALTER TABLE exams ADD COLUMN IF NOT EXISTS tf_score_2 NUMERIC(4, 2) DEFAULT 0.25;")
    cursor.execute("ALTER TABLE exams ADD COLUMN IF NOT EXISTS tf_score_3 NUMERIC(4, 2) DEFAULT 0.50;")
    cursor.execute("ALTER TABLE exams ADD COLUMN IF NOT EXISTS tf_score_4 NUMERIC(4, 2) DEFAULT 1.00;")
    cursor.execute("ALTER TABLE exams ADD COLUMN IF NOT EXISTS sa_score_per_q NUMERIC(4, 2) DEFAULT 0.50;")

    cursor.execute("ALTER TABLE exam_submissions ADD COLUMN IF NOT EXISTS time_taken INTEGER DEFAULT 0;")

    cursor.execute("SELECT COUNT(*) FROM users")
    res = cursor.fetchone()
    user_count = res['count'] if res else 0
    if user_count == 0:
        cursor.execute("INSERT INTO users (username, password, full_name, role, visit_count) VALUES (%s, %s, %s, %s, %s)",
                       ("admin", "123456", "Giáo viên Admin", "teacher", 10))

    conn.commit()
    cursor.close()
    conn.close()

try:
    init_db()
except Exception as e:
    print("Lỗi khởi tạo DB:", e)

def sanitize_and_clean_answer_key(answer_key_raw: str, mc_count: int, tf_count: int, sa_count: int) -> str:
    try:
        key = json.loads(answer_key_raw or "{}")
    except Exception:
        key = {}

    clean_mc = {}
    mc_key = key.get("mc", {})
    for i in range(1, mc_count + 1):
        clean_mc[str(i)] = mc_key.get(str(i), "")

    clean_tf = {}
    tf_key = key.get("tf", {})
    for i in range(1, tf_count + 1):
        for sub in ['a', 'b', 'c', 'd']:
            sub_q = f"{i}{sub}"
            clean_tf[sub_q] = tf_key.get(sub_q, "")

    clean_sa = {}
    sa_key = key.get("sa", {})
    for i in range(1, sa_count + 1):
        clean_sa[str(i)] = sa_key.get(str(i), "")

    return json.dumps({"mc": clean_mc, "tf": clean_tf, "sa": clean_sa})

def calculate_submission_score_details(
    answer_key_raw: str,
    student_answers_raw: str,
    mc_count: int,
    tf_count: int,
    sa_count: int,
    mc_score_per_q: float = 0.25,
    tf_score_1: float = 0.10,
    tf_score_2: float = 0.25,
    tf_score_3: float = 0.50,
    tf_score_4: float = 1.00,
    sa_score_per_q: float = 0.50
):
    try:
        key = json.loads(answer_key_raw or "{}")
    except Exception:
        key = {}
    try:
        ans = json.loads(student_answers_raw or "{}")
    except Exception:
        ans = {}

    max_mc = float(mc_count or 0) * float(mc_score_per_q or 0.25)
    max_tf = float(tf_count or 0) * float(tf_score_4 or 1.0)
    max_sa = float(sa_count or 0) * float(sa_score_per_q or 0.5)
    max_score = round(max_mc + max_tf + max_sa, 2)

    raw_score = 0.0

    mc_key = key.get("mc", {})
    mc_ans = ans.get("mc", {})
    for i in range(1, mc_count + 1):
        q_num = str(i)
        correct_opt = mc_key.get(q_num)
        if not correct_opt:
            continue
        student_opt = mc_ans.get(q_num, "")
        if str(student_opt).strip().upper() == str(correct_opt).strip().upper():
            raw_score += float(mc_score_per_q)

    tf_key = key.get("tf", {})
    tf_ans = ans.get("tf", {})
    for i in range(1, tf_count + 1):
        correct_in_this_q = 0
        has_key = False
        for sub in ['a', 'b', 'c', 'd']:
            sub_q = f"{i}{sub}"
            correct_tf = tf_key.get(sub_q)
            if correct_tf:
                has_key = True
                student_tf = tf_ans.get(sub_q, "")
                if str(student_tf).strip() == str(correct_tf).strip():
                    correct_in_this_q += 1
        if has_key:
            if correct_in_this_q == 1:
                raw_score += float(tf_score_1)
            elif correct_in_this_q == 2:
                raw_score += float(tf_score_2)
            elif correct_in_this_q == 3:
                raw_score += float(tf_score_3)
            elif correct_in_this_q == 4:
                raw_score += float(tf_score_4)

    sa_key = key.get("sa", {})
    sa_ans = ans.get("sa", {})
    for i in range(1, sa_count + 1):
        q_num = str(i)
        correct_val = sa_key.get(q_num)
        if not correct_val:
            continue
        student_val = sa_ans.get(q_num, "")
        k_str = str(correct_val).strip().lower().replace(",", ".")
        s_str = str(student_val).strip().lower().replace(",", ".")
        if k_str == s_str and k_str != "":
            raw_score += float(sa_score_per_q)

    raw_score = round(raw_score, 2)
    score_10 = round((raw_score / max_score) * 10, 2) if max_score > 0 else round(raw_score, 2)

    return raw_score, max_score, score_10

def build_detailed_breakdown(
    answer_key_raw: str,
    student_answers_raw: str,
    mc_count: int,
    tf_count: int,
    sa_count: int
) -> Dict[str, Any]:
    try:
        key = json.loads(answer_key_raw or "{}")
    except Exception:
        key = {}
    try:
        ans = json.loads(student_answers_raw or "{}")
    except Exception:
        ans = {}

    mc_detail = []
    mc_key = key.get("mc", {})
    mc_ans = ans.get("mc", {})
    for i in range(1, mc_count + 1):
        q_str = str(i)
        c_ans = mc_key.get(q_str, "")
        s_ans = mc_ans.get(q_str, "")
        is_corr = bool(c_ans and str(s_ans).strip().upper() == str(c_ans).strip().upper())
        mc_detail.append({
            "question": f"Câu {i}",
            "student_answer": s_ans,
            "correct_answer": c_ans,
            "is_correct": is_corr
        })

    tf_detail = []
    tf_key = key.get("tf", {})
    tf_ans = ans.get("tf", {})
    for i in range(1, tf_count + 1):
        sub_list = []
        for sub in ['a', 'b', 'c', 'd']:
            sub_q = f"{i}{sub}"
            c_ans = tf_key.get(sub_q, "")
            s_ans = tf_ans.get(sub_q, "")
            is_corr = bool(c_ans and str(s_ans).strip() == str(c_ans).strip())
            sub_list.append({
                "sub_question": f"Ý {sub}",
                "student_answer": s_ans,
                "correct_answer": c_ans,
                "is_correct": is_corr
            })
        tf_detail.append({
            "question": f"Câu {i}",
            "subs": sub_list
        })

    sa_detail = []
    sa_key = key.get("sa", {})
    sa_ans = ans.get("sa", {})
    for i in range(1, sa_count + 1):
        q_str = str(i)
        c_ans = sa_key.get(q_str, "")
        s_ans = sa_ans.get(q_str, "")
        k_str = str(c_ans).strip().lower().replace(",", ".")
        s_str = str(s_ans).strip().lower().replace(",", ".")
        is_corr = bool(c_ans and k_str == s_str and k_str != "")
        sa_detail.append({
            "question": f"Câu {i}",
            "student_answer": s_ans,
            "correct_answer": c_ans,
            "is_correct": is_corr
        })

    return {"mc": mc_detail, "tf": tf_detail, "sa": sa_detail}

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

# --- XÁC THỰC & DANH SÁCH TÀI KHOẢN ---
class UserRegister(BaseModel):
    username: str
    password: str
    full_name: str
    role: Optional[str] = "student"

class UserLogin(BaseModel):
    username: str
    password: str

class ChangePassword(BaseModel):
    user_id: int
    old_password: str
    new_password: str

class UserUpdate(BaseModel):
    full_name: str
    role: Optional[str] = "student"

@app.post("/api/register")
def register(u: UserRegister):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password, full_name, role, visit_count) VALUES (%s, %s, %s, %s, %s)",
                       (u.username.strip(), u.password, u.full_name.strip(), u.role, 1))
        conn.commit()
    except Exception:
        conn.close()
        raise HTTPException(status_code=400, detail="Tên đăng nhập đã tồn tại!")
    cursor.close()
    conn.close()
    return {"message": "Đăng ký thành công!"}

@app.post("/api/login")
def login(u: UserLogin):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, full_name, role, visit_count FROM users WHERE username = %s AND password = %s",
                   (u.username.strip(), u.password))
    user = cursor.fetchone()
    if not user:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không đúng!")
    
    cursor.execute("UPDATE users SET visit_count = COALESCE(visit_count, 0) + 1 WHERE id = %s", (user["id"],))
    conn.commit()
    user["visit_count"] = (user.get("visit_count") or 0) + 1
    cursor.close()
    conn.close()
    return dict(user)

@app.get("/api/users")
def get_users():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, full_name, role, COALESCE(visit_count, 1) as visit_count FROM users ORDER BY visit_count DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/users/change-password")
def change_password(data: ChangePassword):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, password FROM users WHERE id = %s", (data.user_id,))
    u = cursor.fetchone()
    if not u or u["password"] != data.old_password:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Mật khẩu cũ không chính xác!")
    
    cursor.execute("UPDATE users SET password = %s WHERE id = %s", (data.new_password, data.user_id))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Đổi mật khẩu thành công!"}

@app.put("/api/users/{user_id}")
def update_user(user_id: int, u: UserUpdate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET full_name = %s, role = %s WHERE id = %s", (u.full_name, u.role, user_id))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Đã cập nhật thông tin người dùng"}

# --- QUẢN LÝ HỌC SINH ---
@app.get("/api/students")
def get_students():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students ORDER BY student_code ASC")
    students = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(s) for s in students]

class StudentCreate(BaseModel):
    student_code: str
    full_name: str
    dob: Optional[str] = ""
    status: Optional[str] = "Active"

@app.post("/api/students")
def create_student(s: StudentCreate):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO students (student_code, full_name, dob, status) VALUES (%s, %s, %s, %s)",
                       (s.student_code, s.full_name, s.dob, s.status))
        conn.commit()
    except Exception:
        conn.close()
        raise HTTPException(status_code=400, detail="Mã học sinh đã tồn tại")
    cursor.close()
    conn.close()
    return {"message": "Đã thêm học sinh"}

@app.put("/api/students/{student_id}")
def update_student(student_id: int, s: StudentCreate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE students
        SET student_code = %s, full_name = %s, dob = %s, status = %s
        WHERE id = %s
    """, (s.student_code, s.full_name, s.dob, s.status, student_id))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Đã cập nhật thông tin học sinh"}

@app.delete("/api/students/{student_id}")
def delete_student(student_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE id = %s", (student_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Đã xóa học sinh"}

# --- ĐIỂM DANH ---
@app.get("/api/attendance")
def get_attendance():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM attendance")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/attendance/dates")
def get_attendance_dates():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT date FROM attendance ORDER BY date ASC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [r["date"] for r in rows]

class AttendanceUpdate(BaseModel):
    student_id: int
    date: str
    status: str

@app.post("/api/attendance")
def save_attendance(data: AttendanceUpdate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO attendance (student_id, date, status)
        VALUES (%s, %s, %s)
        ON CONFLICT(student_id, date) DO UPDATE SET status = EXCLUDED.status
    """, (data.student_id, data.date, data.status))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Đã ghi nhận điểm danh"}

@app.post("/api/attendance/bulk")
def save_bulk_attendance(items: List[AttendanceUpdate]):
    conn = get_db()
    cursor = conn.cursor()
    for item in items:
        cursor.execute("""
            INSERT INTO attendance (student_id, date, status)
            VALUES (%s, %s, %s)
            ON CONFLICT(student_id, date) DO UPDATE SET status = EXCLUDED.status
        """, (item.student_id, item.date, item.status))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": f"Đã ghi nhận điểm danh hàng loạt cho {len(items)} lượt"}

@app.delete("/api/attendance/dates/{date_str}")
def delete_attendance_date(date_str: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM attendance WHERE date = %s", (date_str,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": f"Đã xóa ngày điểm danh {date_str}"}

# --- BÀI GIẢNG & TÀI LIỆU CỤM BÀI HỌC (GỘP VIDEO + DRIVE PDF) ---
@app.get("/api/videos")
def get_videos():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM videos ORDER BY order_index ASC, id DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(r) for r in rows]

class VideoCreate(BaseModel):
    title: str
    youtube_id: str
    description: Optional[str] = ""
    order_index: Optional[int] = 0
    drive_url: Optional[str] = ""
    chapter: Optional[str] = "Chương 1"
    category: Optional[str] = "B
