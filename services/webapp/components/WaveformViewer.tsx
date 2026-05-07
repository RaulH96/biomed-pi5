'use client'
import React, { useEffect, useRef } from 'react'

interface Props {
  sessionId: number
  measurementId?: number
  measurementMeta?: any   // datos del sessionDetail (spo2_pct, hr_bpm, sys_mmhg, etc.)
  type: 'spo2' | 'bp'
  dark: boolean
  c: any
}

export default function WaveformViewer({ sessionId, measurementId, measurementMeta, type, dark, c }: Props) {
  const [data, setData] = React.useState<any>(null)
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  useEffect(() => {
    if (!measurementId) { setData(null); return }
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://192.168.1.75:8000'
    const url = type === 'spo2'
      ? `${API_BASE}/doctor/sessions/${sessionId}/waveform/spo2/${measurementId}`
      : `${API_BASE}/doctor/sessions/${sessionId}/waveform/bp/${measurementId}`
    setLoading(true); setData(null); setError(null)
    fetch(url).then(r => r.json()).then(setData).catch(e => setError(e.message)).finally(() => setLoading(false))
  }, [sessionId, measurementId, type])

  if (loading) return <div style={{ padding: 20, color: c.muted, fontSize: 13 }}>Cargando señal...</div>
  if (error)   return <div style={{ padding: 20, color: '#E8845A', fontSize: 12 }}>Error: {error}</div>
  if (!measurementId) return <div style={{ padding: 20, color: c.muted, fontSize: 13 }}>Selecciona una medición</div>
  if (!data)   return <div style={{ padding: 20, color: c.muted, fontSize: 13 }}>Sin datos...</div>

  return type === 'spo2'
    ? <SpO2Waveform data={data} meta={measurementMeta} dark={dark} c={c} />
    : <BpWaveform   data={data} meta={measurementMeta} dark={dark} c={c} />
}

/* ─── helpers ───────────────────────────────────────────── */
function useCanvas(
  deps: any[],
  draw: (ctx: CanvasRenderingContext2D, W: number, H: number) => void
) {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    const render = () => {
      const W = canvas.clientWidth
      const H = canvas.clientHeight
      if (!W || !H) return
      canvas.width = W
      canvas.height = H
      const ctx = canvas.getContext('2d')!
      draw(ctx, W, H)
    }
    render()
    const ro = new ResizeObserver(render)
    ro.observe(canvas)
    return () => ro.disconnect()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return ref
}

function grid(ctx: CanvasRenderingContext2D, W: number, H: number, dark: boolean) {
  ctx.strokeStyle = dark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.07)'
  ctx.lineWidth = 0.5
  for (let i = 1; i < 5; i++) {
    const y = H / 5 * i
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke()
  }
  for (let i = 1; i < 6; i++) {
    const x = W / 6 * i
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke()
  }
}

function vline(ctx: CanvasRenderingContext2D, x: number, H: number, color: string, label: string) {
  ctx.save()
  ctx.strokeStyle = color
  ctx.lineWidth = 1.5
  ctx.setLineDash([4, 3])
  ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke()
  ctx.setLineDash([])
  ctx.fillStyle = color
  ctx.font = 'bold 10px sans-serif'
  ctx.fillText(label, x + 3, 12)
  ctx.restore()
}

function hline(ctx: CanvasRenderingContext2D, y: number, W: number, color: string, label: string) {
  ctx.save()
  ctx.strokeStyle = color
  ctx.lineWidth = 1
  ctx.setLineDash([4, 3])
  ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke()
  ctx.setLineDash([])
  ctx.fillStyle = color
  ctx.font = '10px sans-serif'
  ctx.fillText(label, 4, y - 3)
  ctx.restore()
}

function polyline(ctx: CanvasRenderingContext2D, xs: number[], ys: number[], color: string, lw = 1.5) {
  if (!xs.length) return
  ctx.strokeStyle = color; ctx.lineWidth = lw
  ctx.beginPath()
  for (let i = 0; i < xs.length; i++) i === 0 ? ctx.moveTo(xs[i], ys[i]) : ctx.lineTo(xs[i], ys[i])
  ctx.stroke()
}

function normalize(arr: number[], outMin: number, outMax: number, inMin?: number, inMax?: number) {
  const mn = inMin ?? Math.min(...arr)
  const mx = inMax ?? Math.max(...arr)
  const rng = mx - mn || 1
  return arr.map(v => outMin + (outMax - outMin) * (1 - (v - mn) / rng))
}

