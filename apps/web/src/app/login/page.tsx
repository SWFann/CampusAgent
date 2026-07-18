"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";
import {
  DEMO_ACCOUNTS,
  DEMO_PASSWORD,
  isDemoPickerEnabled,
  type DemoAccount,
} from "@/lib/demo";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedDemoKey, setSelectedDemoKey] = useState<string | null>(null);

  const demoEnabled = isDemoPickerEnabled();

  function selectDemoAccount(account: DemoAccount) {
    setSelectedDemoKey(account.key);
    setEmail(account.email);
    // Pre-fill the demo password for one-click demo login. The
    // password is a PUBLIC demo constant and is held only in React
    // state (memory) — it is never written to localStorage or
    // sessionStorage. Login still goes through the real /auth/login
    // API, so real auth logic is exercised end-to-end.
    if (account.can_login) {
      setPassword(DEMO_PASSWORD);
    } else {
      setPassword("");
    }
    setError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const result = await login({ email, password });
      if (result.success) {
        router.push("/");
      } else {
        setError(result.error?.message ?? "登录失败");
      }
    } catch {
      setError("网络错误，请重试");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        <h1 className="mb-6 text-center text-2xl font-bold text-gray-900">登录 CampusAgent</h1>
        <form onSubmit={handleSubmit} className="space-y-4 rounded-lg bg-white p-6 shadow-md">
          <div>
            <label htmlFor="email" className="mb-1 block text-sm font-medium text-gray-700">
              邮箱
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="student@example.edu"
            />
          </div>
          <div>
            <label htmlFor="password" className="mb-1 block text-sm font-medium text-gray-700">
              密码
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="至少8个字符，含字母和数字"
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "登录中..." : "登录"}
          </button>
          <p className="text-center text-sm text-gray-500">
            还没有账号？{" "}
            <a href="/register" className="text-blue-600 hover:underline">
              注册
            </a>
          </p>
        </form>

        {demoEnabled && (
          <DemoAccountPicker
            selectedKey={selectedDemoKey}
            onSelect={selectDemoAccount}
          />
        )}
      </div>
    </main>
  );
}

/** Demo account quick-select panel (development/test only). */
function DemoAccountPicker({
  selectedKey,
  onSelect,
}: {
  selectedKey: string | null;
  onSelect: (account: DemoAccount) => void;
}) {
  return (
    <section
      data-testid="demo-account-picker"
      className="mt-4 rounded-lg border border-dashed border-blue-300 bg-blue-50/50 p-4"
    >
      <h2 className="mb-1 text-sm font-semibold text-blue-900">
        Demo 账号快速登录
      </h2>
      <p className="mb-3 text-xs text-blue-700">
        点击下方账号可自动填入邮箱与 demo 密码（仅开发环境可见，不会写入浏览器存储）。
      </p>
      <ul className="space-y-1">
        {DEMO_ACCOUNTS.map((account) => {
          const isSelected = account.key === selectedKey;
          return (
            <li key={account.key}>
              <button
                type="button"
                onClick={() => onSelect(account)}
                aria-pressed={isSelected}
                className={[
                  "w-full rounded-md border px-3 py-2 text-left text-sm transition",
                  isSelected
                    ? "border-blue-500 bg-blue-100 text-blue-900"
                    : "border-gray-200 bg-white text-gray-700 hover:border-blue-400 hover:bg-blue-50",
                  !account.can_login ? "opacity-70" : "",
                ].join(" ")}
              >
                <span className="font-medium">{account.display_name}</span>
                <span className="ml-2 text-xs text-gray-500">
                  {account.role === "SYSTEM_ADMIN" ? "管理员" : "学生"}
                </span>
                <span className="block text-xs text-gray-500">
                  {account.description}
                </span>
                {!account.can_login && (
                  <span className="mt-1 block text-xs text-red-500">
                    不可登录（软删除）
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
