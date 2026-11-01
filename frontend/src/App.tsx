import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, clearToken, getToken } from "./api";
import Dashboard, { inr } from "./Dashboard";
import AuthPage from "./AuthPage";
import ExpenseForm from "./ExpenseForm";
import ManagementPanels from "./ManagementPanels";
import type { Expense, Summary } from "./types";

const PAGE_SIZE = 10;

function Tracker({ username, onLogout }: { username: string; onLogout: () => void }) {
  const [categories, setCategories] = useState<string[]>([]);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [editing, setEditing] = useState<Expense | null>(null);
  const [filterCat, setFilterCat] = useState("");
  const [search, setSearch] = useState("");
  const [month, setMonth] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const noticeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async () => {
    try {
      const [list, sum] = await Promise.all([
        api.expenses({ category: filterCat, q: search, month, from: fromDate, to: toDate }),
        api.summary(),
      ]);
      setExpenses(list);
      setSummary(sum);
      setError("");
    } catch {
      setError("Cannot reach the backend. Is it running on port 5000?");
    }
  }, [filterCat, search, month, fromDate, toDate]);

  const notify = useCallback((message: string) => {
    if (noticeTimer.current) clearTimeout(noticeTimer.current);
    setNotice(message);
    noticeTimer.current = window.setTimeout(() => setNotice(""), 3500);
  }, []);

  useEffect(() => () => {
    if (noticeTimer.current) clearTimeout(noticeTimer.current);
  }, []);

  useEffect(() => {
    api.categories().then(setCategories).catch(() => setError("Cannot reach the backend. Is it running on port 5000?"));
  }, []);

  useEffect(() => {
    setPage(1);
    load();
  }, [load]);

  async function remove(id: number) {
    if (!confirm("Delete this expense?")) return;
    try {
      await api.remove(id);
      if (editing?.id === id) setEditing(null);
      await load();
      notify("Expense deleted.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete expense.");
    }
  }

  const pageCount = Math.max(1, Math.ceil(expenses.length / PAGE_SIZE));
  const visibleExpenses = useMemo(
    () => expenses.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    [expenses, page],
  );

  function exportCsv() {
    const quote = (value: string | number) => `"${String(value).replace(/"/g, '""')}"`;
    const rows = [
      ["Date", "Description", "Category", "Amount"],
      ...expenses.map((expense) => [expense.date, expense.description, expense.category, expense.amount]),
    ];
    const content = "\uFEFF" + rows.map((row) => row.map(quote).join(",")).join("\r\n");
    const url = URL.createObjectURL(new Blob([content], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "expenses.csv";
    link.click();
    URL.revokeObjectURL(url);
    notify(`Exported ${expenses.length} expense${expenses.length === 1 ? "" : "s"}.`);
  }

  return (
    <div className="container tracker-page">
      <header className="topbar">
        <div>
          <h1> Smart Expense Tracker</h1>
          <p className="muted">Expenses are categorized automatically as you type.</p>
        </div>
        <div className="userbox">
          <img className="avatar" src="/panda.png" alt="Panda avatar" />
          <span className="muted">
            Signed in as <strong>{username}</strong>
          </span>
          <button className="secondary" onClick={onLogout}>
            Log out
          </button>
        </div>
      </header>

      {error && <p className="error banner">{error}</p>}
      {notice && <p className="notice banner" role="status" aria-live="polite">{notice}</p>}

      <Dashboard summary={summary} />

      <div className="grid">
        <div>
          <ExpenseForm
            categories={categories}
            editing={editing}
            onCancel={() => setEditing(null)}
            onSaved={() => {
              setEditing(null);
              load();
              notify(editing ? "Expense updated." : "Expense added.");
            }}
          />
          <ManagementPanels
            categories={categories}
            onCategoriesChanged={(next) => {
              setCategories(next);
              if (filterCat && !next.includes(filterCat)) setFilterCat("");
            }}
            onNotice={notify}
            onExpenseCreated={load}
          />
        </div>

        <div className="card">
          <div className="section-heading">
            <h2>Expenses</h2>
            <button className="secondary export-button" onClick={exportCsv} disabled={expenses.length === 0}>
              Export CSV
            </button>
          </div>
          <div className="row filters filter-row">
            <input placeholder="Search…" value={search} onChange={(e) => setSearch(e.target.value)} />
            <select value={filterCat} onChange={(e) => setFilterCat(e.target.value)}>
              <option value="">All categories</option>
              {categories.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </div>
          <div className="row filters date-filters">
            <label>
              Month
              <input type="month" value={month} onChange={(e) => {
                setMonth(e.target.value);
                if (e.target.value) { setFromDate(""); setToDate(""); }
              }} />
            </label>
            <label>
              From
              <input type="date" value={fromDate} onChange={(e) => {
                setFromDate(e.target.value);
                if (e.target.value) setMonth("");
              }} />
            </label>
            <label>
              To
              <input type="date" value={toDate} onChange={(e) => {
                setToDate(e.target.value);
                if (e.target.value) setMonth("");
              }} />
            </label>
            {(month || fromDate || toDate) && (
              <button className="link clear-filters" onClick={() => { setMonth(""); setFromDate(""); setToDate(""); }}>
                Clear dates
              </button>
            )}
          </div>

          {expenses.length === 0 ? (
            <p className="muted">No expenses found.</p>
          ) : (
            <>
            <div className="table-wrap">
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
                {visibleExpenses.map((e) => (
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
            </div>
            <div className="pagination">
              <span className="muted">Showing {((page - 1) * PAGE_SIZE) + 1}–{Math.min(page * PAGE_SIZE, expenses.length)} of {expenses.length}</span>
              <div>
                <button className="secondary" onClick={() => setPage((current) => Math.max(1, current - 1))} disabled={page === 1}>Previous</button>
                <span className="page-number">Page {page} of {pageCount}</span>
                <button className="secondary" onClick={() => setPage((current) => Math.min(pageCount, current + 1))} disabled={page === pageCount}>Next</button>
              </div>
            </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState<string | null>(null);
  const [checking, setChecking] = useState(true);

  // On first load, if a saved login exists, ask the backend who it belongs to.
  useEffect(() => {
    if (!getToken()) {
      setChecking(false);
      return;
    }
    api
      .me()
      .then((r) => setUser(r.username))
      .catch(() => {})
      .finally(() => setChecking(false));
  }, []);

  // api.ts fires this event when the server rejects the saved login (expired token).
  useEffect(() => {
    const onExpired = () => setUser(null);
    window.addEventListener("auth-expired", onExpired);
    return () => window.removeEventListener("auth-expired", onExpired);
  }, []);

  function logout() {
    clearToken();
    setUser(null);
  }

  if (checking) return <div className="container muted">Loading…</div>;
  if (!user) return <AuthPage onAuth={setUser} />;
  return <Tracker username={user} onLogout={logout} />;
}
