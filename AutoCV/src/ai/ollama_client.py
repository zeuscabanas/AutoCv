"""
Cliente de Ollama - Conexión con el modelo de IA local.
"""

import requests
import json
from typing import Optional, List, Dict, Any, Generator
from loguru import logger
from pathlib import Path
import yaml


class OllamaClient:
    """Cliente para interactuar con Ollama API."""
    
    def __init__(self, host: str = None, model: str = None):
        """
        Inicializa el cliente de Ollama.
        
        Args:
            host: URL del servidor Ollama (default: http://localhost:11434)
            model: Modelo a usar (default: qwen3:4b)
        """
        # Cargar configuración
        config = self._load_config()
        ollama_config = config.get('ollama', {})
        
        self.host = host or ollama_config.get('host', 'http://localhost:11434')
        self.model = model or ollama_config.get('model', 'qwen3:4b')
        self.timeout = ollama_config.get('timeout', 120)
        self.temperature = ollama_config.get('temperature', 0.3)
        self.max_tokens = ollama_config.get('max_tokens', 4096)
        
        # Solo log en primer uso o cambio
        if not hasattr(OllamaClient, '_initialized'):
            logger.info(f"OllamaClient: {self.host}, modelo: {self.model}")
            OllamaClient._initialized = True
    
    def _load_config(self) -> Dict[str, Any]:
        """Carga la configuración desde el archivo."""
        # Buscar config en varias ubicaciones
        possible_paths = [
            Path("config/settings.yaml"),
            Path(__file__).parent.parent.parent / "config" / "settings.yaml",
        ]
        for config_path in possible_paths:
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
        return {}
    
    def is_available(self) -> bool:
        """Verifica si Ollama está disponible (alias de check_connection)."""
        return self.check_connection()
    
    def check_connection(self) -> bool:
        """Verifica la conexión con Ollama."""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"Error conectando a Ollama: {e}")
            return False
    
    def list_models(self) -> List[str]:
        """Lista los modelos disponibles en Ollama."""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=10)
            response.raise_for_status()
            data = response.json()
            return [model['name'] for model in data.get('models', [])]
        except requests.RequestException as e:
            logger.error(f"Error listando modelos: {e}")
            return []
    
    def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = None,
        max_tokens: int = None,
        stream: bool = False
    ) -> str:
        """
        Genera una respuesta usando Ollama.
        
        Args:
            prompt: El prompt principal
            system_prompt: Prompt del sistema (opcional)
            temperature: Temperatura para la generación
            max_tokens: Máximo de tokens a generar
            stream: Si usar streaming (no implementado aún)
            
        Returns:
            La respuesta generada
        """
        url = f"{self.host}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature or self.temperature,
                "num_predict": max_tokens or self.max_tokens,
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            logger.debug(f"Enviando prompt a Ollama ({len(prompt)} chars)")
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            generated_text = result.get('response', '')
            
            logger.debug(f"Respuesta recibida ({len(generated_text)} chars)")
            return generated_text
            
        except requests.Timeout:
            logger.error("Timeout en la generación")
            raise TimeoutError("Ollama tardó demasiado en responder")
        except requests.RequestException as e:
            logger.error(f"Error en la generación: {e}")
            raise
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None
    ) -> str:
        """
        Genera una respuesta usando el formato de chat.
        
        Args:
            messages: Lista de mensajes [{"role": "user/assistant/system", "content": "..."}]
            temperature: Temperatura para la generación
            
        Returns:
            La respuesta generada
        """
        url = f"{self.host}/api/chat"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature or self.temperature,
            }
        }
        
        try:
            logger.debug(f"Enviando chat a Ollama ({len(messages)} mensajes)")
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            return result.get('message', {}).get('content', '')
            
        except requests.RequestException as e:
            logger.error(f"Error en el chat: {e}")
            raise
    
    def generate_stream(
        self,
        prompt: str,
        system_prompt: str = None
    ) -> Generator[str, None, None]:
        """
        Genera una respuesta en streaming.
        
        Yields:
            Tokens generados uno a uno
        """
        url = f"{self.host}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": self.temperature,
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            with requests.post(url, json=payload, stream=True, timeout=self.timeout) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line)
                        if 'response' in data:
                            yield data['response']
                        if data.get('done', False):
                            break
                            
        except requests.RequestException as e:
            logger.error(f"Error en streaming: {e}")
            raise
    
    def pull_model(self, model_name: str) -> bool:
        """
        Descarga un modelo en Ollama.
        
        Args:
            model_name: Nombre del modelo a descargar
            
        Returns:
            True si se descargó correctamente
        """
        url = f"{self.host}/api/pull"
        
        try:
            logger.info(f"Descargando modelo: {model_name}")
            response = requests.post(
                url,
                json={"name": model_name},
                stream=True,
                timeout=3600  # 1 hora para descargas grandes
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    status = data.get('status', '')
                    if 'pulling' in status:
                        logger.debug(status)
                    elif 'success' in status:
                        logger.info(f"Modelo {model_name} descargado correctamente")
                        return True
            
            return True
            
        except requests.RequestException as e:
            logger.error(f"Error descargando modelo: {e}")
            return False
    
    def embed(self, text: str) -> List[float]:
        """
        Genera embeddings para un texto.
        
        Args:
            text: Texto a embeber
            
        Returns:
            Vector de embeddings
        """
        url = f"{self.host}/api/embeddings"
        
        try:
            response = requests.post(
                url,
                json={"model": self.model, "prompt": text},
                timeout=self.timeout
            )
            response.raise_for_status()
            
            return response.json().get('embedding', [])
            
        except requests.RequestException as e:
            logger.error(f"Error generando embeddings: {e}")
            return []
