"use client";

import {
  addEdge as rfAddEdge,
  applyEdgeChanges,
  applyNodeChanges,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
} from "@xyflow/react";
import { create } from "zustand";

import { defaultConfigFor, NODE_LABEL, type FlowSpec, type InputField, type NodeType } from "./flowspec";

export type NodeExecutionStatus =
  | "idle"
  | "queued"
  | "running"
  | "success"
  | "failed"
  | "waiting"
  | "skipped";

export interface AgentQNodeData extends Record<string, unknown> {
  nodeType: NodeType;
  label: string;
  config: Record<string, unknown>;
  status: NodeExecutionStatus;
}

export type AgentQNode = Node<AgentQNodeData>;
export type AgentQEdge = Edge<{ condition?: string | null }>;

let idCounter = 0;
function nextId(prefix: string): string {
  idCounter += 1;
  return `${prefix}-${Date.now().toString(36)}-${idCounter}`;
}

interface HistorySnapshot {
  nodes: AgentQNode[];
  edges: AgentQEdge[];
}

const MAX_HISTORY = 50;

interface CanvasState {
  flowId: string | null;
  flowName: string;
  /** The flow's declared input parameters (name/type/required/description) - carried through
   * from whatever created the flow (an example file, AI generation, an import) and preserved on
   * every save, since the canvas has no UI yet to author these directly. */
  flowInputs: InputField[];
  nodes: AgentQNode[];
  edges: AgentQEdge[];
  selectedNodeId: string | null;
  dirty: boolean;
  /** Bumped every time `loadFlow` runs, so the canvas knows to fit-view once for the newly
   * loaded graph (as opposed to every incremental drag/drop, which should not re-fit). */
  loadToken: number;
  /** Undo/redo stacks - only structural edits (add/remove/connect/move) push a snapshot; field
   * edits in the Inspector don't, both to avoid a snapshot per keystroke and because those
   * already have native browser undo inside the focused input. */
  past: HistorySnapshot[];
  future: HistorySnapshot[];

  loadFlow: (flowId: string, name: string, spec: FlowSpec) => void;
  newFlow: () => void;
  onNodesChange: (changes: NodeChange<AgentQNode>[]) => void;
  onEdgesChange: (changes: EdgeChange<AgentQEdge>[]) => void;
  onConnect: (connection: Connection) => void;
  addNode: (type: NodeType, position: { x: number; y: number }) => string;
  updateNodeConfig: (id: string, config: Record<string, unknown>) => void;
  updateNodeLabel: (id: string, label: string) => void;
  removeSelected: () => void;
  duplicateSelected: () => void;
  selectNode: (id: string | null) => void;
  setNodeStatus: (id: string, status: NodeExecutionStatus) => void;
  resetExecutionState: () => void;
  markClean: () => void;
  toFlowSpec: () => FlowSpec;
  loadFromSpec: (spec: FlowSpec) => void;
  beginHistoryCheckpoint: () => void;
  undo: () => void;
  redo: () => void;
}

function snapshotOf(state: CanvasState): HistorySnapshot {
  return { nodes: state.nodes, edges: state.edges };
}

/** Prepends a history checkpoint (capped, and clears redo) - spread into a `set()` update
 * alongside whatever the action is actually changing. */
function withCheckpoint(state: CanvasState) {
  return { past: [...state.past, snapshotOf(state)].slice(-MAX_HISTORY), future: [] };
}

