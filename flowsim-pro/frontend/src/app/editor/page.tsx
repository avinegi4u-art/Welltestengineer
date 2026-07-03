"use client";

import { useEffect, useState, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { api, defaultInputs } from "@/lib/api";
import type { CaseInputs, SimulationCase, SimulationOutput } from "@/lib/types";
import CaseTree from "@/components/CaseTree";
import InputForm from "@/components/InputForm";
import ProfileCharts from "@/components/ProfileCharts";
import ResultsPanel from "@/components/ResultsPanel";
import AssumptionsPanel from "@/components/AssumptionsPanel";
import SensitivityPanel from "@/components/SensitivityPanel";
import { Save, Play, Download } from "lucide-react";

function EditorContent() {
  const searchParams = useSearchParams();
  const caseIdParam = searchParams.get("id");

  const [cases, setCases] = useState<SimulationCase[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(caseIdParam ? parseInt(caseIdParam) : null);
  const [inputs, setInputs] = useState<CaseInputs>(defaultInputs);
  const [caseName, setCaseName] = useState("Untitled Case");
  const [output, setOutput] = useState<SimulationOutput | null>(null);
  const [activeTab, setActiveTab] = useState("Fluid");
  const [solving, setSolving] = useState(false);
  const [saving, setSaving] = useState(false);

  const loadCases = useCallback(async () => {
    const data = await api.listCases();
    setCases(data);
    if (selectedId) {
      const c = data.find((x) => x.id === selectedId);
      if (c) {
        setInputs(c.inputs);
        setCaseName(c.name);
        setOutput(c.outputs);
      }
    } else if (data.length > 0 && !selectedId) {
      setSelectedId(data[0].id);
      setInputs(data[0].inputs);
      setCaseName(data[0].name);
      setOutput(data[0].outputs);
    }
  }, [selectedId]);

  useEffect(() => { loadCases(); }, [loadCases]);

  const handleSelect = async (id: number) => {
    setSelectedId(id);
    const c = await api.getCase(id);
    setInputs(c.inputs);
    setCaseName(c.name);
    setOutput(c.outputs);
  };

  const handleCreate = async () => {
    const c = await api.createCase({ name: `Case ${cases.length + 1}`, ...defaultInputs });
    setCases([c, ...cases]);
    setSelectedId(c.id);
    setInputs(c.inputs);
    setCaseName(c.name);
    setOutput(null);
  };

  const handleSave = async () => {
    if (!selectedId) return;
    setSaving(true);
    await api.updateCase(selectedId, { name: caseName, ...inputs });
    await loadCases();
    setSaving(false);
  };

  const handleSolve = async (id?: number) => {
    const targetId = id ?? selectedId;
    if (!targetId) return;
    setSolving(true);
    try {
      await api.updateCase(targetId, { name: caseName, ...inputs });
      const result = await api.solveCase(targetId);
      setOutput(result);
      await loadCases();
    } finally {
      setSolving(false);
    }
  };

  const handleDuplicate = async (id: number) => {
    const c = await api.duplicateCase(id);
    setCases([c, ...cases]);
    setSelectedId(c.id);
  };

  const handleDelete = async (id: number) => {
    await api.deleteCase(id);
    const remaining = cases.filter((c) => c.id !== id);
    setCases(remaining);
    if (selectedId === id) {
      setSelectedId(remaining[0]?.id ?? null);
      if (remaining[0]) handleSelect(remaining[0].id);
    }
  };

  const handleExport = async (format: "pdf" | "json" | "csv") => {
    if (!selectedId) return;
    const blob = await api.exportReport(selectedId, format);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${caseName}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="h-[calc(100vh-3.5rem)] flex flex-col">
      <div className="flex items-center gap-3 px-4 py-2 border-b border-border-light dark:border-border-dark bg-panel-light dark:bg-panel-dark">
        <input
          className="input-field max-w-xs font-medium"
          value={caseName}
          onChange={(e) => setCaseName(e.target.value)}
        />
        <button onClick={handleSave} disabled={saving || !selectedId} className="btn-secondary flex items-center gap-1 text-xs">
          <Save className="w-3.5 h-3.5" /> {saving ? "Saving..." : "Save"}
        </button>
        <button onClick={() => handleSolve()} disabled={solving || !selectedId} className="btn-primary flex items-center gap-1 text-xs">
          <Play className="w-3.5 h-3.5" /> {solving ? "Solving..." : "Solve"}
        </button>
        <div className="ml-auto flex gap-1">
          {(["pdf", "json", "csv"] as const).map((fmt) => (
            <button key={fmt} onClick={() => handleExport(fmt)} className="btn-secondary text-xs px-2 py-1 flex items-center gap-1" disabled={!selectedId}>
              <Download className="w-3 h-3" /> {fmt.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 grid grid-cols-12 gap-3 p-3 overflow-hidden">
        <div className="col-span-2 overflow-hidden">
          <CaseTree
            cases={cases}
            selectedId={selectedId}
            onSelect={handleSelect}
            onCreate={handleCreate}
            onDuplicate={handleDuplicate}
            onDelete={handleDelete}
            onSolve={handleSolve}
          />
        </div>
        <div className="col-span-3 overflow-hidden">
          <InputForm inputs={inputs} onChange={setInputs} activeTab={activeTab} onTabChange={setActiveTab} />
        </div>
        <div className="col-span-5 overflow-y-auto">
          <ProfileCharts output={output} />
          <div className="mt-3">
            <SensitivityPanel caseId={selectedId} />
          </div>
          <div className="mt-3">
            <AssumptionsPanel output={output} />
          </div>
        </div>
        <div className="col-span-2 overflow-hidden">
          <ResultsPanel output={output} loading={solving} />
        </div>
      </div>
    </div>
  );
}

export default function EditorPage() {
  return (
    <Suspense fallback={<div className="p-6">Loading editor...</div>}>
      <EditorContent />
    </Suspense>
  );
}
