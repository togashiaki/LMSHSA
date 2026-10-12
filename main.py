from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import json
from datetime import datetime

app = FastAPI(title="Hệ thống Quản lý Lớp học")

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
        order_index INTEGER DEFAULT 0
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS visit_count INTEGER DEFAULT 1;")
    cursor.execute("ALTER TABLE assignments ADD COLUMN IF NOT EXISTS pdf_url TEXT DEFAULT '';")
    cursor.execute("ALTER TABLE assignments ADD COLUMN IF NOT EXISTS duration_minutes INTEGER DEFAULT 60;")
    cursor.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS raw_score NUMERIC(5, 2) DEFAULT 0;")
    cursor.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS max_score NUMERIC(5, 2) DEFAULT 0;")
    
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

@app.delete("/api/attendance/dates/{date_str}")
def delete_attendance_date(date_str: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM attendance WHERE date = %s", (date_str,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": f"Đã xóa ngày điểm danh {date_str}"}

# --- VIDEO BÀI GIẢNG ---
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

@app.post("/api/videos")
def create_video(v: VideoCreate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO videos (title, youtube_id, description, order_index) VALUES (%s, %s, %s, %s)",
                   (v.title, v.youtube_id, v.description, v.order_index))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Đã thêm video"}

@app.delete("/api/videos/{video_id}")
def delete_video(video_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM videos WHERE id = %s", (video_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Đã xóa video"}

# --- TÀI LIỆU GOOGLE DRIVE ---
@app.get("/api/documents")
def get_documents():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents ORDER BY chapter ASC, category ASC, doc_date ASC, id DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(r) for r in rows]

class DocumentCreate(BaseModel):
    title: str
    drive_url: str
    chapter: Optional[str] = "Chương 1"
    category: Optional[str] = "Bài 1"
    doc_date: Optional[str] = ""

@app.post("/api/documents")
def create_document(d: DocumentCreate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO documents (title, drive_url, chapter, category, doc_date) VALUES (%s, %s, %s, %s, %s)",
                   (d.title, d.drive_url, d.chapter or "Chương 1", d.category or "Bài 1", d.doc_date or ""))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Đã thêm tài liệu"}

@app.put("/api/documents/{doc_id}")
def update_document(doc_id: int, d: DocumentCreate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE documents
        SET title = %s, drive_url = %s, chapter = %s, category = %s, doc_date = %s
        WHERE id = %s
    """, (d.title, d.drive_url, d.chapter or "Chương 1", d.category or "Bài 1", d.doc_date or "", doc_id))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Đã cập nhật thông tin tài liệu"}

@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Đã xóa tài liệu"}

# --- BÀI TẬP VỀ NHÀ & CHẤM ĐIỂM ---
@app.get("/api/assignments")
def get_assignments():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM assignments ORDER BY id DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    res = []
    for r in rows:
        item = dict(r)
        item["duration_minutes"] = int(item["duration_minutes"]) if item.get("duration_minutes") is not None else 60
        item["mc_score_per_q"] = float(item["mc_score_per_q"]) if item.get("mc_score_per_q") is not None else 0.25
        item["tf_score_1"] = float(item["tf_score_1"]) if item.get("tf_score_1") is not None else 0.10
        item["tf_score_2"] = float(item["tf_score_2"]) if item.get("tf_score_2") is not None else 0.25
        item["tf_score_3"] = float(item["tf_score_3"]) if item.get("tf_score_3") is not None else 0.50
        item["tf_score_4"] = float(item["tf_score_4"]) if item.get("tf_score_4") is not None else 1.00
        item["sa_score_per_q"] = float(item["sa_score_per_q"]) if item.get("sa_score_per_q") is not None else 0.50
        res.append(item)
    return res

class AssignmentCreate(BaseModel):
    title: str
    content: str
    pdf_url: Optional[str] = ""
    due_date: Optional[str] = ""
    duration_minutes: Optional[int] = 60
    mc_count: Optional[int] = 0
    tf_count: Optional[int] = 0
    sa_count: Optional[int] = 0
    answer_key: Optional[str] = "{}"
    mc_score_per_q: Optional[float] = 0.25
    tf_score_1: Optional[float] = 0.10
    tf_score_2: Optional[float] = 0.25
    tf_score_3: Optional[float] = 0.50
    tf_score_4: Optional[float] = 1.00
    sa_score_per_q: Optional[float] = 0.50

@app.post("/api/assignments")
def create_assignment(a: AssignmentCreate):
    conn = get_db()
    cursor = conn.cursor()
    mc_c = a.mc_count or 0
    tf_c = a.tf_count or 0
    sa_c = a.sa_count or 0
    cleaned_key = sanitize_and_clean_answer_key(a.answer_key or "{}", mc_c, tf_c, sa_c)

    cursor.execute("""
        INSERT INTO assignments (title, content, pdf_url, due_date, duration_minutes, mc_count, tf_count, sa_count, answer_key,
                                 mc_score_per_q, tf_score_1, tf_score_2, tf_score_3, tf_score_4, sa_score_per_q)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        a.title, a.content, a.pdf_url or "", a.due_date or "", a.duration_minutes or 60, mc_c, tf_c, sa_c, cleaned_key,
        a.mc_score_per_q or 0.25, a.tf_score_1 or 0.10, a.tf_score_2 or 0.25,
        a.tf_score_3 or 0.50, a.tf_score_4 or 1.00, a.sa_score_per_q or 0.50
    ))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Đã tạo bài tập"}

