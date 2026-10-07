import { useEffect, useState } from "react";
import { api } from "./api";
import type { Expense, ExpenseInput, Prediction } from "./types";

interface Props {
  categories: string[];
  editing: Expense | null;
  onSaved: () => void;
  onCancel: () => void;
}

const today = () => new Date().toISOString().slice(0, 10);

export default function ExpenseForm({ categories, editing, onSaved, onCancel }: Props) {
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState(today());
  const [category, setCategory] = useState(""); // "" = let the system decide
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  // Fill the form when editing
  useEffect(() => {
    if (editing) {
      setDescription(editing.description);
      setAmount(String(editing.amount));
      setDate(editing.date);
      setCategory(editing.auto_categorized ? "" : editing.category);
    } else {
      setDescription("");
      setAmount("");
      setDate(today());
      setCategory("");
    }
    setPrediction(null);
    setError("");
  }, [editing]);

  // Live category suggestion (debounced)
  useEffect(() => {
    if (!description.trim()) {
      setPrediction(null);
      return;
    }
    const t = setTimeout(() => {
      api.categorize(description).then(setPrediction).catch(() => setPrediction(null));
    }, 350);
    return () => clearTimeout(t);
  }, [description]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSaving(true);
    const payload: ExpenseInput = {
      description,
      amount: parseFloat(amount),
      date,
      ...(category ? { category } : {}),
    };
    try {
         if (editing) {
     await api.update(editing.id, payload);
   } else {
     await api.create(payload);
     setDescription("");
     setAmount("");
     setCategory("");
     setDate(today());
     setPrediction(null);
   }
   onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="card form" onSubmit={submit}>
      <h2>{editing ? "Edit expense" : "Add expense"}</h2>

      <label>
        Description
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="e.g. Swiggy dinner"
          required
        />
      </label>

      {prediction && !category && (
        <p className="hint">
          Auto category: <strong>{prediction.category}</strong>{" "}
          <span className="muted">
            ({prediction.method === "rule" ? "keyword match" : `ML ${Math.round(prediction.confidence * 100)}%`})
          </span>
        </p>
      )}

      <div className="row">
        <label>
          Amount (₹)
          <input type="number" step="0.01" min="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} required />
        </label>
        <label>
          Date
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
        </label>
      </div>

      <label>
        Category
        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">Auto-detect</option>
          {categories.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
      </label>

      {error && <p className="error">{error}</p>}

      <div className="row">
        <button type="submit" disabled={saving}>
          {saving ? "Saving…" : editing ? "Update" : "Add"}
        </button>
        {editing && (
          <button type="button" className="secondary" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
