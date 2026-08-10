import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AsyncState } from "./AsyncState";

describe("AsyncState", () => {
  it("announces an initial load", () => {
    render(<AsyncState loading loadingMessage="Loading interviews" error={null}>ready</AsyncState>);
    expect(screen.getByRole("status")).toHaveTextContent("Loading interviews");
    expect(screen.queryByText("ready")).not.toBeInTheDocument();
  });

  it("shows an actionable error", async () => {
    const retry = vi.fn();
    render(<AsyncState loading={false} error="Interviews could not be loaded" onRetry={retry}>ready</AsyncState>);
    expect(screen.getByRole("alert")).toHaveTextContent("Interviews could not be loaded");
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(retry).toHaveBeenCalledOnce();
  });

  it("shows a non-actionable error when retry is unavailable", () => {
    render(<AsyncState loading={false} error="Access denied">ready</AsyncState>);
    expect(screen.getByRole("alert")).toHaveTextContent("Access denied");
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("renders its content after loading succeeds", () => {
    render(<AsyncState loading={false} error={null}>ready</AsyncState>);
    expect(screen.getByText("ready")).toBeVisible();
  });
});
