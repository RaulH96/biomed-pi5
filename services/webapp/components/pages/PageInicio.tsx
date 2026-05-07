'use client'
import { useEffect, useState } from 'react'
import { fetchSummary, fetchSessions } from '@/lib/api'
import { getBadgeStyle, colors } from '@/lib/theme'

interface Props { dark: boolean; patient?: any }

export default function PageInicio({ dark, patient }: Props) {
  const [summary, setSummary] = useState<any>(null)
  const [sessions, setSessions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([fetchSummary(), fetchSessions(10)])
      .then(([s, se]) => { setSummary(s); setSessions(se) })
      .finally(() => setLoading(false))
  }, [])

  const c = dark
    ? { bg: '#0F1117', card: '#161B27', border: '#1E2535', text: '#E4E6EB', muted: '#6B7A99', actText: '#CDD0D8' }
    : { bg: '#FAFBFE', card: '#fff', border: '#E2E8F4', text: '#1C2340', muted: '#8892AA', actText: '#2E3240' }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, color: c.muted, fontSize: 14 }}>
      Cargando resumen...
    </div>
  )

  const temp = summary?.temp
  const spo2 = summary?.spo2
  const bp = summary?.bp

  // Clasificar estado
  const tempState = temp?.state || 'normal'
  const spo2Normal = (spo2?.spo2_pct ?? 98) >= 95
  const bpState = bp?.category || 'Normal'

  const metrics = [
    {
      label: 'Temperatura',
      value: temp?.temp_c?.toFixed(1) ?? '—',
      unit: '°C',
      color: dark ? colors.teal.dark : colors.teal.main,
      badgeText: tempState.replace('_', ' '),
      state: tempState,
    },
    {
      label: 'SpO2',
      value: spo2?.spo2_pct?.toFixed(0) ?? '—',
      unit: '%',
      color: colors.blue.main,
      badgeText: spo2Normal ? 'Normal' : 'Bajo',
      state: spo2Normal ? 'normal' : 'febricula',
    },
    {
      label: 'Presión',
      value: bp ? `${bp.sys_mmhg?.toFixed(0)}/${bp.dia_mmhg?.toFixed(0)}` : '—',
      unit: 'mmHg',
      color: colors.amber.main,
      badgeText: bpState,
      state: bpState === 'Normal' ? 'normal' : 'Elevada',
    },
    {
      label: 'Pulso',
      value: spo2?.hr_bpm ?? bp?.hr_bpm ?? '—',
      unit: 'bpm',
      color: colors.coral.main,
      badgeText: 'Normal',
      state: 'normal',
    },
  ]

  return (
    <div style={{ color: c.text }}>
      {/* Métricas principales */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
        {metrics.map(m => {
          const badge = getBadgeStyle(m.state, dark)
          return (
            <div key={m.label} style={{
              background: c.card,
              borderRadius: 14,
              padding: 16,
              border: `0.5px solid ${c.border}`,
              borderLeft: `3px solid ${m.color}`,
            }}>
              <div style={{
                fontSize: 10,
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                color: c.muted,
                marginBottom: 8,
              }}>
                {m.label}
              </div>
              <div>
                <span style={{ fontSize: 28, fontWeight: 500, color: m.color }}>
                  {m.value}
                </span>
                <span style={{ fontSize: 12, color: c.muted, marginLeft: 3 }}>
                  {m.unit}
                </span>
              </div>
              <div style={{
                display: 'inline-block',
                fontSize: 10,
                padding: '2px 8px',
                borderRadius: 20,
                marginTop: 8,
                fontWeight: 500,
                ...badge,
              }}>
                {m.badgeText}
              </div>
            </div>
          )
        })}
      </div>

      {/* Actividad reciente + Tendencia */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        {/* Actividad */}
        <div style={{
          background: c.card,
          borderRadius: 14,
          padding: 16,
          border: `0.5px solid ${c.border}`,
        }}>
          <div style={{
            fontSize: 12,
            fontWeight: 500,
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            color: c.muted,
            marginBottom: 12,
          }}>
            Actividad reciente
          </div>
          {sessions.length === 0 ? (
            <p style={{ fontSize: 12, color: c.muted }}>Sin sesiones registradas</p>
          ) : (
            sessions.slice(0, 4).map((s: any, i: number) => {
              const start = new Date(s.started_at * 1000)
              const time = start.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })
              const date = start.toLocaleDateString('es-MX', { day: '2-digit', month: 'short' })
              const dots = [
                dark ? colors.teal.dark : colors.teal.main,
                colors.blue.main,
                colors.amber.main,
                colors.coral.main,
              ]
              return (
                <div key={s.id} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '8px 0',
                  borderBottom: i < 3 ? `0.5px solid ${c.border}` : 'none',
                }}>
                  <div style={{
                    width: 7,
                    height: 7,
                    borderRadius: '50%',
                    background: dots[i % 4],
                    flexShrink: 0,
                  }} />
                  <div style={{ fontSize: 12, flex: 1, color: c.actText }}>
                    Sesión #{s.id} · {date}
                  </div>
                  <div style={{ fontSize: 11, color: c.muted }}>{time}</div>
                </div>
              )
            })
          )}
        </div>

        {/* Gráfica tendencia (últimas 7 sesiones) */}
        <div style={{
          background: c.card,
          borderRadius: 14,
          padding: 16,
          border: `0.5px solid ${c.border}`,
        }}>
          <div style={{
            fontSize: 12,
            fontWeight: 500,
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            color: c.muted,
            marginBottom: 4,
          }}>
            Tendencia presión (7 días)
          </div>
          <TrendBars sessions={sessions.slice(-7)} dark={dark} c={c} />
        </div>
      </div>
    </div>
  )
}

function TrendBars({ sessions, dark, c }: any) {
  const days = ['L', 'M', 'M', 'J', 'V', 'S', 'D']
  const filledColor = dark ? '#1E2E28' : '#E8F6F3'
  const activeColor = dark ? colors.teal.dark : colors.teal.main

  return (
    <>
      <div style={{
        display: 'flex',
        alignItems: 'flex-end',
        gap: 6,
        height: 100,
        paddingTop: 8,
      }}>
        {sessions.length === 0 ? (
          <p style={{ fontSize: 12, color: c.muted }}>Sin datos suficientes</p>
        ) : (
          sessions.map((s: any, i: number) => {
            const isLast = i === sessions.length - 1
            const height = 40 + ((i + 1) / sessions.length) * 55
            return (
              <div key={s.id} style={{
                flex: 1,
                borderRadius: '4px 4px 0 0',
                height: `${height}%`,
                background: isLast ? activeColor : filledColor,
                opacity: 0.85,
              }} />
            )
          })
        )}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6 }}>
        {days.map(d => (
          <span key={d} style={{ fontSize: 10, color: c.muted }}>{d}</span>
        ))}
      </div>
    </>
  )
}
