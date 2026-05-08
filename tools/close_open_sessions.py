#!/usr/bin/env python3
"""
Cierra sesiones abiertas (ended_at = NULL) usando el timestamp 
de la última medición de esa sesión + 60 segundos
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'data' / 'storage.db'

def close_open_sessions():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Encontrar sesiones abiertas
    c.execute('SELECT id FROM sessions WHERE ended_at IS NULL')
    open_sessions = [row[0] for row in c.fetchall()]
    
    print(f"Encontradas {len(open_sessions)} sesiones abiertas")
    
    for session_id in open_sessions:
        # Buscar última medición (temp, spo2, o bp)
        c.execute('''
            SELECT MAX(last_ts) FROM (
                SELECT MAX(ts) as last_ts FROM temp_measurements WHERE session_id = ?
                UNION ALL
                SELECT MAX(ts) as last_ts FROM spo2_measurements WHERE session_id = ?
                UNION ALL
                SELECT MAX(ts) as last_ts FROM bp_measurements WHERE session_id = ?
            )
        ''', (session_id, session_id, session_id))
        
        last_ts = c.fetchone()[0]
        
        if last_ts:
            # Cerrar sesión 60 segundos después de última medición
            ended_at = int(last_ts) + 60
            c.execute('UPDATE sessions SET ended_at = ? WHERE id = ?', (ended_at, session_id))
            print(f"  ✓ Sesión #{session_id} cerrada en timestamp {ended_at}")
        else:
            print(f"  ⊘ Sesión #{session_id} sin mediciones, omitida")
    
    conn.commit()
    conn.close()
    print(f"\n✓ Proceso completado")

if __name__ == '__main__':
    close_open_sessions()
