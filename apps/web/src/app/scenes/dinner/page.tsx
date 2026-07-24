"use client";

import Link from "next/link";
import { useState } from "react";
import { AppShell } from "@/components/app/AppShell";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { apiGet, apiPost } from "@/lib/api/client";
import { useAsync } from "@/lib/useAsync";

interface DinnerScene {
  id: string;
  status: string;
  participant_count: number;
  has_submitted: boolean;
}

const BUDGET_OPTIONS = ["30元以下", "30–60元", "60–100元", "100元以上"];
const TIME_OPTIONS = [
  { value: "17:00", label: "17:00–18:00", note: "早点出发" },
  { value: "18:00", label: "18:00–19:00", note: "晚饭时间" },
  { value: "19:00", label: "19:00–20:00", note: "活动结束后" },
  { value: "20:00", label: "20:00–21:00", note: "晚间聚餐" },
];
const DIETARY_OPTIONS = ["素食", "清真", "不吃辣", "海鲜过敏", "无特殊限制"];

function DinnerContent() {
  const [submitting, setSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<"idle" | "success">("idle");
  const [budget, setBudget] = useState("");
  const [dietary, setDietary] = useState<string[]>([]);
  const [timeSlot, setTimeSlot] = useState("");
  const [draftSaved, setDraftSaved] = useState(false);
  const [editingSubmission, setEditingSubmission] = useState(false);

  const { data: scene, loading, error, reload } = useAsync<DinnerScene>(
    async () => apiGet("/scenes/dorm_dinner/status"),
    [],
  );

  const submitted = Boolean(scene?.has_submitted || submitStatus === "success") && !editingSubmission;
  const participantCount = Math.max(scene?.participant_count ?? 0, submitted ? 1 : 0);
  const collaborationStatus = submitted ? "已提交，等待方案" : "偏好收集中";

  const toggleDietary = (option: string) => {
    setDietary((current) => {
      if (option === "无特殊限制") return current.includes(option) ? [] : [option];
      const withoutNone = current.filter((item) => item !== "无特殊限制");
      return withoutNone.includes(option) ? withoutNone.filter((item) => item !== option) : [...withoutNone, option];
    });
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await apiPost("/scenes/dorm_dinner/preferences", {
        budget_range: budget,
        dietary_restrictions: dietary,
        preferred_time: timeSlot,
      });
      setSubmitStatus("success");
      setEditingSubmission(false);
      setDraftSaved(false);
      reload();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="participation-room" aria-label="周末寝室聚餐投票">
      <header className="participation-header">
        <Link href="/scenes" aria-label="返回协作库">←</Link>
        <div><span>番禺校区10栋301寝室群</span><h1>周末寝室聚餐投票</h1><small>吃饭聚餐投票 · {collaborationStatus}</small></div>
        <div className="participation-header-status"><span><strong>{participantCount}/4</strong> 人已参与</span><span><strong>今晚 20:00</strong> 截止</span></div>
      </header>

      {loading && <div className="participation-loading"><LoadingState message="正在加载协作状态…" /></div>}
      {error && <div className="participation-loading"><ErrorState message="加载协作失败，请稍后重试。" /></div>}

      {!loading && !error && <div className="participation-body">
        <aside className="participation-steps" aria-label="协作步骤">
          <header><strong>协作步骤</strong><small>完成后共同形成结果</small></header>
          <ol>
            <li className={submitted ? "is-complete" : "is-current"}><span>{submitted ? "✓" : "1"}</span><div><strong>提交个人偏好</strong><small>{submitted ? "你已完成" : "当前步骤"}</small></div></li>
            <li className={submitted ? "is-current" : ""}><span>2</span><div><strong>生成候选方案</strong><small>{submitted ? "等待成员完成" : "尚未开放"}</small></div></li>
            <li><span>3</span><div><strong>成员方案投票</strong><small>候选方案生成后</small></div></li>
            <li><span>4</span><div><strong>确认聚餐结果</strong><small>投票完成后</small></div></li>
          </ol>
          <Link href="/scenes/dinner/result">查看候选方案与结果 <span>→</span></Link>
        </aside>

        <main className="participation-main">
          {submitted ? (
            <div className="participation-submitted">
              <span>✓</span>
              <p>你的进度</p>
              <h2>个人偏好已提交</h2>
              <strong>现在等待其他寝室成员完成提交</strong>
              <p>所有成员提交或截止时间到达后，场景 Agent 会生成多个候选方案。你的原始选择不会展示给其他成员。</p>
              <div><span><small>当前参与</small><strong>{participantCount}/4 人</strong></span><span><small>下一步</small><strong>生成候选方案</strong></span><span><small>截止时间</small><strong>今晚 20:00</strong></span></div>
              <footer><button type="button" onClick={() => setEditingSubmission(true)}>修改我的提交</button><Link href="/scenes/dinner/result">等待结果 <span>→</span></Link></footer>
            </div>
          ) : (
            <>
              <header className="participation-main-title"><span>步骤 1 · 私密提交</span><h2>告诉我们你的聚餐偏好</h2><p>完成下面三项即可。系统只会用这些信息匹配适合大家的方案。</p></header>

              <aside className="participation-privacy-intro"><span>锁</span><div><strong>提交前先了解可见范围</strong><p>只有你可以看到原始偏好；室友只能看到参与状态、聚合候选方案和最终结果。数据在场景结束后删除，最长不超过24小时。</p></div></aside>

              <div className="participation-form-section">
                <header><span>01</span><div><h3>人均预算</h3><p>选择你可以接受的消费范围</p></div></header>
                <div className="participation-choice-grid is-budget">{BUDGET_OPTIONS.map((option) => <button key={option} className={budget === option ? "is-selected" : ""} type="button" onClick={() => setBudget(option)}><span>{budget === option ? "✓" : "¥"}</span><strong>{option}</strong></button>)}</div>
              </div>

              <div className="participation-form-section">
                <header><span>02</span><div><h3>可以参加的时间</h3><p>选择一个你最方便的时间段</p></div></header>
                <div className="participation-choice-grid is-time">{TIME_OPTIONS.map((option) => <button key={option.value} className={timeSlot === option.value ? "is-selected" : ""} type="button" onClick={() => setTimeSlot(option.value)}><span>{timeSlot === option.value ? "✓" : "时"}</span><div><strong>{option.label}</strong><small>{option.note}</small></div></button>)}</div>
              </div>

              <div className="participation-form-section">
                <header><span>03</span><div><h3>饮食限制</h3><p>可以多选，只用于排除不合适的方案</p></div></header>
                <div className="participation-tag-list">{DIETARY_OPTIONS.map((option) => <button key={option} className={dietary.includes(option) ? "is-selected" : ""} type="button" onClick={() => toggleDietary(option)}>{dietary.includes(option) && <span>✓</span>}{option}</button>)}</div>
              </div>
            </>
          )}
        </main>

        <aside className="participation-context">
          <section><header><span>参与进度</span><strong>{participantCount}/4 人已完成</strong></header><div className="participation-progress"><i style={{ width: `${Math.min(100, participantCount * 25)}%` }} /></div><p>只显示是否完成，不公开成员的具体偏好。</p><div className="participation-avatars"><span>A</span><span>陈</span><span>林</span><span className={participantCount >= 4 ? "" : "is-pending"}>{participantCount >= 4 ? "王" : "…"}</span></div></section>
          <section><header><span>我的提交</span><strong>{submitted ? "已完成" : "尚未提交"}</strong></header><dl><div><dt>原始偏好</dt><dd>仅自己可见</dd></div><div><dt>候选方案</dt><dd>寝室成员可见</dd></div><div><dt>最终结果</dt><dd>寝室成员可见</dd></div></dl></section>
          <section className="participation-agent-card"><header><span>CA</span><div><small>场景 Agent</small><strong>负责聚合，不代替决定</strong></div></header><p>Agent 会根据全体成员提交生成2–3个候选方案，但最终选择仍由寝室成员投票和确认。</p><button type="button">了解 Agent 如何处理数据</button></section>
          <section className="participation-owner"><span>负责人</span><strong>Alice · 寝室成员</strong><p>最终结果需要寝室成员共同确认。</p></section>
        </aside>
      </div>}

      {!loading && !error && !submitted && <footer className="participation-actions"><p>{draftSaved ? "✓ 已在当前设备暂存" : "你的选择尚未提交"}</p><div><button type="button" onClick={() => setDraftSaved(true)}>保存稍后继续</button><button className="is-primary" type="button" onClick={handleSubmit} disabled={submitting || !budget || !timeSlot || dietary.length === 0}>{submitting ? "提交中…" : "提交我的偏好"}<span>→</span></button></div></footer>}
    </section>
  );
}

export default function DinnerPage() {
  return <AppShell requireAuth><DinnerContent /></AppShell>;
}
