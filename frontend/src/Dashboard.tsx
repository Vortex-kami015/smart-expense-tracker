import type { Summary } from "./types";

export const inr = (n: number) => "₹" + n.toLocaleString("en-IN", { maximumFractionDigits: 2 });

const chartColors = ["#f18a3d", "#55c99b", "#e7bb67", "#b58aeb", "#e67870", "#67a9e0", "#d993cb", "#d7b86b"];

function monthLabel(value: string) {
  const [year, month] = value.split("-").map(Number);
  if (!year || !month) return value;
  return new Date(year, month - 1).toLocaleDateString("en", { month: "short" });
}

export default function Dashboard({ summary }: { summary: Summary | null }) {
  if (!summary) return <div className="card dashboard-card">Loading your spending overview…</div>;

  const months = summary.by_month.slice(-6);
  const maxMonthTotal = Math.max(...months.map((item) => item.total), 1);
  const average = summary.count ? summary.total / summary.count : 0;
  const largestCategory = summary.by_category.reduce(
    (largest, category) => category.total > (largest?.total ?? 0) ? category : largest,
    summary.by_category[0],
  );
  const categoryTotal = summary.by_category.reduce((total, item) => total + item.total, 0);
  let categoryProgress = 0;
  const categoryGradient = summary.by_category.map((item, index) => {
    const start = categoryProgress;
    categoryProgress += categoryTotal ? (item.total / categoryTotal) * 100 : 0;
    return `${chartColors[index % chartColors.length]} ${start}% ${categoryProgress}%`;
  }).join(", ");

  const latestMonth = summary.by_month[summary.by_month.length - 1];
  const previousMonth = summary.by_month[summary.by_month.length - 2];
  const monthChange = latestMonth && previousMonth && previousMonth.total
    ? ((latestMonth.total - previousMonth.total) / previousMonth.total) * 100
    : null;

  return (
    <section className="card dashboard-card" aria-labelledby="overview-title">
      <div className="dashboard-heading">
        <div>
          <p className="eyebrow">YOUR FINANCES</p>
          <h2 id="overview-title">Spending overview</h2>
        </div>
        {monthChange !== null && (
          <span className={`trend-pill${monthChange > 0 ? " trend-up" : " trend-down"}`}>
            {monthChange > 0 ? "↑" : "↓"} {Math.abs(Math.round(monthChange))}% this month
          </span>
        )}
      </div>

      <div className="overview-stats">
        <div className="overview-total">
          <span className="muted">Total tracked</span>
          <strong>{inr(summary.total)}</strong>
        </div>
        <div className="overview-stat">
          <span className="muted">Transactions</span>
          <strong>{summary.count}</strong>
        </div>
        <div className="overview-stat">
          <span className="muted">Average expense</span>
          <strong>{inr(average)}</strong>
        </div>
        <div className="overview-stat">
          <span className="muted">Top category</span>
          <strong>{largestCategory?.category ?? "—"}</strong>
        </div>
      </div>

      <div className="dashboard-charts">
        <section className="chart-panel" aria-labelledby="monthly-chart-title">
          <div className="chart-heading">
            <div>
              <h3 id="monthly-chart-title">Monthly spending</h3>
              <p className="muted">Your last {months.length || 0} recorded months</p>
            </div>
            {latestMonth && <strong className="chart-total">{inr(latestMonth.total)}</strong>}
          </div>
          {months.length === 0 ? (
            <p className="chart-empty muted">Add an expense to see your monthly trend.</p>
          ) : (
            <div
              className="monthly-chart"
              role="img"
              aria-label={`Monthly spending: ${months.map((item) => `${monthLabel(item.month)} ${inr(item.total)}`).join(", ")}`}
            >
              {months.map((item, index) => (
                <div className="month-column" key={item.month}>
                  <span className="month-amount">{inr(item.total)}</span>
                  <div className="month-bar-track">
                    <div
                      className={`month-bar${index === months.length - 1 ? " month-bar-current" : ""}`}
                      style={{ height: `${Math.max((item.total / maxMonthTotal) * 100, item.total > 0 ? 5 : 0)}%` }}
                    />
                  </div>
                  <span className="month-label">{monthLabel(item.month)}</span>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="chart-panel category-panel" aria-labelledby="category-chart-title">
          <div className="chart-heading">
            <div>
              <h3 id="category-chart-title">By category</h3>
              <p className="muted">Where your money goes</p>
            </div>
          </div>
          {summary.by_category.length === 0 ? (
            <p className="chart-empty muted">Category details will appear here.</p>
          ) : (
            <div className="category-chart-content">
              <div
                className="donut-chart"
                role="img"
                aria-label={`Spending by category: ${summary.by_category.map((item) => `${item.category} ${inr(item.total)}`).join(", ")}`}
                style={{ background: `conic-gradient(${categoryGradient})` }}
              >
                <span>{summary.count}<small>items</small></span>
              </div>
              <div className="chart-legend">
                {summary.by_category.map((item, index) => (
                  <div key={item.category}>
                    <span className="legend-dot" style={{ background: chartColors[index % chartColors.length] }} />
                    <span>{item.category}</span>
                    <strong>{inr(item.total)}</strong>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      </div>
    </section>
  );
}
