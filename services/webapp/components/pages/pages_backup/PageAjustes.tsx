'use client'
import { useEffect, useState } from 'react'
import { fetchAdminStatus } from '@/lib/api'

interface Props { dark: boolean; onToggleDark: () => void }

export default function PageAjustes({ dark, onToggleDark }: Props) {
  const [status, setStatus] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  const c = dark
    ? { card: '#161B27', border: '#1E2535', text: '#E4E6EB', muted: '#6B7A99', sub: '#CDD0D8', good: '#2DD4AA', warn: '#F0A830' }
    : { card: '#fff', border: '#E2E8F4', text: '#1C2340', muted: '#8892AA', sub: '#4A5268', good: '#1E8A50', warn: '#F0A830' }

  useEffect(() => {
    fetchAdminStatus()
      .then(setStatus)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, color: c.muted, fontSize: 14 }}>
      Cargando configuración...
    </div>
  )

  const db = status?.db || {}
  const mqtt = status?.mqtt || {}
  const totalUnsynced = (mqtt.unsynced_bp || 0) + (mqtt.unsynced_spo2 || 0) + (mqtt.unsynced_temp || 0)

  return (
    <div style={{ color: c.text, display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Apariencia */}
      <Section title="Apariencia" c={c}>
        <Row label="Modo oscuro" c={c}>
          <Toggle active={dark} onToggle={onToggleDark} />
        </Row>
      </Section>

      {/* Base de datos */}
      <Section title="Base de datos" c={c}>
        <Row label="Sesiones registradas" c={c}>
          <Value val={db.sessions} c={c} />
        </Row>
        <Row label="Lecturas temperatura" c={c}>
          <Value val={db.temp_readings} c={c} />
        </Row>
        <Row label="Lecturas SpO2" c={c}>
          <Value val={db.spo2_readings} c={c} />
        </Row>
        <Row label="Lecturas presión" c={c}>
          <Value val={db.bp_readings} c={c} />
        </Row>
      </Section>

      {/* MQTT */}
      <Section title="MQTT / Sincronización" c={c}>
        <Row label="Broker" c={c}>
          <span style={{ fontSize: 12, color: c.sub }}>
            {mqtt.broker || 'localhost'}:{mqtt.port || 1883}
          </span>
        </Row>
        <Row label="Sin sincronizar BP" c={c}>
          <Badge val={mqtt.unsynced_bp || 0} warn={mqtt.unsynced_bp > 0} c={c} />
        </Row>
        <Row label="Sin sincronizar SpO2" c={c}>
          <Badge val={mqtt.unsynced_spo2 || 0} warn={mqtt.unsynced_spo2 > 0} c={c} />
        </Row>
        <Row label="Sin sincronizar Temp" c={c}>
          <Badge val={mqtt.unsynced_temp || 0} warn={mqtt.unsynced_temp > 0} c={c} />
        </Row>
        <Row label="Estado general" c={c}>
          <span style={{
            fontSize: 12,
            fontWeight: 500,
            color: totalUnsynced === 0 ? c.good : c.warn,
          }}>
            {totalUnsynced === 0 ? '✓ Sincronizado' : `⚠ ${totalUnsynced} pendientes`}
          </span>
        </Row>
      </Section>

      {/* Sistema */}
      <Section title="Sistema" c={c}>
        <Row label="Versión PWA" c={c}>
          <span style={{ fontSize: 12, color: c.sub }}>v1.0.0</span>
        </Row>
        <Row label="Dispositivo" c={c}>
          <span style={{ fontSize: 12, color: c.sub }}>pi5-001</span>
        </Row>
        <Row label="API FastAPI" c={c}>
          <span style={{ fontSize: 12, color: c.sub }}>
            {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}
          </span>
        </Row>
      </Section>
    </div>
  )
}

function Section({ title, c, children }: any) {
  return (
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
        {title}
      </div>
      <div>{children}</div>
    </div>
  )
}

function Row({ label, c, children }: any) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '11px 16px',
      borderBottom: `0.5px solid ${c.border}`,
    }}>
      <span style={{ fontSize: 13, color: c.text }}>{label}</span>
      {children}
    </div>
  )
}

function Value({ val, c }: any) {
  return (
    <span style={{ fontSize: 13, fontWeight: 500, color: c.sub }}>
      {val ?? '—'}
    </span>
  )
}

function Badge({ val, warn, c }: any) {
  const bg = warn
    ? (c.warn === '#F0A830' ? '#FEF3E2' : '#2E1B0D')
    : (c.good === '#1E8A50' ? '#DFF5E8' : '#0D2E22')
  return (
    <span style={{
      fontSize: 11,
      padding: '2px 10px',
      borderRadius: 20,
      fontWeight: 500,
      background: bg,
      color: warn ? c.warn : c.good,
    }}>
      {val}
    </span>
  )
}

function Toggle({ active, onToggle }: { active: boolean; onToggle: () => void }) {
  return (
    <div
      onClick={onToggle}
      style={{
        width: 44,
        height: 24,
        borderRadius: 12,
        background: active ? '#2A9080' : '#CBD2E0',
        cursor: 'pointer',
        position: 'relative',
        transition: 'background .2s',
        flexShrink: 0,
      }}
    >
      <div style={{
        position: 'absolute',
        top: 3,
        left: active ? 23 : 3,
        width: 18,
        height: 18,
        borderRadius: '50%',
        background: '#fff',
        transition: 'left .2s',
      }} />
    </div>
  )
}
