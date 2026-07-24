'use client';

import { useState } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { login, register } from '@/lib/api';
import { DEMO_ACCOUNTS, DEMO_PASSWORD, isDemoPickerEnabled, type DemoAccount } from '@/lib/demo';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedDemoKey, setSelectedDemoKey] = useState<string | null>(null);
  const [authMode, setAuthMode] = useState<'login' | 'application'>('login');

  const demoEnabled = isDemoPickerEnabled();

  function selectDemoAccount(account: DemoAccount) {
    setSelectedDemoKey(account.key);
    setEmail(account.email);
    // This public demo credential is only held in memory. Authentication still
    // goes through the real API and nothing is written to browser storage.
    setPassword(account.can_login ? DEMO_PASSWORD : '');
    setError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const normalizedAccount = email.trim().toLowerCase();
      const loginEmail = /^\d{6,20}$/.test(normalizedAccount)
        ? `${normalizedAccount}@jnu.edu.cn`
        : normalizedAccount;
      const result = await login({ email: loginEmail, password });
      if (result.success) {
        router.push('/');
      } else {
        setError(result.error?.message ?? '登录失败');
      }
    } catch {
      setError('无法连接后端服务。请确认终端里打印的 API 地址正在运行，并重新打开对应的 Web 地址。');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <div className="login-orb login-orb-left" aria-hidden="true" />
      <div className="login-orb login-orb-right" aria-hidden="true" />

      <div className="login-window">
        <header className="login-window-bar">
          <div className="window-controls" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
          <div className="login-brand" aria-label="暨南大学 CampusAgent 智能校园管理与协作平台">
            <Image
              src="/brand/jinan-university-logo.png"
              alt="暨南大学 Jinan University"
              width={924}
              height={297}
              priority
              className="login-brand-logo"
            />
          </div>
          <span className="login-window-status">
            <i aria-hidden="true" /> 校园服务正常
          </span>
        </header>

        <div className="login-layout">
          <section className="login-intro" aria-labelledby="login-heading">
            <div className="login-kicker">
              <span aria-hidden="true">◈</span>
              暨南大学 · 智慧校园
            </div>
            <h1 id="login-heading">
              <span className="login-title-line">听见真实的声音，</span>
              <span className="login-title-line">一起做更好的选择。</span>
            </h1>
            <p className="login-lead">
              个人 Agent 帮助每个人表达需求、参与校园；协同 Agent 在清晰授权和隐私边界内汇聚意见、促成共识，也让关怀与专业支持在需要时及时抵达。
            </p>

            <div className="campus-overview" aria-label="平台服务概览">
              <div className="campus-overview-head">
                <div>
                  <span className="campus-overline">暨南园 · 服务总览</span>
                  <strong>多校区协同工作台</strong>
                </div>
                <span className="campus-weather">忠信笃敬</span>
              </div>
              <div className="campus-activity-list">
                <div className="campus-activity campus-activity-blue">
                  <span className="campus-activity-time">校务</span>
                  <span><strong>通知与事务</strong><small>组织、制度与校园服务</small></span>
                </div>
                <div className="campus-activity campus-activity-green">
                  <span className="campus-activity-time">教学</span>
                  <span><strong>课程与班级</strong><small>教学任务与师生协作</small></span>
                </div>
              </div>
              <div className="role-strip" aria-label="平台角色">
                <span><i className="role-dot role-dot-blue" />学校管理</span>
                <span><i className="role-dot role-dot-amber" />教师协作</span>
                <span><i className="role-dot role-dot-green" />学生服务</span>
              </div>
            </div>

            <div className="trust-row" aria-label="平台信任保障">
              <span>统一校园身份</span>
              <i aria-hidden="true" />
              <span>最小必要权限</span>
              <i aria-hidden="true" />
              <span>重要操作可审计</span>
            </div>
          </section>

          <section
            className={`login-panel-wrap${authMode === 'application' ? ' is-application' : ''}`}
            aria-label={authMode === 'login' ? '登录表单' : '新生申请表单'}
          >
            <div className="login-panel-stack">
              {authMode === 'login' ? <>
                <form onSubmit={handleSubmit} className="login-panel">
                <div className="login-panel-heading">
                  <span className="login-entry-label">统一身份入口</span>
                  <h2>登录 CampusAgent</h2>
                  <p>使用学校分配的校园账号进入工作台。</p>
                </div>

                <div className="login-form-field">
                  <label htmlFor="email">暨南大学账号</label>
                  <div className="login-input-wrap">
                    <span className="login-input-icon" aria-hidden="true">@</span>
                    <input
                      id="email"
                      aria-label="暨南大学账号"
                      type="text"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      autoComplete="username"
                      placeholder="请输入学号或校园邮箱"
                    />
                  </div>
                </div>

                <div className="login-form-field">
                  <label htmlFor="password">密码</label>
                  <div className="login-input-wrap">
                    <span className="login-input-icon login-lock-icon" aria-hidden="true" />
                    <input
                      id="password"
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      autoComplete="current-password"
                      placeholder="输入账号密码"
                    />
                  </div>
                </div>

                {error && <p className="login-error" role="alert">{error}</p>}

                <button type="submit" aria-label="登录" disabled={loading} className="login-submit">
                  <span>{loading ? '正在登录…' : '进入校园工作台'}</span>
                  {!loading && <span aria-hidden="true">→</span>}
                </button>

                <div className="login-privacy-note">
                  <span className="privacy-shield" aria-hidden="true">✓</span>
                  <p><strong>你的个人数据由你掌控</strong><br />管理身份不会自动获得你的私人 Agent 数据。</p>
                </div>

                <p className="login-footer">
                  尚未开通账号？{' '}
                  <button type="button" onClick={() => { setAuthMode('application'); setError(null); }}>
                    新生申请
                  </button>
                </p>
              </form>

              {demoEnabled && (
                <DemoAccountPicker selectedKey={selectedDemoKey} onSelect={selectDemoAccount} />
              )}
              </> : (
                <StudentApplicationForm
                  onBack={() => setAuthMode('login')}
                  onSuccess={() => router.push('/')}
                />
              )}
            </div>
          </section>
        </div>
      </div>

      <footer className="login-page-footer">
        <span>© 2026 暨南大学 CampusAgent</span>
        <span>忠信笃敬 · 让校园服务更贴近每一个人</span>
      </footer>
    </main>
  );
}

