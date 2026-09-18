export interface ThreadSummary {
  thread_id: string;
  checkpoint_count: number;
  latest_checkpoint_id: string;
  updated_at: string;
}

export interface CheckpointSnapshot {
  checkpoint_id: string;
  parent_checkpoint_id: string | null;
  step: number;
  created_at: string;
  source: string;
  values: Record<string, unknown>;
  next: string[];
  produced_by_nodes: string[];
}

export interface ForkResponse {
  thread_id: string;
}

export interface GraphTopology {
  mermaid: string;
}
