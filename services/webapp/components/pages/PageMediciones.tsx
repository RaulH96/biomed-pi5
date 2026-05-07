'use client'
import { useEffect, useState } from 'react'
import { fetchDoctorSessions } from '@/lib/api'

interface Props { dark: boolean }

export default function PageMediciones({ dark }: Props) {
  const [sessions, setSessions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDoctorSessions(20)
      .then(setSessions)
      .finally(() => setLoading(false))
  }, [])

  const c = dark
    ? { card: '#161B27', border: '#1E2535', text: '#E4E6EB', muted: '#6B7A99', sub: '#CDD0D8' }
    : { card: '#fff', border: '#E2E8F4', text: '#1C2340', muted: '#8892AA', sub: '#4A5268' }

  const fmtDate = (ts: number) => {
    const d = new Date(ts * 1000)
    return d.toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' })
  }

  const fmtTime = (ts: number) => {
    const d = new Date(ts * 1000)
    return d.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })
  }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, color: c.muted, fontSize: 14 }}>
      Cargando historial...
    </div>
  )

  return (
    <div style={{ color: c.text }}>
      <div style={{
        background: c.card,
        borderRadius: 14,
        border: `0.5px solid ${c.border}`,
        overflow: 'hidden',
      }}>
        <div style={{
          padding: '12px 16px',
          borderBottom: `0.5px solid ${c.border}`,
          fontSize: 11,
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          color: c.muted,
        }}>
          Historial de sesiones
        </div>

        {sessions.length === 0 ? (
          <div style={{ padding: 16, fontSize: 13, color: c.muted }}>
            Sin sesiones registradas
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr>
                {['Sesión', 'Fecha', 'Inicio', 'Fin', 'Temp', 'SpO2', 'Presión'].map(h => (
                  <th key={h} style={{
                    textAlign: 'left',
                    padding: '10px 16px',
                    color: c.muted,
                    fontWeight: 500,
                    borderBottom: `0.5px solid ${c.border}`,
                    fontSize: 11,
                  }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sessions.map((s: any, i: number) => {
                const bg = i % 2 === 0
                  ? 'transparent'
                  : dark ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.01)'
                return (
                  <tr key={s.id} style={{ background: bg }}>
                    <td style={{
                      padding: '10px 16px',
                      color: c.sub,
                      borderBottom: `0.5px solid ${c.border}`,
                    }}>
                      #{s.id}
                    </td>
                    <td style={{
                      padding: '10px 16px',
                      color: c.sub,
                      borderBottom: `0.5px solid ${c.border}`,
                    }}>
                      {fmtDate(s.started_at)}
                    </td>
                    <td style={{
                      padding: '10px 16px',
                      color: c.sub,
                      borderBottom: `0.5px solid ${c.border}`,
                    }}>
                      {fmtTime(s.started_at)}
                    </td>
                    <td style={{
                      padding: '10px 16px',
                      color: c.sub,
                      borderBottom: `0.5px solid ${c.border}`,
                    }}>
                      {s.ended_at ? fmtTime(s.ended_at) : (
                        <span style={{ color: '#2A9080', fontSize: 11 }}>En curso</span>
                      )}
                    </td>
                    <td style={{
                      padding: '10px 16px',
                      color: c.muted,
                      borderBottom: `0.5px solid ${c.border}`,
                    }}>
                      {s.temp_count || 0}
                    </td>
                    <td style={{
                      padding: '10px 16px',
                      color: c.muted,
                      borderBottom: `0.5px solid ${c.border}`,
                    }}>
                      {s.spo2_count || 0}
                    </td>
                    <td style={{
                      padding: '10px 16px',
                      color: c.muted,
                      borderBottom: `0.5px solid ${c.border}`,
                    }}>
                      {s.bp_count || 0}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
