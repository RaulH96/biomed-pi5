'use client'
import { useState } from 'react'
import Sidebar from '@/components/Sidebar'
import PageInicio     from '@/components/pages/PageInicio'
import PageMediciones from '@/components/pages/PageMediciones'
import PagePaciente   from '@/components/pages/PagePaciente'
import PageDoctor     from '@/components/pages/PageDoctor'
import PageAjustes    from '@/components/pages/PageAjustes'

export default function App() {
  const [page, setPage] = useState('inicio')
  const [dark, setDark] = useState(false)

  const t = dark
    ? { bg: '#0F1117', border: '#1E2535', text: '#E4E6EB', muted: '#6B7A99' }
    : { bg: '#FAFBFE', border: '#E2E8F4', text: '#1C2340', muted: '#8892AA' }

  const titles: Record<string, string> = {
    inicio:     'Resumen del día',
    mediciones: 'Mediciones',
    paciente:   'Datos del paciente',
    doctor:     'Vista médica',
    ajustes:    'Ajustes',
  }

  const pages: Record<string, React.ReactElement> = {
    inicio:     <PageInicio dark={dark} />,
    mediciones: <PageMediciones dark={dark} />,
    paciente:   <PagePaciente   dark={dark} />,
    doctor:     <PageDoctor     dark={dark} />,
    ajustes:    <PageAjustes    dark={dark} onToggleDark={() => setDark(!dark)} />,
  }

  return (
    <div style={{ display: 'flex', height: '100vh', background: t.bg, fontFamily: 'system-ui, sans-serif' }}>
      <Sidebar active={page} onNavigate={setPage} dark={dark} />

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* Topbar */}
        <div style={{
          height: 56, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0 24px', borderBottom: `0.5px solid ${t.border}`, background: t.bg, flexShrink: 0
        }}>
          <span style={{ fontSize: 16, fontWeight: 500, color: t.text }}>
            {titles[page]}
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 12, color: t.muted }}>
              {new Date().toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
            </span>
            {/* Toggle dark */}
            <div
              onClick={() => setDark(!dark)}
              style={{ width: 44, height: 24, borderRadius: 12, background: '#2A9080', cursor: 'pointer', position: 'relative' }}
            >
              <div style={{
                position: 'absolute', top: 3, width: 18, height: 18, borderRadius: '50%',
                background: '#fff', transition: 'left .2s', left: dark ? 23 : 3
              }} />
            </div>
            <span style={{ fontSize: 11, color: t.muted }}>{dark ? 'Oscuro' : 'Claro'}</span>
          </div>
        </div>

        {/* Contenido */}
        <div style={{ flex: 1, overflow: 'auto', padding: 24, background: t.bg }}>
          {pages[page]}
        </div>

      </div>
    </div>
  )
}