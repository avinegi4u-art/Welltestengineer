"use client";

import type { SimulationCase } from "@/lib/types";
import { Copy, Trash2, Play, FileText } from "lucide-react";
import clsx from "clsx";

interface CaseTreeProps {
  cases: SimulationCase[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  onCreate: () => void;
  onDuplicate: (id: number) => void;
  onDelete: (id: number) => void;
  onSolve: (id: number) => void;
}

export default function CaseTree({
  cases,
  selectedId,
  onSelect,
  onCreate,
  onDuplicate,
  onDelete,
  onSolve,
}: CaseTreeProps) {
  return (
    <div className="panel p-3 h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-sm">Cases</h3>
        <button onClick={onCreate} className="btn-primary text-xs px-2 py-1">
          + New
        </button>
      </div>
      <div className="flex-1 overflow-y-auto space-y-1">
        {cases.length === 0 && (
          <p className="text-xs text-slate-500 p-2">No cases yet. Create one to begin.</p>
        )}
        {cases.map((c) => (
          <div
            key={c.id}
            className={clsx(
              "p-2 rounded cursor-pointer text-sm group",
              selectedId === c.id
                ? "bg-primary/10 border border-primary/30"
                : "hover:bg-slate-100 dark:hover:bg-slate-700"
            )}
            onClick={() => onSelect(c.id)}
          >
            <div className="flex items-center gap-1">
              <FileText className="w-3.5 h-3.5 text-slate-400" />
              <span className="font-medium truncate flex-1">{c.name}</span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5 truncate">{c.case_type.replace(/_/g, " ")}</p>
            <div className="flex gap-1 mt-1 opacity-0 group-hover:opacity-100 transition">
              <button
                onClick={(e) => { e.stopPropagation(); onSolve(c.id); }}
                className="p-1 hover:bg-primary/20 rounded"
                title="Solve"
              >
                <Play className="w-3 h-3" />
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); onDuplicate(c.id); }}
                className="p-1 hover:bg-slate-200 dark:hover:bg-slate-600 rounded"
                title="Duplicate"
              >
                <Copy className="w-3 h-3" />
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); onDelete(c.id); }}
                className="p-1 hover:bg-red-100 dark:hover:bg-red-900/30 rounded text-red-500"
                title="Delete"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
