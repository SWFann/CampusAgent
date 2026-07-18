"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/app/AppShell";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import {
  acceptContactRequest,
  deleteContact,
  listContactRequests,
  listContacts,
  rejectContactRequest,
  type ContactItem,
  type ContactRequestItem,
} from "@/lib/contacts";
import { createPrivateConversation } from "@/lib/conversations";

function ContactsContent() {
  const router = useRouter();
  const [contacts, setContacts] = useState<ContactItem[]>([]);
  const [incoming, setIncoming] = useState<ContactRequestItem[]>([]);
  const [outgoing, setOutgoing] = useState<ContactRequestItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [contactsResult, requestsResult] = await Promise.all([
        listContacts(),
        listContactRequests(),
      ]);
      if (contactsResult.success && contactsResult.data) {
        setContacts(contactsResult.data.contacts);
      }
      if (requestsResult.success && requestsResult.data) {
        setIncoming(requestsResult.data.incoming);
        setOutgoing(requestsResult.data.outgoing);
      }
      if (!contactsResult.success || !requestsResult.success) {
        setError(contactsResult.error?.message ?? requestsResult.error?.message ?? "加载联系人失败");
      }
    } catch {
      setError("网络错误");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const handleStartChat = async (userId: string) => {
    const result = await createPrivateConversation(userId);
    if (result.success && result.data) {
      router.push(`/conversations/${result.data.id}`);
    } else {
      setError(result.error?.message ?? "创建私聊失败");
    }
  };

  const handleAccept = async (requestId: string) => {
    await acceptContactRequest(requestId);
    await reload();
  };

  const handleReject = async (requestId: string) => {
    await rejectContactRequest(requestId);
    await reload();
  };

  const handleDelete = async (userId: string) => {
    await deleteContact(userId);
    await reload();
  };

  return (
    <div style={{ display: "grid", gap: "var(--space-lg)" }}>
      <h1 style={{ fontSize: "var(--font-size-xl)" }}>联系人</h1>
      {loading && <LoadingState message="正在加载联系人..." />}
      {error && <ErrorState message={error} />}

      <section className="card">
        <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "var(--space-md)" }}>好友</h2>
        {!loading && contacts.length === 0 && (
          <EmptyState title="暂无好友" description="到校园目录搜索用户并发送好友申请。" />
        )}
        {contacts.length > 0 && (
          <div style={{ display: "grid", gap: "var(--space-sm)" }}>
            {contacts.map((contact) => (
              <div key={contact.user.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "var(--space-sm)", borderRadius: "var(--radius-md)", background: "var(--color-surface-hover)" }}>
                <strong>{contact.user.display_name}</strong>
                <div style={{ display: "flex", gap: "var(--space-xs)" }}>
                  <button className="btn btn-sm btn-primary" onClick={() => handleStartChat(contact.user.id)}>发消息</button>
                  <button className="btn btn-sm" onClick={() => handleDelete(contact.user.id)}>删除</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="card">
        <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "var(--space-md)" }}>收到的好友申请</h2>
        {!loading && incoming.length === 0 && <EmptyState title="暂无待处理申请" />}
        {incoming.length > 0 && (
          <div style={{ display: "grid", gap: "var(--space-sm)" }}>
            {incoming.map((request) => (
              <div key={request.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "var(--space-sm)", borderRadius: "var(--radius-md)", background: "var(--color-surface-hover)" }}>
                <span>{request.requester.display_name}</span>
                <div style={{ display: "flex", gap: "var(--space-xs)" }}>
                  <button className="btn btn-sm btn-primary" onClick={() => handleAccept(request.id)}>接受</button>
                  <button className="btn btn-sm" onClick={() => handleReject(request.id)}>拒绝</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="card">
        <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "var(--space-md)" }}>已发送申请</h2>
        {!loading && outgoing.length === 0 && <EmptyState title="暂无已发送申请" />}
        {outgoing.length > 0 && (
          <div style={{ display: "grid", gap: "var(--space-sm)" }}>
            {outgoing.map((request) => (
              <div key={request.id} style={{ display: "flex", justifyContent: "space-between", padding: "var(--space-sm)", borderRadius: "var(--radius-md)", background: "var(--color-surface-hover)" }}>
                <span>{request.addressee.display_name}</span>
                <span style={{ color: "var(--color-text-muted)" }}>等待对方处理</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default function ContactsPage() {
  return (
    <AppShell requireAuth>
      <ContactsContent />
    </AppShell>
  );
}
