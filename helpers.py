from flask import redirect, render_template, session
from datetime import timedelta, datetime
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    
    return decorated_function

def timer_on(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("timer"):
            return redirect("/focus-session")
        return f(*args, **kwargs)
    
    return decorated_function

def currentStreak(date, db):
    rows = db.execute("SELECT * FROM tasks WHERE user_id = ? AND completed_at = ?",session.get("user_id"), date)
    if len(rows) > 0:
        return 1 + currentStreak(date - timedelta(days=1), db)
    else:
        return 0
    
def currentFocusStreak(date, db):
    rows = db.execute("SELECT * FROM focus_sessions WHERE user_id = ? AND date = ?",session.get("user_id"), date)
    if len(rows) > 0:
        return 1 + currentFocusStreak(date - timedelta(days=1), db)
    else:
        return 0
    
def longestStreak(db):
    rows = db.execute("SELECT DISTINCT completed_at FROM tasks WHERE user_id = ? AND status = 'completed' ORDER BY completed_at DESC", session.get("user_id"))
    rows_dict = [row['completed_at'] for row in rows]
    
    try:
        now = rows_dict[0]
        now = datetime.strptime(now, "%Y-%m-%d").date()
        rows_dict.pop(0)
    except:
        return 0
    
    current = 1
    highest = 0
    for date in rows_dict:
        check = now - timedelta(days=1)
        if check.isoformat() == date:
            now = check
            current += 1
        else:
            now = datetime.strptime(date, "%Y-%m-%d").date()
            highest = max(highest, current)
            current = 1
    highest = max(highest, current)
    return highest

def longestFocusStreak(db):
    rows = db.execute("SELECT DISTINCT date FROM focus_sessions WHERE user_id = ? ORDER BY date DESC", session.get("user_id"))
    rows_dict = [row['date'] for row in rows]
    
    try:
        now = rows_dict[0]
        now = datetime.strptime(now, "%Y-%m-%d").date()
        rows_dict.pop(0)
    except:
        return 0
    
    current = 1
    highest = 0
    for date in rows_dict:
        check = now - timedelta(days=1)
        if check.isoformat() == date:
            now = check
            current += 1
        else:
            now = datetime.strptime(date, "%Y-%m-%d").date()
            highest = max(highest, current)
            current = 1
    highest = max(highest, current)
    return highest