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
