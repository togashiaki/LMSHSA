from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import json
import re
import math
import statistics as stats_lib
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
    CREATE TABLE IF NOT EXISTS lessons (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        lesson_date TEXT DEFAULT '',
        chapter VARCHAR(100) DEFAULT 'Chương 1',
        order_index INTEGER DEFAULT 0,
        video_url TEXT DEFAULT '',
        video_id TEXT DEFAULT '',
        document_url TEXT DEFAULT '',
        description TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS visit_count INTEGER DEFAULT 1;")
    cursor.execute("ALTER TABLE assignments ADD COLUMN IF NOT EXISTS pdf_url TEXT DEFAULT '';")
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

    cursor.execute("ALTER TABLE exam_submissions ADD COLUMN IF NOT EXISTS time_taken INTEGER DEFAULT 0;")

    cursor.execute("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS chapter VARCHAR(100) DEFAULT 'Chương 1';")
    cursor.execute("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS order_index INTEGER DEFAULT 0;")
    cursor.execute("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS video_url TEXT DEFAULT '';")
    cursor.execute("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS video_id TEXT DEFAULT '';")
    cursor.execute("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS document_url TEXT DEFAULT '';")
    cursor.execute("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS description TEXT DEFAULT '';")
    cursor.execute("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS lesson_video_url TEXT DEFAULT '';")
    cursor.execute("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS lesson_video_id TEXT DEFAULT '';")
    cursor.execute("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS exercise_video_url TEXT DEFAULT '';")
    cursor.execute("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS exercise_video_id TEXT DEFAULT '';")
    cursor.execute("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS documents_json TEXT DEFAULT '[]';")

    # Dọn dẹp các bản ghi cũ vô tình bị lưu đúp link video bài học sang video chữa BTVN
    cursor.execute("""
        UPDATE lessons
        SET exercise_video_url = '', exercise_video_id = '', video_url = '', video_id = ''
        WHERE (exercise_video_url = lesson_video_url OR video_url = lesson_video_url
               OR video_id = lesson_video_id OR exercise_video_id = lesson_video_id)
          AND lesson_video_url IS NOT NULL AND lesson_video_url != '';
    """)
    # Các bài chỉ có link ở cột cũ video_url/video_id (khi chưa tách 2 loại video) mà chưa có video bài học:
    # chuyển sang video chữa BTVN nếu chưa có, tránh mất dữ liệu cũ (không đụng tới các bài đã tách đúng)
    cursor.execute("""
        UPDATE lessons
        SET exercise_video_url = video_url, exercise_video_id = video_id
        WHERE COALESCE(lesson_video_url, '') = '' AND COALESCE(lesson_video_id, '') = ''
          AND COALESCE(exercise_video_url, '') = '' AND COALESCE(exercise_video_id, '') = ''
          AND (COALESCE(video_url, '') != '' OR COALESCE(video_id, '') != '');
    """)

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
    sa_count: int,
    mc_score_per_q: float = 0.25,
    tf_score_1: float = 0.10,
    tf_score_2: float = 0.25,
    tf_score_3: float = 0.50,
    tf_score_4: float = 1.00,
    sa_score_per_q: float = 0.50
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
            "is_correct": is_corr,
            "score": float(mc_score_per_q) if is_corr else 0.0
        })

    tf_detail = []
    tf_key = key.get("tf", {})
    tf_ans = ans.get("tf", {})
    for i in range(1, tf_count + 1):
        sub_list = []
        correct_in_this_q = 0
        has_key = False
        for sub in ['a', 'b', 'c', 'd']:
            sub_q = f"{i}{sub}"
            c_ans = tf_key.get(sub_q, "")
            s_ans = tf_ans.get(sub_q, "")
            if c_ans:
                has_key = True
            is_corr = bool(c_ans and str(s_ans).strip() == str(c_ans).strip())
            if is_corr:
                correct_in_this_q += 1
            sub_list.append({
                "sub_question": f"Ý {sub}",
                "student_answer": s_ans,
                "correct_answer": c_ans,
                "is_correct": is_corr
            })
        pts = 0.0
        if has_key:
            if correct_in_this_q == 1:
                pts = float(tf_score_1)
            elif correct_in_this_q == 2:
                pts = float(tf_score_2)
            elif correct_in_this_q == 3:
                pts = float(tf_score_3)
            elif correct_in_this_q == 4:
                pts = float(tf_score_4)
        tf_detail.append({
            "question": f"Câu {i}",
            "subs": sub_list,
            "correct_subs_count": correct_in_this_q,
            "score": pts
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
            "is_correct": is_corr,
            "score": float(sa_score_per_q) if is_corr else 0.0
        })

    return {"mc": mc_detail, "tf": tf_detail, "sa": sa_detail}

