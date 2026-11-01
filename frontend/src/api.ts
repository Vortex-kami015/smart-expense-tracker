import type { AuthResponse, Budget, Expense, ExpenseInput, Prediction, RecurringExpense, Summary } from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "";
const TOKEN_KEY = "token";

// "Remember me" keeps the token in localStorage; otherwise it lives only for this browser tab.
export const getToken = () => localStorage.getItem(TOKEN_KEY) ?? sessionStorage.getItem(TOKEN_KEY);

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(TOKEN_KEY);
}

export function setToken(token: string, remember: boolean) {
  clearToken();
  (remember ? localStorage : sessionStorage).setItem(TOKEN_KEY, token);
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(BASE + url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  // A saved token that the server rejects means the session expired: log the user out.
  if (res.status === 401 && token) {
    clearToken();
    window.dispatchEvent(new Event("auth-expired"));
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const msg = body.errors ? Object.values(body.errors).join(", ") : body.error || res.statusText;
    throw new Error(msg);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  login: (username: string, password: string) =>
    request<AuthResponse>("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  register: (username: string, password: string) =>
    request<AuthResponse>("/api/auth/register", { method: "POST", body: JSON.stringify({ username, password }) }),
  me: () => request<{ username: string }>("/api/auth/me"),
  categories: () => request<string[]>("/api/categories"),
  createCategory: (name: string) =>
    request<{ name: string }>("/api/categories", { method: "POST", body: JSON.stringify({ name }) }),
  removeCategory: (name: string) =>
    request<void>(`/api/categories/${encodeURIComponent(name)}`, { method: "DELETE" }),
  renameCategory: (name: string, newName: string) =>
    request<{ name: string }>(`/api/categories/${encodeURIComponent(name)}`, {
      method: "PATCH",
      body: JSON.stringify({ name: newName }),
    }),
  expenses: (params: Record<string, string> = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString();
    return request<Expense[]>(`/api/expenses${qs ? "?" + qs : ""}`);
  },
  create: (e: ExpenseInput) => request<Expense>("/api/expenses", { method: "POST", body: JSON.stringify(e) }),
  update: (id: number, e: ExpenseInput) =>
    request<Expense>(`/api/expenses/${id}`, { method: "PUT", body: JSON.stringify(e) }),
  remove: (id: number) => request<void>(`/api/expenses/${id}`, { method: "DELETE" }),
  summary: () => request<Summary>("/api/summary"),
  budgets: () => request<Budget[]>("/api/budgets"),
  saveBudget: (budget: { period: "week" | "month"; category: string; target: number }) =>
    request<{ id: number }>("/api/budgets", { method: "POST", body: JSON.stringify(budget) }),
  removeBudget: (id: number) => request<void>(`/api/budgets/${id}`, { method: "DELETE" }),
  recurring: () => request<RecurringExpense[]>("/api/recurring"),
  createRecurring: (expense: {
    description: string;
    amount: number;
    category: string;
    frequency: "weekly" | "monthly";
    next_due: string;
  }) => request<RecurringExpense>("/api/recurring", { method: "POST", body: JSON.stringify(expense) }),
  completeRecurring: (id: number) =>
    request<Expense>(`/api/recurring/${id}/complete`, { method: "POST" }),
  removeRecurring: (id: number) => request<void>(`/api/recurring/${id}`, { method: "DELETE" }),
  categorize: (description: string) =>
    request<Prediction>("/api/categorize", { method: "POST", body: JSON.stringify({ description }) }),
};
