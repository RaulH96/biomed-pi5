'use client'
import { useEffect, useState } from 'react'
import { fetchPatient, fetchSummary, fetchSessions } from '@/lib/api'
import { getBadgeStyle, colors } from '@/lib/theme'

interface Props { dark: boolean; patient?: any }

export default function PagePaciente({ dark, patient }: Props) {
  const [patientData, setPatientData] = useState<any>(null)
  const [summary, setSummary] = useState<any>(null)
  const [sessions, setSessions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState<any>({})

  const c = dark
    ? { card: '#161B27', border: '#1E2535', text: '#E4E6EB', muted: '#6B7A99', sub: '#CDD0D8', input: '#0F1117' }
    : { card: '#fff', border: '#E2E8F4', text: '#1C2340', muted: '#8892AA', sub: '#4A5268', input: '#F4F6FB' }

  useEffect(() => {
    Promise.all([fetchPatient(), fetchSummary(), fetchSessions(10)])
      .then(([p, s, se]) => {
        setPatientData(p)
        setForm(p)
        setSummary(s)
        setSessions(se)
      })
      .finally(() => setLoading(false))
  }, [])

  async function savePatient() {
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    await fetch(`${API_BASE}/patient`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    })
    setPatientData(form)
    setEditing(false)
  }

  const fmtTs = (ts: number) => {
    if (!ts) return '—'
    const d = new Date(ts * 1000)
    return d.toLocaleString('es-MX', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const initials = (name: string) =>
    name?.split(' ').slice(0, 2).map((w: string) => w[0]).join('').toUpperCase() || '?'

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, color: c.muted, fontSize: 14 }}>
      Cargando expediente...
    </div>
  )

  const temp = summary?.temp
  const spo2 = summary?.spo2
  const bp = summary?.bp

  return (
    <div style={{ color: c.text, display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Perfil del paciente */}
      <div style={{
        background: c.card,
        borderRadius: 14,
        padding: 20,
        border: `0.5px solid ${c.border}`,
        display: 'flex',
        gap: 20,
        alignItems: 'flex-start',
      }}>
        {/* Avatar */}
        <div style={{
          width: 56,
          height: 56,
          borderRadius: '50%',
          background: colors.teal.main,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#fff',
          fontSize: 18,
          fontWeight: 600,
          flexShrink: 0,
        }}>
          {initials(patientData?.name || patientData?.nombre || '')}
        </div>

        {/* Datos / Formulario */}
        <div style={{ flex: 1 }}>
          {!editing ? (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 24px' }}>
              <Field label="Nombre" value={patientData?.name || patientData?.nombre || '—'} c={c} />
              <Field label="UUID" value={patientData?.uuid || '—'} c={c} />
              <Field label="Edad" value={patientData?.age || patientData?.edad || '—'} c={c} />
              <Field label="Teléfono" value={patientData?.phone || patientData?.telefono || '—'} c={c} />
              <Field label="Condiciones" value={patientData?.conditions || patientData?.condiciones || '—'} c={c} />
              <Field label="Medicamentos" value={patientData?.medications || patientData?.medicamentos || '—'} c={c} />
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px 24px' }}>
              {['name', 'age', 'phone', 'conditions', 'medications', 'allergies'].map(key => (
                <div key={key}>
                  <div style={{
                    fontSize: 10,
                    color: c.muted,
                    textTransform: 'uppercase',
                    marginBottom: 4,
                  }}>
                    {key}
                  </div>
                  <input
                    value={form[key] || ''}
                    onChange={e => setForm((p: any) => ({ ...p, [key]: e.target.value }))}
                    style={{
                      width: '100%',
                      padding: '6px 10px',
                      borderRadius: 8,
                      border: `0.5px solid ${c.border}`,
                      background: c.input,
                      color: c.text,
                      fontSize: 12,
                      outline: 'none',
                    }}
                  />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Botones */}
        <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
          {!editing ? (
            <Btn label="Editar" onClick={() => setEditing(true)} color={colors.teal.main} />
          ) : (
            <>
              <Btn label="Guardar" onClick={savePatient} color={colors.teal.main} />
              <Btn
                label="Cancelar"
                onClick={() => {
                  setEditing(false)
                  setForm(patientData)
                }}
                color={c.muted}
              />
            </>
          )}
        </div>
      </div>

      {/* Últimas lecturas */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
        <MetricCard
          title="Temperatura"
          color={dark ? colors.teal.dark : colors.teal.main}
          value={temp?.temp_c?.toFixed(1) || '—'}
          unit="°C"
          sub={temp?.state?.replace('_', ' ') || '—'}
          ts={fmtTs(temp?.ts)}
          dark={dark}
          c={c}
        />
        <MetricCard
          title="SpO2 / FC"
          color={colors.blue.main}
          value={spo2?.spo2_pct?.toFixed(0) || '—'}
          unit="%"
          sub={`FC ${spo2?.hr_bpm || '—'} bpm`}
          ts={fmtTs(spo2?.ts)}
          dark={dark}
          c={c}
        />
        <MetricCard
          title="Presión arterial"
          color={colors.amber.main}
          value={bp ? `${bp.sys_mmhg?.toFixed(0)}/${bp.dia_mmhg?.toFixed(0)}` : '—'}
          unit="mmHg"
          sub={bp?.category || '—'}
          ts={fmtTs(bp?.ts)}
          dark={dark}
          c={c}
        />
      </div>

      {/* Historial de sesiones */}
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
          Últimas sesiones
        </div>
        {sessions.length === 0 ? (
          <p style={{ fontSize: 12, color: c.muted }}>Sin sesiones registradas</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr>
                {['#', 'Inicio', 'Fin', 'Duración'].map(h => (
                  <th key={h} style={{
                    textAlign: 'left',
                    padding: '6px 10px',
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
                const duration = s.ended_at
                  ? Math.round((s.ended_at - s.started_at) / 60)
                  : null
                return (
                  <tr key={s.id} style={{
                    background: i % 2 === 0
                      ? 'transparent'
                      : dark ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.01)',
                  }}>
                    <td style={{
                      padding: '8px 10px',
                      color: c.sub,
                      borderBottom: `0.5px solid ${c.border}`,
                    }}>
                      #{s.id}
                    </td>
                    <td style={{
                      padding: '8px 10px',
                      color: c.sub,
                      borderBottom: `0.5px solid ${c.border}`,
                    }}>
                      {fmtTs(s.started_at)}
                    </td>
                    <td style={{
                      padding: '8px 10px',
                      color: c.sub,
                      borderBottom: `0.5px solid ${c.border}`,
                    }}>
                      {s.ended_at ? fmtTs(s.ended_at) : (
                        <span style={{ color: colors.teal.main, fontSize: 11 }}>En curso</span>
                      )}
                    </td>
                    <td style={{
                      padding: '8px 10px',
                      color: c.muted,
                      borderBottom: `0.5px solid ${c.border}`,
                    }}>
                      {duration ? `${duration} min` : '—'}
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

function Field({ label, value, c }: { label: string; value: any; c: any }) {
  return (
    <div>
      <div style={{
        fontSize: 10,
        color: c.muted,
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
        marginBottom: 2,
      }}>
        {label}
      </div>
      <div style={{ fontSize: 13, color: c.text }}>{value}</div>
    </div>
  )
}

function Btn({ label, onClick, color }: { label: string; onClick: () => void; color: string }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '6px 14px',
        borderRadius: 8,
        border: 'none',
        background: color,
        color: '#fff',
        fontSize: 12,
        fontWeight: 500,
        cursor: 'pointer',
      }}
    >
      {label}
    </button>
  )
}

function MetricCard({ title, color, value, unit, sub, ts, dark, c }: any) {
  return (
    <div style={{
      background: c.card,
      borderRadius: 14,
      padding: 16,
      border: `0.5px solid ${c.border}`,
      borderLeft: `3px solid ${color}`,
    }}>
      <div style={{
        fontSize: 10,
        textTransform: 'uppercase',
        letterSpacing: '0.08em',
        color: c.muted,
        marginBottom: 8,
      }}>
        {title}
      </div>
      <div>
        <span style={{ fontSize: 26, fontWeight: 500, color }}>{value}</span>
        <span style={{ fontSize: 12, color: c.muted, marginLeft: 4 }}>{unit}</span>
      </div>
      <div style={{ fontSize: 11, color: c.muted, marginTop: 4 }}>{sub}</div>
      <div style={{ fontSize: 10, color: c.muted, marginTop: 6 }}>{ts}</div>
    </div>
  )
}