def compute_item_statistics(item: dict, submissions: list) -> dict:
    total_submissions = len(submissions)
    max_possible_raw = float((item.get("mc_count") or 0) * float(item.get("mc_score_per_q") or 0.25) +
                             (item.get("tf_count") or 0) * float(item.get("tf_score_4") or 1.0) +
                             (item.get("sa_count") or 0) * float(item.get("sa_score_per_q") or 0.5))
    if max_possible_raw <= 0:
        max_possible_raw = 10.0

    if total_submissions == 0:
        return {
            "total_submissions": 0,
            "avg_raw_score": 0.0,
            "avg_score": 0.0,
            "median_raw_score": 0.0,
            "median_score": 0.0,
            "min_raw_score": 0.0,
            "max_raw_score": 0.0,
            "min_score": 0.0,
            "max_score": 0.0,
            "max_possible_raw": round(max_possible_raw, 2),
            "score_distribution": [],
            "frequently_missed": [],
            "high_correct": [],
            "all_questions": []
        }

    raw_scores = [float(s.get("raw_score") or 0.0) for s in submissions]
    scores_10 = [float(s.get("score") or 0.0) for s in submissions]

    sub_max_raw = float(submissions[0].get("max_score") or 0.0)
    if sub_max_raw > 0:
        max_possible_raw = sub_max_raw

    avg_raw = round(sum(raw_scores) / total_submissions, 2)
    avg_10 = round(sum(scores_10) / total_submissions, 2)

    try:
        med_raw = round(float(stats_lib.median(raw_scores)), 2)
        med_10 = round(float(stats_lib.median(scores_10)), 2)
    except Exception:
        med_raw = avg_raw
        med_10 = avg_10

    min_raw = min(raw_scores)
    max_raw = max(raw_scores)
    min_10 = min(scores_10)
    max_10 = max(scores_10)

    # Bảng tần số điểm (Tần số theo điểm số đạt được - Points scored)
    raw_counts = {}
    for r in raw_scores:
        key = int(r) if r.is_integer() else r
        raw_counts[key] = raw_counts.get(key, 0) + 1

    # Nếu khoảng điểm nằm trong phạm vi vừa phải (<= 30 đơn vị), tạo dải điểm liên tục để biểu đồ hiển thị giống Ảnh 1
    distribution = []
    min_int = int(math.floor(min_raw))
    max_int = int(math.ceil(max_raw))
    # Hiển thị từ min_int đến max_int hoặc max_possible_raw nếu khoảng hợp lý
    range_span = max_int - min_int
    if 0 <= range_span <= 30 and all(r.is_integer() for r in raw_scores):
        target_max = min(max_int + 2, int(math.ceil(max_possible_raw))) if max_possible_raw >= max_int else max_int
        target_min = max(0, min_int - 1)
        for val in range(target_min, target_max + 1):
            cnt = raw_counts.get(val, 0)
            distribution.append({
                "score": val,
                "count": cnt,
                "percentage": round((cnt / total_submissions) * 100, 1)
            })
    else:
        for k in sorted(raw_counts.keys()):
            distribution.append({
                "score": k,
                "count": raw_counts[k],
                "percentage": round((raw_counts[k] / total_submissions) * 100, 1)
            })

    # Phân tích câu hỏi: Đúng / Sai
    try:
        key_obj = json.loads(item.get("answer_key") or "{}")
    except Exception:
        key_obj = {}

    mc_key = key_obj.get("mc", {})
    tf_key = key_obj.get("tf", {})
    sa_key = key_obj.get("sa", {})

    parsed_subs = []
    for s in submissions:
        try:
            ans_obj = json.loads(s.get("answer_text") or "{}")
        except Exception:
            ans_obj = {}
        parsed_subs.append(ans_obj)

    mc_count = int(item.get("mc_count") or 0)
    tf_count = int(item.get("tf_count") or 0)
    sa_count = int(item.get("sa_count") or 0)

    questions_stat = []

    # 1. Trắc nghiệm (Câu 1 .. N)
    for i in range(1, mc_count + 1):
        q_str = str(i)
        c_ans = str(mc_key.get(q_str, "")).strip().upper()
        corr_cnt = 0
        for p in parsed_subs:
            s_ans = str(p.get("mc", {}).get(q_str, "")).strip().upper()
            if c_ans and s_ans == c_ans:
                corr_cnt += 1
        pct = round(corr_cnt / total_submissions * 100, 1)
        questions_stat.append({
            "id": f"mc_{i}",
            "section": "Trắc nghiệm",
            "question_label": f"Phần trắc nghiệm (Câu {i})",
            "correct_count": corr_cnt,
            "total_count": total_submissions,
            "percentage": pct,
            "correct_answer": c_ans
        })

    # 2. Đúng / Sai (Câu i ý a, b, c, d) - hiển thị giống hệt Ảnh 1: "Phần Đúng/Sai (Câu 14b)"
    for i in range(1, tf_count + 1):
        for sub in ['a', 'b', 'c', 'd']:
            sub_q = f"{i}{sub}"
            c_ans = str(tf_key.get(sub_q, "")).strip()
            corr_cnt = 0
            for p in parsed_subs:
                s_ans = str(p.get("tf", {}).get(sub_q, "")).strip()
                if c_ans and s_ans == c_ans:
                    corr_cnt += 1
            pct = round(corr_cnt / total_submissions * 100, 1)
            questions_stat.append({
                "id": f"tf_{sub_q}",
                "section": "Đúng/Sai",
                "question_label": f"Phần Đúng/Sai (Câu {i}{sub})",
                "correct_count": corr_cnt,
                "total_count": total_submissions,
                "percentage": pct,
                "correct_answer": c_ans
            })

    # 3. Trả lời ngắn / Điền số (Câu 1 .. N)
    for i in range(1, sa_count + 1):
        q_str = str(i)
        c_ans = str(sa_key.get(q_str, "")).strip().lower().replace(",", ".")
        corr_cnt = 0
        for p in parsed_subs:
            s_ans = str(p.get("sa", {}).get(q_str, "")).strip().lower().replace(",", ".")
            if c_ans and s_ans == c_ans and c_ans != "":
                corr_cnt += 1
        pct = round(corr_cnt / total_submissions * 100, 1)
        questions_stat.append({
            "id": f"sa_{i}",
            "section": "Trả lời ngắn",
            "question_label": f"Phần Trả lời ngắn (Câu {i})",
            "correct_count": corr_cnt,
            "total_count": total_submissions,
            "percentage": pct,
            "correct_answer": sa_key.get(q_str, "")
        })

    # Các câu hay bị sai (Frequently missed questions):
    # Sắp xếp tăng dần theo tỷ lệ đúng (ít người làm đúng nhất lên đầu)
    missed_candidates = [q for q in questions_stat if q["correct_count"] < total_submissions]
    missed_candidates.sort(key=lambda x: (x["correct_count"], x["percentage"]))

    # Các câu làm đúng nhiều (High mastery questions):
    # Sắp xếp giảm dần theo tỷ lệ đúng (nhiều người làm đúng nhất lên đầu)
    high_candidates = [q for q in questions_stat if q["correct_count"] > 0]
    high_candidates.sort(key=lambda x: (-x["correct_count"], -x["percentage"]))

    return {
        "total_submissions": total_submissions,
        "avg_raw_score": avg_raw,
        "avg_score": avg_10,
        "median_raw_score": med_raw,
        "median_score": med_10,
        "min_raw_score": min_raw,
        "max_raw_score": max_raw,
        "min_score": min_10,
        "max_score": max_10,
        "max_possible_raw": round(max_possible_raw, 2),
        "score_distribution": distribution,
        "frequently_missed": missed_candidates[:15],
        "high_correct": high_candidates[:15],
        "all_questions": questions_stat
    }

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

