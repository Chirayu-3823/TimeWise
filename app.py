import os

from cs50 import SQL
from flask import Flask, render_template, redirect, flash, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, date, timedelta, timezone

from helpers import login_required, currentStreak, longestStreak, timer_on, currentFocusStreak, longestFocusStreak

# start app
app = Flask(__name__)

# auto-reload
app.jinja_env.auto_reload = True
app.config['TEMPLATES_AUTO_RELOAD'] = True

# setting up sessions
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# connecting database
db = SQL("sqlite:///tracker.db")

@app.route("/", methods=["GET", "POST"])
@login_required
@timer_on
def index():
    user = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])[0]
    if request.method == "POST":
        today = date.today()
        id = request.form.get("completed")
        current = db.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?", id, user['id'])[0]['status']
        status = "completed" if current == "pending" else "pending"
        completion = today if status == "completed" else None
        db.execute("UPDATE tasks SET status = ?, completed_at = ? WHERE id = ? AND user_id = ?", status, completion, id, user['id'])
        return redirect("/")

    else:
        user_tasks = db.execute(
            "SELECT * FROM tasks " 
            "WHERE user_id = ? " 
            "ORDER BY due_date ASC, priority DESC", 
            user['id'])
        tasks = []
        completed = 0
        today = date.today()
        today_str = str(today)
        streak = currentStreak(today, db)
        longest = longestStreak(db)
        for task in user_tasks :
            due = task['due_date']
            status = task['status'] == "pending"
            due = due.split("T")
            if due[0] == today_str:
                due =  " ".join(due)
                overdue = False
                now = datetime.now()
                now = now.strftime("%Y-%m-%d %H:%M")
                if now >= due and status:
                    overdue = True
                task['overdue'] = overdue
                due = datetime.strptime(due, "%Y-%m-%d %H:%M")
                due = due.strftime("%b %d %Y at %I:%M %p")
                task['due_date'] = due
                tasks.append(task)

                if task['status'] == 'completed':
                    completed += 1

        progress = (completed / len(tasks) * 100) if len(tasks) > 0 else 0

        return render_template("index.html", user=user, tasks=tasks, completed=completed, progress=progress, streak=streak, longest=longest)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST": 
        email = request.form.get("email")
        password = request.form.get("password")

        if not email:
            return render_template("login.html", error="Please enter email")
        elif not password:
            return render_template("login.html", error="Please enter password", email=email)
        
        rows = db.execute("SELECT * FROM users WHERE email = ?", email)
        
        if len(rows) != 1 or not check_password_hash(rows[0]['password'], password):
            return render_template("login.html", error="Invalid email or password", email=email)
        
        session["user_id"] = rows[0]['id']

        flash("Logged in")
        return redirect("/")

    else:
        if session.get("user_id"):
            return redirect("/")
        return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST": 
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")
        confirm = request.form.get("confirm")

        if not email:
            return render_template("register.html", error="Please enter an email"), 400
        elif not username:
            return render_template("register.html", error="Please enter a username"), 400
        elif not password:
            return render_template("register.html", error="Please enter a password"), 400
        elif not confirm:
            return render_template("register.html", error="Please enter re-enter password"), 400
        elif password != confirm:
            return render_template("register.html", error="Passwords do not match", username=username, email=email), 400
        
        rows = db.execute("SELECT * FROM users WHERE email = ?", email)
        
        if len(rows) != 0:
            return render_template("register.html", error="Email already registered, try logging in.", username=username), 400
        
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        if len(rows) != 0:
            return render_template("register.html", error="Username taken, choose another one.", email=email), 400
        
        db.execute("INSERT INTO users (email, username, password) VALUES(?, ?, ?)", email, username, generate_password_hash(password))

        rows = db.execute(
            "SELECT * FROM users WHERE email = ?", email
        )

        session["user_id"] = rows[0]['id']

        flash("Successfully Registered!")
        return redirect("/")

    else:
        if session.get("user_id"):
            return redirect("/")
        return render_template("register.html")
    
@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Logged Out")
    return redirect("/login")

@app.route("/add", methods=["GET", "POST"])
@login_required
@timer_on
def add():
    user = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])[0]
    title = request.form.get("title")
    desc = request.form.get("desc")
    due = request.form.get("due")
    priority = request.form.get("priority")
    category = request.form.get("category")
    if request.method == "POST":

        if not title:
            return render_template("add.html", error="Please enter a title", user=user)
        elif not due:
            return render_template("add.html", error="Please enter a due date", user=user)
        elif not priority:
            return render_template("add.html", error="Please set priority", user=user)
        
        if not desc:    
            desc = "N/A"
        if not category:
            category = "MISC"
        
        flash("Task Added!")
        db.execute("INSERT INTO tasks (user_id, title, description, priority, category, due_date) VALUES(?, ?, ?, ?, ?, ?)", user['id'], title, desc, int(priority), category, due)
        return redirect("/")
    else:
        return render_template("add.html", user=user)
    