/* ─── SpO2 ──────────────────────────────────────────────── */
function SpO2Waveform({ data, meta, dark, c }: any) {
  const ir:   number[] = data.ir  ?? []
  const red:  number[] = data.red ?? []
  const thH:  number[] = data.thresh_high ?? []
  const thL:  number[] = data.thresh_low  ?? []

  // Panel IR con umbrales
  const refIR = useCanvas([data, dark], (ctx, W, H) => {
    ctx.fillStyle = dark ? '#161B27' : '#fff'
    ctx.fillRect(0, 0, W, H)
    grid(ctx, W, H, dark)

    const len = Math.min(ir.length, 600)
    if (!len) return

    const allVals = [...ir.slice(0,len), ...thH.slice(0,len), ...thL.slice(0,len)]
    const mn = Math.min(...allVals), mx = Math.max(...allVals)
    const pad = 8

    const toY = (v: number) => pad + (H - pad*2) * (1 - (v - mn) / (mx - mn))
    const xs  = Array.from({length: len}, (_, i) => i * W / len)

    // zona entre umbrales sombreada
    if (thH.length && thL.length) {
      ctx.fillStyle = dark ? 'rgba(74,170,222,0.08)' : 'rgba(74,170,222,0.10)'
      ctx.beginPath()
      ctx.moveTo(xs[0], toY(thH[0]))
      for (let i = 1; i < len; i++) ctx.lineTo(xs[i], toY(thH[i]))
      for (let i = len-1; i >= 0; i--) ctx.lineTo(xs[i], toY(thL[i]))
      ctx.closePath(); ctx.fill()

      // líneas de umbral
      polyline(ctx, xs, thH.slice(0,len).map(toY), 'rgba(74,170,222,0.55)', 1)
      polyline(ctx, xs, thL.slice(0,len).map(toY), 'rgba(74,170,222,0.55)', 1)
    }

    // señal IR
    polyline(ctx, xs, ir.slice(0,len).map(toY), '#4AAADE', 1.8)

    ctx.font = 'bold 11px sans-serif'
    ctx.fillStyle = '#4AAADE'; ctx.fillText('IR', 6, 14)
    if (thH.length) {
      ctx.fillStyle = 'rgba(74,170,222,0.8)'; ctx.font = '10px sans-serif'
      ctx.fillText('umbral alto', 6, 26)
      ctx.fillText('umbral bajo', 6, H - 6)
    }
  })

  // Panel Red
  const refRed = useCanvas([data, dark], (ctx, W, H) => {
    ctx.fillStyle = dark ? '#161B27' : '#fff'
    ctx.fillRect(0, 0, W, H)
    grid(ctx, W, H, dark)

    const len = Math.min(red.length, 600)
    if (!len) return
    const mn = Math.min(...red.slice(0,len)), mx = Math.max(...red.slice(0,len))
    const pad = 8
    const toY = (v: number) => pad + (H - pad*2) * (1 - (v - mn) / (mx - mn))
    const xs  = Array.from({length: len}, (_, i) => i * W / len)
    polyline(ctx, xs, red.slice(0,len).map(toY), '#E8845A', 1.8)
    ctx.font = 'bold 11px sans-serif'
    ctx.fillStyle = '#E8845A'; ctx.fillText('Red', 6, 14)
  })

  const spo2  = meta?.spo2_pct?.toFixed(1) ?? '—'
  const hr    = meta?.hr_bpm ?? '—'
  const fs    = data.sample_rate ? `${data.sample_rate} Hz` : '—'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10 }}>
        <Stat label="SpO2"        value={`${spo2}%`}     color='#4AAADE' c={c} />
        <Stat label="Frec. card." value={`${hr} bpm`}    color='#E8845A' c={c} />
        <Stat label="Sample rate" value={fs}              color={c.muted} c={c} />
      </div>
      <canvas ref={refIR} style={{ display:'block', width:'100%', height:180,
        border:`1px solid ${c.border}`, borderRadius:8 }} />
      <canvas ref={refRed} style={{ display:'block', width:'100%', height:120,
        border:`1px solid ${c.border}`, borderRadius:8 }} />
    </div>
  )
}

