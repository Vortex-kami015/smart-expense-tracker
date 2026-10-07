import os
import sqlite3
from datetime import date

from flask import Flask, g, jsonify, request

from categorizer import categorizer
from training_data import CATEGORIES

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "expenses.db"))


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or DB_PATH

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
            """CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                category TEXT NOT NULL,
                auto_categorized INTEGER NOT NULL DEFAULT 0
            )"""
        )
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

    def validate(data, partial=False):
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
        if cat and cat not in CATEGORIES:
            errors["category"] = "Unknown category"
        return errors, desc, amount, d, cat

    # ---------- routes ----------
    @app.after_request
    def cors(resp):  # simple CORS so the frontend works with or without the Vite proxy
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
        return resp

    @app.route("/api/<path:_p>", methods=["OPTIONS"])
    def options(_p):
        return "", 204

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/categories")
    def categories():
        return jsonify(CATEGORIES)

    @app.post("/api/categorize")
    def categorize():
        data = request.get_json(silent=True) or {}
        return jsonify(categorizer.predict(data.get("description", "")))

    @app.get("/api/expenses")
    def list_expenses():
        sql, params = "SELECT * FROM expenses WHERE 1=1", []
        if request.args.get("category"):
            sql += " AND category = ?"
            params.append(request.args["category"])
        if request.args.get("q"):
            sql += " AND description LIKE ?"
            params.append(f"%{request.args['q']}%")
        if request.args.get("month"):  # YYYY-MM
            sql += " AND substr(date, 1, 7) = ?"
            params.append(request.args["month"])
        sql += " ORDER BY date DESC, id DESC"
        rows = get_db().execute(sql, params).fetchall()
        return jsonify([row_to_dict(r) for r in rows])

    @app.post("/api/expenses")
    def create_expense():
        errors, desc, amount, d, cat = validate(request.get_json(silent=True) or {})
        if errors:
            return jsonify({"errors": errors}), 400
        auto = 0
        if not cat:
            cat = categorizer.predict(desc)["category"]
            auto = 1
        db = get_db()
        cur = db.execute(
            "INSERT INTO expenses (description, amount, date, category, auto_categorized) VALUES (?,?,?,?,?)",
            (desc, amount, d, cat, auto),
        )
        db.commit()
        if not auto:
            retrain()  # learn from the user's explicit choice
        row = db.execute("SELECT * FROM expenses WHERE id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(row_to_dict(row)), 201

    @app.put("/api/expenses/<int:eid>")
    def update_expense(eid):
        db = get_db()
        if not db.execute("SELECT 1 FROM expenses WHERE id = ?", (eid,)).fetchone():
            return jsonify({"error": "Not found"}), 404
        errors, desc, amount, d, cat = validate(request.get_json(silent=True) or {})
        if errors:
            return jsonify({"errors": errors}), 400
        auto = 0
        if not cat:
            cat = categorizer.predict(desc)["category"]
            auto = 1
        db.execute(
            "UPDATE expenses SET description=?, amount=?, date=?, category=?, auto_categorized=? WHERE id=?",
            (desc, amount, d, cat, auto, eid),
        )
        db.commit()
        if not auto:
            retrain()
        row = db.execute("SELECT * FROM expenses WHERE id = ?", (eid,)).fetchone()
        return jsonify(row_to_dict(row))

    @app.delete("/api/expenses/<int:eid>")
    def delete_expense(eid):
        db = get_db()
        cur = db.execute("DELETE FROM expenses WHERE id = ?", (eid,))
        db.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Not found"}), 404
        return "", 204

    @app.get("/api/summary")
    def summary():
        db = get_db()
        total = db.execute("SELECT COALESCE(SUM(amount),0) AS t, COUNT(*) AS n FROM expenses").fetchone()
        by_cat = db.execute(
            "SELECT category, ROUND(SUM(amount),2) AS total FROM expenses GROUP BY category ORDER BY total DESC"
        ).fetchall()
        by_month = db.execute(
            "SELECT substr(date,1,7) AS month, ROUND(SUM(amount),2) AS total FROM expenses GROUP BY month ORDER BY month"
        ).fetchall()
        return jsonify(
            {
                "total": round(total["t"], 2),
                "count": total["n"],
                "by_category": [dict(r) for r in by_cat],
                "by_month": [dict(r) for r in by_month],
            }
        )

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=True)