function StudentApplicationForm({
  onBack,
  onSuccess,
}: {
  onBack: () => void;
  onSuccess: () => void;
}) {
  const [account, setAccount] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [agreed, setAgreed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const normalizedAccount = account.replace(/\s/g, '');
  const agentCode = `campusagent${normalizedAccount || '学号'}`;

  async function handleApplication(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!/^\d{6,20}$/.test(normalizedAccount)) {
      setError('请输入 6–20 位数字的暨南大学账号。');
      return;
    }
    const normalizedPhone = phoneNumber.replace(/[\s-]/g, '');
    if (!/^\+?\d{7,15}$/.test(normalizedPhone)) {
      setError('请输入有效的手机号码。');
      return;
    }
    if (password !== confirmPassword) {
      setError('两次输入的密码不一致。');
      return;
    }
    if (!agreed) {
      setError('请先确认校园身份与隐私说明。');
      return;
    }

    setLoading(true);
    try {
      const result = await register({
        email: `${normalizedAccount}@jnu.edu.cn`,
        password,
        display_name: displayName.trim(),
        student_no: normalizedAccount,
        phone_number: normalizedPhone,
      });
      if (result.success) {
        onSuccess();
      } else {
        setError(result.error?.message ?? '申请提交失败');
      }
    } catch {
      setError('无法连接校园服务，请稍后重试。');
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleApplication} className="login-panel application-panel">
      <button type="button" className="application-back" onClick={onBack}>
        <span aria-hidden="true">←</span> 返回登录
      </button>

      <div className="login-panel-heading application-heading">
        <span className="login-entry-label application-welcome-label">
          <i aria-hidden="true" />
          欢迎新同学加入暨南大家庭
        </span>
        <h2>开启你的 CampusAgent</h2>
        <p>用你的校园账号建立身份，我们会同步生成专属 Agent 编号。</p>
      </div>

      <div className="application-fields-grid">
        <div className="login-form-field">
          <label htmlFor="application-name">姓名</label>
          <div className="login-input-wrap">
            <span className="login-input-icon" aria-hidden="true">名</span>
            <input
              id="application-name"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              required
              autoComplete="name"
              placeholder="与校园身份一致"
            />
          </div>
        </div>

        <div className="login-form-field">
          <label htmlFor="application-account">暨南大学账号（学号）</label>
          <div className="login-input-wrap">
            <span className="login-input-icon" aria-hidden="true">#</span>
            <input
              id="application-account"
              type="text"
              inputMode="numeric"
              value={account}
              onChange={(e) => setAccount(e.target.value)}
              required
              autoComplete="username"
              placeholder="20260001"
            />
          </div>
        </div>
      </div>

      <div className="login-form-field">
        <label htmlFor="application-phone">绑定手机</label>
        <div className="login-input-wrap">
          <span className="login-input-icon login-phone-icon" aria-hidden="true" />
          <input
            id="application-phone"
            type="tel"
            value={phoneNumber}
            onChange={(e) => setPhoneNumber(e.target.value)}
            required
            autoComplete="tel"
            placeholder="用于账号安全提醒"
          />
        </div>
      </div>

      <div className="application-fields-grid">
        <div className="login-form-field">
          <label htmlFor="application-password">设置密码</label>
          <div className="login-input-wrap">
            <span className="login-input-icon login-lock-icon" aria-hidden="true" />
            <input
              id="application-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
              placeholder="8 位以上"
            />
          </div>
        </div>

        <div className="login-form-field">
          <label htmlFor="application-password-confirm">确认密码</label>
          <div className="login-input-wrap">
            <span className="login-input-icon login-lock-icon" aria-hidden="true" />
            <input
              id="application-password-confirm"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
              placeholder="再输入一次"
            />
          </div>
        </div>
      </div>

      <div className="agent-code-preview" aria-live="polite">
        <span className="agent-code-mark" aria-hidden="true">CA</span>
        <span>
          <small>专属 Agent 编号</small>
          <strong>{agentCode}</strong>
        </span>
        <span className="agent-code-status">自动分配</span>
      </div>

      <label className="application-consent">
        <input
          type="checkbox"
          checked={agreed}
          onChange={(e) => setAgreed(e.target.checked)}
          required
        />
        <span>我已确认信息属于本人，并知悉手机号仅用于账号安全，不向教师或其他学生公开。</span>
      </label>

      {error && <p className="login-error" role="alert">{error}</p>}

      <button type="submit" aria-label="提交新生申请" disabled={loading} className="login-submit">
        <span>{loading ? '正在创建校园身份…' : '提交申请并创建 Agent'}</span>
        {!loading && <span aria-hidden="true">→</span>}
      </button>

      <p className="application-footnote">
        申请成功后可继续完善专业、年级和偏好；敏感信息默认不向管理者开放。
      </p>
    </form>
  );
}

