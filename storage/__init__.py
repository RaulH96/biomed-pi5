"""
Storage module - Gestión de sesiones y persistencia
"""
from pathlib import Path
from storage.session_manager import SessionManager

# Instancia global del session manager
session_manager = None

def init_session_manager(patient_config_path: Path = None):
    """Inicializa el session manager global"""
    global session_manager
    session_manager = SessionManager.get()
    return session_manager

# Exportar para uso externo
__all__ = ['session_manager', 'init_session_manager', 'SessionManager']