@app.put("/api/videos/{video_id}")
def update_video(video_id: int, v: VideoCreate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE videos
        SET title = %s, youtube_id = %s, description = %s, order_index = %s
        WHERE id = %s
    """, (v.title, v.youtube_id, v.description, v.order_index, video_id))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Đã cập nhật video"}

@app.delete("/api/videos/{video_id}")
def delete_video(video_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM videos WHERE id = %s", (video_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Đã xóa video"}

# --- BÀI HỌC (GỒM VIDEO CHỮA BÀI & TÀI LIỆU) ---
def extract_youtube_id(url_or_id: str) -> str:
    if not url_or_id:
        return ""
    text = url_or_id.strip()
    match = re.search(r'(?:v=|\/embed\/|\/watch\?v=|youtu\.be\/|\/v\/|shorts\/|^)([A-Za-z0-9_-]{11})', text)
    if match:
        return match.group(1)
    return text

class LessonCreate(BaseModel):
    title: str
    lesson_date: Optional[str] = ""
    chapter: Optional[str] = "Chương 1"
    order_index: Optional[int] = 0
    lesson_video_url: Optional[str] = ""
    lesson_video_id: Optional[str] = ""
    exercise_video_url: Optional[str] = ""
    exercise_video_id: Optional[str] = ""
    video_url: Optional[str] = ""
    video_id: Optional[str] = ""
    document_url: Optional[str] = ""
    documents_json: Optional[str] = "[]"
    description: Optional[str] = ""

@app.get("/api/lessons")
def get_lessons():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lessons ORDER BY order_index ASC, id ASC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/lessons")
def create_lesson(l: LessonCreate):
    conn = get_db()
    cursor = conn.cursor()
    l_v_id = extract_youtube_id(l.lesson_video_id or l.lesson_video_url or "")
    ex_v_id = extract_youtube_id(l.exercise_video_id or l.exercise_video_url or "")
    v_url = l.exercise_video_url or ""
    v_id = ex_v_id or ""

    cursor.execute("""
        INSERT INTO lessons (title, lesson_date, chapter, order_index,
                             lesson_video_url, lesson_video_id,
                             exercise_video_url, exercise_video_id,
                             video_url, video_id, document_url, documents_json, description)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        l.title.strip(),
        l.lesson_date or "",
        l.chapter or "Chương 1",
        l.order_index or 0,
        l.lesson_video_url or "",
        l_v_id,
        l.exercise_video_url or "",
        ex_v_id,
        v_url,
        v_id,
        l.document_url or "",
        l.documents_json or "[]",
        l.description or ""
    ))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Đã tạo bài học thành công"}