/* ─── BP ────────────────────────────────────────────────── */
function BpWaveform({ data, meta, dark, c }: any) {
  const pressure: number[] = data.pressure ?? []
  const time:     number[] = data.time     ?? []
  const osc:      number[] = data.osc      ?? []
  const env:      number[] = data.env      ?? []
  // peaks contiene índices de los picos en el array de osc (len=278)

  const sys = meta?.sys_mmhg
  const dia = meta?.dia_mmhg
  const map = meta?.map_mmhg
  const hr  = meta?.hr_bpm

  // Panel presión principal
  const refPress = useCanvas([data, dark, sys, dia], (ctx, W, H) => {
    ctx.fillStyle = dark ? '#161B27' : '#fff'
    ctx.fillRect(0, 0, W, H)
    grid(ctx, W, H, dark)

    const len = Math.min(pressure.length, 1000) // muestra hasta 1000pts (de 13010)
    // Para no tardar siglos en dibujar, submuestreamos
    const step = Math.max(1, Math.floor(pressure.length / 1200))
    const pSub = pressure.filter((_,i) => i % step === 0)
    const tSub = time.filter((_,i) => i % step === 0)
    const n = pSub.length

    const mn = Math.min(...pSub), mx = Math.max(...pSub)
    const tMin = tSub[0] ?? 0, tMax = tSub[n-1] ?? 1
    const pad = 10

    const toX = (t: number) => (t - tMin) / (tMax - tMin) * W
    const toY = (v: number) => pad + (H - pad*2) * (1 - (v - mn) / (mx - mn))

    polyline(ctx, tSub.map(toX), pSub.map(toY), '#F0A830', 1.5)

    // Líneas horizontales SYS / DIA / MAP
    if (sys && sys >= mn && sys <= mx) hline(ctx, toY(sys), W, '#E8845A', `SYS ${sys.toFixed(0)}`)
    if (dia && dia >= mn && dia <= mx) hline(ctx, toY(dia), W, '#4AAADE', `DIA ${dia.toFixed(0)}`)
    if (map && map >= mn && map <= mx) hline(ctx, toY(map), W, 'rgba(100,200,100,0.9)', `MAP ${map.toFixed(0)}`)

    ctx.font = 'bold 11px sans-serif'
    ctx.fillStyle = '#F0A830'; ctx.fillText('Presión (mmHg)', 6, 13)
  })

  // Panel oscilaciones + envolvente
  const refOsc = useCanvas([data, dark], (ctx, W, H) => {
    ctx.fillStyle = dark ? '#161B27' : '#fff'
    ctx.fillRect(0, 0, W, H)
    grid(ctx, W, H, dark)

    const n = osc.length
    if (!n) return

    const mn = Math.min(...osc), mx = Math.max(...osc)
    const pad = 10
    const xs = Array.from({length: n}, (_, i) => i * W / n)
    const toY = (v: number) => pad + (H - pad*2) * (1 - (v - mn) / (mx - mn))

    // oscilaciones
    polyline(ctx, xs, osc.map(toY), '#E8845A', 1.5)

    // envolvente
    if (env.length === n) {
      const eMn = Math.min(...env), eMx = Math.max(...env)
      const toYe = (v: number) => pad + (H - pad*2) * (1 - (v - eMn) / (eMx - eMn || 1))
      polyline(ctx, xs, env.map(toYe), 'rgba(240,168,48,0.7)', 2)
    }

    ctx.font = 'bold 11px sans-serif'
    ctx.fillStyle = '#E8845A'; ctx.fillText('Oscilaciones', 6, 13)
    ctx.fillStyle = 'rgba(240,168,48,0.9)'; ctx.fillText('Envolvente', 80, 13)
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10 }}>
        <Stat label="Sistólica"  value={sys ? `${sys.toFixed(0)} mmHg` : '—'} color='#E8845A'                   c={c} />
        <Stat label="Diastólica" value={dia ? `${dia.toFixed(0)} mmHg` : '—'} color='#4AAADE'                   c={c} />
        <Stat label="MAP"        value={map ? `${map.toFixed(0)} mmHg` : '—'} color='rgba(100,200,100,0.9)'     c={c} />
        <Stat label="FC"         value={hr  ? `${hr} bpm`              : '—'} color={c.muted}                   c={c} />
      </div>
      <canvas ref={refPress} style={{ display:'block', width:'100%', height:200,
        border:`1px solid ${c.border}`, borderRadius:8 }} />
      <canvas ref={refOsc} style={{ display:'block', width:'100%', height:160,
        border:`1px solid ${c.border}`, borderRadius:8 }} />
    </div>
  )
}

/* ─── Stat ──────────────────────────────────────────────── */
function Stat({ label, value, color, c }: any) {
  return (
    <div style={{ background: c.card, padding: '8px 12px', borderRadius: 8, border: `0.5px solid ${c.border}`,
      borderLeft: `3px solid ${color}` }}>
      <div style={{ fontSize: 10, color: c.muted, marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 14, fontWeight: 600, color: c.text }}>{value}</div>
    </div>
  )
}

// ─── CAMBIO EN PageDoctor.tsx ────────────────────────────
// En WaveformModal, cambia la línea de <WaveformViewer> por:
//
// <WaveformViewer
//   sessionId={session.id}
//   measurementId={selectedMeasurement || undefined}
//   measurementMeta={
//     tab === 'spo2'
//       ? spo2List.find((m: any) => m.id === selectedMeasurement)
//       : bpList.find((m: any) => m.id === selectedMeasurement)
//   }
//   type={tab}
//   dark={dark}
//   c={c}
// />