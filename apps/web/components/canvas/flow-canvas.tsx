"use client";

import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useCallback, useEffect, useRef } from "react";

import { useCanvasStore } from "@/lib/canvas-store";
import type { NodeType } from "@/lib/flowspec";

import { AgentQNodeView } from "./agentq-node";

const nodeTypes: NodeTypes = { agentq: AgentQNodeView };

function CanvasInner() {
  const nodes = useCanvasStore((s) => s.nodes);
  const edges = useCanvasStore((s) => s.edges);
  const onNodesChange = useCanvasStore((s) => s.onNodesChange);
  const onEdgesChange = useCanvasStore((s) => s.onEdgesChange);
  const onConnect = useCanvasStore((s) => s.onConnect);
  const selectNode = useCanvasStore((s) => s.selectNode);
  const addNode = useCanvasStore((s) => s.addNode);
  const loadToken = useCanvasStore((s) => s.loadToken);
  const beginHistoryCheckpoint = useCanvasStore((s) => s.beginHistoryCheckpoint);

  const wrapperRef = useRef<HTMLDivElement>(null);
  const { screenToFlowPosition, fitView } = useReactFlow();

  // Fit the viewport once per `loadFlow` call (opening a saved flow) - never on every
  // incremental drag/drop, and never on a genuinely empty canvas (fitView degenerates to
  // max zoom with zero nodes, which is how this bug was first found).
  useEffect(() => {
    if (loadToken === 0 || nodes.length === 0) return;
    const raf = requestAnimationFrame(() => fitView({ padding: 0.2, maxZoom: 1, duration: 200 }));
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadToken]);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const type = event.dataTransfer.getData("application/agentq-node-type") as NodeType;
      if (!type) return;
      const position = screenToFlowPosition({ x: event.clientX, y: event.clientY });
      addNode(type, position);
    },
    [addNode, screenToFlowPosition]
  );

  return (
    <div ref={wrapperRef} className="h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        onNodeClick={(_, node) => selectNode(node.id)}
        onNodeDragStart={() => beginHistoryCheckpoint()}
        onPaneClick={() => selectNode(null)}
        onDrop={onDrop}
        onDragOver={(e) => e.preventDefault()}
        defaultViewport={{ x: 0, y: 0, zoom: 1 }}
        minZoom={0.2}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
        deleteKeyCode={["Backspace", "Delete"]}
      >
        <Background variant={BackgroundVariant.Dots} gap={18} size={1} className="!bg-canvas" />
        <Controls className="!shadow-panel" />
        <MiniMap pannable zoomable className="!bg-surface" />
      </ReactFlow>
    </div>
  );
}

export function FlowCanvas() {
  return (
    <ReactFlowProvider>
      <CanvasInner />
    </ReactFlowProvider>
  );
}
