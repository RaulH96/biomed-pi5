# processing/pressure.py
# Algoritmo oscilometrico para calculo de presion arterial
import numpy as np
from scipy.signal import butter, filtfilt, find_peaks, savgol_filter
import yaml

with open("config/settings.yaml") as f:
    _cfg = yaml.safe_load(f)["sensors"]["pressure"]

_CAL = _cfg["calibration"]
_ALG = _cfg["algorithm"]
OFFSET_MMHG = _cfg.get("offset_mmhg", 3.8)


def voltaje_a_mmhg(v: float) -> float:
    kpa = (v - 0.2) * (50.0 / (4.7 - 0.2))
    return max(0.0, (kpa * 7.50062) + OFFSET_MMHG)


def filtro_banda(data: np.ndarray, fs: float) -> np.ndarray:
    nyq  = fs / 2.0
    b, a = butter(2, [0.8 / nyq, 4.0 / nyq], btype='band')
    return filtfilt(b, a, np.array(data, dtype=float))


def calcular_bp(presiones: list, tiempos: list) -> tuple[dict | None, str | None]:
    """
    Algoritmo oscilometrico completo.
    Retorna (resultado_dict, None) o (None, mensaje_error).
    """
    p = np.array(presiones, dtype=float)
    t = np.array(tiempos,   dtype=float)

    fs_real = len(t) / (t[-1] - t[0]) if len(t) > 1 else 394.0

    if len(p) < fs_real * 8:
        return None, f"Senal corta ({len(p)/fs_real:.1f}s) necesitas >= 8s"

    osc      = filtro_banda(p, fs_real)
    dist_min = int(fs_real * _ALG["peak_distance"])
    umbral   = np.percentile(np.abs(osc), 75) * 0.3

    picos, _ = find_peaks(osc,
                           height=umbral,
                           distance=dist_min,
                           prominence=np.std(osc) * 0.25)

    if len(picos) < 5:
        return None, f"Pocos picos ({len(picos)})"

    picos = picos[p[picos] > 50]

    if len(picos) < 5:
        return None, f"Picos insuficientes tras filtrar zona baja ({len(picos)})"

    amp     = np.abs(osc[picos])
    p_picos = p[picos]

    wl  = min(11, len(amp) if len(amp) % 2 == 1 else len(amp) - 1)
    wl  = max(wl, 5)
    env = savgol_filter(amp, window_length=wl, polyorder=2) if len(amp) >= 5 else amp.copy()

    idx_max  = np.argmax(env)
    amp_max  = env[idx_max]
    map_mmhg = p_picos[idx_max]

    # Ratios oscilometricos — ajustados empiricamente
    ratio_sys = _ALG["ratio_sys"]
    ratio_dia = _ALG["ratio_dia"]

    idx_sys = 0
    for i in range(idx_max, -1, -1):
        if env[i] <= amp_max * ratio_sys:
            idx_sys = i; break
    sys_crudo = p_picos[idx_sys]

    idx_dia = len(env) - 1
    for i in range(idx_max, len(env)):
        if env[i] <= amp_max * ratio_dia:
            idx_dia = i; break
    dia_crudo = p_picos[idx_dia]

    # FC
    intervalos = np.diff(t[picos])
    intervalos = intervalos[
        (intervalos > _ALG["hr_interval_min"]) &
        (intervalos < _ALG["hr_interval_max"])
    ]
    hr = int(60.0 / np.median(intervalos)) if len(intervalos) >= 3 else 0

    # Calibracion empirica — regresion lineal
    sys_cal = sys_crudo * _CAL["sys_scale"] + _CAL["sys_offset"]
    dia_cal = dia_crudo * _CAL["dia_scale"] + _CAL["dia_offset"]

    return {
        'sys': round(sys_cal, 1),
        'dia': round(dia_cal, 1),
        'map': round(map_mmhg, 1),
        'hr':  hr,
        'n_picos': len(picos),
        'sys_crudo': sys_crudo,
        'dia_crudo': dia_crudo,
        'osc': osc, 'picos': picos, 'env': env,
        'p_arr': p, 't_arr': t, 'p_picos': p_picos,
        'idx_max': idx_max, 'idx_sys': idx_sys, 'idx_dia': idx_dia,
    }, None


def classify_bp(sys: float, dia: float) -> tuple[str, str]:
    """Retorna (categoria, color_hex) segun JNC/AHA"""
    if sys >= 140 or dia >= 90:
        return "Hipertension", "#E8845A"
    elif sys >= 130 or dia >= 80:
        return "Elevada",      "#F0A830"
    else:
        return "Normal",       "#45C07A"
