import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { inr } from "./Dashboard";
import type { Budget, RecurringExpense } from "./types";

interface Props {
  categories: string[];
  onCategoriesChanged: (categories: string[]) => void;
  onNotice: (message: string) => void;
  onExpenseCreated: () => Promise<void>;
}

const today = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
};

export default function ManagementPanels({ categories, onCategoriesChanged, onNotice, onExpenseCreated }: Props) {
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [recurring, setRecurring] = useState<RecurringExpense[]>([]);
  const [target, setTarget] = useState("");
  const [period, setPeriod] = useState<"week" | "month">("month");
  const [budgetCategory, setBudgetCategory] = useState("");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [recurringCategory, setRecurringCategory] = useState("");
  const [frequency, setFrequency] = useState<"weekly" | "monthly">("monthly");
  const [nextDue, setNextDue] = useState(today());
  const [newCategory, setNewCategory] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const refreshBudgets = useCallback(async () => setBudgets(await api.budgets()), []);
  const refreshRecurring = useCallback(async () => setRecurring(await api.recurring()), []);

  useEffect(() => {
    Promise.all([refreshBudgets(), refreshRecurring()]).catch((err: unknown) => {
      setError(err instanceof Error ? err.message : "Could not load budgets and reminders.");
    });
  }, [refreshBudgets, refreshRecurring]);

  async function submitBudget(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.saveBudget({ period, category: budgetCategory, target: Number(target) });
      setTarget("");
      await refreshBudgets();
      onNotice("Spending target saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save spending target.");
    } finally {
      setBusy(false);
    }
  }

  async function removeBudget(id: number) {
    try {
      await api.removeBudget(id);
      await refreshBudgets();
      onNotice("Spending target removed.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove spending target.");
    }
  }

  async function submitRecurring(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.createRecurring({
        description,
        amount: Number(amount),
        category: recurringCategory,
        frequency,
        next_due: nextDue,
      });
      setDescription("");
      setAmount("");
      setRecurringCategory("");
      setNextDue(today());
      await refreshRecurring();
      onNotice("Recurring reminder added.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add recurring reminder.");
    } finally {
      setBusy(false);
    }
  }

  async function completeReminder(item: RecurringExpense) {
    try {
      await api.completeRecurring(item.id);
      await Promise.all([refreshRecurring(), onExpenseCreated()]);
      onNotice(`Added ${item.description} as an expense.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add the recurring expense.");
    }
  }

  async function removeRecurring(id: number) {
    try {
      await api.removeRecurring(id);
      await refreshRecurring();
      onNotice("Recurring reminder removed.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove recurring reminder.");
    }
  }

  async function addCategory(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api.createCategory(newCategory);
      onCategoriesChanged(await api.categories());
      setNewCategory("");
      onNotice("Category added.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add category.");
    }
  }

  async function renameCategory(name: string) {
    const value = prompt("New category name:", name);
    if (value === null || value.trim() === name) return;
    setError("");
    try {
      await api.renameCategory(name, value.trim());
      onCategoriesChanged(await api.categories());
      await Promise.all([refreshBudgets(), refreshRecurring()]);
      onNotice("Category renamed.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not rename category.");
    }
  }

  async function removeCategory(name: string) {
    if (!confirm(`Delete the custom category "${name}"?`)) return;
    setError("");
    try {
      await api.removeCategory(name);
      onCategoriesChanged(await api.categories());
      onNotice("Category deleted.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete category.");
    }
  }

  const customCategories = categories.filter((category) => ![
    "Food & Dining", "Groceries", "Transport", "Shopping", "Bills & Utilities", "Entertainment",
    "Health", "Education", "Housing", "Travel", "Other",
  ].includes(category));

  return (
    <section className="card management">
      <h2>Spending targets</h2>
      <p className="muted">Set weekly or monthly limits. Alerts appear when you reach 80% or exceed a target.</p>
      <form className="management-form" onSubmit={submitBudget}>
        <label>
          Period
          <select value={period} onChange={(event) => setPeriod(event.target.value as "week" | "month")}>
            <option value="month">Monthly</option>
            <option value="week">Weekly</option>
          </select>
        </label>
        <label>
          Category
          <select value={budgetCategory} onChange={(event) => setBudgetCategory(event.target.value)}>
            <option value="">All categories</option>
            {categories.map((category) => <option key={category}>{category}</option>)}
          </select>
        </label>
        <label>
          Limit (₹)
          <input type="number" min="0.01" step="0.01" value={target} onChange={(event) => setTarget(event.target.value)} required />
        </label>
        <button disabled={busy}>Save target</button>
      </form>
      {budgets.length === 0 ? <p className="muted">No spending targets yet.</p> : (
        <div className="target-list">
          {budgets.map((budget) => (
            <div className={`target-item${budget.percent >= 100 ? " over-target" : budget.percent >= 80 ? " near-target" : ""}`} key={budget.id}>
              <div className="target-title">
                <strong>{budget.category || "All categories"}</strong>
                <span>{budget.period === "week" ? "This week" : "This month"}</span>
              </div>
              <div className="progress-track" role="progressbar" aria-valuenow={Math.min(budget.percent, 100)} aria-valuemin={0} aria-valuemax={100}>
                <div className="progress-fill" style={{ width: `${Math.min(budget.percent, 100)}%` }} />
              </div>
              <div className="target-summary">
                <span>{inr(budget.spent)} / {inr(budget.target)} ({Math.round(budget.percent)}%)</span>
                <button className="link danger" onClick={() => removeBudget(budget.id)}>Remove</button>
              </div>
              {budget.percent >= 100 && <p className="target-alert">Target exceeded.</p>}
              {budget.percent >= 80 && budget.percent < 100 && <p className="target-alert">You’re getting close to this target.</p>}
            </div>
          ))}
        </div>
      )}

      <h2 className="panel-heading">Recurring reminders</h2>
      <p className="muted">Confirm a reminder when it is due to add the expense to your tracker.</p>
      <form className="management-form recurring-form" onSubmit={submitRecurring}>
        <label>
          Description
          <input value={description} onChange={(event) => setDescription(event.target.value)} required />
        </label>
        <label>
          Amount (₹)
          <input type="number" min="0.01" step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} required />
        </label>
        <label>
          Category
          <select value={recurringCategory} onChange={(event) => setRecurringCategory(event.target.value)}>
            <option value="">Auto-detect</option>
            {categories.map((category) => <option key={category}>{category}</option>)}
          </select>
        </label>
        <label>
          Repeat
          <select value={frequency} onChange={(event) => setFrequency(event.target.value as "weekly" | "monthly")}>
            <option value="monthly">Monthly</option>
            <option value="weekly">Weekly</option>
          </select>
        </label>
        <label>
          First due date
          <input type="date" value={nextDue} onChange={(event) => setNextDue(event.target.value)} required />
        </label>
        <button disabled={busy}>Add reminder</button>
      </form>
      {recurring.length === 0 ? <p className="muted">No recurring reminders yet.</p> : (
        <div className="reminder-list">
          {recurring.map((item) => (
            <div className="reminder-item" key={item.id}>
              <div>
                <strong>{item.description}</strong>
                <div className="muted">{inr(item.amount)} · {item.category || "Auto-detect"} · {item.frequency} · due {item.next_due}</div>
              </div>
              <div className="reminder-actions">
                {item.due && <button onClick={() => completeReminder(item)}>Add expense</button>}
                <button className="link danger" onClick={() => removeRecurring(item.id)}>Remove</button>
              </div>
            </div>
          ))}
        </div>
      )}

      <h2 className="panel-heading">Manage custom categories</h2>
      <form className="management-form category-form" onSubmit={addCategory}>
        <label>
          New category
          <input value={newCategory} maxLength={40} onChange={(event) => setNewCategory(event.target.value)} required />
        </label>
        <button>Add category</button>
      </form>
      {customCategories.length > 0 && (
        <ul className="custom-categories">
          {customCategories.map((category) => (
            <li key={category}>
              <span>{category}</span>
              <span>
                <button className="link" onClick={() => renameCategory(category)}>Rename</button>
                <button className="link danger" onClick={() => removeCategory(category)}>Delete</button>
              </span>
            </li>
          ))}
        </ul>
      )}
      {error && <p className="error banner" role="alert">{error}</p>}
    </section>
  );
}
