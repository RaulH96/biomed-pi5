import sys
import atexit
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow

# Inicializar storage ANTES de crear ventana
import storage

def cleanup():
    """Cerrar sesión al salir"""
    if storage.session_manager and storage.session_manager.has_session():
        storage.session_manager.end_session()
        print("[Cleanup] Sesión cerrada")

if __name__ == "__main__":
    # Inicializar session manager con config de paciente
    patient_config = Path(__file__).parent / 'config' / 'patient.json'
    storage.init_session_manager(patient_config)
    
    # Registrar cleanup para cerrar sesión al salir
    atexit.register(cleanup)
    
    # Arrancar app
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    
    # Maximizar (pantalla completa pero respetando barra de tareas)
    win.showMaximized()
    
    sys.exit(app.exec())
