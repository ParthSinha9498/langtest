import type { ThreadSummary } from "../types";

interface ThreadListProps {
  threads: ThreadSummary[];
  selectedThreadId: string | null;
  onSelect: (threadId: string) => void;
}

export function ThreadList({ threads, selectedThreadId, onSelect }: ThreadListProps) {
  if (threads.length === 0) {
    return <p className="empty-state">No threads yet — run the example app to generate some.</p>;
  }

  return (
    <ul className="thread-list">
      {threads.map((thread) => (
        <li key={thread.thread_id}>
          <button
            type="button"
            className={thread.thread_id === selectedThreadId ? "selected" : ""}
            onClick={() => onSelect(thread.thread_id)}
          >
            <span className="thread-id">{thread.thread_id}</span>
            <span className="thread-meta">
              {thread.checkpoint_count} checkpoints · {new Date(thread.updated_at).toLocaleString()}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
