import { useState } from "react";
import type { FormEvent } from "react";
import { api, setToken } from "./api";
import "./auth.css";

export default function AuthPage({ onAuth }: { onAuth: (username: string) => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const isLogin = mode === "login";

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = isLogin ? await api.login(username, password) : await api.register(username, password);
      setToken(res.token, remember);
      onAuth(res.username);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  function switchMode() {
    setMode(isLogin ? "register" : "login");
    setError("");
  }

  return (
    <div className="auth-bg">
      <div className="auth-card">
        <div className="auth-brand">
          Smart Expense<span>.</span>
        </div>

        <div className="auth-body">
          <form className="auth-form" onSubmit={submit}>
            <h1>{isLogin ? "WELCOME BACK!" : "CREATE ACCOUNT"}</h1>
            <p className="auth-switch">
              {isLogin ? "Don't have an account? " : "Already have an account? "}
              <button type="button" onClick={switchMode}>
                {isLogin ? "Sign up" : "Sign in"}
              </button>
            </p>

            <label>
              Username
              <input
                className="field"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. nisha"
                autoComplete="username"
                required
              />
            </label>

            <label>
              Password
              <div className="pw">
                <input
                  className="field"
                  type={show ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 6 characters"
                  autoComplete={isLogin ? "current-password" : "new-password"}
                  required
                />
                <button type="button" className="eye" onClick={() => setShow(!show)}>
                  {show ? "Hide" : "Show"}
                </button>
              </div>
            </label>

            <label className="remember">
              <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
              Remember me
            </label>

            {error && <p className="auth-error">{error}</p>}

            <button className="auth-submit" disabled={busy}>
              {busy ? "Please wait…" : isLogin ? "Sign In" : "Sign Up"}
            </button>
          </form>

          <div className="auth-art">
            <div className="circle">
              <img src="/panda.png" alt="Panda mascot" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
