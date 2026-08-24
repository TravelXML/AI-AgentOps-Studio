"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, ChevronDown, ChevronRight, Plus, XCircle } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Label, Select, TextArea, TextInput } from "@/components/ui/field";
import {
  api,
  ApiError,
  type EvaluationRun,
  type EvaluatorConfig,
  type EvaluatorType,
} from "@/lib/api-client";
import { formatRelativeTime } from "@/lib/utils";

const EVALUATOR_LABELS: Record<EvaluatorType, string> = {
  exact_match: "Exact match",
  contains: "Contains",
  regex: "Regex",
  schema: "Schema",
  latency: "Latency",
  cost: "Cost",
  llm_judge: "LLM judge",
};

function DatasetsPanel() {
  const queryClient = useQueryClient();
  const datasetsQuery = useQuery({ queryKey: ["datasets"], queryFn: api.listDatasets });
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [casesJson, setCasesJson] = useState('[\n  {"inputs": {"query": "hello"}, "expected_output": null}\n]');
  const [addError, setAddError] = useState<string | null>(null);

  const createDataset = useMutation({
    mutationFn: (n: string) => api.createDataset({ name: n }),
    onSuccess: (ds) => {
      queryClient.invalidateQueries({ queryKey: ["datasets"] });
      setCreating(false);
      setName("");
      setExpanded(ds.id);
    },
  });

  const addCases = useMutation({
    mutationFn: async (datasetId: string) => {
      const parsed = JSON.parse(casesJson);
      return api.addTestCases(datasetId, parsed);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["datasets"] });
      queryClient.invalidateQueries({ queryKey: ["test-cases"] });
    },
    onError: (err) =>
      setAddError(err instanceof ApiError ? err.message : err instanceof SyntaxError ? "Invalid JSON." : "Failed."),
  });

  return (
    <Card className="mb-6">
      <CardHeader className="flex items-center justify-between">
        <span className="text-sm font-medium">Datasets</span>
        {!creating ? (
          <Button variant="secondary" size="sm" onClick={() => setCreating(true)}>
            <Plus size={12} /> New dataset
          </Button>
        ) : (
          <div className="flex items-center gap-2">
            <TextInput
              autoFocus
              placeholder="Dataset name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-48"
            />
            <Button variant="primary" size="sm" disabled={!name} onClick={() => createDataset.mutate(name)}>
              Create
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setCreating(false)}>
              Cancel
            </Button>
          </div>
        )}
      </CardHeader>
      <CardBody className="p-0">
        {(datasetsQuery.data ?? []).length === 0 ? (
          <p className="px-4 py-6 text-center text-sm text-ink-faint">
            No datasets yet - create one, then add test cases (input + optional expected output).
          </p>
        ) : (
          <div className="divide-y divide-border">
            {(datasetsQuery.data ?? []).map((ds) => (
              <div key={ds.id}>
                <button
                  className="flex w-full items-center justify-between px-4 py-2.5 text-left text-sm hover:bg-surface-raised"
                  onClick={() => setExpanded(expanded === ds.id ? null : ds.id)}
                >
                  <span className="flex items-center gap-1.5">
                    {expanded === ds.id ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    {ds.name}
                  </span>
                  <span className="text-xs text-ink-faint">{ds.test_case_count} test cases</span>
                </button>
                {expanded === ds.id && (
                  <div className="border-t border-border bg-canvas/40 px-4 py-3">
                    <Label>Test cases (JSON array of {"{inputs, expected_output}"})</Label>
                    <TextArea rows={5} value={casesJson} onChange={(e) => setCasesJson(e.target.value)} />
                    {addError && <div className="mt-1 text-xs text-danger">{addError}</div>}
                    <Button
                      variant="secondary"
                      size="sm"
                      className="mt-2"
                      disabled={addCases.isPending}
                      onClick={() => {
                        setAddError(null);
                        addCases.mutate(ds.id);
                      }}
                    >
                      Add test cases
                    </Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function RunEvaluationPanel() {
  const queryClient = useQueryClient();
  const flowsQuery = useQuery({ queryKey: ["flows"], queryFn: api.listFlows });
  const datasetsQuery = useQuery({ queryKey: ["datasets"], queryFn: api.listDatasets });
  const modelsQuery = useQuery({ queryKey: ["models"], queryFn: api.listModels });

  const [flowId, setFlowId] = useState("");
  const [datasetId, setDatasetId] = useState("");
  const [selected, setSelected] = useState<Partial<Record<EvaluatorType, Record<string, unknown>>>>({
    contains: {},
  });
  const [judgeModel, setJudgeModel] = useState("default");
  const [error, setError] = useState<string | null>(null);

  const toggle = (type: EvaluatorType) => {
    setSelected((prev) => {
      const next = { ...prev };
      if (type in next) delete next[type];
      else next[type] = {};
      return next;
    });
  };

  const setEvalConfig = (type: EvaluatorType, key: string, value: unknown) =>
    setSelected((prev) => ({ ...prev, [type]: { ...prev[type], [key]: value } }));

  const run = useMutation({
    mutationFn: () => {
      const evaluators: EvaluatorConfig[] = Object.entries(selected).map(([type, config]) => ({
        type: type as EvaluatorType,
        config: config ?? {},
      }));
      return api.runEvaluation({ flow_id: flowId, dataset_id: datasetId, evaluators, judge_model: judgeModel });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["evaluation-runs"] }),
    onError: (err) => setError(err instanceof ApiError ? err.message : "Evaluation failed."),
  });

  return (
    <Card className="mb-6">
      <CardHeader>
        <span className="text-sm font-medium">Run an evaluation</span>
      </CardHeader>
      <CardBody>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>Flow (uses its latest saved version)</Label>
            <Select value={flowId} onChange={(e) => setFlowId(e.target.value)}>
              <option value="">Select a flow…</option>
              {(flowsQuery.data ?? []).map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label>Dataset</Label>
            <Select value={datasetId} onChange={(e) => setDatasetId(e.target.value)}>
              <option value="">Select a dataset…</option>
              {(datasetsQuery.data ?? []).map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.test_case_count} cases)
                </option>
              ))}
            </Select>
          </div>
        </div>

        <div className="mt-3">
          <Label>Evaluators</Label>
          <div className="space-y-2">
            {(Object.keys(EVALUATOR_LABELS) as EvaluatorType[]).map((type) => (
              <div key={type} className="rounded-md border border-border px-2.5 py-1.5">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={type in selected}
                    onChange={() => toggle(type)}
                    className="accent-accent"
                  />
                  {EVALUATOR_LABELS[type]}
                </label>
                {type in selected && (
                  <div className="mt-1.5 pl-6">
                    {type === "contains" && (
                      <TextInput
                        placeholder="substring the output must contain"
                        className="text-xs"
                        onChange={(e) => setEvalConfig("contains", "value", e.target.value)}
                      />
                    )}
                    {type === "regex" && (
                      <TextInput
                        placeholder="regex pattern"
                        className="text-xs"
                        onChange={(e) => setEvalConfig("regex", "pattern", e.target.value)}
                      />
                    )}
                    {type === "latency" && (
                      <TextInput
                        type="number"
                        placeholder="max latency ms"
                        className="text-xs"
                        onChange={(e) => setEvalConfig("latency", "max_ms", Number(e.target.value))}
                      />
                    )}
                    {type === "cost" && (
                      <TextInput
                        type="number"
                        step="0.001"
                        placeholder="max cost usd"
                        className="text-xs"
                        onChange={(e) => setEvalConfig("cost", "max_usd", Number(e.target.value))}
                      />
                    )}
                    {type === "llm_judge" && (
                      <div className="space-y-1.5">
                        <TextInput
                          placeholder="criteria, e.g. 'answers the question correctly'"
                          className="text-xs"
                          onChange={(e) => setEvalConfig("llm_judge", "criteria", e.target.value)}
                        />
                        <Select value={judgeModel} onChange={(e) => setJudgeModel(e.target.value)}>
                          <option value="default">default (MockLLM - will not judge meaningfully)</option>
                          {(modelsQuery.data ?? []).map((m) => (
                            <option key={m.id} value={m.model_key}>
                              {m.model_key} ({m.provider})
                            </option>
                          ))}
                        </Select>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {error && <div className="mt-2 text-xs text-danger">{error}</div>}
        <Button
          variant="primary"
          className="mt-3"
          disabled={!flowId || !datasetId || Object.keys(selected).length === 0 || run.isPending}
          onClick={() => {
            setError(null);
            run.mutate();
          }}
        >
          {run.isPending ? "Running…" : "Run evaluation"}
        </Button>
      </CardBody>
    </Card>
  );
}

function EvaluationRunRow({ run }: { run: EvaluationRun }) {
  const [expanded, setExpanded] = useState(false);
  const rate = run.total_cases > 0 ? Math.round((run.passed_cases / run.total_cases) * 100) : 0;

  return (
    <div>
      <button
        className="flex w-full items-center justify-between px-4 py-2.5 text-left text-sm hover:bg-surface-raised"
        onClick={() => setExpanded((v) => !v)}
      >
        <span className="flex items-center gap-1.5">
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          <code className="text-xs text-ink-faint">{run.id.slice(0, 8)}</code>
        </span>
        <span className="flex items-center gap-3">
          <Badge tone={rate === 100 ? "success" : rate === 0 ? "danger" : "warning"}>
            {run.passed_cases}/{run.total_cases} passed ({rate}%)
          </Badge>
          <span className="text-xs text-ink-faint">{formatRelativeTime(run.created_at)}</span>
        </span>
      </button>
      {expanded && (
        <div className="space-y-1.5 border-t border-border bg-canvas/40 px-4 py-3">
          {run.results.map((r) => (
            <div key={r.id} className="rounded-md border border-border px-2.5 py-1.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  {r.passed ? (
                    <CheckCircle2 size={12} className="text-success" />
                  ) : (
                    <XCircle size={12} className="text-danger" />
                  )}
                  Test case {r.test_case_id.slice(0, 8)}
                </span>
                {r.run_id && (
                  <a href={`/runs/${r.run_id}`} className="text-accent hover:underline">
                    view run
                  </a>
                )}
              </div>
              {r.error && <div className="mt-1 text-danger">{r.error}</div>}
              <div className="mt-1 space-y-0.5 text-ink-faint">
                {r.evaluator_results.map((er, i) => (
                  <div key={i}>
                    {er.passed ? "✓" : "✗"} {er.evaluator}: {er.detail}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function EvaluationsPage() {
  const runsQuery = useQuery({ queryKey: ["evaluation-runs"], queryFn: api.listEvaluationRuns });

  return (
    <div className="scrollbar-thin h-full overflow-y-auto p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold text-ink">Evaluations</h1>
        <p className="text-sm text-ink-muted">
          Run a dataset of test cases through a flow and grade every result - each case drives a
          real flow execution, not a simulation, so you can open its trace like any other run.
        </p>
      </div>

      <DatasetsPanel />
      <RunEvaluationPanel />

      <Card>
        <CardHeader>
          <span className="text-sm font-medium">Evaluation Runs</span>
        </CardHeader>
        <CardBody className="p-0">
          {(runsQuery.data ?? []).length === 0 ? (
            <p className="px-4 py-6 text-center text-sm text-ink-faint">No evaluation runs yet.</p>
          ) : (
            <div className="divide-y divide-border">
              {(runsQuery.data ?? []).map((r) => (
                <EvaluationRunRow key={r.id} run={r} />
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
