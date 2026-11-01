export interface Expense {
  id: number;
  description: string;
  amount: number;
  date: string;
  category: string;
  auto_categorized: boolean;
}

export interface ExpenseInput {
  description: string;
  amount: number;
  date: string;
  category?: string;
}

export interface Prediction {
  category: string;
  confidence: number;
  method: string;
}

export interface Summary {
  total: number;
  count: number;
  by_category: { category: string; total: number }[];
  by_month: { month: string; total: number }[];
}

export interface Budget {
  id: number;
  period: "week" | "month";
  category: string;
  target: number;
  spent: number;
  percent: number;
}

export interface RecurringExpense {
  id: number;
  description: string;
  amount: number;
  category: string;
  frequency: "weekly" | "monthly";
  next_due: string;
  due: boolean;
}

export interface AuthResponse {
  token: string;
  username: string;
}
