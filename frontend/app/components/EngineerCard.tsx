"use client";

import { useState } from "react";
import { Engineer } from "@/app/types";

const TYPE_BADGES: Record<string, string> = {
  feature: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  "bugfix-critical": "bg-red-500/20 text-red-400 border-red-500/30",
  "bugfix-minor": "bg-orange-500/20 text-orange-400 border-orange-500/30",
  refactor: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  performance: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  docs: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  test: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
};

function TypeBadge({ type }: { type: string }) {
  const colors = TYPE_BADGES[type] || "bg-gray-500/20 text-gray-400 border-gray-500/30";
  return (
    <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded-full border ${colors}`}>
      {type}
    </span>
  );
}

function PillarBar({ label, score, color }: { label: string; score: number; color: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-gray-400 w-28 shrink-0 text-right">{label}</span>
      <div className="flex-1 h-2.5 bg-gray-700/50 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className="text-xs font-mono text-gray-300 w-10 text-right">{score.toFixed(1)}</span>
    </div>
  );
}

function ScoreBadge({ value, max = 10 }: { value: number; max?: number }) {
  const pct = (value / max) * 100;
  let color = "text-gray-400";
  if (pct >= 80) color = "text-emerald-400";
  else if (pct >= 60) color = "text-blue-400";
  else if (pct >= 40) color = "text-yellow-400";
  return <span className={`font-mono text-sm font-semibold ${color}`}>{value}</span>;
}

const RANK_STYLES: Record<number, string> = {
  1: "from-yellow-500/20 to-yellow-600/5 border-yellow-500/30",
  2: "from-gray-300/15 to-gray-400/5 border-gray-400/25",
  3: "from-amber-600/15 to-amber-700/5 border-amber-600/25",
};

const RANK_BADGE: Record<number, string> = {
  1: "bg-yellow-500 text-black",
  2: "bg-gray-300 text-black",
  3: "bg-amber-600 text-white",
};

export default function EngineerCard({ engineer }: { engineer: Engineer }) {
  const [expanded, setExpanded] = useState(false);
  const { pillars } = engineer;

  const cardBg =
    RANK_STYLES[engineer.rank] || "from-gray-800/50 to-gray-900/30 border-gray-700/40";
  const rankBadge = RANK_BADGE[engineer.rank] || "bg-gray-600 text-white";

  return (
    <div
      className={`rounded-xl border bg-gradient-to-br ${cardBg} backdrop-blur-sm overflow-hidden transition-all duration-200`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-5 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900 rounded-xl"
      >
        <div className="flex items-start gap-4">
          {/* Rank badge */}
          <div
            className={`w-9 h-9 rounded-lg flex items-center justify-center font-bold text-sm shrink-0 ${rankBadge}`}
          >
            #{engineer.rank}
          </div>

          {/* Avatar */}
          <img
            src={engineer.avatar_url}
            alt={engineer.login}
            className="w-12 h-12 rounded-full bg-gray-700 shrink-0"
            onError={(e) => {
              const target = e.target as HTMLImageElement;
              target.src = `https://ui-avatars.com/api/?name=${engineer.login}&background=374151&color=9ca3af&size=48`;
            }}
          />

          {/* Name + score */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 flex-wrap">
              <h3 className="text-lg font-semibold text-white truncate">{engineer.login}</h3>
              <div className="flex items-baseline gap-1">
                <span className="text-2xl font-bold text-white">{engineer.final_score.toFixed(1)}</span>
                <span className="text-xs text-gray-500">/100</span>
              </div>
            </div>

            {/* Pillar bars */}
            <div className="mt-3 space-y-1.5">
              <PillarBar label="Contribution" score={pillars.contribution_impact.score} color="bg-blue-500" />
              <PillarBar label="Review" score={pillars.review_impact.score} color="bg-purple-500" />
              <PillarBar label="Velocity" score={pillars.collaboration_velocity.score} color="bg-emerald-500" />
              <PillarBar label="Breadth" score={pillars.codebase_breadth.score} color="bg-orange-500" />
            </div>
          </div>

          {/* Expand indicator */}
          <svg
            className={`w-5 h-5 text-gray-500 shrink-0 transition-transform duration-200 mt-1 ${expanded ? "rotate-180" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="px-5 pb-5 border-t border-gray-700/40">
          {/* Stats row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4 mb-5">
            <StatBox label="PRs Authored" value={pillars.contribution_impact.pr_count} />
            <StatBox label="Reviews Given" value={pillars.review_impact.review_count} />
            <StatBox
              label="Review Turnaround"
              value={pillars.collaboration_velocity.median_review_turnaround_hours != null ? `${pillars.collaboration_velocity.median_review_turnaround_hours}h` : "N/A"}
            />
            <StatBox
              label="Feedback Response"
              value={pillars.collaboration_velocity.median_feedback_incorporation_hours != null ? `${pillars.collaboration_velocity.median_feedback_incorporation_hours}h` : "N/A"}
            />
          </div>

          {/* Codebase Zones */}
          <div className="mb-5">
            <h4 className="text-sm font-medium text-gray-400 mb-2">
              Codebase Zones ({pillars.codebase_breadth.zones_touched.length}/{pillars.codebase_breadth.zones_total})
            </h4>
            <div className="flex flex-wrap gap-1.5">
              {pillars.codebase_breadth.zones_touched.map((zone) => (
                <span
                  key={zone}
                  className="px-2 py-1 text-xs font-mono bg-gray-700/60 text-gray-300 rounded-md border border-gray-600/40"
                >
                  {zone}
                </span>
              ))}
            </div>
          </div>

          {/* Top PRs */}
          {engineer.top_prs.length > 0 && (
            <div className="mb-5">
              <h4 className="text-sm font-medium text-gray-400 mb-3">Top PRs</h4>
              <div className="space-y-3">
                {engineer.top_prs.map((pr) => (
                  <div
                    key={pr.number}
                    className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/30"
                  >
                    <div className="flex items-start gap-2 flex-wrap">
                      <TypeBadge type={pr.type_classification} />
                      <a
                        href={pr.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm font-medium text-blue-400 hover:text-blue-300 hover:underline flex-1 min-w-0"
                        onClick={(e) => e.stopPropagation()}
                      >
                        #{pr.number} {pr.title}
                      </a>
                      <span className="text-sm font-mono font-semibold text-white shrink-0">
                        {pr.composite.toFixed(2)}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400 mt-1.5">{pr.one_line_summary}</p>
                    <div className="flex gap-3 mt-2 flex-wrap">
                      <ScoreLabel label="Complexity" value={pr.scores.complexity} />
                      <ScoreLabel label="Scope" value={pr.scores.scope_of_impact} />
                      <ScoreLabel label="Type" value={pr.scores.type_weight} />
                      <ScoreLabel label="Risk" value={pr.scores.risk_and_judgment} />
                      <ScoreLabel label="Novelty" value={pr.scores.novelty} />
                    </div>
                    <p className="text-xs text-gray-500 mt-2 italic">{pr.reasoning}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top Reviews */}
          {engineer.top_reviews.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-400 mb-3">Top Reviews</h4>
              <div className="space-y-3">
                {engineer.top_reviews.map((review) => (
                  <div
                    key={review.pr_number}
                    className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/30"
                  >
                    <div className="flex items-start gap-2 flex-wrap">
                      <a
                        href={review.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm font-medium text-purple-400 hover:text-purple-300 hover:underline flex-1 min-w-0"
                        onClick={(e) => e.stopPropagation()}
                      >
                        #{review.pr_number} {review.pr_title}
                      </a>
                      <span className="text-sm font-mono font-semibold text-white shrink-0">
                        {review.weighted_composite.toFixed(2)}
                      </span>
                    </div>
                    <div className="flex gap-3 mt-2 flex-wrap">
                      <ScoreLabel label="Depth" value={review.scores.review_depth} />
                      <ScoreLabel label="Detection" value={review.scores.issue_detection} />
                      <ScoreLabel label="Constructive" value={review.scores.constructiveness} />
                    </div>
                    <p className="text-xs text-gray-500 mt-2 italic">{review.reasoning}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StatBox({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-gray-800/40 rounded-lg p-2.5 text-center border border-gray-700/20">
      <div className="text-lg font-semibold text-white">{value}</div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}

function ScoreLabel({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-1">
      <span className="text-xs text-gray-500">{label}:</span>
      <ScoreBadge value={value} />
    </div>
  );
}
