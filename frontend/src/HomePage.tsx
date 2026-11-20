type Page = "home" | "overview" | "add-expense" | "targets" | "recurring";

interface Props {
  onNavigate: (page: Page) => void;
}

const features = [
  {
    title: "See the full picture",
    description: "Review your recent expenses, monthly totals, category breakdown, and spending trends in one overview.",
    page: "overview" as const,
    action: "Go to overview",
  },
  {
    title: "Log a purchase",
    description: "Record an expense with a description, amount, date, and category. Categories can be suggested as you type.",
    page: "add-expense" as const,
    action: "Add an expense",
  },
  {
    title: "Stay on budget",
    description: "Set weekly or monthly spending targets and keep an eye on progress as expenses are recorded.",
    page: "targets" as const,
    action: "Set spending targets",
  },
  {
    title: "Plan regular costs",
    description: "Create weekly or monthly reminders for recurring costs and add them to your expenses when due.",
    page: "recurring" as const,
    action: "Manage reminders",
  },
];

export default function HomePage({ onNavigate }: Props) {
  return (
    <main className="home-page">
      <section className="home-hero">
        <p className="eyebrow">YOUR MONEY, MADE CLEARER</p>
        <h2>Make every expense easier to understand.</h2>
        <p className="home-intro">
          Smart Expense Tracker helps you record day-to-day spending, understand where your money goes,
          and build simple habits around your budget.
        </p>
        <div className="home-actions">
          <button onClick={() => onNavigate("add-expense")}>Add your first expense</button>
          <button className="secondary" onClick={() => onNavigate("overview")}>Explore overview</button>
        </div>
      </section>

      <section className="home-features" aria-labelledby="home-features-heading">
        <div className="home-section-heading">
          <p className="eyebrow">A SIMPLE WAY TO STAY IN CONTROL</p>
          <h2 id="home-features-heading">Everything you need to track spending</h2>
          <p className="muted">Choose a place to start. Your tools are ready whenever you need them.</p>
        </div>
        <div className="home-feature-grid">
          {features.map((feature, index) => (
            <article className="home-feature card" key={feature.page}>
              <span className="home-feature-number">0{index + 1}</span>
              <h3>{feature.title}</h3>
              <p className="muted">{feature.description}</p>
              <button className="link" onClick={() => onNavigate(feature.page)}>{feature.action} <span aria-hidden="true">→</span></button>
            </article>
          ))}
        </div>
      </section>

      <section className="home-tip">
        <span aria-hidden="true">✦</span>
        <p><strong>A helpful habit:</strong> Add expenses as they happen, then check your overview regularly to spot patterns early.</p>
      </section>
    </main>
  );
}
