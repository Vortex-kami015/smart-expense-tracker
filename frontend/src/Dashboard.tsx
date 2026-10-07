import type { Summary } from "./types";

export const inr = (n: number) => "₹" + n.toLocaleString("en-IN", { maximumFractionDigits: 2 });

function Bars({ items }: { items: { label: string; value: number }[] }) {
  const max = Math.max(...items.map((i) => i.value), 1);
  return (
    <div className="bars">
      {items.map((i) => (
        <div className="bar-row" key={i.label}>
          <span className="bar-label">{i.label}</span>
          <div className="bar-track">
            <div className="bar-fill" style={{ width: `${(i.value / max) * 100}%` }} />
          </div>
          <span className="bar-value">{inr(i.value)}</span>
        </div>
      ))}
    </div>
  );
}

export default function Dashboard({ summary }: { summary: Summary | null }) {
  if (!summary) return <div className="card">Loading…</div>;
  return (
    <div className="card">
      <h2>Overview</h2>
      <div className="stats">
        <div>
          <div className="stat-num">{inr(summary.total)}</div>
          <div className="muted">Total spent</div>
        </div>
        <div>
          <div className="stat-num">{summary.count}</div>
          <div className="muted">Expenses</div>
        </div>
      </div>

      <h3>By category</h3>
      {summary.by_category.length === 0 ? (
        <p className="muted">No data yet.</p>
      ) : (
        <Bars items={summary.by_category.map((c) => ({ label: c.category, value: c.total }))} />
      )}

      <h3>By month</h3>
      {summary.by_month.length === 0 ? (
        <p className="muted">No data yet.</p>
      ) : (
        <Bars items={summary.by_month.map((m) => ({ label: m.month, value: m.total }))} />
      )}
    </div>
  );
}
