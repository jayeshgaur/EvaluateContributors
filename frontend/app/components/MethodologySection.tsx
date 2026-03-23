"use client";

import { useState } from "react";
import { Methodology } from "@/app/types";

const PILLAR_LABELS: Record<string, { name: string; color: string; weight: string }> = {
  contribution_impact: { name: "Contribution Impact", color: "text-blue-400", weight: "40%" },
  review_impact: { name: "Review Impact", color: "text-purple-400", weight: "25%" },
  collaboration_velocity: { name: "Collaboration Velocity", color: "text-emerald-400", weight: "20%" },
  codebase_breadth: { name: "Codebase Breadth", color: "text-orange-400", weight: "15%" },
};

export default function MethodologySection({ methodology }: { methodology: Methodology }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-xl border border-gray-700/40 bg-gray-800/30 backdrop-blur-sm overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-4 text-left cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
      >
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          <h2 className="text-base font-semibold text-white">Scoring Methodology</h2>
        </div>
        <svg
          className={`w-5 h-5 text-gray-500 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="px-4 pb-5 border-t border-gray-700/40">
          <p className="text-sm text-gray-300 mt-4 mb-4">{methodology.summary}</p>

          <div className="bg-gray-900/50 rounded-lg p-3 mb-4 border border-gray-700/20">
            <span className="text-xs text-gray-500 uppercase tracking-wider">Final Score Formula</span>
            <p className="text-sm font-mono text-gray-300 mt-1">{methodology.final_formula}</p>
          </div>

          <div className="space-y-4">
            {Object.entries(methodology.pillars).map(([key, pillar]) => {
              const meta = PILLAR_LABELS[key];
              return (
                <div key={key} className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/20">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className={`text-sm font-semibold ${meta?.color || "text-white"}`}>
                      {meta?.name || key}
                    </h3>
                    <span className="text-xs font-mono text-gray-500">
                      ({(pillar.weight * 100).toFixed(0)}% weight)
                    </span>
                  </div>
                  <p className="text-xs text-gray-400">{pillar.description}</p>
                  {pillar.pr_formula && (
                    <div className="mt-2">
                      <span className="text-xs text-gray-500">PR Formula: </span>
                      <code className="text-xs font-mono text-gray-300">{pillar.pr_formula}</code>
                    </div>
                  )}
                  {pillar.review_formula && (
                    <div className="mt-2">
                      <span className="text-xs text-gray-500">Review Formula: </span>
                      <code className="text-xs font-mono text-gray-300">{pillar.review_formula}</code>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
