import os
import sys
import atexit
import signal
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
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

    # biomed-control.sh stop/restart terminan la Edge UI con SIGTERM. Por
    # defecto Python muere en seco y la sesión activa queda abierta ("En curso"
    # en la PWA). Se cierra como con la X: closeEvent cierra la sesión (y la
    # publica por MQTT) y apaga sensores y bomba. Luego se sale sin esperar al
    # bucle de Qt ni a los hilos de los sensores, que mantendrían vivo el
    # proceso. El QTimer devuelve el control a Python periódicamente para que
    # el manejador pueda ejecutarse mientras corre el bucle de Qt.
    def _on_sigterm(*_):
        print("[Main] SIGTERM: cerrando sesión y sensores", flush=True)
        try:
            w = globals().get("win")
            if w is not None:
                w.close()
            else:
                cleanup()
        finally:
            sys.stdout.flush()
            os._exit(0)
    signal.signal(signal.SIGTERM, _on_sigterm)
    _signal_timer = QTimer()
    _signal_timer.timeout.connect(lambda: None)
    _signal_timer.start(500)
    app.setStyle("Fusion")
    win = MainWindow()
    
    # Maximizar (pantalla completa pero respetando barra de tareas)
    win.showMaximized()
    
    sys.exit(app.exec())
