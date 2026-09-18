import type { CheckpointSnapshot } from "../types";

interface HistoryTimelineProps {
  history: CheckpointSnapshot[];
  selectedCheckpointId: string | null;
  onSelect: (checkpoint: CheckpointSnapshot) => void;
}

export function HistoryTimeline({ history, selectedCheckpointId, onSelect }: HistoryTimelineProps) {
  if (history.length === 0) {
    return <p className="empty-state">Select a thread to see its checkpoint history.</p>;
  }

  return (
    <ol className="history-timeline">
      {history.map((checkpoint) => (
        <li key={checkpoint.checkpoint_id}>
          <button
            type="button"
            className={checkpoint.checkpoint_id === selectedCheckpointId ? "selected" : ""}
            onClick={() => onSelect(checkpoint)}
          >
            <span className="step">step {checkpoint.step}</span>
            <span className="produced-by">
              {checkpoint.produced_by_nodes.length > 0 ? checkpoint.produced_by_nodes.join(", ") : "(start)"}
            </span>
            {checkpoint.next.length > 0 && (
              <span className="pending">next: {checkpoint.next.join(", ")}</span>
            )}
          </button>
        </li>
      ))}
    </ol>
  );
}
