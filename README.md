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

## API
GET/POST /api/expenses, PUT/DELETE /api/expenses/<id>, GET /api/categories, GET /api/summary, POST /api/categorize
