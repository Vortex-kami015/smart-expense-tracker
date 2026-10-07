import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import Dashboard, { inr } from "./Dashboard";
import ExpenseForm from "./ExpenseForm";
import type { Expense, Summary } from "./types";

export default function App() {
  const [categories, setCategories] = useState<string[]>([]);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [editing, setEditing] = useState<Expense | null>(null);
  const [filterCat, setFilterCat] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [list, sum] = await Promise.all([
        api.expenses({ category: filterCat, q: search }),
        api.summary(),
      ]);
      setExpenses(list);
      setSummary(sum);
      setError("");
    } catch {
      setError("Cannot reach the backend. Is it running on port 5000?");
    }
  }, [filterCat, search]);

  useEffect(() => {
    api.categories().then(setCategories).catch(() => setError("Cannot reach the backend. Is it running on port 5000?"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function remove(id: number) {
    if (!confirm("Delete this expense?")) return;
    await api.remove(id);
    if (editing?.id === id) setEditing(null);
    load();
  }

  return (
    <div className="container">
      <header>
        <h1>💸 Smart Expense Tracker</h1>
        <p className="muted">Expenses are categorized automatically as you type.</p>
      </header>

      {error && <p className="error banner">{error}</p>}

      <div className="grid">
        <div>
          <ExpenseForm
            categories={categories}
            editing={editing}
            onCancel={() => setEditing(null)}
            onSaved={() => {
              setEditing(null);
              load();
            }}
          />
          <Dashboard summary={summary} />
        </div>

        <div className="card">
          <h2>Expenses</h2>
          <div className="row filters">
            <input placeholder="Search…" value={search} onChange={(e) => setSearch(e.target.value)} />
            <select value={filterCat} onChange={(e) => setFilterCat(e.target.value)}>
              <option value="">All categories</option>
              {categories.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </div>

          {expenses.length === 0 ? (
            <p className="muted">No expenses found.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Description</th>
                  <th>Category</th>
                  <th className="right">Amount</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {expenses.map((e) => (
                  <tr key={e.id}>
                    <td>{e.date}</td>
                    <td>{e.description}</td>
                    <td>
                      <span className="tag">{e.category}</span>
                      {e.auto_categorized && <span className="auto" title="Categorized automatically"> ⚡</span>}
                    </td>
                    <td className="right">{inr(e.amount)}</td>
                    <td className="actions">
                      <button className="link" onClick={() => setEditing(e)}>Edit</button>
                      <button className="link danger" onClick={() => remove(e.id)}>Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
