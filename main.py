import sqlite3
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="LMS Lightweight System")

DB_FILE = "classroom.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        name TEXT,
        dob TEXT,
        status TEXT DEFAULT 'Đang học'
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        date TEXT,
        status TEXT,
        UNIQUE(student_id, date)
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        youtube_url TEXT,
        description TEXT
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS homeworks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        question TEXT,
        due_date TEXT
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        homework_id INTEGER,
        student_code TEXT,
        student_name TEXT,
        answer TEXT,
        submitted_at TEXT
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        drive_embed_url TEXT,
        download_url TEXT
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        question_content TEXT,
        answer_key TEXT
    )''')
    
    conn.commit()
    conn.close()

init_db()

class StudentModel(BaseModel):
    code: str
    name: str
    dob: str
    status: Optional[str] = "Đang học"

class AttendanceModel(BaseModel):
    student_id: int
    date: str
    status: str

class VideoModel(BaseModel):
    title: str
    youtube_url: str
    description: Optional[str] = ""

class HomeworkModel(BaseModel):
    title: str
    question: str
    due_date: str

class SubmissionModel(BaseModel):
    homework_id: int
    student_code: str
    student_name: str
    answer: str

class DocumentModel(BaseModel):
    title: str
    drive_embed_url: str
    download_url: str

class ExamModel(BaseModel):
    title: str
    question_content: str
    answer_key: str

@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/students")
def get_students():
    conn = get_db()
    students = conn.execute("SELECT * FROM students ORDER BY code ASC").fetchall()
    conn.close()
    return [dict(s) for s in students]

@app.post("/api/students")
def add_student(student: StudentModel):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO students (code, name, dob, status) VALUES (?, ?, ?, ?)",
            (student.code, student.name, student.dob, student.status)
        )
        conn.commit()
        student_id = cursor.lastrowid
        conn.close()
        return {"id": student_id, "message": "Thêm học sinh thành công"}
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Mã học sinh đã tồn tại")

@app.delete("/api/students/{student_id}")
def delete_student(student_id: int):
    conn = get_db()
    conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()
    return {"message": "Xóa học sinh thành công"}

@app.get("/api/attendance")
def get_attendance(date: str):
    conn = get_db()
    records = conn.execute(
        "SELECT student_id, status FROM attendance WHERE date = ?", (date,)
    ).fetchall()
    conn.close()
    return {r["student_id"]: r["status"] for r in records}

@app.post("/api/attendance")
def save_attendance(data: List[AttendanceModel]):
    conn = get_db()
    cursor = conn.cursor()
    for item in data:
        cursor.execute(
            '''INSERT INTO attendance (student_id, date, status)
               VALUES (?, ?, ?)
               ON CONFLICT(student_id, date) DO UPDATE SET status=excluded.status''',
            (item.student_id, item.date, item.status)
        )
    conn.commit()
    conn.close()
    return {"message": "Lưu điểm danh thành công"}

@app.get("/api/videos")
def get_videos():
    conn = get_db()
    videos = conn.execute("SELECT * FROM videos ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(v) for v in videos]

@app.post("/api/videos")
def add_video(video: VideoModel):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO videos (title, youtube_url, description) VALUES (?, ?, ?)",
        (video.title, video.youtube_url, video.description)
    )
    conn.commit()
    conn.close()
    return {"message": "Thêm video thành công"}

@app.get("/api/homeworks")
def get_homeworks():
    conn = get_db()
    homeworks = conn.execute("SELECT * FROM homeworks ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(h) for h in homeworks]

@app.post("/api/homeworks")
def add_homework(hw: HomeworkModel):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO homeworks (title, question, due_date) VALUES (?, ?, ?)",
        (hw.title, hw.question, hw.due_date)
    )
    conn.commit()
    conn.close()
    return {"message": "Tạo BTVN thành công"}

@app.get("/api/submissions/{homework_id}")
def get_submissions(homework_id: int):
    conn = get_db()
    subs = conn.execute(
        "SELECT * FROM submissions WHERE homework_id = ? ORDER BY id DESC", (homework_id,)
    ).fetchall()
    conn.close()
    return [dict(s) for s in subs]

@app.post("/api/submissions")
def submit_homework(sub: SubmissionModel):
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO submissions (homework_id, student_code, student_name, answer, submitted_at) VALUES (?, ?, ?, ?, ?)",
        (sub.homework_id, sub.student_code, sub.student_name, sub.answer, now)
    )
    conn.commit()
    conn.close()
    return {"message": "Nộp bài thành công"}

@app.get("/api/documents")
def get_documents():
    conn = get_db()
    docs = conn.execute("SELECT * FROM documents ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(d) for d in docs]

@app.post("/api/documents")
def add_document(doc: DocumentModel):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO documents (title, drive_embed_url, download_url) VALUES (?, ?, ?)",
        (doc.title, doc.drive_embed_url, doc.download_url)
    )
    conn.commit()
    conn.close()
    return {"message": "Thêm tài liệu thành công"}

@app.get("/api/exams")
def get_exams():
    conn = get_db()
    exams = conn.execute("SELECT * FROM exams ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(e) for e in exams]

@app.post("/api/exams")
def add_exam(exam: ExamModel):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO exams (title, question_content, answer_key) VALUES (?, ?, ?)",
        (exam.title, exam.question_content, exam.answer_key)
    )
    conn.commit()
    conn.close()
    return {"message": "Thêm đề kiểm tra thành công"}
