export type RiskLevel = 'low' | 'medium' | 'high';

export interface Evidence {
  id: string;
  title: string;
  reason: string;
  scores: {
    bm25: number;
    dense: number;
    url: number;
    keyword: number;
  };
  fusionScore: number;
  rerankScore: number;
  content: string;
}

export interface Suggestion {
  immediate: string[];
  verify: string[];
  followUp: string[];
}

export interface TrainingQuestion {
  question: string;
  options: { id: string; text: string }[];
  correctAnswerId: string;
  explanation: string;
}

export interface AnalysisResult {
  id: string;
  date: string;
  inputType: 'text' | 'image' | 'sms' | 'email' | 'url';
  originalText: string;
  riskLevel: RiskLevel;
  riskScore: number;
  fraudType: string;
  riskFeatures: string[];
  evidence: Evidence[];
  suggestions: Suggestion;
  complianceRewrite: string;
  trainingQuestion: TrainingQuestion;
  rawJson: string;
}
