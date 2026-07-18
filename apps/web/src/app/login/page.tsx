'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { login } from '@/lib/api';
import { DEMO_ACCOUNTS, DEMO_PASSWORD, isDemoPickerEnabled, type DemoAccount } from '@/lib/demo';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedDemoKey, setSelectedDemoKey] = useState<string | null>(null);

  const demoEnabled = isDemoPickerEnabled();

  function selectDemoAccount(account: DemoAccount) {
    setSelectedDemoKey(account.key);
    setEmail(account.email);
    // Pre-fill the demo password，用途：one-click demo login. The
    // password is a PUBLIC demo constant and is held only in React
    // state (memory) — it is never written to localStorage or
    // sessionStorage. Login still goes through the real /auth/login
    // API, so real auth logic is exercised end-to-end.
    if (account.can_login) {
      setPassword(DEMO_PASSWORD);
    } else {
      setPassword('');
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
        router.push('/');
      } else {
        setError(result.error?.message ?? '登录失败');
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
      <section className="auth-intro" aria-label="校园智能体">
        <div className="auth-kicker">校园智能体</div>
        <h1 className="auth-title">校园协作，从可信身份开始。</h1>
        <p className="auth-copy">
          登录后进入组织、会话、记忆与场景协作工作台。演示
          环境已准备好账号，可以直接体验完整主路径。
        </p>
        <div className="auth-points" aria-label="平台能力">
          <div className="auth-point">
            <strong>组织目录</strong>
            <span>按学院、社团和项目空间组织校园关系。</span>
          </div>
          <div className="auth-point">
            <strong>隐私优先</strong>
            <span>私密偏好与记忆默认只对本人可见。</span>
          </div>
          <div className="auth-point">
            <strong>智能场景</strong>
            <span>用智能体协调聚餐、消息和协作决策。</span>
          </div>
        </div>
      </section>

      <section className="auth-panel-wrap" aria-label="登录表单">
        <div>
          <form onSubmit={handleSubmit} className="auth-panel auth-form">
            <div>
              <h1>登录校园智能体</h1>
              <p className="auth-panel-subtitle">使用校园账号进入你的工作台。</p>
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
            </div>

            {error && <p className="auth-error">{error}</p>}

            <button type="submit" disabled={loading} className="btn btn-primary">
              {loading ? '登录中...' : '登录'}
            </button>

            <p className="auth-footer">
              还没有账号？ <Link href="/register">注册</Link>
            </p>
          </form>

          {demoEnabled && (
            <DemoAccountPicker selectedKey={selectedDemoKey} onSelect={selectDemoAccount} />
          )}
        </div>
      </section>
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
    <section data-testid="demo-account-picker" className="demo-picker">
      <h2>演示账号快速登录</h2>
      <p>点击下方账号可自动填入邮箱与演示密码（仅开发环境可见，不会写入浏览器存储）。</p>
      <ul className="demo-account-list">
        {DEMO_ACCOUNTS.map((account) => {
          const isSelected = account.key === selectedKey;
          return (
            <li key={account.key}>
              <button
                type="button"
                onClick={() => onSelect(account)}
                aria-pressed={isSelected}
                disabled={!account.can_login}
                className="demo-account-button"
              >
                <span className="font-medium">{account.display_name}</span>
                <span className="demo-account-meta">
                  {account.role === 'SYSTEM_ADMIN' ? '管理员' : '学生'}
                  {' · '}
                  {account.description}
                </span>
                {!account.can_login && (
                  <span className="demo-account-meta text-danger">不可登录（软删除）</span>
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
