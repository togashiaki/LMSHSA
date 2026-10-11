from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import os

app = FastAPI(title="Hệ thống Quản lý Lớp học")

DB_FILE = "classroom.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_code TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        dob TEXT,
        status TEXT DEFAULT 'Active'
    );
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        status TEXT NOT NULL,
        UNIQUE(student_id, date)
    );
    CREATE TABLE IF NOT EXISTS videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        youtube_id TEXT NOT NULL,
        description TEXT,
        order_index INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        drive_url TEXT NOT NULL,
        category TEXT DEFAULT 'Chung'
    );
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        due_date TEXT
    );
    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER NOT NULL,
        student_name TEXT NOT NULL,
        answer_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        question_mathml TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()

init_db()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

# --- QUẢN LÝ HỌC SINH ---
@app.get("/api/students")
def get_students():
    conn = get_db()
    students = conn.execute("SELECT * FROM students ORDER BY student_code ASC").fetchall()
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
    try:
        conn.execute("INSERT INTO students (student_code, full_name, dob, status) VALUES (?, ?, ?, ?)",
                     (s.student_code, s.full_name, s.dob, s.status))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Mã học sinh đã tồn tại")
    conn.close()
    return {"message": "Đã thêm học sinh"}

@app.delete("/api/students/{student_id}")
def delete_student(student_id: int):
    conn = get_db()
    conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()
    return {"message": "Đã xóa học sinh"}

# --- ĐIỂM DANH ---
@app.get("/api/attendance")
def get_attendance():
    conn = get_db()
    rows = conn.execute("SELECT * FROM attendance").fetchall()
    conn.close()
    return [dict(r) for r in rows]

class AttendanceUpdate(BaseModel):
    student_id: int
    date: str
    status: str

@app.post("/api/attendance")
def save_attendance(data: AttendanceUpdate):
    conn = get_db()
    conn.execute("""
        INSERT INTO attendance (student_id, date, status)
        VALUES (?, ?, ?)
        ON CONFLICT(student_id, date) DO UPDATE SET status=excluded.status
    """, (data.student_id, data.date, data.status))
    conn.commit()
    conn.close()
    return {"message": "Đã ghi nhận điểm danh"}

# --- VIDEO BÀI GIẢNG ---
@app.get("/api/videos")
def get_videos():
    conn = get_db()
    rows = conn.execute("SELECT * FROM videos ORDER BY order_index ASC, id DESC").fetchall()
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
    conn.execute("INSERT INTO videos (title, youtube_id, description, order_index) VALUES (?, ?, ?, ?)",
                 (v.title, v.youtube_id, v.description, v.order_index))
    conn.commit()
    conn.close()
    return {"message": "Đã thêm video"}

# --- TÀI LIỆU GOOGLE DRIVE ---
@app.get("/api/documents")
def get_documents():
    conn = get_db()
    rows = conn.execute("SELECT * FROM documents ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

class DocumentCreate(BaseModel):
    title: str
    drive_url: str
    category: Optional[str] = "Chung"

@app.post("/api/documents")
def create_document(d: DocumentCreate):
    conn = get_db()
    conn.execute("INSERT INTO documents (title, drive_url, category) VALUES (?, ?, ?)",
                 (d.title, d.drive_url, d.category))
    conn.commit()
    conn.close()
    return {"message": "Đã thêm tài liệu"}

# --- BÀI TẬP VỀ NHÀ ---
@app.get("/api/assignments")
def get_assignments():
    conn = get_db()
    rows = conn.execute("SELECT * FROM assignments ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

class AssignmentCreate(BaseModel):
    title: str
    content: str
    due_date: Optional[str] = ""

@app.post("/api/assignments")
def create_assignment(a: AssignmentCreate):
    conn = get_db()
    conn.execute("INSERT INTO assignments (title, content, due_date) VALUES (?, ?, ?)",
                 (a.title, a.content, a.due_date))
    conn.commit()
    conn.close()
    return {"message": "Đã tạo bài tập"}

@app.get("/api/submissions")
def get_submissions(assignment_id: Optional[int] = None):
    conn = get_db()
    if assignment_id:
        rows = conn.execute("SELECT * FROM submissions WHERE assignment_id = ? ORDER BY id DESC", (assignment_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM submissions ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

class SubmissionCreate(BaseModel):
    assignment_id: int
    student_name: str
    answer_text: str

@app.post("/api/submissions")
def create_submission(s: SubmissionCreate):
    conn = get_db()
    conn.execute("INSERT INTO submissions (assignment_id, student_name, answer_text) VALUES (?, ?, ?)",
                 (s.assignment_id, s.student_name, s.answer_text))
    conn.commit()
    conn.close()
    return {"message": "Nộp bài thành công"}

# --- ĐỀ KIỂM TRA & MATHML ---
@app.get("/api/exams")
def get_exams():
    conn = get_db()
    rows = conn.execute("SELECT * FROM exams ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

class ExamCreate(BaseModel):
    title: str
    question_mathml: str

@app.post("/api/exams")
def create_exam(e: ExamCreate):
    conn = get_db()
    conn.execute("INSERT INTO exams (title, question_mathml) VALUES (?, ?)", (e.title, e.question_mathml))
    conn.commit()
    conn.close()
    return {"message": "Đã thêm câu hỏi/đề thi"}
