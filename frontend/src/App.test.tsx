import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import App from "./App";
import { createMockApi } from "./test/mockApi";

describe("App", () => {
  it("renders core views with mocked API responses", async () => {
    const api = createMockApi();
    const user = userEvent.setup();

    render(<App api={api} />);

    expect(await screen.findByText("AlphaSift Local Control Panel")).toBeInTheDocument();
    expect(await screen.findByText("Recent Experiment Runs")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Strategies" }));
    expect(await screen.findByRole("cell", { name: "buy_and_hold" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Experiments" }));
    expect(await screen.findByRole("cell", { name: "run-1" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Paper Sessions" }));
    expect(await screen.findByRole("cell", { name: "session-1" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Jobs" }));
    expect(await screen.findByRole("cell", { name: "job-1" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Artifacts" }));
    expect(await screen.findByRole("cell", { name: "artifact-1" })).toBeInTheDocument();
  });

  it("shows backend unavailable state when health check fails", async () => {
    const api = createMockApi({
      getHealth: vi.fn().mockRejectedValue(new Error("connection refused")),
    });

    render(<App api={api} />);

    expect(await screen.findByRole("alert")).toHaveTextContent("connection refused");
  });
});
