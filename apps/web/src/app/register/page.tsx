"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { register } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [studentNo, setStudentNo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const result = await register({
        email,
        password,
        display_name: displayName,
        student_no: studentNo,
      });
      if (result.success) {
        router.push("/");
      } else {
        setError(result.error?.message ?? "注册失败");
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
        <h1 className="mb-6 text-center text-2xl font-bold text-gray-900">注册 CampusAgent</h1>
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
          <div>
            <label htmlFor="displayName" className="mb-1 block text-sm font-medium text-gray-700">
              显示名称
            </label>
            <input
              id="displayName"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              required
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="张三"
            />
          </div>
          <div>
            <label htmlFor="studentNo" className="mb-1 block text-sm font-medium text-gray-700">
              学号
            </label>
            <input
              id="studentNo"
              type="text"
              value={studentNo}
              onChange={(e) => setStudentNo(e.target.value)}
              required
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="20260001"
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-green-600 px-4 py-2 text-white hover:bg-green-700 disabled:opacity-50"
          >
            {loading ? "注册中..." : "注册"}
          </button>
          <p className="text-center text-sm text-gray-500">
            已有账号？{" "}
            <a href="/login" className="text-blue-600 hover:underline">
              登录
            </a>
          </p>
        </form>
      </div>
    </main>
  );
}
