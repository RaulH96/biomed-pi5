# biomed-pi5 — Estructura del proyecto
biomed-pi5/
│
├── main.py                       # Punto de entrada, arranca el scheduler
│
├── config/                       # Configuración global
│   ├── settings.yaml             # Intervalos, umbrales, IPs MQTT, flags por sensor
│   └── secrets.yaml              # Credenciales broker (en .gitignore)
│
├── drivers/                      # Comunicación de bajo nivel con cada chip
│   ├── mlx90640.py               # Leer matriz térmica 24×32
│   ├── ads1115.py                # Leer canal ADC 16-bit por I²C
│   ├── max30102.py               # Leer datos crudos SpO2 y pulso
│   └── camera.py                 # Captura de cámara (opcional)
│
├── processing/                   # Algoritmos de cálculo, calibración e IA
│   ├── temperature.py            # Matriz térmica → temperatura corporal (P95 + ROI)
│   ├── pressure.py               # Voltaje MPX5050 → mmHg sistólica/diastólica
│   ├── spo2_hr.py                # Algoritmo fotopletismografía → SpO2 y BPM
│   └── face_ai.py                # Detección de cara en matriz térmica (TFLite)
│
├── core/                         # Núcleo orquestador
│   ├── manager.py                # Coordina drivers y processing
│   ├── scheduler.py              # Frecuencia de muestreo por sensor (APScheduler)
│   └── logger.py                 # Logging estructurado en JSON lines
│
├── comms/                        # Comunicación hacia el exterior
│   ├── mqtt_client.py            # Cliente Paho MQTT con reconexión automática
│   ├── serializer.py             # Arma payload JSON para cada tópico
│   ├── topics.py                 # Constantes: biomed/temp, biomed/spo2, etc.
│   └── tls/                      # Certificados para MQTT seguro (opcional)
│
├── storage/                      # Persistencia local
│   ├── db.py                     # SQLite — historial de lecturas
│   └── csv_export.py             # Exportar sesiones a CSV
│
├── dataset/                      # Datos para entrenar el modelo térmico
│   ├── with_face/                # Matrices .npy capturadas con cara presente
│   └── no_face/                  # Matrices .npy capturadas sin cara
│
├── models/                       # Modelos entrenados listos para inferencia
│                                 # Aquí va el .tflite o .onnx exportado desde la PC
│
├── tests/                        # Pruebas
│   ├── test_sensors.py           # Pruebas unitarias con datos simulados
│   └── mock_data.py              # Datos falsos para desarrollo sin hardware
│
└── tools/                        # Scripts de utilidad y mantenimiento
├── calibrate_pressure.py     # Calibración one-shot del MPX5050
├── collect_dataset.py        # Captura matrices del MLX90640 para el dataset
└── scan_i2c.py               # Detecta direcciones I²C conectadas en el bus
ui/
├── __init__.py
├── main_window.py        # ventana principal con tabs o panel lateral
├── widgets/
│   ├── thermal_widget.py     # visualización MLX90640
│   ├── pressure_widget.py    # baumanómetro animado
│   ├── spo2_widget.py        # señal de pulso en tiempo real
│   └── status_bar.py         # conexión MQTT, estado sensores
└── styles/
    └── theme.qss             # estilos globales


    
python -m venv biomed-pi5/.venv
source biomed-pi5/.venv/bin/activate




