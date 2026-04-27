import numpy as np
from scipy.ndimage import label

# Límites fisiológicos absolutos
SKIN_MIN = 28.0   # hipotermia moderada
SKIN_MAX = 42.0   # fiebre extrema
MIN_PIXELS = 12
AMBIENT_MARGIN = 3.0  # °C mínimo sobre el ambiente para considerar piel

def get_body_temperature(matrix: np.ndarray, offset: float = 0.0) -> float | None:
    """
    Recibe matriz (24, 32), detecta región corporal y retorna
    temperatura en °C corregida con offset de calibración.
    Retorna None si no detecta persona.

    offset: diferencia empírica entre lectura del sensor y
            termómetro de referencia (ej. bucal). Se suma al resultado.
    """
    # Temperatura ambiente estimada como percentil 10 del frame
    ambient = float(np.percentile(matrix, 10))

    # Umbral dinámico — evita rango fijo que excluye fiebre o hipotermia
    dynamic_min = max(SKIN_MIN, ambient + AMBIENT_MARGIN)

    mask = (matrix >= dynamic_min) & (matrix <= SKIN_MAX)
    labeled, num_regions = label(mask)

    if num_regions == 0:
        return None

    # Tomar la región conectada más grande
    sizes = [np.sum(labeled == i) for i in range(1, num_regions + 1)]
    largest = np.argmax(sizes) + 1

    if sizes[largest - 1] < MIN_PIXELS:
        return None  # demasiado pequeño, probablemente ruido

    roi = matrix[labeled == largest]

    # P95 — ignora píxeles fríos de cabello/ropa sin dispararse con outliers
    raw = float(np.percentile(roi, 95))
    return round(raw + offset, 1)


def classify_temperature(temp: float) -> str:
    """
    Clasifica la temperatura corporal.
    Basado en equivalencia a temperatura bucal (ya con offset aplicado).
    """
    if temp < 35.0:
        return "hipotermia"
    elif temp < 36.1:
        return "normal_baja"
    elif temp <= 37.2:
        return "normal"
    elif temp <= 38.0:
        return "febricula"
    elif temp <= 39.0:
        return "fiebre_moderada"
    elif temp <= 40.0:
        return "fiebre_alta"
    else:
        return "fiebre_muy_alta"


def get_scene_stats(matrix: np.ndarray) -> dict:
    """Stats generales de la escena para logging y debug"""
    return {
        "max_c": round(float(matrix.max()), 2),
        "min_c": round(float(matrix.min()), 2),
        "mean_c": round(float(matrix.mean()), 2),
        "ambient_estimated_c": round(float(np.percentile(matrix, 10)), 2),
    }