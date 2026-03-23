export interface PRScores {
  complexity: number;
  scope_of_impact: number;
  type_weight: number;
  risk_and_judgment: number;
  novelty: number;
}

export interface TopPR {
  number: number;
  title: string;
  url: string;
  type_classification: string;
  composite: number;
  scores: PRScores;
  one_line_summary: string;
  reasoning: string;
}

export interface ReviewScores {
  review_depth: number;
  issue_detection: number;
  constructiveness: number;
}

export interface TopReview {
  pr_number: number;
  pr_title: string;
  url: string;
  weighted_composite: number;
  scores: ReviewScores;
  reasoning: string;
}

export interface ContributionImpact {
  score: number;
  raw_total: number;
  pr_count: number;
  dominant_type: string;
}

export interface ReviewImpact {
  score: number;
  raw_total: number;
  review_count: number;
}

export interface CollaborationVelocity {
  score: number;
  median_review_turnaround_hours: number;
  median_feedback_incorporation_hours: number;
}

export interface CodebaseBreadth {
  score: number;
  zones_touched: string[];
  zones_total: number;
}

export interface EngineerPillars {
  contribution_impact: ContributionImpact;
  review_impact: ReviewImpact;
  collaboration_velocity: CollaborationVelocity;
  codebase_breadth: CodebaseBreadth;
}

export interface Engineer {
  rank: number;
  login: string;
  avatar_url: string;
  final_score: number;
  pillars: EngineerPillars;
  top_prs: TopPR[];
  top_reviews: TopReview[];
}

export interface PillarInfo {
  weight: number;
  description: string;
  pr_formula?: string;
  review_formula?: string;
}

export interface Methodology {
  summary: string;
  pillars: {
    contribution_impact: PillarInfo;
    review_impact: PillarInfo;
    collaboration_velocity: PillarInfo;
    codebase_breadth: PillarInfo;
  };
  final_formula: string;
}

export interface Metadata {
  generated_at: string;
  period: { start: string; end: string };
  total_prs_analyzed: number;
  total_engineers: number;
  model_used: string;
}

export interface ResultsData {
  metadata: Metadata;
  methodology: Methodology;
  engineers: Engineer[];
}