@app.put("/api/lessons/{lesson_id}")
def update_lesson(lesson_id: int, l: LessonCreate):
    conn = get_db()
    cursor = conn.cursor()
    l_v_id = extract_youtube_id(l.lesson_video_id or l.lesson_video_url or "")
    ex_v_id = extract_youtube_id(l.exercise_video_id or l.exercise_video_url or "")
    v_url = l.exercise_video_url or ""
    v_id = ex_v_id or ""

    cursor.execute("""
        UPDATE lessons
        SET title = %s, lesson_date = %s, chapter = %s, order_index = %s,
            lesson_video_url = %s, lesson_video_id = %s,
            exercise_video_url = %s, exercise_video_id = %s,
            video_url = %s, video_id = %s, document_url = %s, documents_json = %s, description = %s
        WHERE id = %s
    """, (
        l.title.strip(),
        l.lesson_date or "",
        l.chapter or "Chương 1",
        l.order_index or 0,
        l.lesson_video_url or "",
        l_v_id,
        l.exercise_video_url or "",
        ex_v_id,
        v_url,
        v_id,
        l.document_url or "",
        l.documents_json or "[]",
        l.description or "",
        lesson_id
    ))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Đã cập nhật bài học"}

@app.delete("/api/lessons/{lesson_id}")
def delete_lesson(lesson_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM lessons WHERE id = %s", (lesson_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Đã xóa bài học"}

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
        INSERT INTO assignments (title, content, pdf_url, due_date, mc_count, tf_count, sa_count, answer_key,
                                 mc_score_per_q, tf_score_1, tf_score_2, tf_score_3, tf_score_4, sa_score_per_q)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        a.title, a.content, a.pdf_url or "", a.due_date, mc_c, tf_c, sa_c, cleaned_key,
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
        SET title = %s, content = %s, pdf_url = %s, due_date = %s, mc_count = %s, tf_count = %s, sa_count = %s, answer_key = %s,
            mc_score_per_q = %s, tf_score_1 = %s, tf_score_2 = %s, tf_score_3 = %s, tf_score_4 = %s, sa_score_per_q = %s
        WHERE id = %s
    """, (
        a.title, a.content, a.pdf_url or "", a.due_date, mc_c, tf_c, sa_c, cleaned_key,
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

@app.get("/api/assignments/{assignment_id}/statistics")
def get_assignment_statistics(assignment_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM assignments WHERE id = %s", (assignment_id,))
    item = cursor.fetchone()
    if not item:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Bài tập không tồn tại!")
    cursor.execute("SELECT * FROM submissions WHERE assignment_id = %s ORDER BY id DESC", (assignment_id,))
    subs = cursor.fetchall()
    cursor.close()
    conn.close()
    return compute_item_statistics(dict(item), [dict(s) for s in subs])

@app.get("/api/submissions/{submission_id}/detail")
def get_submission_detail(submission_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, a.answer_key, a.mc_count, a.tf_count, a.sa_count, a.title as assignment_title,
               a.mc_score_per_q, a.tf_score_1, a.tf_score_2, a.tf_score_3, a.tf_score_4, a.sa_score_per_q
        FROM submissions s
        JOIN assignments a ON s.assignment_id = a.id
        WHERE s.id = %s
    """, (submission_id,))
    sub = cursor.fetchone()
    cursor.close()
    conn.close()
    if not sub:
        raise HTTPException(status_code=404, detail="Bài nộp không tồn tại!")
    
    breakdown = build_detailed_breakdown(
        sub["answer_key"],
        sub["answer_text"],
        sub["mc_count"] or 0,
        sub["tf_count"] or 0,
        sub["sa_count"] or 0,
        mc_score_per_q=float(sub.get("mc_score_per_q") or 0.25),
        tf_score_1=float(sub.get("tf_score_1") or 0.10),
        tf_score_2=float(sub.get("tf_score_2") or 0.25),
        tf_score_3=float(sub.get("tf_score_3") or 0.50),
        tf_score_4=float(sub.get("tf_score_4") or 1.00),
        sa_score_per_q=float(sub.get("sa_score_per_q") or 0.50)
    )
    result = dict(sub)
    result["raw_score"] = float(result["raw_score"]) if result.get("raw_score") is not None else 0.0
    result["max_score"] = float(result["max_score"]) if result.get("max_score") is not None else 0.0
    result["score"] = float(result["score"]) if result.get("score") is not None else 0.0
    result["breakdown"] = breakdown
    return result

