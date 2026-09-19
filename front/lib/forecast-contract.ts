export interface ForecastPoint {
  horizon_months: number
  as_of: string
  pessimistic: number
  conservative: number
  optimistic: number
  probability_down: number
  probability_stable: number
  probability_up: number
  model: string
  test_mae: number
  test_interval_coverage: number
  explanation: {
    method: string
    current_score: number
    reference_delta: number
    contributions: { feature: string; points: number }[]
    other_points: number
    calibration_points: number
    clipping_points: number
    predicted_score: number
  }
}

export interface Forecast {
  company_id: string
  run_id: string
  as_of: string
  current_score: number
  status: 'available' | 'insufficient_history'
  target: 'bank_only_score'
  history: { as_of: string; score: number; eligible: boolean }[]
  points: ForecastPoint[]
  context: { country: string | null; sector: string | null; external_indicators_available: number }
}

export interface ForecastMetrics {
  mae: number
  macro_group_mae: number
  interval_80_coverage: number
  balanced_direction_accuracy: number
}

export interface ForecastBenchmark {
  run_id: string
  context: { mode: string; historical_value_coverage: number }
  horizons: Record<string, { selected: string; test: Record<string, ForecastMetrics> }>
}
