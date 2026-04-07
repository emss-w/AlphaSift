import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { ExperimentsPage } from "./ExperimentsPage";
import { createMockApi } from "../test/mockApi";

describe("ExperimentsPage", () => {
  it("shows loading and error states", async () => {
    let resolveList: ((value: []) => void) | null = null;
    const listExperiments = vi.fn().mockImplementation(
      () =>
        new Promise<[]>((resolve) => {
          resolveList = resolve;
        }),
    );
    const api = createMockApi({
      listExperiments,
    });

    const mounted = render(<ExperimentsPage api={api} />);

    expect(screen.getByText("Loading...")).toBeInTheDocument();
    resolveList?.([]);
    await screen.findByText("No experiment runs yet.");
    mounted.unmount();

    const failingApi = createMockApi({
      listExperiments: vi.fn().mockRejectedValue(new Error("boom")),
    });
    render(<ExperimentsPage api={failingApi} />);
    const alerts = await screen.findAllByRole("alert");
    expect(alerts.map((node) => node.textContent ?? "").join(" ")).toContain("boom");
  });

  it("submits experiment form successfully", async () => {
    const createdRun = {
      ...(await createMockApi().getExperiment("run-1")),
      id: "run-new",
    };
    const runSmaExperiment = vi.fn().mockResolvedValue(createdRun);
    const listExperiments = vi
      .fn()
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([createdRun]);

    const api = createMockApi({
      listExperiments,
      runSmaExperiment,
      getExperiment: vi.fn().mockResolvedValue(createdRun),
    });

    render(<ExperimentsPage api={api} />);
    await screen.findByText("No experiment runs yet.");

    const user = userEvent.setup();
    await user.clear(screen.getByLabelText("short values"));
    await user.type(screen.getByLabelText("short values"), "3,7");
    await user.clear(screen.getByLabelText("long values"));
    await user.type(screen.getByLabelText("long values"), "20,40");
    await user.click(screen.getByRole("button", { name: "Run Experiment" }));

    await waitFor(() => expect(runSmaExperiment).toHaveBeenCalledTimes(1));
    expect(runSmaExperiment).toHaveBeenCalledWith(
      expect.objectContaining({
        pair: "BTC/USD",
        interval: 60,
        short_windows: [3, 7],
        long_windows: [20, 40],
      }),
    );
  });
});
