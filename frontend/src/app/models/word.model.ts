export interface WordFilter {
  contains?: string;
  starts_with?: string;
  ends_with?: string;
  min_length?: number;
  max_length?: number;
  exact_length?: number;
  limit?: number;
}

export interface WordStats {
  total_words: number;
  min_length: number;
  max_length: number;
  avg_length: number;
}

export interface WordsByLength {
  length: number;
  count: number;
  words: string[];
}