@app.delete("/api/submissions/{submission_id}")
def delete_submission(submission_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM submissions WHERE id = %s", (submission_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Đã xóa bài nộp"}

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
        item["time_taken"] = int(item["time_taken"]) if item.get("time_taken") is not None else 0
        res.append(item)
    return res

@app.get("/api/exam_submissions/{submission_id}/detail")
def get_exam_submission_detail(submission_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, e.answer_key, e.mc_count, e.tf_count, e.sa_count, e.title as exam_title,
               e.mc_score_per_q, e.tf_score_1, e.tf_score_2, e.tf_score_3, e.tf_score_4, e.sa_score_per_q
        FROM exam_submissions s
        JOIN exams e ON s.exam_id = e.id
        WHERE s.id = %s
    """, (submission_id,))
    sub = cursor.fetchone()
    cursor.close()
    conn.close()
    if not sub:
        raise HTTPException(status_code=404, detail="Bài nộp không tồn tại!")

    breakdown = build_detailed_breakdown(
        sub["answer_key"],
        sub["answer_text"],
        sub["mc_count"] or 0,
        sub["tf_count"] or 0,
        sub["sa_count"] or 0,
        mc_score_per_q=float(sub.get("mc_score_per_q") or 0.25),
        tf_score_1=float(sub.get("tf_score_1") or 0.10),
        tf_score_2=float(sub.get("tf_score_2") or 0.25),
        tf_score_3=float(sub.get("tf_score_3") or 0.50),
        tf_score_4=float(sub.get("tf_score_4") or 1.00),
        sa_score_per_q=float(sub.get("sa_score_per_q") or 0.50)
    )
    result = dict(sub)
    result["raw_score"] = float(result["raw_score"]) if result.get("raw_score") is not None else 0.0
    result["max_score"] = float(result["max_score"]) if result.get("max_score") is not None else 0.0
    result["score"] = float(result["score"]) if result.get("score") is not None else 0.0
    for k in ["mc_score_per_q", "tf_score_1", "tf_score_2", "tf_score_3", "tf_score_4", "sa_score_per_q"]:
        if result.get(k) is not None:
            result[k] = float(result[k])
    result["breakdown"] = breakdown
    return result

@app.get("/api/exams/{exam_id}/statistics")
def get_exam_statistics(exam_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM exams WHERE id = %s", (exam_id,))
    item = cursor.fetchone()
    if not item:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Đề thi không tồn tại!")
    cursor.execute("SELECT * FROM exam_submissions WHERE exam_id = %s ORDER BY id DESC", (exam_id,))
    subs = cursor.fetchall()
    cursor.close()
    conn.close()
    return compute_item_statistics(dict(item), [dict(s) for s in subs])

@app.delete("/api/exam_submissions/{submission_id}")
def delete_exam_submission(submission_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM exam_submissions WHERE id = %s", (submission_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Đã xóa bài nộp đề kiểm tra"}

class ExamSubmissionCreate(BaseModel):
    exam_id: int
    student_name: str
    answer_text: str
    time_taken: Optional[int] = 0

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
        INSERT INTO exam_submissions (exam_id, student_name, answer_text, raw_score, max_score, score, time_taken)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (s.exam_id, s.student_name, s.answer_text, raw_score, max_score, score_10, s.time_taken or 0))
    
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Nộp bài kiểm tra thành công!", "raw_score": raw_score, "max_score": max_score, "score": score_10}

# --- THỐNG KÊ TỔNG QUAN HỆ THỐNG ---
@app.get("/api/dashboard/stats")
def get_dashboard_stats():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as cnt FROM students")
    total_students = cursor.fetchone()["cnt"]
    
    cursor.execute("SELECT COUNT(*) as cnt FROM videos")
    total_videos = cursor.fetchone()["cnt"]
    
    cursor.execute("SELECT COUNT(*) as cnt FROM documents")
    total_documents = cursor.fetchone()["cnt"]
    
    cursor.execute("SELECT COUNT(*) as cnt FROM assignments")
    total_assignments = cursor.fetchone()["cnt"]
    
    cursor.execute("SELECT COUNT(*) as cnt FROM exams")
    total_exams = cursor.fetchone()["cnt"]
    
    cursor.execute("SELECT COALESCE(AVG(score), 0) as avg_score, COUNT(*) as total_sub FROM submissions")
    sub_stat = cursor.fetchone()
    avg_hw_score = round(float(sub_stat["avg_score"]), 2)
    total_hw_subs = sub_stat["total_sub"]
    
    cursor.execute("SELECT COALESCE(AVG(score), 0) as avg_score, COUNT(*) as total_sub FROM exam_submissions")
    ex_stat = cursor.fetchone()
    avg_ex_score = round(float(ex_stat["avg_score"]), 2)
    total_ex_subs = ex_stat["total_sub"]
    
    cursor.execute("SELECT COUNT(*) as total, SUM(CASE WHEN status = 'Có mặt' THEN 1 ELSE 0 END) as present FROM attendance")
    att_stat = cursor.fetchone()
    tot_att = att_stat["total"] or 0
    pres_att = att_stat["present"] or 0
    attendance_rate = round((pres_att / tot_att) * 100) if tot_att > 0 else 100
    
    cursor.close()
    conn.close()
    
    return {
        "total_students": total_students,
        "total_videos": total_videos,
        "total_documents": total_documents,
        "total_assignments": total_assignments,
        "total_exams": total_exams,
        "avg_hw_score": avg_hw_score,
        "total_hw_submissions": total_hw_subs,
        "avg_exam_score": avg_ex_score,
        "total_exam_submissions": total_ex_subs,
        "attendance_rate": attendance_rate
    }
