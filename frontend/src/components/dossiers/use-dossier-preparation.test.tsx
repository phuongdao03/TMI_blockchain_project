import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { useState } from "react";
import Link from "next/link";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/client";
import type { DossierPreparationPayload } from "@/lib/api/types";
import { useDossierPreparation } from "./use-dossier-preparation";
import { broadcastAuthSessionChange } from "@/lib/auth/session-sync";
import { clearPreparationBackup } from "./preparation-recovery-storage";

const api = vi.hoisted(() => ({
  getPreparation: vi.fn(),
  savePreparation: vi.fn(),
}));
vi.mock("@/lib/api/client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/api/client")>(
      "@/lib/api/client",
    );
  return { ApiError: actual.ApiError, dossierApi: api };
});
const empty: DossierPreparationPayload = {
  dossierTypeVersionId: null,
  step: 0,
  values: { title: "", summary: "", visibility: "PRIVATE" },
  formData: {},
};
const payload = (title: string): DossierPreparationPayload => ({
  ...empty,
  values: { ...empty.values, title },
});
function Harness({ owner = "owner-1" }: { owner?: string }) {
  const [value, setValue] = useState(empty);
  const recovery = useDossierPreparation({
    userId: owner,
    value,
    onRestore: setValue,
    delay: 10,
  });
  if (!recovery.ready) return <p>Loading recovery</p>;
  return (
    <>
      <input
        aria-label="Title"
        value={value.values.title}
        onChange={(event) => setValue(payload(event.target.value))}
      />
      <output>
        {recovery.conflict
          ? "conflict"
          : recovery.saving
            ? "saving"
            : recovery.dirty
              ? "unsaved"
              : "saved"}
      </output>
      <button onClick={recovery.keepLocal}>Keep local</button>
      <button onClick={recovery.useServer}>Use server</button>
      <button onClick={() => void recovery.flush()}>Retry</button>
      <Link href="/works">Leave preparation</Link>
      <span>{recovery.error}</span>
    </>
  );
}
beforeEach(() => {
  clearPreparationBackup("owner-1");
  clearPreparationBackup("owner-2");
  sessionStorage.clear();
  api.getPreparation.mockReset();
  api.savePreparation.mockReset();
  api.getPreparation.mockResolvedValue({
    revision: 0,
    payload: null,
    updatedAt: null,
    ownerUserId: "owner-1",
  });
});
afterEach(() => vi.restoreAllMocks());

it("does not expose another account's preparation returned by a changed session", async () => {
  api.getPreparation.mockResolvedValue({
    revision: 1,
    payload: payload("Other account private title"),
    updatedAt: null,
    ownerUserId: "owner-2",
  });
  render(<Harness />);
  await waitFor(() => expect(api.getPreparation).toHaveBeenCalledTimes(1));
  await act(async () => {});
  expect(screen.queryByDisplayValue("Other account private title")).toBeNull();
  expect(screen.queryByLabelText("Title")).toBeNull();
  expect(api.savePreparation).not.toHaveBeenCalled();
});

it("restores a confirmed preparation on a new mount without overwriting it", async () => {
  api.getPreparation.mockResolvedValue({
    revision: 3,
    payload: payload("Recovered title"),
    updatedAt: null,
    ownerUserId: "owner-1",
  });
  render(<Harness />);
  expect(await screen.findByDisplayValue("Recovered title")).toBeDefined();
  expect(screen.getByText("saved")).toBeDefined();
  expect(api.savePreparation).not.toHaveBeenCalled();
});

