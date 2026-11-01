import pytest
from datetime import date

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    return app.test_client()


def register(client, username="nisha", password="secret123"):
    r = client.post("/api/auth/register", json={"username": username, "password": password})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.get_json()['token']}"}


# ---------- auth ----------
def test_requires_login(client):
    assert client.get("/api/expenses").status_code == 401
    assert client.get("/api/summary").status_code == 401
    assert client.post("/api/expenses", json={"description": "x", "amount": 1}).status_code == 401


def test_register_login_me(client):
    register(client)
    r = client.post("/api/auth/login", json={"username": "NISHA", "password": "secret123"})
    assert r.status_code == 200 and r.get_json()["username"] == "nisha"
    h = {"Authorization": f"Bearer {r.get_json()['token']}"}
    assert client.get("/api/auth/me", headers=h).get_json() == {"username": "nisha"}


def test_wrong_password_and_duplicate(client):
    register(client)
    assert client.post("/api/auth/login", json={"username": "nisha", "password": "nope"}).status_code == 401
    r = client.post("/api/auth/register", json={"username": "nisha", "password": "another1"})
    assert r.status_code == 409


def test_register_validation(client):
    r = client.post("/api/auth/register", json={"username": "a", "password": "123"})
    assert r.status_code == 400
    assert "username" in r.get_json()["errors"] and "password" in r.get_json()["errors"]


def test_bad_token_rejected(client):
    r = client.get("/api/expenses", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


def test_users_only_see_own_expenses(client):
    a = register(client, "alice")
    b = register(client, "bobby")
    exp = client.post("/api/expenses", json={"description": "Uber ride", "amount": 100}, headers=a).get_json()
    assert len(client.get("/api/expenses", headers=a).get_json()) == 1
    assert client.get("/api/expenses", headers=b).get_json() == []
    assert client.get("/api/summary", headers=b).get_json()["total"] == 0
    # bob cannot edit or delete alice's expense
    body = {"description": "hack", "amount": 1}
    assert client.put(f"/api/expenses/{exp['id']}", json=body, headers=b).status_code == 404
    assert client.delete(f"/api/expenses/{exp['id']}", headers=b).status_code == 404
    assert client.delete(f"/api/expenses/{exp['id']}", headers=a).status_code == 204


# ---------- categorizer ----------
@pytest.mark.parametrize(
    "desc,expected",
    [
        ("Swiggy order biryani", "Food & Dining"),
        ("Uber ride to office", "Transport"),
        ("Netflix subscription", "Entertainment"),
        ("electricity bill september", "Bills & Utilities"),
        ("Apollo pharmacy", "Health"),
        ("monthly house rent", "Housing"),
        ("bigbasket groceries", "Groceries"),
    ],
)
def test_categorize_rules(client, desc, expected):
    h = register(client)
    r = client.post("/api/categorize", json={"description": desc}, headers=h)
    assert r.get_json()["category"] == expected


def test_categorize_ml_fallback(client):
    h = register(client)
    r = client.post("/api/categorize", json={"description": "cappuccino and sandwich"}, headers=h).get_json()
    assert r["category"] == "Food & Dining"
    assert r["method"] == "ml"


# ---------- expenses ----------
def test_crud_flow(client):
    h = register(client)
    r = client.post("/api/expenses", json={"description": "Zomato dinner", "amount": 450, "date": "2026-10-01"}, headers=h)
    assert r.status_code == 201
    exp = r.get_json()
    assert exp["category"] == "Food & Dining" and exp["auto_categorized"] is True

    r = client.put(
        f"/api/expenses/{exp['id']}",
        json={"description": "Zomato dinner", "amount": 500, "date": "2026-10-01", "category": "Other"},
        headers=h,
    )
    assert r.get_json()["category"] == "Other" and r.get_json()["auto_categorized"] is False

    assert len(client.get("/api/expenses", headers=h).get_json()) == 1
    assert client.delete(f"/api/expenses/{exp['id']}", headers=h).status_code == 204
    assert client.delete(f"/api/expenses/{exp['id']}", headers=h).status_code == 404


def test_validation(client):
    h = register(client)
    r = client.post("/api/expenses", json={"description": "", "amount": -5}, headers=h)
    assert r.status_code == 400
    assert "description" in r.get_json()["errors"] and "amount" in r.get_json()["errors"]


def test_summary_and_filters(client):
    h = register(client)
    client.post("/api/expenses", json={"description": "Uber ride", "amount": 200, "date": "2026-09-10"}, headers=h)
    client.post("/api/expenses", json={"description": "Uber ride", "amount": 300, "date": "2026-10-10"}, headers=h)
    client.post("/api/expenses", json={"description": "Netflix", "amount": 649, "date": "2026-10-11"}, headers=h)
    s = client.get("/api/summary", headers=h).get_json()
    assert s["total"] == 1149 and s["count"] == 3
    assert {m["month"] for m in s["by_month"]} == {"2026-09", "2026-10"}
    assert len(client.get("/api/expenses?category=Transport", headers=h).get_json()) == 2
    assert len(client.get("/api/expenses?month=2026-10", headers=h).get_json()) == 2
    assert len(client.get("/api/expenses?q=netflix", headers=h).get_json()) == 1


def test_learns_from_user_choice(client):
    h = register(client)
    client.post("/api/expenses", json={"description": "zorblax widget", "amount": 10, "category": "Education"}, headers=h)
    r = client.post("/api/categorize", json={"description": "zorblax widget"}, headers=h).get_json()
    assert r["category"] == "Education"


def test_old_database_is_upgraded(tmp_path):
    import sqlite3

    path = str(tmp_path / "old.db")
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, description TEXT NOT NULL, amount REAL NOT NULL, date TEXT NOT NULL, category TEXT NOT NULL, auto_categorized INTEGER NOT NULL DEFAULT 0)"
    )
    conn.execute("INSERT INTO expenses (description, amount, date, category) VALUES ('old', 5, '2026-01-01', 'Other')")
    conn.commit()
    conn.close()
    client = create_app(path).test_client()
    h = register(client)
    assert client.get("/api/expenses", headers=h).get_json() == []  # old rows belong to nobody


