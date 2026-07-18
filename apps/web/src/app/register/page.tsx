'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { register } from '@/lib/api';

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [studentNo, setStudentNo] = useState('');
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
        router.push('/');
      } else {
        setError(result.error?.message ?? '注册失败');
      }
    } catch {
      setError(
        '无法连接后端服务。请确认终端里打印的 API 地址正在运行，并重新打开对应的 Web 地址。'
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-intro" aria-label="校园智能体注册">
        <div className="auth-kicker">加入校园智能体</div>
        <h1 className="auth-title">把校园身份变成协作入口。</h1>
        <p className="auth-copy">
          创建账号后，你可以加入组织、管理个人资料，并在受控边界内使用智能体辅助校园沟通。
        </p>
        <div className="auth-points" aria-label="注册后能力">
          <div className="auth-point">
            <strong>真实身份</strong>
            <span>用邮箱、学号和展示名建立清晰的校园身份。</span>
          </div>
          <div className="auth-point">
            <strong>组织连接</strong>
            <span>注册后可浏览并加入校园组织空间。</span>
          </div>
          <div className="auth-point">
            <strong>可控记忆</strong>
            <span>个人资料与偏好会按隐私策略受控使用。</span>
          </div>
        </div>
      </section>

      <section className="auth-panel-wrap" aria-label="注册表单">
        <form onSubmit={handleSubmit} className="auth-panel auth-form">
          <div>
            <h1>创建账号</h1>
            <p className="auth-panel-subtitle">填写基础身份信息即可进入校园智能体。</p>
          </div>

          <div className="form-field">
            <label htmlFor="email">邮箱</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="input"
              placeholder="student@example.edu"
            />
          </div>

          <div className="form-field">
            <label htmlFor="password">密码</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="input"
              placeholder="至少8个字符，含字母和数字"
            />
            <span className="form-help">建议使用 12 位以上密码。</span>
          </div>

          <div className="form-field">
            <label htmlFor="displayName">显示名称</label>
            <input
              id="displayName"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              required
              className="input"
              placeholder="张三"
            />
          </div>

          <div className="form-field">
            <label htmlFor="studentNo">学号</label>
            <input
              id="studentNo"
              type="text"
              value={studentNo}
              onChange={(e) => setStudentNo(e.target.value)}
              required
              className="input"
              placeholder="20260001"
            />
          </div>

          {error && <p className="auth-error">{error}</p>}

          <button type="submit" disabled={loading} className="btn btn-primary">
            {loading ? '注册中...' : '注册'}
          </button>

          <p className="auth-footer">
            已有账号？ <Link href="/login">登录</Link>
          </p>
        </form>
      </section>
    </main>
  );
}
