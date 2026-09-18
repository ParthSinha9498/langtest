import { useEffect, useState } from "react";
import { toErrorMessage } from "../errors";
import type { CheckpointSnapshot } from "../types";

interface ForkEditorProps {
  checkpoint: CheckpointSnapshot | null;
  onFork: (editedState: Record<string, unknown>) => Promise<void>;
}

export function ForkEditor({ checkpoint, onFork }: ForkEditorProps) {
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setText(checkpoint ? JSON.stringify(checkpoint.values, null, 2) : "");
    setError(null);
  }, [checkpoint]);

  if (!checkpoint) {
    return <p className="empty-state">Select a checkpoint to edit and fork from it.</p>;
  }

  async function handleSubmit() {
    let editedState: Record<string, unknown>;
    try {
      editedState = JSON.parse(text) as Record<string, unknown>;
    } catch {
      setError("Not valid JSON.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await onFork(editedState);
    } catch (err) {
      setError(toErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fork-editor">
      <p>
        Forking from checkpoint <code>{checkpoint.checkpoint_id}</code> (step {checkpoint.step}). Only state
        values are editable here — routing (which node runs next) is not affected by this edit.
      </p>
      <textarea value={text} onChange={(event) => setText(event.target.value)} rows={16} spellCheck={false} />
      {error && <p className="fork-error">{error}</p>}
      <button type="button" onClick={handleSubmit} disabled={submitting}>
        {submitting ? "Forking…" : "Fork from here"}
      </button>
    </div>
  );
}