it("serializes saves and retains edits made while a request is in flight", async () => {
  let finish!: (result: unknown) => void;
  api.savePreparation
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    )
    .mockImplementationOnce(async (_owner, revision, next) => ({
      revision: revision + 1,
      payload: next,
      updatedAt: null,
      ownerUserId: "owner-1",
    }));
  render(<Harness />);
  fireEvent.change(await screen.findByLabelText("Title"), {
    target: { value: "First" },
  });
  await waitFor(() => expect(api.savePreparation).toHaveBeenCalledTimes(1));
  fireEvent.change(screen.getByLabelText("Title"), {
    target: { value: "Latest" },
  });
  expect(screen.queryByText("saved")).toBeNull();
  await act(async () =>
    finish({
      revision: 1,
      payload: payload("First"),
      updatedAt: null,
      ownerUserId: "owner-1",
    }),
  );
  await waitFor(() => expect(screen.getByText("saved")).toBeDefined());
  expect(api.savePreparation).toHaveBeenLastCalledWith(
    "owner-1",
    1,
    payload("Latest"),
  );
});

it("retains failed input across a reload and retries only the account's copy", async () => {
  api.savePreparation.mockRejectedValue(new Error("offline"));
  const view = render(<Harness />);
  fireEvent.change(await screen.findByLabelText("Title"), {
    target: { value: "Offline input" },
  });
  await waitFor(() => expect(screen.getByText("unsaved")).toBeDefined());
  await waitFor(() => expect(api.savePreparation).toHaveBeenCalled());
  view.unmount();
  api.savePreparation.mockImplementation(async (_owner, revision, next) => ({
    revision: revision + 1,
    payload: next,
    updatedAt: null,
    ownerUserId: "owner-1",
  }));
  render(<Harness />);
  expect(await screen.findByDisplayValue("Offline input")).toBeDefined();
  await waitFor(() => expect(screen.getByText("saved")).toBeDefined());
});

it("requires an explicit choice before overwriting another device", async () => {
  api.savePreparation.mockRejectedValueOnce(
    new ApiError("conflict", "DOSSIER_INVALID_STATE", 409),
  );
  render(<Harness />);
  fireEvent.change(await screen.findByLabelText("Title"), {
    target: { value: "My edit" },
  });
  api.getPreparation.mockResolvedValue({
    revision: 2,
    payload: payload("Other device"),
    updatedAt: null,
    ownerUserId: "owner-1",
  });
  await screen.findByText("conflict");
  expect(api.savePreparation).toHaveBeenCalledTimes(1);
  expect(screen.getByDisplayValue("My edit")).toBeDefined();
  api.savePreparation.mockImplementation(async (_owner, revision, next) => ({
    revision: revision + 1,
    payload: next,
    updatedAt: null,
    ownerUserId: "owner-1",
  }));
  fireEvent.click(screen.getByText("Keep local"));
  await waitFor(() => expect(screen.getByText("saved")).toBeDefined());
  expect(api.savePreparation).toHaveBeenLastCalledWith(
    "owner-1",
    2,
    payload("My edit"),
  );
});

it("retains a conflict through refresh rather than overwriting the server", async () => {
  api.savePreparation.mockRejectedValue(
    new ApiError("conflict", "DOSSIER_PREPARATION_CONFLICT", 409),
  );
  const view = render(<Harness />);
  fireEvent.change(await screen.findByLabelText("Title"), {
    target: { value: "Local copy" },
  });
  api.getPreparation.mockResolvedValue({
    revision: 2,
    payload: payload("Server copy"),
    updatedAt: null,
    ownerUserId: "owner-1",
  });
  await screen.findByText("conflict");
  view.unmount();
  const previousCalls = api.savePreparation.mock.calls.length;
  render(<Harness />);
  await screen.findByText("conflict");
  expect(screen.getByDisplayValue("Local copy")).toBeDefined();
  expect(api.savePreparation).toHaveBeenCalledTimes(previousCalls);
  fireEvent.click(screen.getByText("Use server"));
  expect(screen.getByDisplayValue("Server copy")).toBeDefined();
  expect(screen.getByText("saved")).toBeDefined();
});

