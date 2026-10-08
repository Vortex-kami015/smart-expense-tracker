import type { Expense, ExpenseInput, Prediction, Summary } from "./types";
const BASE = import.meta.env.VITE_API_URL ?? "";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(BASE +url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const msg = body.errors ? Object.values(body.errors).join(", ") : body.error || res.statusText;
    throw new Error(msg);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  categories: () => request<string[]>("/api/categories"),
  expenses: (params: Record<string, string> = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString();
    return request<Expense[]>(`/api/expenses${qs ? "?" + qs : ""}`);
  },
  create: (e: ExpenseInput) => request<Expense>("/api/expenses", { method: "POST", body: JSON.stringify(e) }),
  update: (id: number, e: ExpenseInput) =>
    request<Expense>(`/api/expenses/${id}`, { method: "PUT", body: JSON.stringify(e) }),
  remove: (id: number) => request<void>(`/api/expenses/${id}`, { method: "DELETE" }),
  summary: () => request<Summary>("/api/summary"),
  categorize: (description: string) =>
    request<Prediction>("/api/categorize", { method: "POST", body: JSON.stringify({ description }) }),
};
      