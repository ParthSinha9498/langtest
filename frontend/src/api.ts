import type { CheckpointSnapshot, ForkResponse, GraphTopology, ThreadSummary } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8010";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${init?.method ?? "GET"} ${path} failed (${response.status}): ${body}`);
  }
  return response.json() as Promise<T>;
}

export function listThreads(): Promise<ThreadSummary[]> {
  return request<ThreadSummary[]>("/threads");
}

export function getThreadHistory(threadId: string): Promise<CheckpointSnapshot[]> {
  return request<CheckpointSnapshot[]>(`/threads/${encodeURIComponent(threadId)}/history`);
}

export function getGraphTopology(): Promise<GraphTopology> {
  return request<GraphTopology>("/graph");
}

export function forkThread(
  threadId: string,
  checkpointId: string,
  editedState: Record<string, unknown>,
): Promise<ForkResponse> {
  return request<ForkResponse>("/fork", {
    method: "POST",
    body: JSON.stringify({
      thread_id: threadId,
      checkpoint_id: checkpointId,
      edited_state: editedState,
    }),
  });
}
