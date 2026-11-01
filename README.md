https://smart-expense-tracker-tau-seven.vercel.app
# Smart Expense Tracker with Auto-Categorization

Flask + SQLite backend with a hybrid auto-categorizer (keyword rules, then a TF-IDF + Logistic Regression model),
and a React + TypeScript (Vite) frontend.

## Run it

Backend (terminal 1):
```
cd backend
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python app.py                  # http://127.0.0.1:5000
```

Frontend (terminal 2):
```
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

Tests: `cd backend && python -m pytest`

## How auto-categorization works
1. Keyword rules (e.g. "uber" -> Transport) are checked first.
2. Otherwise the ML model predicts a category; below 30% confidence it falls back to "Other".
3. When you pick a category yourself, that example is saved and the model retrains, so it learns your habits.

## Features
- Search and filter expenses by category, month, or custom date range; export the filtered results as CSV.
- Browse long expense lists with pagination and review category shares and month-over-month trends.
- Create, rename, and remove custom categories. A category that is still used by an expense, budget, or reminder cannot be deleted.
- Set weekly (Monday-Sunday) or monthly spending targets for all expenses or a selected category. The dashboard alerts at 80% and when a target is exceeded.
- Set up weekly or monthly recurring reminders. Due reminders are not added automatically; confirm one to create the expense and advance its next due date.
- The interface adapts to narrow screens, and save/delete actions display feedback.

## API
All user-specific routes require a bearer token obtained from `/api/auth/register` or `/api/auth/login`.

- `GET/POST /api/expenses`, `PUT/DELETE /api/expenses/<id>` — create, list, update, and delete expenses. List filters include `category`, `q`, `month`, `from`, and `to`.
- `GET/POST /api/categories`, `PATCH/DELETE /api/categories/<name>` — list/manage per-user custom categories.
- `GET/POST /api/budgets`, `DELETE /api/budgets/<id>` — list and manage weekly/monthly spending targets.
- `GET/POST /api/recurring`, `POST /api/recurring/<id>/complete`, `DELETE /api/recurring/<id>` — manage recurring reminders and confirm a due occurrence.
- `GET /api/summary`, `POST /api/categorize`, `GET /api/auth/me`.