@app.route("/edit", methods=["POST", "GET"])
@login_required
@timer_on
def search():
    user = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])[0]
    title = request.form.get("title")
    desc = request.form.get("desc")
    due = request.form.get("due")
    priority = request.form.get("priority")
    category = request.form.get("category")
    task_id = request.args.get("t")

    if request.method == "POST":
        if not task_id:
            flash("Please select task to edit", "error")
            return redirect("/")
        try:
            task = db.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?", task_id, user['id'])[0]
        except:
            flash("Please Select a valid task!", "error")
            return redirect("/")
        if not title:
            return render_template("edit.html", error="Please enter a title", user=user, task=task)
        elif not due:
            return render_template("edit.html", error="Please enter a deadline", user=user, task=task)
        elif not priority:
            return render_template("edit.html", error="Please enter priority", user=user, task=task)
        
        if not desc:    
            desc = "N/A"
        if not category:
            category = "MISC"

        flash("Task edited!")
        db.execute("UPDATE tasks SET title = ?, description = ?, priority = ?, category = ?, due_date = ? WHERE id = ? AND user_id = ?", title, desc, int(priority), category, due, task_id, user['id'])
        return redirect("/")
    
    else:
        if not task_id:
            flash("Please select task to edit", "error")
            return redirect("/")
        try:
            task = db.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?", task_id, user['id'])[0]
        except:
            flash("Please Select a valid task!", "error")
            return redirect("/")
        return render_template("edit.html", user=user, task=task)
        
@app.route("/view", methods=["POST", "GET"])
@login_required
@timer_on
def view():
    user = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])[0]

    if request.method == "POST":
        id = request.form.get("completed")
        filter = request.form.get("filter")
        sort = request.form.get("sort")
        search = request.form.get("search")

        today = date.today().isoformat()
        current = db.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?", id, user['id'])[0]
        status = current['status']
        status = "completed" if status == "pending" else "pending"
        completion = current['completed_at']
        completion = today if status == "completed" else None
        db.execute("UPDATE tasks SET status = ?, completed_at = ? WHERE id = ? AND user_id = ?", status, completion, id, user['id'])
        return redirect(f'/view?filter={filter}&sort={sort}&search={search}')

    else:
        filters = ["pending", "all", "overdue", "completed"]
        filter = request.args.get("filter")
        if filter not in filters:
            filter = "all"

        sorts = ["due_date", "priority"]
        sort = request.args.get("sort")
        if sort not in sorts or sort == sorts[0]:
            sort = sorts[0]
            sort1 = "due_date ASC"
            sort2 = "priority DESC"
        else:
            sort1 = "priority DESC"
            sort2 = "due_date ASC"

        search = request.args.get("search")
        if not search:
            search = ""

        if filter == "all":
            user_tasks = db.execute(
                "SELECT * FROM tasks " 
                "WHERE user_id = ? AND "
                "title LIKE ? "
                f'ORDER BY {sort1}, {sort2}', 
                user['id'], "%" + search + "%")
        elif filter == "completed":
            user_tasks = db.execute(
                "SELECT * FROM tasks " 
                "WHERE user_id = ? AND "
                "title LIKE ? "
                "AND status = 'completed' " 
                f'ORDER BY {sort1}, {sort2}', 
                user['id'], "%" + search + "%")
        else:
            user_tasks = db.execute(
                "SELECT * FROM tasks " 
                "WHERE user_id = ? AND "
                "title LIKE ? "
                "AND status = 'pending' " 
                f'ORDER BY {sort1}, {sort2}',  
                user['id'], "%" + search + "%")
            
        tasks = []
        
        if user_tasks: 
            now = datetime.now()
            now = now.strftime("%Y-%m-%d %H:%M")
            for task in user_tasks :
                due = task['due_date'].replace("T", " ")
                overdue = now >= due
                task['overdue'] = overdue
                due = datetime.strptime(due, "%Y-%m-%d %H:%M")
                due = due.strftime("%b %d %Y at %I:%M %p")
                task['due_date'] = due
                if (filter == "overdue" and task['overdue']) or (filter != "overdue"):
                    tasks.append(task)

        return render_template("view.html", user=user, tasks=tasks, filter=filter, sort=sort, search=search)

