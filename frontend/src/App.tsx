import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { forkThread, getGraphTopology, getThreadHistory, listThreads } from "./api";
import { ForkEditor } from "./components/ForkEditor";
import { GraphView } from "./components/GraphView";
import { HistoryTimeline } from "./components/HistoryTimeline";
import { ThreadList } from "./components/ThreadList";
import { toErrorMessage } from "./errors";
import type { CheckpointSnapshot, ThreadSummary } from "./types";

export function App() {
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [mermaidDefinition, setMermaidDefinition] = useState("");
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
  const [history, setHistory] = useState<CheckpointSnapshot[]>([]);
  const [selectedCheckpoint, setSelectedCheckpoint] = useState<CheckpointSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Tracks the most recently *requested* thread, so a slow response for a
  // thread the user has since navigated away from doesn't overwrite what's
  // currently showing.
  const latestRequestedThreadId = useRef<string | null>(null);

  const refreshThreads = useCallback(async () => {
    try {
      setThreads(await listThreads());
    } catch (err) {
      setError(toErrorMessage(err));
    }
  }, []);

  useEffect(() => {
    refreshThreads();
    getGraphTopology()
      .then((topology) => setMermaidDefinition(topology.mermaid))
      .catch((err) => setError(toErrorMessage(err)));
  }, [refreshThreads]);

  const selectThread = useCallback(async (threadId: string) => {
    latestRequestedThreadId.current = threadId;
    setSelectedThreadId(threadId);
    setSelectedCheckpoint(null);
    setHistory([]);
    try {
      const result = await getThreadHistory(threadId);
      if (latestRequestedThreadId.current === threadId) {
        setHistory(result);
      }
    } catch (err) {
      if (latestRequestedThreadId.current === threadId) {
        setError(toErrorMessage(err));
      }
    }
  }, []);

  const handleFork = useCallback(
    async (editedState: Record<string, unknown>) => {
      if (!selectedThreadId || !selectedCheckpoint) return;
      const requestedThreadBeforeFork = latestRequestedThreadId.current;
      const result = await forkThread(selectedThreadId, selectedCheckpoint.checkpoint_id, editedState);
      await refreshThreads();
      // Only jump to the new thread if the user hasn't since selected a
      // different one while the fork was in flight — otherwise it's still
      // in the (refreshed) thread list for them to open manually.
      if (latestRequestedThreadId.current === requestedThreadBeforeFork) {
        await selectThread(result.thread_id);
      }
    },
    [selectedThreadId, selectedCheckpoint, refreshThreads, selectThread],
  );

  const visitedNodes = useMemo(() => new Set(history.flatMap((c) => c.produced_by_nodes)), [history]);
  const pendingNodes = useMemo(
    () => new Set(history.length > 0 ? history[history.length - 1].next : []),
    [history],
  );

  return (
    <div className="app">
      <header className="app-header">
        <h1>LangTest</h1>
        {error && <p className="app-error">{error}</p>}
      </header>
      <div className="app-body">
        <aside className="sidebar">
          <h2>Threads</h2>
          <ThreadList threads={threads} selectedThreadId={selectedThreadId} onSelect={selectThread} />
        </aside>
        <main className="main-panel">
          <section className="graph-panel">
            <GraphView
              mermaidDefinition={mermaidDefinition}
              visitedNodes={visitedNodes}
              pendingNodes={pendingNodes}
            />
          </section>
          <section className="detail-panel">
            <div className="timeline-panel">
              <h2>History</h2>
              <HistoryTimeline
                history={history}
                selectedCheckpointId={selectedCheckpoint?.checkpoint_id ?? null}
                onSelect={setSelectedCheckpoint}
              />
            </div>
            <div className="fork-panel">
              <h2>Fork &amp; edit state</h2>
              <ForkEditor checkpoint={selectedCheckpoint} onFork={handleFork} />
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
