import os
import re
import sqlite3
import calendar
from datetime import date, timedelta
from functools import wraps

from flask import Flask, g, jsonify, request
from itsdangerous import BadSignature, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from categorizer import categorizer
from training_data import CATEGORIES

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "expenses.db"))
TOKEN_MAX_AGE = 60 * 60 * 24 * 7  # login stays valid for 7 days
USERNAME_RE = re.compile(r"^[a-z0-9._-]{3,30}$")


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or DB_PATH
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])

    # ---------- database ----------
    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DB_PATH"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db():
        conn = sqlite3.connect(app.config["DB_PATH"])
        conn.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                category TEXT NOT NULL,
                auto_categorized INTEGER NOT NULL DEFAULT 0,
                user_id INTEGER
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS user_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                UNIQUE(user_id, name)
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                period TEXT NOT NULL CHECK(period IN ('week', 'month')),
                category TEXT NOT NULL DEFAULT '',
                target REAL NOT NULL CHECK(target > 0),
                UNIQUE(user_id, period, category)
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS recurring_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                category TEXT NOT NULL DEFAULT '',
                frequency TEXT NOT NULL CHECK(frequency IN ('weekly', 'monthly')),
                next_due TEXT NOT NULL,
                anchor_day INTEGER NOT NULL
            )"""
        )
        # upgrade an older database that has no user_id column yet
        cols = [r[1] for r in conn.execute("PRAGMA table_info(expenses)")]
        if "user_id" not in cols:
            conn.execute("ALTER TABLE expenses ADD COLUMN user_id INTEGER")
        conn.commit()
        conn.close()

    def retrain():
        conn = sqlite3.connect(app.config["DB_PATH"])
        rows = conn.execute(
            "SELECT description, category FROM expenses WHERE auto_categorized = 0"
        ).fetchall()
        conn.close()
        categorizer.train(rows)

    init_db()
    retrain()

    # ---------- helpers ----------
    def row_to_dict(r):
        d = dict(r)
        d["auto_categorized"] = bool(d["auto_categorized"])
        return d

    def user_categories(user_id):
        rows = get_db().execute(
            "SELECT name FROM user_categories WHERE user_id = ? ORDER BY name", (user_id,)
        ).fetchall()
        return CATEGORIES + [row["name"] for row in rows]

    def predict_category(description, user_id):
        prediction = categorizer.predict(description)
        if prediction["category"] not in user_categories(user_id):
            prediction["category"] = "Other"
            prediction["method"] = "ml-low-confidence"
        return prediction

    def validate(data, user_id):
        errors = {}
        desc = (data.get("description") or "").strip()
        if not desc:
            errors["description"] = "Description is required"
        try:
            amount = float(data.get("amount"))
            if amount <= 0:
                errors["amount"] = "Amount must be greater than 0"
        except (TypeError, ValueError):
            amount = None
            errors["amount"] = "Amount must be a number"
        d = data.get("date") or date.today().isoformat()
        try:
            date.fromisoformat(d)
        except ValueError:
            errors["date"] = "Date must be YYYY-MM-DD"
        cat = data.get("category")
        if cat and cat not in user_categories(user_id):
            errors["category"] = "Unknown category"
        return errors, desc, amount, d, cat

    def make_token(user_id):
        return serializer.dumps({"uid": user_id})

    def login_required(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            header = request.headers.get("Authorization", "")
            token = header[7:] if header.startswith("Bearer ") else ""
            try:
                data = serializer.loads(token, max_age=TOKEN_MAX_AGE)
            except BadSignature:  # also covers expired tokens
                return jsonify({"error": "Please log in"}), 401
            g.user_id = data["uid"]
            return f(*args, **kwargs)

        return wrapper

    # ---------- routes ----------
    @app.after_request
    def cors(resp):  # simple CORS so the frontend works with or without the Vite proxy
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        resp.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
        return resp

    @app.route("/api/<path:_p>", methods=["OPTIONS"])
    def options(_p):
        return "", 204

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    def read_credentials():
        data = request.get_json(silent=True) or {}
        return (data.get("username") or "").strip().lower(), data.get("password") or ""

    @app.post("/api/auth/register")
    def register():
        username, password = read_credentials()
        errors = {}
        if not USERNAME_RE.match(username):
            errors["username"] = "Username must be 3-30 characters: letters, numbers, . _ -"
        if len(password) < 6:
            errors["password"] = "Password must be at least 6 characters"
        if errors:
            return jsonify({"errors": errors}), 400
        db = get_db()
        try:
            cur = db.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, generate_password_hash(password)),
            )
            db.commit()
        except sqlite3.IntegrityError:
            return jsonify({"errors": {"username": "That username is already taken"}}), 409
        return jsonify({"token": make_token(cur.lastrowid), "username": username}), 201

    @app.post("/api/auth/login")
    def login():
        username, password = read_credentials()
        user = get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not user or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "Invalid username or password"}), 401
        return jsonify({"token": make_token(user["id"]), "username": user["username"]})

    @app.get("/api/auth/me")
    @login_required
    def me():
        user = get_db().execute("SELECT username FROM users WHERE id = ?", (g.user_id,)).fetchone()
        if not user:
            return jsonify({"error": "Please log in"}), 401
        return jsonify({"username": user["username"]})

    @app.get("/api/categories")
    @login_required
    def categories():
        return jsonify(user_categories(g.user_id))

    @app.post("/api/categories")
    @login_required
    def create_category():
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        if not name or len(name) > 40:
            return jsonify({"error": "Category name must be 1-40 characters"}), 400
        if name in CATEGORIES:
            return jsonify({"error": "That category already exists"}), 409
        try:
            get_db().execute(
                "INSERT INTO user_categories (user_id, name) VALUES (?, ?)", (g.user_id, name)
            )
            get_db().commit()
        except sqlite3.IntegrityError:
            return jsonify({"error": "That category already exists"}), 409
        return jsonify({"name": name}), 201

    @app.delete("/api/categories/<path:name>")
    @login_required
    def delete_category(name):
        db = get_db()
        if name in CATEGORIES:
            return jsonify({"error": "Built-in categories cannot be deleted"}), 400
        if db.execute(
            "SELECT 1 FROM expenses WHERE user_id = ? AND category = ? LIMIT 1",
            (g.user_id, name),
        ).fetchone():
            return jsonify({"error": "This category is used by an expense"}), 409
        if db.execute(
            "SELECT 1 FROM budgets WHERE user_id = ? AND category = ? LIMIT 1",
            (g.user_id, name),
        ).fetchone():
            return jsonify({"error": "Remove this category's budget first"}), 409
        if db.execute(
            "SELECT 1 FROM recurring_expenses WHERE user_id = ? AND category = ? LIMIT 1",
            (g.user_id, name),
        ).fetchone():
            return jsonify({"error": "Remove or update recurring reminders using this category first"}), 409
        cur = db.execute("DELETE FROM user_categories WHERE user_id = ? AND name = ?", (g.user_id, name))
        db.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Not found"}), 404
        return "", 204

    @app.patch("/api/categories/<path:name>")
    @login_required
    def rename_category(name):
        data = request.get_json(silent=True) or {}
        new_name = (data.get("name") or "").strip()
        if name in CATEGORIES:
            return jsonify({"error": "Built-in categories cannot be renamed"}), 400
        if not new_name or len(new_name) > 40:
            return jsonify({"error": "Category name must be 1-40 characters"}), 400
        if new_name in CATEGORIES:
            return jsonify({"error": "That category already exists"}), 409
        db = get_db()
        if not db.execute(
            "SELECT 1 FROM user_categories WHERE user_id = ? AND name = ?", (g.user_id, name)
        ).fetchone():
            return jsonify({"error": "Not found"}), 404
        if db.execute(
            "SELECT 1 FROM user_categories WHERE user_id = ? AND name = ?", (g.user_id, new_name)
        ).fetchone():
            return jsonify({"error": "That category already exists"}), 409
        db.execute(
            "UPDATE user_categories SET name = ? WHERE user_id = ? AND name = ?",
            (new_name, g.user_id, name),
        )
        db.execute(
            "UPDATE expenses SET category = ? WHERE user_id = ? AND category = ?",
            (new_name, g.user_id, name),
        )
        db.execute(
            "UPDATE budgets SET category = ? WHERE user_id = ? AND category = ?",
            (new_name, g.user_id, name),
        )
        db.execute(
            "UPDATE recurring_expenses SET category = ? WHERE user_id = ? AND category = ?",
            (new_name, g.user_id, name),
        )
        db.commit()
        retrain()
        return jsonify({"name": new_name})

    @app.post("/api/categorize")
    @login_required
    def categorize():
        data = request.get_json(silent=True) or {}
        return jsonify(predict_category(data.get("description", ""), g.user_id))

    @app.get("/api/expenses")
    @login_required
    def list_expenses():
        sql, params = "SELECT * FROM expenses WHERE user_id = ?", [g.user_id]
        if request.args.get("category"):
            sql += " AND category = ?"
            params.append(request.args["category"])
        if request.args.get("q"):
            sql += " AND description LIKE ?"
            params.append(f"%{request.args['q']}%")
        if request.args.get("month"):  # YYYY-MM
            month = request.args["month"]
            try:
                if len(month) != 7 or date.fromisoformat(month + "-01").strftime("%Y-%m") != month:
                    raise ValueError
            except ValueError:
                return jsonify({"error": "Month must be YYYY-MM"}), 400
            sql += " AND substr(date, 1, 7) = ?"
            params.append(month)
        for param, operator in (("from", ">="), ("to", "<=")):
            value = request.args.get(param)
            if value:
                try:
                    date.fromisoformat(value)
                except ValueError:
                    return jsonify({"error": f"{param} must be YYYY-MM-DD"}), 400
                sql += f" AND date {operator} ?"
                params.append(value)
        start, end = request.args.get("from"), request.args.get("to")
        if start and end and start > end:
            return jsonify({"error": "Start date must not be after end date"}), 400
        sql += " ORDER BY date DESC, id DESC"
        rows = get_db().execute(sql, params).fetchall()
        return jsonify([row_to_dict(r) for r in rows])

    @app.post("/api/expenses")
    @login_required
    def create_expense():
        errors, desc, amount, d, cat = validate(request.get_json(silent=True) or {}, g.user_id)
        if errors:
            return jsonify({"errors": errors}), 400
        auto = 0
        if not cat:
            cat = predict_category(desc, g.user_id)["category"]
            auto = 1
        db = get_db()
        cur = db.execute(
            "INSERT INTO expenses (description, amount, date, category, auto_categorized, user_id) VALUES (?,?,?,?,?,?)",
            (desc, amount, d, cat, auto, g.user_id),
        )
        db.commit()
        if not auto:
            retrain()  # learn from the user's explicit choice
        row = db.execute("SELECT * FROM expenses WHERE id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(row_to_dict(row)), 201

    @app.put("/api/expenses/<int:eid>")
    @login_required
    def update_expense(eid):
        db = get_db()
        if not db.execute("SELECT 1 FROM expenses WHERE id = ? AND user_id = ?", (eid, g.user_id)).fetchone():
            return jsonify({"error": "Not found"}), 404
        errors, desc, amount, d, cat = validate(request.get_json(silent=True) or {}, g.user_id)
        if errors:
            return jsonify({"errors": errors}), 400
        auto = 0
        if not cat:
            cat = predict_category(desc, g.user_id)["category"]
            auto = 1
        db.execute(
            "UPDATE expenses SET description=?, amount=?, date=?, category=?, auto_categorized=? WHERE id=? AND user_id=?",
            (desc, amount, d, cat, auto, eid, g.user_id),
        )
        db.commit()
        if not auto:
            retrain()
        row = db.execute("SELECT * FROM expenses WHERE id = ?", (eid,)).fetchone()
        return jsonify(row_to_dict(row))

    @app.delete("/api/expenses/<int:eid>")
    @login_required
    def delete_expense(eid):
        db = get_db()
        cur = db.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (eid, g.user_id))
        db.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Not found"}), 404
        return "", 204

    @app.get("/api/summary")
    @login_required
    def summary():
        db = get_db()
        uid = g.user_id
        total = db.execute(
            "SELECT COALESCE(SUM(amount),0) AS t, COUNT(*) AS n FROM expenses WHERE user_id = ?", (uid,)
        ).fetchone()
        by_cat = db.execute(
            "SELECT category, ROUND(SUM(amount),2) AS total FROM expenses WHERE user_id = ? GROUP BY category ORDER BY total DESC",
            (uid,),
        ).fetchall()
        by_month = db.execute(
            "SELECT substr(date,1,7) AS month, ROUND(SUM(amount),2) AS total FROM expenses WHERE user_id = ? GROUP BY month ORDER BY month",
            (uid,),
        ).fetchall()
        return jsonify(
            {
                "total": round(total["t"], 2),
                "count": total["n"],
                "by_category": [dict(r) for r in by_cat],
                "by_month": [dict(r) for r in by_month],
            }
        )

    @app.get("/api/budgets")
    @login_required
    def list_budgets():
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        periods = {
            "week": (week_start.isoformat(), (week_start + timedelta(days=6)).isoformat()),
            "month": (today.replace(day=1).isoformat(), today.replace(day=calendar.monthrange(today.year, today.month)[1]).isoformat()),
        }
        db = get_db()
        budgets = db.execute(
            "SELECT * FROM budgets WHERE user_id = ? ORDER BY period, category", (g.user_id,)
        ).fetchall()
        results = []
        for budget in budgets:
            start, end = periods[budget["period"]]
            sql = "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE user_id = ? AND date BETWEEN ? AND ?"
            params = [g.user_id, start, end]
            if budget["category"]:
                sql += " AND category = ?"
                params.append(budget["category"])
            spent = db.execute(sql, params).fetchone()[0]
            item = dict(budget)
            item["spent"] = round(spent, 2)
            item["percent"] = round(spent / budget["target"] * 100, 1)
            results.append(item)
        return jsonify(results)

    @app.post("/api/budgets")
    @login_required
    def save_budget():
        data = request.get_json(silent=True) or {}
        period = data.get("period")
        category = (data.get("category") or "").strip()
        try:
            target = float(data.get("target"))
        except (TypeError, ValueError):
            target = 0
        if period not in ("week", "month"):
            return jsonify({"error": "Period must be week or month"}), 400
        if target <= 0:
            return jsonify({"error": "Target must be greater than 0"}), 400
        if category and category not in user_categories(g.user_id):
            return jsonify({"error": "Unknown category"}), 400
        db = get_db()
        db.execute(
            """INSERT INTO budgets (user_id, period, category, target) VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id, period, category) DO UPDATE SET target = excluded.target""",
            (g.user_id, period, category, target),
        )
        db.commit()
        row = db.execute(
            "SELECT id FROM budgets WHERE user_id = ? AND period = ? AND category = ?",
            (g.user_id, period, category),
        ).fetchone()
        return jsonify({"id": row["id"], "period": period, "category": category, "target": target}), 200

    @app.delete("/api/budgets/<int:budget_id>")
    @login_required
    def delete_budget(budget_id):
        cur = get_db().execute(
            "DELETE FROM budgets WHERE id = ? AND user_id = ?", (budget_id, g.user_id)
        )
        get_db().commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Not found"}), 404
        return "", 204

    @app.get("/api/recurring")
    @login_required
    def list_recurring():
        rows = get_db().execute(
            "SELECT * FROM recurring_expenses WHERE user_id = ? ORDER BY next_due, id", (g.user_id,)
        ).fetchall()
        today = date.today().isoformat()
        return jsonify([{**dict(row), "due": row["next_due"] <= today} for row in rows])

    @app.post("/api/recurring")
    @login_required
    def create_recurring():
        data = request.get_json(silent=True) or {}
        desc = (data.get("description") or "").strip()
        category = (data.get("category") or "").strip()
        frequency = data.get("frequency")
        try:
            amount = float(data.get("amount"))
            due = date.fromisoformat(data.get("next_due", ""))
        except (TypeError, ValueError):
            return jsonify({"error": "Enter a valid amount and due date"}), 400
        if not desc:
            return jsonify({"error": "Description is required"}), 400
        if amount <= 0:
            return jsonify({"error": "Amount must be greater than 0"}), 400
        if frequency not in ("weekly", "monthly"):
            return jsonify({"error": "Frequency must be weekly or monthly"}), 400
        if category and category not in user_categories(g.user_id):
            return jsonify({"error": "Unknown category"}), 400
        cur = get_db().execute(
            """INSERT INTO recurring_expenses
               (user_id, description, amount, category, frequency, next_due, anchor_day)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (g.user_id, desc, amount, category, frequency, due.isoformat(), due.day),
        )
        get_db().commit()
        row = get_db().execute("SELECT * FROM recurring_expenses WHERE id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(dict(row)), 201

    @app.post("/api/recurring/<int:recurring_id>/complete")
    @login_required
    def complete_recurring(recurring_id):
        db = get_db()
        item = db.execute(
            "SELECT * FROM recurring_expenses WHERE id = ? AND user_id = ?",
            (recurring_id, g.user_id),
        ).fetchone()
        if not item:
            return jsonify({"error": "Not found"}), 404
        due = date.fromisoformat(item["next_due"])
        if due > date.today():
            return jsonify({"error": "This reminder is not due yet"}), 409
        category = item["category"]
        auto = 0
        if not category:
            prediction = predict_category(item["description"], g.user_id)
            category = prediction["category"]
            auto = 1
        cur = db.execute(
            """INSERT INTO expenses
               (description, amount, date, category, auto_categorized, user_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (item["description"], item["amount"], due.isoformat(), category, auto, g.user_id),
        )
        if item["frequency"] == "weekly":
            next_due = due + timedelta(days=7)
        else:
            month_index = due.month
            year = due.year + (month_index // 12)
            month = month_index % 12 + 1
            day = min(item["anchor_day"], calendar.monthrange(year, month)[1])
            next_due = date(year, month, day)
        db.execute(
            "UPDATE recurring_expenses SET next_due = ? WHERE id = ? AND user_id = ?",
            (next_due.isoformat(), recurring_id, g.user_id),
        )
        db.commit()
        expense = db.execute("SELECT * FROM expenses WHERE id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(row_to_dict(expense)), 201

    @app.delete("/api/recurring/<int:recurring_id>")
    @login_required
    def delete_recurring(recurring_id):
        cur = get_db().execute(
            "DELETE FROM recurring_expenses WHERE id = ? AND user_id = ?",
            (recurring_id, g.user_id),
        )
        get_db().commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Not found"}), 404
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=True)
