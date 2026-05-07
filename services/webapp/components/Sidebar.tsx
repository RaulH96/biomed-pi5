'use client'
import { useState, useEffect } from 'react'
import { Home, BarChart2, User, Stethoscope, Settings, ChevronLeft, ChevronRight } from 'lucide-react'
import { fetchPatient } from '@/lib/api'

const NAV = [
  { key: 'inicio',     label: 'Inicio',     icon: Home },
  { key: 'mediciones', label: 'Mediciones', icon: BarChart2 },
  { key: 'paciente',   label: 'Paciente',   icon: User },
  { key: 'doctor',     label: 'Doctor',     icon: Stethoscope },
  { key: 'ajustes',    label: 'Ajustes',    icon: Settings },
]

interface Props {
  active: string
  onNavigate: (key: string) => void
  dark: boolean
}

export default function Sidebar({ active, onNavigate, dark }: Props) {
  const [collapsed, setCollapsed] = useState(false)
  const [patient,   setPatient]   = useState<any>(null)

  useEffect(() => {
    fetchPatient().then(setPatient).catch(() => {})
  }, [])

  const s = dark
    ? { bg: '#13161F', border: '#1E2535', text: '#E4E6EB', muted: '#6B7A99' }
    : { bg: '#FFFFFF',  border: '#E2E8F4', text: '#1C2340', muted: '#8892AA' }

  // Soporta cualquier campo que use patient.json
  const name = patient?.name ?? patient?.nombre ?? ''
  const initials = name
    ? name.split(' ').slice(0, 2).map((w: string) => w[0]).join('').toUpperCase()
    : '?'

  return (
    <div style={{
      width: collapsed ? 60 : 220,
      background: s.bg,
      borderRight: `0.5px solid ${s.border}`,
      display: 'flex', flexDirection: 'column',
      transition: 'width .25s', flexShrink: 0,
    }}>
      {/* Logo */}
      <div style={{ padding: '18px 14px 14px', display: 'flex', alignItems: 'center', gap: 10, borderBottom: `0.5px solid ${s.border}` }}>
        <div style={{ width: 32, height: 32, borderRadius: 10, background: '#2A9080', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 14, fontWeight: 500, flexShrink: 0 }}>B</div>
        {!collapsed && <span style={{ color: s.text, fontSize: 14, fontWeight: 500, whiteSpace: 'nowrap' }}>Biomed Pi5</span>}
      </div>

      {/* Paciente */}
      {!collapsed && (
        <div style={{ padding: '12px 14px', borderBottom: `0.5px solid ${s.border}`, display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 34, height: 34, borderRadius: '50%', background: '#2A9080', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 12, fontWeight: 500, flexShrink: 0 }}>
            {initials}
          </div>
          <div style={{ overflow: 'hidden' }}>
            <div style={{ fontSize: 12, fontWeight: 500, color: s.text, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {name || 'Sin paciente'}
            </div>
            <div style={{ fontSize: 10, color: s.muted }}>Sesión activa</div>
          </div>
        </div>
      )}

      {/* Nav */}
      <nav style={{ flex: 1, padding: '10px 8px', display: 'flex', flexDirection: 'column', gap: 2 }}>
        {NAV.map(({ key, label, icon: Icon }) => {
          const isActive = active === key
          return (
            <button key={key} onClick={() => onNavigate(key)} style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: collapsed ? '9px 0' : '9px 10px',
              justifyContent: collapsed ? 'center' : 'flex-start',
              borderRadius: 10, border: 'none', cursor: 'pointer', width: '100%',
              background: isActive ? (dark ? '#0D2E28' : '#E8F6F3') : 'transparent',
              color: isActive ? '#2A9080' : s.muted,
              fontWeight: isActive ? 500 : 400, fontSize: 13,
              transition: 'background .15s',
            }}>
              <Icon size={18} style={{ flexShrink: 0 }} />
              {!collapsed && <span style={{ whiteSpace: 'nowrap' }}>{label}</span>}
            </button>
          )
        })}
      </nav>

      {/* Footer */}
      <div style={{ padding: '10px 8px', borderTop: `0.5px solid ${s.border}` }}>
        {!collapsed && <div style={{ fontSize: 10, color: s.muted, padding: '0 10px 6px' }}>v1.0.0 · pi5-001</div>}
        <button onClick={() => setCollapsed(!collapsed)} style={{
          width: '100%', display: 'flex', alignItems: 'center', justifyContent: collapsed ? 'center' : 'flex-end',
          padding: '6px 10px', borderRadius: 8, border: 'none', cursor: 'pointer',
          background: 'transparent', color: s.muted, gap: 6, fontSize: 12,
        }}>
          {!collapsed && <span>Colapsar</span>}
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>
    </div>
  )
}