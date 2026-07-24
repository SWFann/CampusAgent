import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import ConversationsPage from "@/app/conversations/page";
import { createGroupConversation, listConversations } from "@/lib/conversations";
import { listContacts } from "@/lib/contacts";
import { searchDirectory } from "@/lib/directory";

jest.mock("@/lib/conversations", () => ({
  listConversations: jest.fn(),
  createPrivateConversation: jest.fn(),
  createGroupConversation: jest.fn(),
}));

jest.mock("@/lib/contacts", () => ({
  listContacts: jest.fn(),
}));

jest.mock("@/lib/directory", () => ({
  searchDirectory: jest.fn(),
}));

jest.mock("@/components/app/AppShell", () => ({
  AppShell: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

describe("ConversationsPage group creation", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (listConversations as jest.Mock).mockResolvedValue({
      success: true,
      data: { conversations: [], total: 0, page: 1, page_size: 20 },
    });
    (listContacts as jest.Mock).mockResolvedValue({
      success: true,
      data: { contacts: [], total: 0 },
    });
    (searchDirectory as jest.Mock).mockResolvedValue({
      success: true,
      data: {
        users: [
          {
            id: "user-alice",
            display_name: "Alice Chen",
            avatar_url: null,
            profile_visibility: "PUBLIC",
          },
        ],
        organizations: [],
        total: 1,
        query: "Alice",
        search_type: "users",
      },
    });
    (createGroupConversation as jest.Mock).mockResolvedValue({
      success: true,
      data: {
        id: "conversation-1",
        type: "GROUP",
        title: "测试群聊",
        organization_id: null,
        created_by: "me",
        status: "ACTIVE",
        created_at: "2026-07-19T00:00:00Z",
        updated_at: "2026-07-19T00:00:00Z",
      },
    });
  });

  it("creates a group chat from searched and selected users", async () => {
    const user = userEvent.setup();
    render(<ConversationsPage />);

    await user.click(await screen.findByText("发起沟通"));
    await user.click(screen.getByText("创建群聊"));
    await user.type(screen.getByLabelText("群聊标题（可选）"), "测试群聊");
    await user.type(screen.getByLabelText("搜索成员"), "Alice");
    await user.click(screen.getByRole("button", { name: "搜索" }));
    await user.click(await screen.findByRole("button", { name: "添加 Alice Chen" }));

    expect(screen.getByText("Alice Chen")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "确认创建" }));

    await waitFor(() => {
      expect(createGroupConversation).toHaveBeenCalledWith({
        title: "测试群聊",
        participant_user_ids: ["user-alice"],
      });
    });
  });
});