it("does not apply an old account's in-flight response to the next account", async () => {
  let finish!: (result: unknown) => void;
  api.savePreparation.mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const view = render(<Harness />);
  fireEvent.change(await screen.findByLabelText("Title"), {
    target: { value: "First account private draft" },
  });
  await waitFor(() => expect(api.savePreparation).toHaveBeenCalledTimes(1));
  api.getPreparation.mockResolvedValue({
    revision: 7,
    payload: payload("Second account draft"),
    updatedAt: null,
    ownerUserId: "owner-2",
  });
  view.rerender(<Harness owner="owner-2" />);
  expect(screen.queryByDisplayValue("First account private draft")).toBeNull();
  await screen.findByDisplayValue("Second account draft");
  await act(async () =>
    finish({
      revision: 1,
      payload: payload("First account private draft"),
      updatedAt: null,
      ownerUserId: "owner-1",
    }),
  );
  expect(screen.getByDisplayValue("Second account draft")).toBeDefined();
  expect(screen.getByText("saved")).toBeDefined();
  expect(
    api.savePreparation.mock.calls.every(([owner]) => owner === "owner-1"),
  ).toBe(true);
});

it("warns on unsafe navigation and recovers a draft across remounts without browser storage", async () => {
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw new Error("blocked");
  });
  api.savePreparation.mockRejectedValue(new Error("offline"));
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  const view = render(<Harness />);
  fireEvent.change(await screen.findByLabelText("Title"), {
    target: { value: "Keep on back" },
  });
  await screen.findByText(/Chưa đồng bộ được/);
  expect(
    fireEvent.click(screen.getByRole("link", { name: "Leave preparation" })),
  ).toBe(false);
  expect(confirm).toHaveBeenCalledTimes(1);
  view.unmount();
  render(<Harness />);
  await screen.findByDisplayValue("Keep on back");
});

it("does not warn for internal navigation when a local draft backup exists", async () => {
  api.savePreparation.mockRejectedValue(new Error("offline"));
  const confirm = vi.spyOn(window, "confirm");
  render(<Harness />);
  fireEvent.change(await screen.findByLabelText("Title"), {
    target: { value: "Local recovery" },
  });
  await screen.findByText(/Chưa đồng bộ được/);
  const link = screen.getByRole("link", { name: "Leave preparation" });
  link.addEventListener("click", (event) => event.preventDefault(), {
    once: true,
  });
  fireEvent.click(link);
  expect(confirm).not.toHaveBeenCalled();
});

it("can save to the server when browser recovery storage is unavailable", async () => {
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw new Error("storage unavailable");
  });
  api.savePreparation.mockImplementation(async (_owner, revision, next) => ({
    revision: revision + 1,
    payload: next,
    updatedAt: null,
    ownerUserId: "owner-1",
  }));
  render(<Harness />);
  fireEvent.change(await screen.findByLabelText("Title"), {
    target: { value: "Server protected" },
  });
  await waitFor(() => expect(api.savePreparation).toHaveBeenCalledTimes(1));
  await screen.findByText("saved");
  expect(screen.getByDisplayValue("Server protected")).toBeDefined();
});

it("clears tab recovery and stops old writes on logout", async () => {
  let finish!: (result: unknown) => void;
  api.savePreparation.mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  render(<Harness />);
  fireEvent.change(await screen.findByLabelText("Title"), {
    target: { value: "Unsaved account input" },
  });
  await waitFor(() => expect(api.savePreparation).toHaveBeenCalledTimes(1));
  expect(
    sessionStorage.getItem("thv:dossier-preparation:owner-1"),
  ).not.toBeNull();
  act(() => broadcastAuthSessionChange());
  expect(sessionStorage.getItem("thv:dossier-preparation:owner-1")).toBeNull();
  await act(async () =>
    finish({
      revision: 1,
      payload: payload("Unsaved account input"),
      updatedAt: null,
      ownerUserId: "owner-1",
    }),
  );
  expect(sessionStorage.getItem("thv:dossier-preparation:owner-1")).toBeNull();
  expect(api.savePreparation).toHaveBeenCalledTimes(1);
});