@app.put("/api/assignments/{assignment_id}")
def update_assignment(assignment_id: int, a: AssignmentCreate):
    conn = get_db()
    cursor = conn.cursor()
    mc_c = a.mc_count or 0
    tf_c = a.tf_count or 0
    sa_c = a.sa_count or 0
    cleaned_key = sanitize_and_clean_answer_key(a.answer_key or "{}", mc_c, tf_c, sa_c)

    cursor.execute("""
        UPDATE assignments
        SET title = %s, content = %s, pdf_url = %s, due_date = %s, duration_minutes = %s, mc_count = %s, tf_count = %s, sa_count = %s, answer_key = %s,
            mc_score_per_q = %s, tf_score_1 = %s, tf_score_2 = %s, tf_score_3 = %s, tf_score_4 = %s, sa_score_per_q = %s
        WHERE id = %s
    """, (
        a.title, a.content, a.pdf_url or "", a.due_date or "", a.duration_minutes or 60, mc_c, tf_c, sa_c, cleaned_key,
        a.mc_score_per_q or 0.25, a.tf_score_1 or 0.10, a.tf_score_2 or 0.25,
        a.tf_score_3 or 0.50, a.tf_score_4 or 1.00, a.sa_score_per_q or 0.50,
        assignment_id
    ))
    
    cursor.execute("SELECT id, answer_text FROM submissions WHERE assignment_id = %s", (assignment_id,))
    subs = cursor.fetchall()
    for sub in subs:
        raw_score, max_score, score_10 = calculate_submission_score_details(
            cleaned_key, sub["answer_text"],
            mc_count=mc_c, tf_count=tf_c, sa_count=sa_c,
            mc_score_per_q=a.mc_score_per_q or 0.25,
            tf_score_1=a.tf_score_1 or 0.10,
            tf_score_2=a.tf_score_2 or 0.25,
            tf_score_3=a.tf_score_3 or 0.50,
            tf_score_4=a.tf_score_4 or 1.00,
            sa_score_per_q=a.sa_score_per_q or 0.50
        )
        cursor.execute("UPDATE submissions SET raw_score = %s, max_score = %s, score = %s WHERE id = %s",
                       (raw_score, max_score, score_10, sub["id"]))

    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Đã cập nhật bài tập và tự động chấm lại toàn bộ bài nộp!"}