def test_date_range_filters(client):
    h = register(client)
    client.post("/api/expenses", json={"description": "first", "amount": 10, "date": "2026-10-01"}, headers=h)
    client.post("/api/expenses", json={"description": "middle", "amount": 20, "date": "2026-10-15"}, headers=h)
    client.post("/api/expenses", json={"description": "last", "amount": 30, "date": "2026-10-31"}, headers=h)
    rows = client.get("/api/expenses?from=2026-10-10&to=2026-10-20", headers=h).get_json()
    assert [row["description"] for row in rows] == ["middle"]
    assert client.get("/api/expenses?from=invalid", headers=h).status_code == 400
    assert client.get("/api/expenses?from=2026-10-20&to=2026-10-10", headers=h).status_code == 400


def test_custom_categories_are_user_owned_and_rename_expense_category(client):
    alice = register(client, "alice")
    bob = register(client, "bobby")
    assert client.post("/api/categories", json={"name": "Pets"}, headers=alice).status_code == 201
    assert "Pets" in client.get("/api/categories", headers=alice).get_json()
    assert "Pets" not in client.get("/api/categories", headers=bob).get_json()
    expense = client.post(
        "/api/expenses",
        json={"description": "pet food", "amount": 25, "category": "Pets"},
        headers=alice,
    ).get_json()
    client.post(
        "/api/budgets",
        json={"period": "month", "category": "Pets", "target": 100},
        headers=alice,
    )
    client.post(
        "/api/recurring",
        json={
            "description": "Pet food delivery",
            "amount": 25,
            "category": "Pets",
            "frequency": "monthly",
            "next_due": "2026-11-01",
        },
        headers=alice,
    )
    assert client.patch("/api/categories/Pets", json={"name": "Pet care"}, headers=alice).status_code == 200
    assert client.get("/api/expenses", headers=alice).get_json()[0]["category"] == "Pet care"
    assert client.delete("/api/categories/Pet%20care", headers=alice).status_code == 409
    assert client.get(f"/api/expenses?category=Pet%20care", headers=alice).get_json()[0]["id"] == expense["id"]
    assert client.get("/api/budgets", headers=alice).get_json()[0]["category"] == "Pet care"
    assert client.get("/api/recurring", headers=alice).get_json()[0]["category"] == "Pet care"
    assert client.delete("/api/categories/Pets", headers=bob).status_code == 404
    assert client.post("/api/categorize", json={"description": "pet food"}, headers=bob).get_json()["category"] in client.get("/api/categories", headers=bob).get_json()


def test_budgets_are_upserted_and_user_scoped(client):
    alice = register(client, "alice")
    bob = register(client, "bobby")
    today = date.today().isoformat()
    client.post("/api/expenses", json={"description": "coffee", "amount": 25, "date": today, "category": "Other"}, headers=alice)
    result = client.post(
        "/api/budgets",
        json={"period": "month", "category": "Other", "target": 100},
        headers=alice,
    )
    assert result.status_code == 200
    client.post(
        "/api/budgets",
        json={"period": "month", "category": "Other", "target": 50},
        headers=alice,
    )
    budgets = client.get("/api/budgets", headers=alice).get_json()
    assert len(budgets) == 1
    assert budgets[0]["target"] == 50 and budgets[0]["spent"] == 25 and budgets[0]["percent"] == 50
    assert client.get("/api/budgets", headers=bob).get_json() == []
    assert client.post("/api/budgets", json={"period": "year", "target": 100}, headers=alice).status_code == 400
    assert client.delete(f"/api/budgets/{result.get_json()['id']}", headers=alice).status_code == 204


def test_recurring_reminder_creates_expense_only_when_confirmed(client):
    from datetime import date, timedelta

    h = register(client)
    due = (date.today() - timedelta(days=14)).isoformat()
    created = client.post(
        "/api/recurring",
        json={
            "description": "Monthly subscription",
            "amount": 99,
            "category": "Entertainment",
            "frequency": "weekly",
            "next_due": due,
        },
        headers=h,
    )
    assert created.status_code == 201
    reminder = created.get_json()
    assert client.get("/api/expenses", headers=h).get_json() == []
    result = client.post(f"/api/recurring/{reminder['id']}/complete", headers=h)
    assert result.status_code == 201
    assert result.get_json()["date"] == due
    assert result.get_json()["category"] == "Entertainment"
    assert client.get("/api/recurring", headers=h).get_json()[0]["next_due"] == (
        date.fromisoformat(due) + timedelta(days=7)
    ).isoformat()
