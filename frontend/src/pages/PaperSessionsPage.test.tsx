import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { PaperSessionsPage } from "./PaperSessionsPage";
import { createMockApi } from "../test/mockApi";

describe("PaperSessionsPage", () => {
  it("submits paper session form successfully", async () => {
    const createdSession = {
      ...(await createMockApi().getPaperSession("session-1")),
      id: "session-new",
    };
    const startPaperSession = vi.fn().mockResolvedValue(createdSession);
    const listPaperSessions = vi
      .fn()
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([createdSession]);

    const api = createMockApi({
      listPaperSessions,
      startPaperSession,
      getPaperSession: vi.fn().mockResolvedValue(createdSession),
    });

    render(<PaperSessionsPage api={api} />);
    await screen.findByText("No paper sessions yet.");

    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText("Strategy"), "sma_cross");
    await user.clear(screen.getByLabelText("Short Window"));
    await user.type(screen.getByLabelText("Short Window"), "8");
    await user.clear(screen.getByLabelText("Long Window"));
    await user.type(screen.getByLabelText("Long Window"), "32");
    await user.click(screen.getByRole("button", { name: "Start Session" }));

    await waitFor(() => expect(startPaperSession).toHaveBeenCalledTimes(1));
    expect(startPaperSession).toHaveBeenCalledWith(
      expect.objectContaining({
        pair: "BTC/USD",
        interval: 60,
        strategy_id: "sma_cross",
        short_window: 8,
        long_window: 32,
      }),
    );
  });
});
