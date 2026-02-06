"""
Cargador de configuración.
"""

import yaml
from pathlib import Path
from typing import Dict, Any


def load_config(config_path: str = "config/settings.yaml") -> Dict[str, Any]:
    """
    Carga la configuración desde un archivo YAML.
    
    Args:
        config_path: Ruta al archivo de configuración
        
    Returns:
        Diccionario con la configuración
    """
    path = Path(config_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Archivo de configuración no encontrado: {path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config or {}


def load_linkedin_config() -> Dict[str, Any]:
    """Carga la configuración de LinkedIn."""
    return load_config("config/linkedin_config.yaml")


def get_setting(key: str, default: Any = None) -> Any:
    """
    Obtiene un valor de configuración por clave.
    Soporta claves anidadas con punto (ej: "ollama.model")
    
    Args:
        key: Clave de configuración
        default: Valor por defecto si no existe
        
    Returns:
        El valor de configuración
    """
    try:
        config = load_config()
        
        # Navegar por claves anidadas
        keys = key.split('.')
        value = config
        for k in keys:
            value = value[k]
        
        return value
        
    except (KeyError, TypeError, FileNotFoundError):
        return default