function DemoAccountPicker({
  selectedKey,
  onSelect,
}: {
  selectedKey: string | null;
  onSelect: (account: DemoAccount) => void;
}) {
  const selectedAccount = selectedKey
    ? DEMO_ACCOUNTS.find((account) => account.key === selectedKey) ?? null
    : null;

  return (
    <section data-testid="demo-account-picker" className="demo-picker login-demo-picker">
      <div className="demo-picker-heading">
        <div>
          <h2>选择演示身份</h2>
          <p>点击人物查看其身份与作用。</p>
        </div>
        <span>仅开发环境</span>
      </div>
      <ul className="demo-account-list">
        {DEMO_ACCOUNTS.map((account) => {
          const isSelected = account.key === selectedKey;
          const roleLabel = account.role === 'SYSTEM_ADMIN' ? '校务' : '学生';
          return (
            <li key={account.key}>
              <button
                type="button"
                onClick={() => onSelect(account)}
                aria-pressed={isSelected}
                disabled={!account.can_login}
                className="demo-account-button"
              >
                <span className={`demo-avatar demo-avatar-${account.key}`} aria-hidden="true">
                  {account.key === 'admin' ? '管' : account.key === 'deleted' ? '停' : account.display_name.slice(0, 1)}
                </span>
                <span className="demo-person-name">{account.display_name}</span>
                <span className="demo-person-role">{account.can_login ? roleLabel : '已停用'}</span>
              </button>
            </li>
          );
        })}
      </ul>
      <div className={`demo-account-detail${selectedAccount ? ' is-visible' : ''}`} aria-live="polite">
        {selectedAccount ? (
          <>
            <span className="demo-detail-icon" aria-hidden="true">→</span>
            <span>
              <strong>{selectedAccount.display_name} · {selectedAccount.role === 'SYSTEM_ADMIN' ? '学校管理员' : '在校学生'}</strong>
              <small>{selectedAccount.description}，已为你填入演示账号。</small>
            </span>
          </>
        ) : (
          <span className="demo-detail-placeholder">选择一位人物后，这里会显示他的身份和可体验功能。</span>
        )}
      </div>
    </section>
  );
}
