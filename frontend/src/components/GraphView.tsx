import mermaid from "mermaid";
import { useEffect, useRef, useState } from "react";
import { TransformComponent, TransformWrapper } from "react-zoom-pan-pinch";
import { toErrorMessage } from "../errors";

interface GraphViewProps {
  mermaidDefinition: string;
  visitedNodes: Set<string>;
  pendingNodes: Set<string>;
}

let mermaidInitialized = false;

export function GraphView({ mermaidDefinition, visitedNodes, pendingNodes }: GraphViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState("");
  const [renderError, setRenderError] = useState<string | null>(null);

  useEffect(() => {
    if (!mermaidInitialized) {
      mermaid.initialize({ startOnLoad: false, theme: "neutral" });
      mermaidInitialized = true;
    }
  }, []);

  useEffect(() => {
    if (!mermaidDefinition) return;
    let cancelled = false;
    mermaid
      .render("langtest-graph", mermaidDefinition)
      .then(({ svg: rendered }) => {
        if (!cancelled) setSvg(rendered);
      })
      .catch((err) => {
        if (!cancelled) setRenderError(toErrorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [mermaidDefinition]);

  // Match by rendered label text rather than mermaid's internal element ids,
  // since those ids are sanitized/index-suffixed and not worth depending on.
  useEffect(() => {
    const nodes = containerRef.current?.querySelectorAll<SVGGElement>(".node");
    nodes?.forEach((node) => {
      const label = node.textContent?.trim() ?? "";
      node.classList.remove("lt-visited", "lt-pending");
      if (pendingNodes.has(label)) {
        node.classList.add("lt-pending");
      } else if (visitedNodes.has(label)) {
        node.classList.add("lt-visited");
      }
    });
  }, [svg, visitedNodes, pendingNodes]);

  if (renderError) {
    return <p className="app-error">Failed to render graph: {renderError}</p>;
  }

  if (!svg) {
    return <p className="empty-state">Loading graph topology…</p>;
  }

  return (
    <TransformWrapper minScale={0.3} maxScale={3} initialScale={1}>
      <TransformComponent wrapperClass="graph-transform-wrapper" contentClass="graph-transform-content">
        {/* eslint-disable-next-line react/no-danger -- trusted output from our own server's /graph endpoint */}
        <div ref={containerRef} className="graph-svg" dangerouslySetInnerHTML={{ __html: svg }} />
      </TransformComponent>
    </TransformWrapper>
  );
}