@app.route("/stats")
@login_required
@timer_on
def stats():
    user = db.execute("SELECT * FROM users WHERE id =?", session["user_id"])[0]
    
    tasks = db.execute("SELECT * FROM tasks WHERE user_id = ? ORDER BY due_date ASC", user['id'])

    # total = db.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ?", user['id'])[0]['COUNT(*)']
    # completed = db.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'completed'", user['id'])[0]['COUNT(*)']

    today = date.today()
    today_str = today.isoformat()

    total_today = db.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND due_date LIKE ?", user['id'], today_str + "%")[0]['COUNT(*)']
    completed_today = db.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND due_date LIKE ? AND status = 'completed'", user['id'], today_str + "%")[0]['COUNT(*)']

    week = today - timedelta(weeks=1)
    end = datetime.combine(today - timedelta(days=1), datetime.max.time()).isoformat(timespec="minutes")
    start = datetime.combine(week, datetime.min.time()).isoformat(timespec="minutes")

    weekly_labels = []

    weekly_tasks_dict = db.execute(
        """SELECT
            strftime('%w', due_date) AS weekday_index,  -- 0 (Sun) to 6 (Sat)
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed
        FROM tasks
        WHERE user_id = ?
        AND due_date BETWEEN ? AND ?
        GROUP BY weekday_index""", user['id'], start, end
    )
    
    weekly_tasks = {row['weekday_index']: row for row in weekly_tasks_dict}
    
    current = week
    weekly_total = []
    weekly_completed = []
    
    for _ in range(7):
        weekly_labels.append(current.strftime("%a"))
        index = weekly_tasks.get(current.strftime("%w"))
        current += timedelta(days=1)
        
        if index:
            weekly_total.append(index['total'])
            weekly_completed.append(index['completed'])
        else:
            weekly_total.append(0)
            weekly_completed.append(0)

    categories = db.execute("SELECT category FROM tasks WHERE user_id = ?", user['id'])
    category_data={}
    for category in categories:
        category = category['category']
        if category in category_data:
            category_data[category] += 1    
        else:
            category_data[category] = 1
            
    streak = currentStreak(today, db)
    longest = longestStreak(db)

    focus_streak = currentFocusStreak(today, db)
    focus_longest = longestFocusStreak(db)

    period = today - timedelta(days=6)
    periods = {"day": 0, "Week": 6, "Month": 29, "Year": 364}
    given_period = "Week" if not request.args.get("period") else request.args.get("period")
    if given_period:
        period = today - timedelta(days=periods[given_period])

    if given_period != "day":
        focus_info = db.execute("""
                            SELECT date, 
                            SUM(planned_time) AS planned, 
                            SUM(actual_time) AS actual
                        FROM focus_sessions
                        WHERE user_id = ? AND
                        date >= ?
                        GROUP BY date
                        ORDER BY date;""",
                        user['id'], str(period)
                    )
        score_info = db.execute("""
                            SELECT date,
                            AVG(score) AS score
                        FROM focus_sessions
                        WHERE user_id = ? AND
                        date >= ?
                        GROUP BY date
                        ORDER BY date;""",
                        user['id'], str(period)
                    )
    else:
        focus_info = db.execute("""
                                SELECT id AS date,
                                planned_time AS planned,
                                actual_time AS actual
                            FROM focus_sessions
                            WHERE user_id = ? AND
                            date >= ?
                            ORDER BY date;""",
                            user['id'], str(period)
                    )
        score_info = db.execute("""
                                SELECT id AS date,
                                score
                            FROM focus_sessions
                            WHERE user_id = ? AND
                            date >= ?
                            ORDER BY date;""",
                            user['id'], str(period)
                    )
        
    
    change1 = db.execute("SELECT AVG(score) AS score FROM focus_sessions WHERE user_id = ? AND date >= ? AND date < ?", user['id'], str(period - timedelta(days=periods[given_period]+1)), str(period))
    change2 = db.execute("SELECT AVG(score) AS score FROM focus_sessions WHERE user_id = ? AND date >= ?", user['id'], str(period))
    change1 = change1[0]['score'] if change1[0]['score'] else 0
    change2 = change2[0]['score'] if change2[0]['score'] else 0
    try:
        change = round((change2 - change1) / change1 * 100, 2)
    except ZeroDivisionError:
        change = -101

    focus_data = {row['date']: row for row in focus_info}
    score_data_bef = {row['date']: row for row in score_info}

    focus_data_dates = []
    focus_data_actual = []
    focus_data_planned = []
    score_data = []

    current = period

    if given_period != "day":
        for _ in range(periods[given_period]+1):
            date_str = str(current)
            focus_data_dates.append(current.strftime("%b %d %Y"))

            if date_str in focus_data:
                focus_data_actual.append(focus_data[date_str]['actual'] // 60)
                focus_data_planned.append(focus_data[date_str]['planned'] / 60)
                score_data.append(score_data_bef[date_str]['score'])
            else:
                focus_data_actual.append(0)
                focus_data_planned.append(0)
                score_data.append(0)
            

            current += timedelta(days=1)
    else:
        for i, id in enumerate(focus_data):
            focus_data_dates.append(f'Session: {i + 1}')
            focus_data_actual.append(focus_data[id]['actual'] // 60)
            focus_data_planned.append(focus_data[id]['planned'] / 60)
            score_data.append(score_data_bef[id]['score'])

    if all(x == 0 for x in score_data):
        score_data = False
        print(change)
        if change == -101:
            change = 0

    tab = "tasks" if not request.args.get("tab") else request.args.get("tab")
            
    return render_template("stats.html", user=user, tasks=tasks, total_today=total_today, completed_today=completed_today, weekly_labels=weekly_labels, weekly_total=weekly_total, weekly_completed=weekly_completed, category_data=category_data, streak=streak, longest=longest, focus_streak=focus_streak, focus_longest=focus_longest, focus_data_dates=focus_data_dates, focus_data_actual=focus_data_actual, focus_data_planned=focus_data_planned, tab=tab, score_data=score_data, change = change)

@app.route("/focus-session", methods=["POST", "GET"])
@login_required
def focus():
    user = db.execute("SELECT * FROM users WHERE id =?", session["user_id"])[0]

    if session.get("timer"):
        if request.method == "POST":

            id = db.execute("SELECT * FROM focus_sessions WHERE user_id = ? ORDER BY id DESC", user['id'])[0]['id']

            start = session.get("timer_start")
            now = datetime.now(timezone.utc)
            duration = session["timer_duration"]

            time = min(int((now-start).total_seconds()), duration)
            score = time / duration * 100

            db.execute("UPDATE focus_sessions SET actual_time = ?, score = ? WHERE user_id = ? AND id = ?", time, score, user['id'], id)

            session.pop("timer", None)
            session.pop("timer_start", None)
            session.pop("timer_duration", None)
            session.pop("last_heartbeat", None)
            return redirect("/focus-session")
        else:
            id = db.execute("SELECT * FROM focus_sessions WHERE user_id = ? ORDER BY id DESC", user['id'])[0]['id']

            beat = session["last_heartbeat"]
            duration = session["timer_duration"]
            start = session.get("timer_start")
            now = datetime.now(timezone.utc)
            end = int(start.timestamp()) + duration

            if (now-beat).total_seconds() > 30:
                time = (now-start).total_seconds()
                score = min((time / duration) * 100, 100)

                db.execute("UPDATE focus_sessions SET actual_time = ?, score = ? WHERE user_id = ? AND id = ?", time, score, user['id'], id)

                session.pop("timer", None)
                session.pop("timer_start", None)
                session.pop("timer_duration", None)
                session.pop("last_heartbeat", None)
                return redirect("/focus-session")
            
            end = int(start.timestamp()) + duration
            start = int(start.timestamp())
            return render_template("timer.html", user=user, end = end, start=start)
    else:
        if request.method == "POST":

            if request.form.get("form_id") != "pomodoro":
              return render_template("pomodoro.html", user=user)
            
            try:
                hours = int(request.form.get("hours"))
            except:
                return render_template("pomodoro.html", user=user, error="Please enter valid hours")
            
            try:
                mins = int(request.form.get("mins"))
            except:
                return render_template("pomodoro.html", user=user, error="Please enter valid minutes")

            if hours < 0:
                return render_template("pomodoro.html", user=user, error="Please enter valid hours")
            elif mins < 0:
                return render_template("pomodoro.html", user=user, error="Please enter valid minutes")
            elif hours == 0 and mins == 0:
                return render_template("pomodoro.html", user=user, error="Please enter valid Time")

            session["timer"] = True
            start = datetime.now(timezone.utc)
            session["timer_start"] = start
            duration = mins * 60 + hours * 3600
            session["timer_duration"] = duration
            session["last_heartbeat"] = datetime.now(timezone.utc)
            end = int(start.timestamp()) + duration
            start = int(start.timestamp())

            db.execute("INSERT INTO focus_sessions (user_id, planned_time, actual_time, date, score) VALUES(?, ?, ?, ?, ?)", user['id'], duration, 0, date.today(), 0)

            return render_template("timer.html", user=user, end=end, start = start)
        else:
            return render_template("pomodoro.html", user=user)    
        
@app.route("/focus-session/heartbeat", methods=["POST", "GET"])
@login_required
def heartbeat():
    if request.method == "POST":
        if session.get("timer"):
            session["last_heartbeat"] = datetime.now(timezone.utc)
            return {"status": "alive"}, 200
        else:
            return {"status": "no timer running"}, 400
    else:
        return redirect("/focus-session")