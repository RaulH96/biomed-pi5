export const colors = {
  teal:   { main: '#2A9080', light: '#E8F6F3', dark: '#2DD4AA', bg_dark: '#0D2E28' },
  blue:   { main: '#4AAADE', light: '#DFF0FB', dark: '#4AAADE', bg_dark: '#0D1E2E' },
  coral:  { main: '#E8845A', light: '#FDDDD6', dark: '#F0A070', bg_dark: '#2E1215' },
  amber:  { main: '#F0A830', light: '#FFF0D6', dark: '#F0A830', bg_dark: '#2E1B0D' },
  green:  { main: '#45C07A', light: '#DFF5E8', dark: '#60D090', bg_dark: '#0D2E22' },
  slate:  {
    50: '#F4F5F7', 100: '#E4E6EB', 200: '#CDD0D8',
    400: '#8892AA', 600: '#555A6A', 800: '#2E3240', 900: '#1C1F2B'
  }
}

export const badge = {
  normal:     { bg: colors.green.light,  text: '#1E8A50',  bg_dark: colors.green.bg_dark,  text_dark: colors.green.dark },
  normal_baja:{ bg: colors.green.light,  text: '#1E8A50',  bg_dark: colors.green.bg_dark,  text_dark: colors.green.dark },
  febricula:  { bg: colors.amber.light,  text: '#C07A10',  bg_dark: colors.amber.bg_dark,  text_dark: colors.amber.dark },
  fiebre_moderada: { bg: colors.coral.light, text: '#C05A38', bg_dark: colors.coral.bg_dark, text_dark: colors.coral.dark },
  fiebre_alta:{ bg: colors.coral.light,  text: '#C05A38',  bg_dark: colors.coral.bg_dark,  text_dark: colors.coral.dark },
  hipotermia: { bg: '#DFF0FB',           text: '#1E72A8',  bg_dark: '#0D1E2E',             text_dark: '#4AAADE' },
  Hipertension:{ bg: colors.coral.light, text: '#C05A38',  bg_dark: colors.coral.bg_dark,  text_dark: colors.coral.dark },
  Elevada:    { bg: colors.amber.light,  text: '#C07A10',  bg_dark: colors.amber.bg_dark,  text_dark: colors.amber.dark },
  Normal:     { bg: colors.green.light,  text: '#1E8A50',  bg_dark: colors.green.bg_dark,  text_dark: colors.green.dark },
}

export function getBadgeStyle(state: string, dark: boolean) {
  const b = badge[state as keyof typeof badge] || badge.normal
  return dark
    ? { background: b.bg_dark, color: b.text_dark }
    : { background: b.bg,      color: b.text }
}

export const light = {
  bg:      '#FAFBFE',
  surface: '#FFFFFF',
  sidebar: '#FFFFFF',
  border:  '#E2E8F4',
  text:    '#1C2340',
  muted:   '#8892AA',
}

export const dark = {
  bg:      '#0F1117',
  surface: '#161B27',
  sidebar: '#13161F',
  border:  '#1E2535',
  text:    '#E4E6EB',
  muted:   '#6B7A99',
}
