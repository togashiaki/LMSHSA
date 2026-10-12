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
        role VARCHAR(50) NOT NULL DEFAULT 'student'
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
        category VARCHAR(100) DEFAULT 'Chung'
    );
    CREATE TABLE IF NOT EXISTS assignments (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
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
        score NUMERIC(5, 2) DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS exams (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        question_mathml TEXT NOT NULL
    );
    """)
    
    cursor.execute("ALTER TABLE assignments ADD COLUMN IF NOT EXISTS mc_count INTEGER DEFAULT 0;")
    cursor.execute("ALTER TABLE assignments ADD COLUMN IF NOT EXISTS tf_count INTEGER DEFAULT 0;")
    cursor.execute("ALTER TABLE assignments ADD COLUMN IF NOT EXISTS sa_count INTEGER DEFAULT 0;")
    cursor.execute("ALTER TABLE assignments ADD COLUMN IF NOT EXISTS answer_key TEXT DEFAULT '{}';")
    cursor.execute("ALTER TABLE assignments ADD COLUMN IF NOT EXISTS mc_score_per_q NUMERIC(4, 2) DEFAULT 0.25;")
    cursor.execute("ALTER TABLE assignments ADD COLUMN IF NOT EXISTS tf_score_1 NUMERIC(4, 2) DEFAULT 0.10;")
    cursor.execute("ALTER TABLE assignments ADD COLUMN IF NOT EXISTS tf_score_2 NUMERIC(4, 2) DEFAULT 0.25;")
    cursor.execute("ALTER TABLE assignments ADD COLUMN IF NOT EXISTS tf_score_3 NUMERIC(4, 2) DEFAULT 0.50;")
    cursor.execute("ALTER TABLE assignments ADD COLUMN IF NOT EXISTS tf_score_4 NUMERIC(4, 2) DEFAULT 1.00;")
    cursor.execute("ALTER TABLE assignments ADD COLUMN IF NOT EXISTS sa_score_per_q NUMERIC(4, 2) DEFAULT 0.50;")
    cursor.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS score NUMERIC(5, 2) DEFAULT 0;")

    cursor.execute("SELECT COUNT(*) FROM users")
    res = cursor.fetchone()
    user_count = res['count'] if res else 0
    if user_count == 0:
        cursor.execute("INSERT INTO users (username, password, full_name, role) VALUES (%s, %s, %s, %s)",
                       ("admin", "123456", "Giáo viên Admin", "teacher"))

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

def calculate_submission_score(
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
) -> float:
    try:
        key = json.loads(answer_key_raw or "{}")
    except Exception:
        key = {}
    try:
        ans = json.loads(student_answers_raw or "{}")
    except Exception:
        ans = {}

    total_score = 0.0

    mc_key = key.get("mc", {})
    mc_ans = ans.get("mc", {})
    for i in range(1, mc_count + 1):
        q_num = str(i)
        correct_opt = mc_key.get(q_num)
        if not correct_opt:
            continue
        student_opt = mc_ans.get(q_num, "")
        if str(student_opt).strip().upper() == str(correct_opt).strip().upper():
            total_score += float(mc_score_per_q)

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
                total_score += float(tf_score_1)
            elif correct_in_this_q == 2:
                total_score += float(tf_score_2)
            elif correct_in_this_q == 3:
                total_score += float(tf_score_3)
            elif correct_in_this_q == 4:
                total_score += float(tf_score_4)

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
            total_score += float(sa_score_per_q)

    return round(total_score, 2)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

# --- XÁC THỰC & TÀI KHOẢN ---
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
        cursor.execute("INSERT INTO users (username, password, full_name, role) VALUES (%s, %s, %s, %s)",
                       (u.username.strip(), u.password, u.full_name.strip(), u.role))
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
    cursor.execute("SELECT id, username, full_name, role FROM users WHERE username = %s AND password = %s",
                   (u.username.strip(), u.password))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không đúng!")
    return dict(user)

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
    cursor.execute("SELECT * FROM documents ORDER BY id DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(r) for r in rows]

class DocumentCreate(BaseModel):
    title: str
    drive_url: str
    category: Optional[str] = "Chung"

@app.post("/api/documents")
def create_document(d: DocumentCreate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO documents (title, drive_url, category) VALUES (%s, %s, %s)",
                   (d.title, d.drive_url, d.category))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Đã thêm tài liệu"}

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
    due_date: Optional[str] = ""
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
        INSERT INTO assignments (title, content, due_date, mc_count, tf_count, sa_count, answer_key,
                                 mc_score_per_q, tf_score_1, tf_score_2, tf_score_3, tf_score_4, sa_score_per_q)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        a.title, a.content, a.due_date, mc_c, tf_c, sa_c, cleaned_key,
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
        SET title = %s, content = %s, due_date = %s, mc_count = %s, tf_count = %s, sa_count = %s, answer_key = %s,
            mc_score_per_q = %s, tf_score_1 = %s, tf_score_2 = %s, tf_score_3 = %s, tf_score_4 = %s, sa_score_per_q = %s
        WHERE id = %s
    """, (
        a.title, a.content, a.due_date, mc_c, tf_c, sa_c, cleaned_key,
        a.mc_score_per_q or 0.25, a.tf_score_1 or 0.10, a.tf_score_2 or 0.25,
        a.tf_score_3 or 0.50, a.tf_score_4 or 1.00, a.sa_score_per_q or 0.50,
        assignment_id
    ))
    
    cursor.execute("SELECT id, answer_text FROM submissions WHERE assignment_id = %s", (assignment_id,))
    subs = cursor.fetchall()
    for sub in subs:
        score = calculate_submission_score(
            cleaned_key, sub["answer_text"],
            mc_count=mc_c, tf_count=tf_c, sa_count=sa_c,
            mc_score_per_q=a.mc_score_per_q or 0.25,
            tf_score_1=a.tf_score_1 or 0.10,
            tf_score_2=a.tf_score_2 or 0.25,
            tf_score_3=a.tf_score_3 or 0.50,
            tf_score_4=a.tf_score_4 or 1.00,
            sa_score_per_q=a.sa_score_per_q or 0.50
        )
        cursor.execute("UPDATE submissions SET score = %s WHERE id = %s", (score, sub["id"]))

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
        item["score"] = float(item["score"]) if item["score"] is not None else 0.0
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
    
    due_date_str = assign.get("due_date")
    if due_date_str:
        try:
            due_dt = datetime.fromisoformat(due_date_str)
            if datetime.now() > due_dt:
                cursor.close()
                conn.close()
                raise HTTPException(status_code=400, detail="Bài tập đã hết hạn nộp bài!")
        except ValueError:
            pass

    mc_c = assign.get("mc_count", 0)
    tf_c = assign.get("tf_count", 0)
    sa_c = assign.get("sa_count", 0)

    score = calculate_submission_score(
        assign.get("answer_key", "{}"),
        s.answer_text,
        mc_count=mc_c,
        tf_count=tf_c,
        sa_count=sa_c,
        mc_score_per_q=assign.get("mc_score_per_q", 0.25),
        tf_score_1=assign.get("tf_score_1", 0.10),
        tf_score_2=assign.get("tf_score_2", 0.25),
        tf_score_3=assign.get("tf_score_3", 0.50),
        tf_score_4=assign.get("tf_score_4", 1.00),
        sa_score_per_q=assign.get("sa_score_per_q", 0.50)
    )

    cursor.execute("""
        INSERT INTO submissions (assignment_id, student_name, answer_text, score)
        VALUES (%s, %s, %s, %s)
    """, (s.assignment_id, s.student_name, s.answer_text, score))
    
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Nộp bài thành công!", "score": score}

# --- ĐỀ KIỂM TRA & MATHML ---
@app.get("/api/exams")
def get_exams():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM exams ORDER BY id DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(r) for r in rows]

class ExamCreate(BaseModel):
    title: str
    question_mathml: str

@app.post("/api/exams")
def create_exam(e: ExamCreate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO exams (title, question_mathml) VALUES (%s, %s)", (e.title, e.question_mathml))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Đã thêm câu hỏi/đề thi"}