@app.delete("/api/assignments/{assignment_id}")
def delete_assignment(assignment_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM submissions WHERE assignment_id = %s", (assignment_id,))
    cursor.execute("DELETE FROM assignments WHERE id = %s", (assignment_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Đã xóa bài tập"}

@app.get("/api/submissions")
def get_submissions(assignment_id: Optional[int] = None):
    conn = get_db()
    cursor = conn.cursor()
    if assignment_id:
        cursor.execute("SELECT * FROM submissions WHERE assignment_id = %s ORDER BY score DESC, id DESC", (assignment_id,))
    else:
        cursor.execute("SELECT * FROM submissions ORDER BY id DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    res = []
    for r in rows:
        item = dict(r)
        item["raw_score"] = float(item["raw_score"]) if item.get("raw_score") is not None else 0.0
        item["max_score"] = float(item["max_score"]) if item.get("max_score") is not None else 0.0
        item["score"] = float(item["score"]) if item.get("score") is not None else 0.0
        res.append(item)
    return res

class SubmissionCreate(BaseModel):
    assignment_id: int
    student_name: str
    answer_text: str

@app.post("/api/submissions")
def create_submission(s: SubmissionCreate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM assignments WHERE id = %s", (s.assignment_id,))
    assign = cursor.fetchone()
    if not assign:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Bài tập không tồn tại!")

    raw_score, max_score, score_10 = calculate_submission_score_details(
        assign.get("answer_key", "{}"),
        s.answer_text,
        mc_count=assign.get("mc_count", 0),
        tf_count=assign.get("tf_count", 0),
        sa_count=assign.get("sa_count", 0),
        mc_score_per_q=assign.get("mc_score_per_q", 0.25),
        tf_score_1=assign.get("tf_score_1", 0.10),
        tf_score_2=assign.get("tf_score_2", 0.25),
        tf_score_3=assign.get("tf_score_3", 0.50),
        tf_score_4=assign.get("tf_score_4", 1.00),
        sa_score_per_q=assign.get("sa_score_per_q", 0.50)
    )

    cursor.execute("""
        INSERT INTO submissions (assignment_id, student_name, answer_text, raw_score, max_score, score)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (s.assignment_id, s.student_name, s.answer_text, raw_score, max_score, score_10))
    
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Nộp bài thành công!", "raw_score": raw_score, "max_score": max_score, "score": score_10}

# --- ĐỀ KIỂM TRA & BÀI NỘP BÀI KIỂM TRA ---
@app.get("/api/exams")
def get_exams():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM exams ORDER BY id DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    res = []
    for r in rows:
        item = dict(r)
        item["duration_minutes"] = int(item["duration_minutes"]) if item.get("duration_minutes") is not None else 60
        item["mc_score_per_q"] = float(item["mc_score_per_q"]) if item.get("mc_score_per_q") is not None else 0.25
        item["tf_score_1"] = float(item["tf_score_1"]) if item.get("tf_score_1") is not None else 0.10
        item["tf_score_2"] = float(item["tf_score_2"]) if item.get("tf_score_2") is not None else 0.25
        item["tf_score_3"] = float(item["tf_score_3"]) if item.get("tf_score_3") is not None else 0.50
        item["tf_score_4"] = float(item["tf_score_4"]) if item.get("tf_score_4") is not None else 1.00
        item["sa_score_per_q"] = float(item["sa_score_per_q"]) if item.get("sa_score_per_q") is not None else 0.50
        res.append(item)
    return res

class ExamCreate(BaseModel):
    title: str
    pdf_url: Optional[str] = ""
    content: Optional[str] = ""
    question_mathml: Optional[str] = ""
    due_date: Optional[str] = ""
    duration_minutes: Optional[int] = 60
    mc_count: Optional[int] = 0
    tf_count: Optional[int] = 0
    sa_count: Optional[int] = 0
    answer_key: Optional[str] = "{}"
    mc_score_per_q: Optional[float] = 0.25
    tf_score_1: Optional[float] = 0.10
    tf_score_2: Optional[float] = 0.25
    tf_score_3: Optional[float] = 0.50
    tf_score_4: Optional[float] = 1.00
    sa_score_per_q: Optional[float] = 0.50

@app.post("/api/exams")
def create_exam(e: ExamCreate):
    conn = get_db()
    cursor = conn.cursor()
    mc_c = e.mc_count or 0
    tf_c = e.tf_count or 0
    sa_c = e.sa_count or 0
    cleaned_key = sanitize_and_clean_answer_key(e.answer_key or "{}", mc_c, tf_c, sa_c)

    cursor.execute("""
        INSERT INTO exams (title, pdf_url, content, question_mathml, due_date, duration_minutes, mc_count, tf_count, sa_count, answer_key,
                           mc_score_per_q, tf_score_1, tf_score_2, tf_score_3, tf_score_4, sa_score_per_q)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        e.title, e.pdf_url or "", e.content or "", e.question_mathml or "", e.due_date or "", e.duration_minutes or 60, mc_c, tf_c, sa_c, cleaned_key,
        e.mc_score_per_q or 0.25, e.tf_score_1 or 0.10, e.tf_score_2 or 0.25,
        e.tf_score_3 or 0.50, e.tf_score_4 or 1.00, e.sa_score_per_q or 0.50
    ))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Đã tạo đề kiểm tra thành công"}

@app.put("/api/exams/{exam_id}")
def update_exam(exam_id: int, e: ExamCreate):
    conn = get_db()
    cursor = conn.cursor()
    mc_c = e.mc_count or 0
    tf_c = e.tf_count or 0
    sa_c = e.sa_count or 0
    cleaned_key = sanitize_and_clean_answer_key(e.answer_key or "{}", mc_c, tf_c, sa_c)

    cursor.execute("""
        UPDATE exams
        SET title = %s, pdf_url = %s, content = %s, question_mathml = %s, due_date = %s, duration_minutes = %s,
            mc_count = %s, tf_count = %s, sa_count = %s, answer_key = %s,
            mc_score_per_q = %s, tf_score_1 = %s, tf_score_2 = %s, tf_score_3 = %s, tf_score_4 = %s, sa_score_per_q = %s
        WHERE id = %s
    """, (
        e.title, e.pdf_url or "", e.content or "", e.question_mathml or "", e.due_date or "", e.duration_minutes or 60, mc_c, tf_c, sa_c, cleaned_key,
        e.mc_score_per_q or 0.25, e.tf_score_1 or 0.10, e.tf_score_2 or 0.25,
        e.tf_score_3 or 0.50, e.tf_score_4 or 1.00, e.sa_score_per_q or 0.50,
        exam_id
    ))
    
    cursor.execute("SELECT id, answer_text FROM exam_submissions WHERE exam_id = %s", (exam_id,))
    subs = cursor.fetchall()
    for sub in subs:
        raw_score, max_score, score_10 = calculate_submission_score_details(
            cleaned_key, sub["answer_text"],
            mc_count=mc_c, tf_count=tf_c, sa_count=sa_c,
            mc_score_per_q=e.mc_score_per_q or 0.25,
            tf_score_1=e.tf_score_1 or 0.10,
            tf_score_2=e.tf_score_2 or 0.25,
            tf_score_3=e.tf_score_3 or 0.50,
            tf_score_4=e.tf_score_4 or 1.00,
            sa_score_per_q=e.sa_score_per_q or 0.50
        )
        cursor.execute("UPDATE exam_submissions SET raw_score = %s, max_score = %s, score = %s WHERE id = %s",
                       (raw_score, max_score, score_10, sub["id"]))

    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Đã cập nhật đề thi và chấm lại điểm!"}

@app.delete("/api/exams/{exam_id}")
def delete_exam(exam_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM exam_submissions WHERE exam_id = %s", (exam_id,))
    cursor.execute("DELETE FROM exams WHERE id = %s", (exam_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Đã xóa đề thi"}

@app.get("/api/exam_submissions")
def get_exam_submissions(exam_id: Optional[int] = None):
    conn = get_db()
    cursor = conn.cursor()
    if exam_id:
        cursor.execute("SELECT * FROM exam_submissions WHERE exam_id = %s ORDER BY score DESC, id DESC", (exam_id,))
    else:
        cursor.execute("SELECT * FROM exam_submissions ORDER BY id DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    res = []
    for r in rows:
        item = dict(r)
        item["raw_score"] = float(item["raw_score"]) if item.get("raw_score") is not None else 0.0
        item["max_score"] = float(item["max_score"]) if item.get("max_score") is not None else 0.0
        item["score"] = float(item["score"]) if item.get("score") is not None else 0.0
        res.append(item)
    return res

class ExamSubmissionCreate(BaseModel):
    exam_id: int
    student_name: str
    answer_text: str

@app.post("/api/exam_submissions")
def create_exam_submission(s: ExamSubmissionCreate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM exams WHERE id = %s", (s.exam_id,))
    ex = cursor.fetchone()
    if not ex:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Đề thi không tồn tại!")

    raw_score, max_score, score_10 = calculate_submission_score_details(
        ex.get("answer_key", "{}"),
        s.answer_text,
        mc_count=ex.get("mc_count", 0),
        tf_count=ex.get("tf_count", 0),
        sa_count=ex.get("sa_count", 0),
        mc_score_per_q=ex.get("mc_score_per_q", 0.25),
        tf_score_1=ex.get("tf_score_1", 0.10),
        tf_score_2=ex.get("tf_score_2", 0.25),
        tf_score_3=ex.get("tf_score_3", 0.50),
        tf_score_4=ex.get("tf_score_4", 1.00),
        sa_score_per_q=ex.get("sa_score_per_q", 0.50)
    )

    cursor.execute("""
        INSERT INTO exam_submissions (exam_id, student_name, answer_text, raw_score, max_score, score)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (s.exam_id, s.student_name, s.answer_text, raw_score, max_score, score_10))
    
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Nộp bài kiểm tra thành công!", "raw_score": raw_score, "max_score": max_score, "score": score_10}
