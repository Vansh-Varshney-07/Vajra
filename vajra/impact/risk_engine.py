import os
import yaml
from typing import Dict, Any, Optional

class RiskEngine:
    """
    Translates physical meteorological outputs (precipitation, wind speed, temperature)
    into standard disaster management threat classifications and actionable advisories.
    """

    DEFAULT_CONFIG_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "configs",
        "impact_thresholds.yaml"
    )

    def __init__(self, config_path: Optional[str] = None):
        cfg_file = config_path or self.DEFAULT_CONFIG_PATH
        if os.path.exists(cfg_file):
            with open(cfg_file, "r") as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {}

    def assess_cyclone_threat(self, wind_kmh: float, rain_mm_12hr: float) -> Dict[str, Any]:
        """Classifies cyclone severity according to IMD wind & rainfall scales."""
        wind_cfg = self.config.get("cyclone", {}).get("wind_kmh", {})
        rain_cfg = self.config.get("cyclone", {}).get("rainfall_mm_12hr", {})

        # Determine wind level
        if wind_kmh >= wind_cfg.get("catastrophic", [167, 9999])[0]:
            level = "CATASTROPHIC"
            color = "RED"
            action = "Mandatory evacuation of 5km coastal zone. Severe storm surge threat."
        elif wind_kmh >= wind_cfg.get("severe", [118, 166])[0]:
            level = "SEVERE"
            color = "RED"
            action = "Immediate shelter in pucca structures. Suspend fishing & coastal operations."
        elif wind_kmh >= wind_cfg.get("moderate", [89, 117])[0]:
            level = "MODERATE"
            color = "ORANGE"
            action = "Be prepared for localized flash flooding, uprooted trees, and power cuts."
        elif wind_kmh >= wind_cfg.get("low", [63, 88])[0]:
            level = "LOW"
            color = "YELLOW"
            action = "Watch situation closely. Secure loose objects and avoid coastal areas."
        else:
            level = "NORMAL"
            color = "GREEN"
            action = "Standard routine conditions."

        return {
            "threat_level": level,
            "color_code": color,
            "peak_wind_kmh": round(wind_kmh, 1),
            "peak_rain_mm_12hr": round(rain_mm_12hr, 1),
            "action_advisory": action
        }

    def assess_heatwave_threat(self, t2m_celsius: float) -> Dict[str, Any]:
        """Classifies heatwave warning levels based on maximum 2m surface temperature."""
        hw_cfg = self.config.get("heatwave", {}).get("t2m_celsius", {})

        if t2m_celsius >= hw_cfg.get("emergency", [47.0, 9999])[0]:
            level = "EMERGENCY"
            color = "RED"
            action = "High probability of heat stroke for all ages. Avoid outdoor exposure 11am-4pm."
        elif t2m_celsius >= hw_cfg.get("warning", [44.1, 46.9])[0]:
            level = "WARNING"
            color = "ORANGE"
            action = "Severe heat stress for vulnerable populations. Maintain continuous hydration."
        elif t2m_celsius >= hw_cfg.get("watch", [40.0, 44.0])[0]:
            level = "WATCH"
            color = "YELLOW"
            action = "Moderate heat. Caution recommended for elderly and children."
        else:
            level = "NORMAL"
            color = "GREEN"
            action = "Temperatures within normal range."

        return {
            "threat_level": level,
            "color_code": color,
            "max_temperature_celsius": round(t2m_celsius, 1),
            "action_advisory": action
        }
