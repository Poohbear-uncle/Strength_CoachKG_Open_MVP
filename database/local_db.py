import sqlite3
import os

# DB 파일이 프로젝트 루트의 database/ 디렉토리 내에 보존되도록 경로를 지정합니다.
DB_PATH = os.path.join(os.path.dirname(__file__), "coachkg.db")

def init_local_db():
    """
    애플리케이션 작동 시 호출되어 로그 테이블의 생성을 보장합니다.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 세션 묶음 로그 테이블 생성 (SQL 내의 샵 주석을 완벽히 소거하여 안정성 유지)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assessment_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_token TEXT,
            email TEXT,
            name TEXT,
            strength_code TEXT,
            sorting_group TEXT,
            final_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_user_run(session_token, email, name, final_results):
    """
    사용자가 진단을 완료했을 때 도출된 최종 결과 리스트 전체를 일괄 저장합니다.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.executemany("""
            INSERT INTO assessment_logs (session_token, email, name, strength_code, sorting_group, final_score)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            (session_token, email, name, r["code"], r["group"], r["final_score"])
            for r in final_results
        ])
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_user_history_by_email(email):
    """
    이메일을 기반으로 사용자의 과거 진단 이력을 최신순으로 역추적하여 반환합니다.
    """
    conn = sqlite3.connect(DB_PATH)
    # 튜플 대신 딕셔너리 형태로 데이터를 다루기 위해 row_factory 변경
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT session_token, name, strength_code, sorting_group, final_score, created_at 
        FROM assessment_logs 
        WHERE email = ? 
        ORDER BY created_at DESC
    """, (email,))
    
    rows = cursor.fetchall()
    conn.close()
    
    # 로우 데이터를 다루기 쉬운 기본 딕셔너리 리스트로 직렬화
    return [dict(row) for row in rows]