export const useCanvasStore = create<CanvasState>((set, get) => ({
  flowId: null,
  flowName: "Untitled Flow",
  flowInputs: [],
  nodes: [],
  edges: [],
  selectedNodeId: null,
  dirty: false,
  loadToken: 0,
  past: [],
  future: [],

  loadFlow: (flowId, name, spec) => {
    const nodes: AgentQNode[] = spec.nodes.map((n) => ({
      id: n.id,
      type: "agentq",
      position: n.position ?? { x: 0, y: 0 },
      data: {
        nodeType: n.type,
        label: n.label || NODE_LABEL[n.type],
        config: n.config ?? {},
        status: "idle",
      },
    }));
    const edges: AgentQEdge[] = spec.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      data: { condition: e.condition },
    }));
    set((state) => ({
      flowId,
      flowName: name,
      flowInputs: spec.inputs,
      nodes,
      edges,
      selectedNodeId: null,
      dirty: false,
      loadToken: state.loadToken + 1,
      past: [],
      future: [],
    }));
  },

  newFlow: () =>
    set({
      flowId: null,
      flowName: "Untitled Flow",
      flowInputs: [],
      nodes: [],
      edges: [],
      selectedNodeId: null,
      dirty: false,
      past: [],
      future: [],
    }),

  /** Loads a FlowSpec (e.g. an imported JSON file) as the current unsaved working copy - unlike
   * `loadFlow`, this doesn't require an existing saved flow id, and marks the canvas dirty since
   * nothing has been persisted yet. */
  loadFromSpec: (spec) => {
    const nodes: AgentQNode[] = spec.nodes.map((n) => ({
      id: n.id,
      type: "agentq",
      position: n.position ?? { x: 0, y: 0 },
      data: {
        nodeType: n.type,
        label: n.label || NODE_LABEL[n.type],
        config: n.config ?? {},
        status: "idle",
      },
    }));
    const edges: AgentQEdge[] = spec.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      data: { condition: e.condition },
    }));
    set((state) => ({
      flowName: spec.name || state.flowName,
      flowInputs: spec.inputs,
      nodes,
      edges,
      selectedNodeId: null,
      dirty: true,
      loadToken: state.loadToken + 1,
      past: [],
      future: [],
    }));
  },

  /** Call before a structural edit that doesn't go through one of the store's own mutating
   * actions (currently: right before a node drag starts) so it lands on the undo stack too. */
  beginHistoryCheckpoint: () => set((state) => withCheckpoint(state)),

  onNodesChange: (changes) =>
    set((state) => {
      const removing = changes.some((c) => c.type === "remove");
      return {
        nodes: applyNodeChanges(changes, state.nodes),
        dirty: true,
        ...(removing ? withCheckpoint(state) : {}),
      };
    }),

  onEdgesChange: (changes) =>
    set((state) => {
      const removing = changes.some((c) => c.type === "remove");
      return {
        edges: applyEdgeChanges(changes, state.edges),
        dirty: true,
        ...(removing ? withCheckpoint(state) : {}),
      };
    }),

  onConnect: (connection) =>
    set((state) => ({
      ...withCheckpoint(state),
      edges: rfAddEdge({ ...connection, id: nextId("edge") }, state.edges) as AgentQEdge[],
      dirty: true,
    })),

  addNode: (type, position) => {
    const id = nextId(type);
    const node: AgentQNode = {
      id,
      type: "agentq",
      position,
      data: {
        nodeType: type,
        label: NODE_LABEL[type],
        config: defaultConfigFor(type),
        status: "idle",
      },
    };
    set((state) => ({
      ...withCheckpoint(state),
      nodes: [...state.nodes, node],
      selectedNodeId: id,
      dirty: true,
    }));
    return id;
  },

  updateNodeConfig: (id, config) =>
    set((state) => ({
      nodes: state.nodes.map((n) => (n.id === id ? { ...n, data: { ...n.data, config } } : n)),
      dirty: true,
    })),

  updateNodeLabel: (id, label) =>
    set((state) => ({
      nodes: state.nodes.map((n) => (n.id === id ? { ...n, data: { ...n.data, label } } : n)),
      dirty: true,
    })),

  removeSelected: () =>
    set((state) => {
      if (!state.selectedNodeId) return state;
      const id = state.selectedNodeId;
      return {
        ...withCheckpoint(state),
        nodes: state.nodes.filter((n) => n.id !== id),
        edges: state.edges.filter((e) => e.source !== id && e.target !== id),
        selectedNodeId: null,
        dirty: true,
      };
    }),

  duplicateSelected: () =>
    set((state) => {
      const original = state.nodes.find((n) => n.id === state.selectedNodeId);
      if (!original) return state;
      const id = nextId(original.data.nodeType);
      const copy: AgentQNode = {
        ...original,
        id,
        position: { x: original.position.x + 40, y: original.position.y + 40 },
        selected: false,
        data: { ...original.data },
      };
      return { ...withCheckpoint(state), nodes: [...state.nodes, copy], selectedNodeId: id, dirty: true };
    }),

  selectNode: (id) => set({ selectedNodeId: id }),

  setNodeStatus: (id, status) =>
    set((state) => ({
      nodes: state.nodes.map((n) => (n.id === id ? { ...n, data: { ...n.data, status } } : n)),
    })),

  resetExecutionState: () =>
    set((state) => ({ nodes: state.nodes.map((n) => ({ ...n, data: { ...n.data, status: "idle" as const } })) })),

  markClean: () => set({ dirty: false }),

  toFlowSpec: () => {
    const state = get();
    return {
      schema_version: 1,
      id: state.flowId ?? "unsaved",
      name: state.flowName,
      version: 1,
      description: "",
      inputs: state.flowInputs,
      nodes: state.nodes.map((n) => ({
        id: n.id,
        type: n.data.nodeType,
        position: { x: n.position.x, y: n.position.y },
        label: n.data.label,
        config: n.data.config,
      })),
      edges: state.edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        condition: e.data?.condition ?? null,
      })),
      variables: {},
      policies: {},
      metadata: {},
    };
  },

  undo: () =>
    set((state) => {
      if (state.past.length === 0) return state;
      const previous = state.past[state.past.length - 1]!;
      return {
        past: state.past.slice(0, -1),
        future: [snapshotOf(state), ...state.future].slice(0, MAX_HISTORY),
        nodes: previous.nodes,
        edges: previous.edges,
        selectedNodeId: null,
        dirty: true,
      };
    }),

  redo: () =>
    set((state) => {
      if (state.future.length === 0) return state;
      const next = state.future[0]!;
      return {
        future: state.future.slice(1),
        past: [...state.past, snapshotOf(state)].slice(-MAX_HISTORY),
        nodes: next.nodes,
        edges: next.edges,
        selectedNodeId: null,
        dirty: true,
      };
    }),
}));
