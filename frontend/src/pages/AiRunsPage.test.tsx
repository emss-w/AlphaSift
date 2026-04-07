import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { AiRunsPage } from "./AiRunsPage";
import { createMockApi } from "../test/mockApi";

describe("AiRunsPage", () => {
  it("renders runs from mocked API responses", async () => {
    const api = createMockApi();
    render(<AiRunsPage api={api} />);

    expect(await screen.findByRole("cell", { name: "ai-run-1" })).toBeInTheDocument();
    expect(await screen.findByText("Trend continuation after pullback")).toBeInTheDocument();
  });

  it("submits hypothesis form successfully", async () => {
    const createdRun = {
      ...(await createMockApi().getAiRun("ai-run-1")),
      id: "ai-run-created-h",
    };
    const createHypothesis = vi.fn().mockResolvedValue(createdRun);
    const listAiRuns = vi.fn().mockResolvedValueOnce([]).mockResolvedValueOnce([createdRun]);
    const api = createMockApi({
      listAiRuns,
      createHypothesis,
      getAiRun: vi.fn().mockResolvedValue(createdRun),
    });

    render(<AiRunsPage api={api} />);
    await screen.findByText("No AI runs yet.");

    const user = userEvent.setup();
    const researchInputs = screen.getAllByLabelText("Research Objective");
    await user.type(researchInputs[0], "Test BTC pullback hypothesis");
    await user.click(screen.getByRole("button", { name: "Generate Hypothesis" }));

    await waitFor(() => expect(createHypothesis).toHaveBeenCalledTimes(1));
    expect(createHypothesis).toHaveBeenCalledWith(
      expect.objectContaining({
        research_objective: "Test BTC pullback hypothesis",
      }),
    );
  });

  it("submits strategy draft form successfully", async () => {
    const createdRun = {
      ...(await createMockApi().getAiRun("ai-run-1")),
      id: "ai-run-created-s",
      run_type: "strategy_draft" as const,
      strategy_draft: {
        draft_summary: "Draft summary",
        code_artifact: "class Strategy: pass",
        assumptions: [],
        missing_information: [],
        suggested_tests: [],
        notes: null,
      },
      hypothesis: null,
    };
    const createStrategyDraft = vi.fn().mockResolvedValue(createdRun);
    const api = createMockApi({
      createStrategyDraft,
      getAiRun: vi.fn().mockResolvedValue(createdRun),
    });

    render(<AiRunsPage api={api} />);
    await screen.findByRole("cell", { name: "ai-run-1" });

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Strategy Prompt (optional)"), "Draft SMA strategy");
    await user.click(screen.getByRole("button", { name: "Generate Strategy Draft" }));

    await waitFor(() => expect(createStrategyDraft).toHaveBeenCalledTimes(1));
    expect(createStrategyDraft).toHaveBeenCalledWith(
      expect.objectContaining({
        prompt: "Draft SMA strategy",
      }),
    );
  });

  it("submits sandbox code report form successfully", async () => {
    const createdRun = {
      ...(await createMockApi().getAiRun("ai-run-1")),
      id: "ai-run-created-c",
      run_type: "code_report" as const,
      strategy_draft: null,
      backtest_report: null,
      code_report: {
        title: "Sandbox Candle Counter",
        summary: "Counts rows.",
        report: { rows: 100 },
        execution: {
          success: true,
          exit_code: 0,
          timed_out: false,
          duration_seconds: 0.1,
          stdout_tail: "ok",
          stderr_tail: "",
        },
        attempts: [
          {
            attempt: 1,
            repaired: false,
            failure_reason: null,
            execution: {
              success: true,
              exit_code: 0,
              timed_out: false,
              duration_seconds: 0.1,
              stdout_tail: "ok",
              stderr_tail: "",
            },
          },
        ],
        generated_at: "2026-04-06T00:02:00Z",
      },
      hypothesis: null,
    };
    const createCodeReport = vi.fn().mockResolvedValue(createdRun);
    const api = createMockApi({
      createCodeReport,
      getAiRun: vi.fn().mockResolvedValue(createdRun),
    });

    render(<AiRunsPage api={api} />);
    await screen.findByRole("cell", { name: "ai-run-1" });

    const user = userEvent.setup();
    const researchInputs = screen.getAllByLabelText("Research Objective");
    await user.type(researchInputs[1], "Count candles");
    await user.click(screen.getByRole("button", { name: "Run Sandbox Code" }));

    await waitFor(() => expect(createCodeReport).toHaveBeenCalledTimes(1));
    expect(createCodeReport).toHaveBeenCalledWith(
      expect.objectContaining({
        research_objective: "Count candles",
      }),
    );
  });

  it("shows loading and error states", async () => {
    let resolveRuns: ((value: []) => void) | null = null;
    const listAiRuns = vi.fn().mockImplementation(
      () =>
        new Promise<[]>((resolve) => {
          resolveRuns = resolve;
        }),
    );
    const api = createMockApi({
      listAiRuns,
    });

    const mounted = render(<AiRunsPage api={api} />);
    expect(screen.getAllByText("Loading...").length).toBeGreaterThan(0);
    resolveRuns?.([]);
    await screen.findByText("No AI runs yet.");
    mounted.unmount();

    const failingApi = createMockApi({
      listAiRuns: vi.fn().mockRejectedValue(new Error("ai list failed")),
    });
    render(<AiRunsPage api={failingApi} />);
    const alerts = await screen.findAllByRole("alert");
    expect(alerts.map((node) => node.textContent ?? "").join(" ")).toContain("ai list failed");
  });
});
