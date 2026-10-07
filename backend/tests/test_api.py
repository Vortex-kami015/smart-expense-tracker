import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    return app.test_client()


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
    r = client.post("/api/categorize", json={"description": desc})
    assert r.get_json()["category"] == expected


def test_categorize_ml_fallback(client):
    # no keyword rule matches "cappuccino and sandwich"; the ML model should still pick Food
    r = client.post("/api/categorize", json={"description": "cappuccino and sandwich"}).get_json()
    assert r["category"] == "Food & Dining"
    assert r["method"] == "ml"


def test_crud_flow(client):
    r = client.post("/api/expenses", json={"description": "Zomato dinner", "amount": 450, "date": "2026-10-01"})
    assert r.status_code == 201
    exp = r.get_json()
    assert exp["category"] == "Food & Dining" and exp["auto_categorized"] is True

    r = client.put(f"/api/expenses/{exp['id']}", json={"description": "Zomato dinner", "amount": 500, "date": "2026-10-01", "category": "Other"})
    assert r.get_json()["category"] == "Other" and r.get_json()["auto_categorized"] is False

    assert len(client.get("/api/expenses").get_json()) == 1
    assert client.delete(f"/api/expenses/{exp['id']}").status_code == 204
    assert client.delete(f"/api/expenses/{exp['id']}").status_code == 404


def test_validation(client):
    r = client.post("/api/expenses", json={"description": "", "amount": -5})
    assert r.status_code == 400
    assert "description" in r.get_json()["errors"] and "amount" in r.get_json()["errors"]


def test_summary_and_filters(client):
    client.post("/api/expenses", json={"description": "Uber ride", "amount": 200, "date": "2026-09-10"})
    client.post("/api/expenses", json={"description": "Uber ride", "amount": 300, "date": "2026-10-10"})
    client.post("/api/expenses", json={"description": "Netflix", "amount": 649, "date": "2026-10-11"})
    s = client.get("/api/summary").get_json()
    assert s["total"] == 1149 and s["count"] == 3
    assert {m["month"] for m in s["by_month"]} == {"2026-09", "2026-10"}
    assert len(client.get("/api/expenses?category=Transport").get_json()) == 2
    assert len(client.get("/api/expenses?month=2026-10").get_json()) == 2
    assert len(client.get("/api/expenses?q=netflix").get_json()) == 1


def test_learns_from_user_choice(client):
    client.post("/api/expenses", json={"description": "zorblax widget", "amount": 10, "category": "Education"})
    r = client.post("/api/categorize", json={"description": "zorblax widget"}).get_json()
    assert r["category"] == "Education"
