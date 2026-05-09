'use client'
import { useEffect, useState } from 'react'
import { fetchBpTrends, fetchSpo2Trends, fetchTempTrends, fetchAlerts, fetchDoctorSessions, fetchSession } from '@/lib/api'
import { colors } from '@/lib/theme'
import WaveformViewer from '@/components/WaveformViewer'

interface Props { dark: boolean }

export default function PageDoctor({ dark }: Props) {
  const [bpTrends, setBpTrends] = useState<any[]>([])
  const [spo2Trends, setSpo2Trends] = useState<any[]>([])
  const [tempTrends, setTempTrends] = useState<any[]>([])
  const [alerts, setAlerts] = useState<any>(null)
  const [sessions, setSessions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedSession, setSelectedSession] = useState<any>(null)
  const [sessionDetail, setSessionDetail] = useState<any>(null)

  // Histograma configuración
  const [histogramMetric, setHistogramMetric] = useState<'temp' | 'spo2' | 'bp'>('temp')
  const [histogramRange, setHistogramRange] = useState<number>(15)

  const c = dark
    ? { card: '#161B27', border: '#1E2535', text: '#E4E6EB', muted: '#6B7A99', sub: '#CDD0D8', bg: '#0F1117' }
    : { card: '#fff', border: '#E2E8F4', text: '#1C2340', muted: '#8892AA', sub: '#4A5268', bg: '#FAFBFE' }

  useEffect(() => {
    Promise.all([
      fetchBpTrends(100),      // Traer más datos para histograma
      fetchSpo2Trends(100),
      fetchTempTrends(100),
      fetchAlerts(),
      fetchDoctorSessions(999), // TODAS las sesiones
    ])
      .then(([bp, spo2, temp, al, sess]) => {
        setBpTrends(bp)
        setSpo2Trends(spo2)
        setTempTrends(temp)
        setAlerts(al)
        setSessions(sess)
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (selectedSession) {
      fetchSession(selectedSession.id)
        .then(setSessionDetail)
    }
  }, [selectedSession])

  const fmtDate = (ts: number) => {
    const d = new Date(ts * 1000)
    return d.toLocaleDateString('es-MX', { day: '2-digit', month: 'short' })
  }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, color: c.muted, fontSize: 14 }}>
      Cargando datos médicos...
    </div>
  )

  const allAlerts = [
    ...(alerts?.bp || []),
    ...(alerts?.spo2 || []),
    ...(alerts?.temp || []),
  ].sort((a, b) => b.ts - a.ts)

  // Datos para histograma
  const getHistogramData = () => {
    let data: number[] = []
    let label = ''
    let unit = ''
    let color = ''

    switch (histogramMetric) {
      case 'temp':
        data = tempTrends.slice(-histogramRange).map((d: any) => d.temp_c)
        label = 'Temperatura'
        unit = '°C'
        color = dark ? colors.teal.dark : colors.teal.main
        break
      case 'spo2':
        data = spo2Trends.slice(-histogramRange).map((d: any) => d.spo2_pct)
        label = 'SpO2'
        unit = '%'
        color = colors.blue.main
        break
      case 'bp':
        data = bpTrends.slice(-histogramRange).map((d: any) => d.sys_mmhg)
        label = 'Presión Sistólica'
        unit = 'mmHg'
        color = colors.amber.main
        break
    }

    return { data, label, unit, color }
  }

  const histogramData = getHistogramData()

  return (
    <div style={{ color: c.text, display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Alertas */}
      <div style={{
        background: c.card,
        borderRadius: 14,
        border: `0.5px solid ${c.border}`,
        padding: 16,
      }}>
        <div style={{
          fontSize: 12,
          fontWeight: 500,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          color: c.muted,
          marginBottom: 12,
        }}>
          ⚠ Alertas recientes
        </div>
        {allAlerts.length === 0 ? (
          <p style={{ fontSize: 12, color: c.muted }}>Sin alertas</p>
        ) : (
          allAlerts.slice(0, 5).map((a: any, i: number) => (
            <div key={i} style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '8px 0',
              borderBottom: i < 4 ? `0.5px solid ${c.border}` : 'none',
            }}>
              <div style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: colors.amber.main,
                flexShrink: 0,
              }} />
              <div style={{ fontSize: 12, flex: 1, color: c.sub }}>
                {a.type === 'bp' && `Presión ${a.sys_mmhg}/${a.dia_mmhg} mmHg · ${a.category}`}
                {a.type === 'spo2' && `SpO2 ${a.spo2_pct}% · FC ${a.hr_bpm} bpm`}
                {a.type === 'temp' && `Temperatura ${a.temp_c}°C · ${a.state}`}
              </div>
              <div style={{ fontSize: 11, color: c.muted }}>{fmtDate(a.ts)}</div>
            </div>
          ))
        )}
      </div>

      {/* NUEVO: Histograma configurable */}
      <div style={{
        background: c.card,
        borderRadius: 14,
        border: `0.5px solid ${c.border}`,
        padding: 16,
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 16,
        }}>
          <div style={{
            fontSize: 12,
            fontWeight: 500,
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            color: c.muted,
          }}>
            📊 Histograma de tendencias
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            {/* Selector de métrica */}
            <select
              value={histogramMetric}
              onChange={(e) => setHistogramMetric(e.target.value as any)}
              style={{
                padding: '6px 10px',
                borderRadius: 6,
                border: `0.5px solid ${c.border}`,
                background: dark ? '#0F1117' : '#F4F6FB',
                color: c.text,
                fontSize: 11,
                cursor: 'pointer',
              }}
            >
              <option value="temp">Temperatura</option>
              <option value="spo2">SpO2</option>
              <option value="bp">Presión Arterial</option>
            </select>

            {/* Selector de rango */}
            <select
              value={histogramRange}
              onChange={(e) => setHistogramRange(Number(e.target.value))}
              style={{
                padding: '6px 10px',
                borderRadius: 6,
                border: `0.5px solid ${c.border}`,
                background: dark ? '#0F1117' : '#F4F6FB',
                color: c.text,
                fontSize: 11,
                cursor: 'pointer',
              }}
            >
              <option value={7}>Últimas 7</option>
              <option value={15}>Últimas 15</option>
              <option value={30}>Últimas 30</option>
              <option value={50}>Últimas 50</option>
            </select>
          </div>
        </div>

        {/* Histograma */}
        <Histogram
          data={histogramData.data}
          label={histogramData.label}
          unit={histogramData.unit}
          color={histogramData.color}
          dark={dark}
          c={c}
        />
      </div>

      {/* Mini tendencias (sin cambios) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
        <TrendCard
          title="Presión arterial"
          color={colors.amber.main}
          data={bpTrends.slice(-7).map((d: any) => d.sys_mmhg)}
          unit="mmHg"
          dark={dark}
          c={c}
        />
        <TrendCard
          title="SpO2"
          color={colors.blue.main}
          data={spo2Trends.slice(-7).map((d: any) => d.spo2_pct)}
          unit="%"
          dark={dark}
          c={c}
        />
        <TrendCard
          title="Temperatura"
          color={dark ? colors.teal.dark : colors.teal.main}
          data={tempTrends.slice(-7).map((d: any) => d.temp_c)}
          unit="°C"
          dark={dark}
          c={c}
        />
      </div>

      {/* Sesiones con señales raw - TODAS */}
      <div style={{
        background: c.card,
        borderRadius: 14,
        border: `0.5px solid ${c.border}`,
        overflow: 'hidden',
      }}>
        <div style={{
          padding: '10px 16px',
          borderBottom: `0.5px solid ${c.border}`,
          fontSize: 11,
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          color: c.muted,
        }}>
          Señales raw disponibles ({sessions.filter(s => s.spo2_count > 0 || s.bp_count > 0).length} sesiones)
        </div>
        {sessions.filter(s => s.spo2_count > 0 || s.bp_count > 0).length === 0 ? (
          <div style={{ padding: 16, fontSize: 12, color: c.muted }}>
            Sin señales registradas
          </div>
        ) : (
          <div style={{ maxHeight: 400, overflow: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead style={{ position: 'sticky', top: 0, background: c.card, zIndex: 1 }}>
                <tr>
                  {['Sesión', 'Fecha', 'SpO2', 'Presión', 'Ver'].map(h => (
                    <th key={h} style={{
                      textAlign: 'left',
                      padding: '8px 16px',
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
                {sessions.filter(s => s.spo2_count > 0 || s.bp_count > 0).map((s: any, i: number) => (
                  <tr key={s.id} style={{
                    background: i % 2 === 0
                      ? 'transparent'
                      : dark ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.01)',
                  }}>
                    <td style={{
                      padding: '8px 16px',
                      color: c.sub,
                      borderBottom: `0.5px solid ${c.border}`,
                    }}>
                      #{s.id}
                    </td>
                    <td style={{
                      padding: '8px 16px',
                      color: c.sub,
                      borderBottom: `0.5px solid ${c.border}`,
                    }}>
                      {fmtDate(s.started_at)}
                    </td>
                    <td style={{
                      padding: '8px 16px',
                      color: c.muted,
                      borderBottom: `0.5px solid ${c.border}`,
                    }}>
                      {s.spo2_count || 0}
                    </td>
                    <td style={{
                      padding: '8px 16px',
                      color: c.muted,
                      borderBottom: `0.5px solid ${c.border}`,
                    }}>
                      {s.bp_count || 0}
                    </td>
                    <td style={{
                      padding: '8px 16px',
                      borderBottom: `0.5px solid ${c.border}`,
                    }}>
                      <button
                        onClick={() => setSelectedSession(s)}
                        style={{
                          padding: '4px 12px',
                          borderRadius: 6,
                          border: 'none',
                          background: colors.teal.main,
                          color: '#fff',
                          fontSize: 11,
                          cursor: 'pointer',
                        }}
                      >
                        Ver señales
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal señal raw */}
      {selectedSession && sessionDetail && (
        <WaveformModal
          session={selectedSession}
          sessionDetail={sessionDetail}
          onClose={() => { setSelectedSession(null); setSessionDetail(null) }}
          dark={dark}
          c={c}
        />
      )}
    </div>
  )
}

// NUEVO: Componente Histograma
function Histogram({ data, label, unit, color, dark, c }: any) {
  if (data.length === 0) {
    return (
      <div style={{ padding: 32, textAlign: 'center', color: c.muted, fontSize: 12 }}>
        Sin datos suficientes
      </div>
    )
  }

  const max = Math.max(...data)
  const min = Math.min(...data)
  const range = max - min || 1
  const avg = data.reduce((a: number, b: number) => a + b, 0) / data.length

  return (
    <div>
      {/* Gráfica */}
      <div style={{
        display: 'flex',
        alignItems: 'flex-end',
        gap: 4,
        height: 180,
        padding: '0 8px',
        marginBottom: 12,
        borderBottom: `1px solid ${c.border}`,
      }}>
        {data.map((val: number, i: number) => {
          const height = ((val - min) / range) * 100 || 50
          return (
            <div
              key={i}
              title={`${val.toFixed(1)} ${unit}`}
              style={{
                flex: 1,
                height: `${height}%`,
                background: color,
                opacity: 0.8,
                borderRadius: '3px 3px 0 0',
                cursor: 'pointer',
                transition: 'opacity 0.2s',
              }}
              onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
              onMouseLeave={(e) => e.currentTarget.style.opacity = '0.8'}
            />
          )
        })}
      </div>

      {/* Estadísticas */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: 12,
        fontSize: 11,
      }}>
        <div>
          <div style={{ color: c.muted }}>Promedio</div>
          <div style={{ color, fontWeight: 500, fontSize: 14 }}>
            {avg.toFixed(1)} {unit}
          </div>
        </div>
        <div>
          <div style={{ color: c.muted }}>Máximo</div>
          <div style={{ color: c.sub, fontWeight: 500, fontSize: 14 }}>
            {max.toFixed(1)} {unit}
          </div>
        </div>
        <div>
          <div style={{ color: c.muted }}>Mínimo</div>
          <div style={{ color: c.sub, fontWeight: 500, fontSize: 14 }}>
            {min.toFixed(1)} {unit}
          </div>
        </div>
        <div>
          <div style={{ color: c.muted }}>Mediciones</div>
          <div style={{ color: c.sub, fontWeight: 500, fontSize: 14 }}>
            {data.length}
          </div>
        </div>
      </div>
    </div>
  )
}

// Resto del código sin cambios (WaveformModal, TrendCard)
function WaveformModal({ session, sessionDetail, onClose, dark, c }: any) {
  const [tab, setTab] = useState<'spo2' | 'bp'>('spo2')
  const [selectedMeasurement, setSelectedMeasurement] = useState<number | null>(null)

  const spo2List = sessionDetail?.spo2 || []
  const bpList = sessionDetail?.bp || []

  useEffect(() => {
    if (tab === 'spo2' && spo2List.length > 0) {
      setSelectedMeasurement(spo2List[0].id)
    } else if (tab === 'bp' && bpList.length > 0) {
      setSelectedMeasurement(bpList[0].id)
    } else {
      setSelectedMeasurement(null)
    }
  }, [tab, sessionDetail])

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0,0,0,0.7)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: 20,
    }}>
      <div style={{
        background: c.card,
        borderRadius: 16,
        padding: 24,
        maxWidth: 900,
        width: '100%',
        maxHeight: '90vh',
        overflow: 'auto',
        border: `0.5px solid ${c.border}`,
      }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 20,
        }}>
          <h3 style={{ fontSize: 16, fontWeight: 500, color: c.text }}>
            Señales raw - Sesión #{session.id}
          </h3>
          <button
            onClick={onClose}
            style={{
              padding: '6px 14px',
              borderRadius: 8,
              border: 'none',
              background: c.muted,
              color: '#fff',
              fontSize: 12,
              cursor: 'pointer',
            }}
          >
            Cerrar
          </button>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 16, borderBottom: `0.5px solid ${c.border}` }}>
          <button
            onClick={() => setTab('spo2')}
            style={{
              padding: '8px 16px',
              border: 'none',
              background: 'transparent',
              color: tab === 'spo2' ? colors.blue.main : c.muted,
              fontSize: 13,
              fontWeight: 500,
              cursor: 'pointer',
              borderBottom: tab === 'spo2' ? `2px solid ${colors.blue.main}` : 'none',
            }}
          >
            SpO2 ({spo2List.length})
          </button>
          <button
            onClick={() => setTab('bp')}
            style={{
              padding: '8px 16px',
              border: 'none',
              background: 'transparent',
              color: tab === 'bp' ? colors.amber.main : c.muted,
              fontSize: 13,
              fontWeight: 500,
              cursor: 'pointer',
              borderBottom: tab === 'bp' ? `2px solid ${colors.amber.main}` : 'none',
            }}
          >
            Presión ({bpList.length})
          </button>
        </div>

        {/* Selector medición */}
        {tab === 'spo2' && spo2List.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 12, color: c.muted, marginBottom: 6, display: 'block' }}>
              Seleccionar medición:
            </label>
            <select
              value={selectedMeasurement || ''}
              onChange={e => setSelectedMeasurement(Number(e.target.value))}
              style={{
                padding: '6px 10px',
                borderRadius: 6,
                border: `0.5px solid ${c.border}`,
                background: dark ? '#0F1117' : '#F4F6FB',
                color: c.text,
                fontSize: 12,
              }}
            >
              {spo2List.map((m: any) => (
                <option key={m.id} value={m.id}>
                  #{m.id} - {new Date(m.ts * 1000).toLocaleTimeString('es-MX')} - {m.spo2_pct}% / {m.hr_bpm}bpm
                </option>
              ))}
            </select>
          </div>
        )}

        {tab === 'bp' && bpList.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 12, color: c.muted, marginBottom: 6, display: 'block' }}>
              Seleccionar medición:
            </label>
            <select
              value={selectedMeasurement || ''}
              onChange={e => setSelectedMeasurement(Number(e.target.value))}
              style={{
                padding: '6px 10px',
                borderRadius: 6,
                border: `0.5px solid ${c.border}`,
                background: dark ? '#0F1117' : '#F4F6FB',
                color: c.text,
                fontSize: 12,
              }}
            >
              {bpList.map((m: any) => (
                <option key={m.id} value={m.id}>
                  #{m.id} - {new Date(m.ts * 1000).toLocaleTimeString('es-MX')} - {m.sys_mmhg}/{m.dia_mmhg} mmHg
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Waveform */}
        <WaveformViewer
          sessionId={session.id}
          measurementId={selectedMeasurement || undefined}
          measurementMeta={
            tab === 'spo2'
              ? spo2List.find((m: any) => m.id === selectedMeasurement)
              : bpList.find((m: any) => m.id === selectedMeasurement)
          }
          type={tab}
          dark={dark}
          c={c}
        />
      </div>
    </div>
  )
}

function TrendCard({ title, color, data, unit, dark, c }: any) {
  const max = Math.max(...data)
  const min = Math.min(...data)
  const range = max - min || 1

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
      <div style={{
        display: 'flex',
        alignItems: 'flex-end',
        gap: 4,
        height: 60,
        marginTop: 8,
      }}>
        {data.map((val: number, i: number) => {
          const height = ((val - min) / range) * 100 || 50
          return (
            <div key={i} style={{
              flex: 1,
              height: `${height}%`,
              background: color,
              opacity: 0.7,
              borderRadius: '2px 2px 0 0',
            }} />
          )
        })}
      </div>
      <div style={{ fontSize: 11, color: c.muted, marginTop: 8 }}>
        Promedio: <span style={{ color }}>{(data.reduce((a: number, b: number) => a + b, 0) / data.length).toFixed(1)}</span> {unit}
      </div>
    </div>
  )
}