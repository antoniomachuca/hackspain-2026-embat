// Tokens del sistema visual de Embat en modo inverso (oscuro).
// Son los mismos valores que usa front-dashboard/app/globals.css.
export const theme = {
  deep: '#08070c',
  deep2: '#120d1d',
  deep3: '#1d1630',
  ink: '#ffffff',
  ink2: '#d2d2db',
  ink3: '#afafbb',
  line: 'rgba(255,255,255,.10)',
  glass: '#ffffff0d',
  purple: '#b083e8',
  purpleDark: '#a154e9',
  purpleDeep: '#7b32c0',
  // Rampa de riesgo: crítico → sólido.
  risk: ['#e5775b', '#e59f5e', '#dfb631', '#a154e9', '#c357ec'],
  font: '"General Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
} as const;

export const riskColor = (score: number) =>
  theme.risk[Math.min(4, Math.max(0, Math.floor(score / 20)))];
