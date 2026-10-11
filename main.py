from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import sqlite3

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
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'student'
    );
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
    
    # Tạo tài khoản Admin mặc định nếu chưa có người dùng nào
    user_count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count == 0:
        cursor.execute("INSERT INTO users (username, password, full_name, role) VALUES (?, ?, ?, ?)",
                       ("admin", "123456", "Giáo viên Admin", "teacher"))
        
    conn.commit()
    conn.close()

init_db()

# --- XÁC THỰC & TÀI KHOẢN ---
class UserRegister(BaseModel):
    username: str
    password: str
    full_name: str
    role: str = "student" # "teacher" hoặc "student"

class UserLogin(BaseModel):
    username: str
    password: str

@app.post("/api/register")
def register(u: UserRegister):
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (username, password, full_name, role) VALUES (?, ?, ?, ?)",
                     (u.username.strip(), u.password, u.full_name.strip(), u.role))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Tên đăng nhập đã tồn tại!")
    conn.close()
    return {"message": "Đăng ký thành công!"}

@app.post("/api/login")
def login(u: UserLogin):
    conn = get_db()
    user = conn.execute("SELECT id, username, full_name, role FROM users WHERE username = ? AND password = ?",
                        (u.username.strip(), u.password)).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không đúng!")
    return dict(user)

# ... Giữ nguyên toàn bộ các endpoint cũ bên dưới (/api/students, /api/attendance, /api/videos, v.v.) ...
