from drivers.mlx90640 import MLX90640Driver
from processing.temperature import get_body_temperature, classify_temperature, get_scene_stats
from core.logger import get_logger
import yaml

log = get_logger(__name__)

# Cargar configuración
with open("config/settings.yaml", "r") as f:
    config = yaml.safe_load(f)

mlx_cfg = config["sensors"]["mlx90640"]
OFFSET = mlx_cfg.get("calibration_offset", 0.0)

# Inicializar driver solo si está habilitado
_driver = MLX90640Driver() if mlx_cfg.get("enabled", True) else None


def read_temperature() -> dict:
    """
    Lee el sensor térmico y retorna dict con todos los datos.
    Retorna dict con body_temp=None si no hay persona detectada.
    """
    if _driver is None:
        return {"enabled": False}

    try:
        matrix = _driver.read_frame()
        body_temp = get_body_temperature(matrix, offset=OFFSET)
        stats = get_scene_stats(matrix)

        result = {
            "enabled": True,
            "body_temp_c": body_temp,
            "classification": classify_temperature(body_temp) if body_temp else None,
            "person_detected": body_temp is not None,
            "scene": stats,
        }

        log.info("temperature_read", extra=result)
        return result

    except Exception as e:
        log.error(f"Error leyendo MLX90640: {e}")
        return {"enabled": True, "error": str(e)}