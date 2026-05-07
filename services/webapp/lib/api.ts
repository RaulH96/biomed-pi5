const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`)
  return res.json()
}

export async function fetchPatient() {
  const res = await fetch(`${API_BASE}/patient`)
  return res.json()
}

export async function fetchSummary() {
  const res = await fetch(`${API_BASE}/patient/summary`)
  return res.json()
}

export async function fetchSessions(limit = 20) {
  const res = await fetch(`${API_BASE}/sessions?limit=${limit}`)
  return res.json()
}

export async function fetchSession(id: number) {
  const res = await fetch(`${API_BASE}/sessions/${id}`)
  return res.json()
}

export async function fetchDoctorSessions(limit = 50) {
  const res = await fetch(`${API_BASE}/doctor/sessions?limit=${limit}`)
  return res.json()
}

export async function fetchBpTrends(limit = 20) {
  const res = await fetch(`${API_BASE}/doctor/trends/bp?limit=${limit}`)
  return res.json()
}

export async function fetchSpo2Trends(limit = 20) {
  const res = await fetch(`${API_BASE}/doctor/trends/spo2?limit=${limit}`)
  return res.json()
}

export async function fetchTempTrends(limit = 20) {
  const res = await fetch(`${API_BASE}/doctor/trends/temp?limit=${limit}`)
  return res.json()
}

export async function fetchAlerts() {
  const res = await fetch(`${API_BASE}/doctor/alerts`)
  return res.json()
}

export async function fetchAdminStatus() {
  const res = await fetch(`${API_BASE}/admin/status`)
  return res.json()
}

export async function fetchBpWaveform(sessionId: number, measurementId: number) {
  const res = await fetch(`${API_BASE}/doctor/sessions/${sessionId}/waveform/bp/${measurementId}`)
  return res.json()
}

export async function fetchSpo2Waveform(sessionId: number, measurementId: number) {
  const res = await fetch(`${API_BASE}/doctor/sessions/${sessionId}/waveform/spo2/${measurementId}`)
  return res.json()
}
