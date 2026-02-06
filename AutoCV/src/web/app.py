"""
AutoCV Web Interface - Aplicación web para gestionar CVs personalizados.
"""

import asyncio
import json
import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn
import yaml

# Configurar loguru para reducir spam
from loguru import logger
import logging

# Reducir nivel de log para módulos ruidosos
logger.remove()  # Eliminar handler por defecto
logger.add(sys.stderr, level="INFO")  # Solo INFO y superior

# Añadir el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.core.profile_manager import ProfileManager
from src.core.cv_generator import CVGenerator
from src.scraper.linkedin_scraper import LinkedInScraper
from src.ai.ollama_client import OllamaClient

app = FastAPI(
    title="AutoCV",
    description="Generador Automático de CVs Personalizados",
    version="1.0.0"
)

# Configurar templates y archivos estáticos
TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

TEMPLATES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Estado global de la aplicación
app_state = {
    "current_task": None,
    "task_progress": 0,
    "task_message": "",
    "task_logs": [],
    # Caché de Ollama para evitar crear instancias constantemente
    "ollama_available": None,
    "ollama_model": None,
    "ollama_last_check": 0
}


# ============================================================================
# Modelos Pydantic
# ============================================================================

class SearchRequest(BaseModel):
    keywords: str
    location: str = "Madrid"
    limit: int = 10
    fast_mode: bool = True
    fetch_descriptions: bool = True

class GenerateRequest(BaseModel):
    job_id: str
    include_cover_letter: bool = True

class ProfileUpdate(BaseModel):
    content: str


# ============================================================================
# Rutas de la API
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Página principal - Dashboard."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "page": "dashboard"
    })


@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """Página de perfil."""
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "page": "profile"
    })


@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    """Página de búsqueda."""
    return templates.TemplateResponse("search.html", {
        "request": request,
        "page": "search"
    })


@app.get("/jobs", response_class=HTMLResponse)
async def jobs_page(request: Request):
    """Página de ofertas."""
    return templates.TemplateResponse("jobs.html", {
        "request": request,
        "page": "jobs"
    })


@app.get("/generated", response_class=HTMLResponse)
async def generated_page(request: Request):
    """Página de CVs generados."""
    return templates.TemplateResponse("generated.html", {
        "request": request,
        "page": "generated"
    })


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Página de configuración."""
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "page": "settings"
    })


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/api/status")
async def get_status():
    """Estado del sistema."""
    import time
    
    # Verificar Ollama solo cada 30 segundos (cacheado)
    current_time = time.time()
    if app_state["ollama_available"] is None or (current_time - app_state["ollama_last_check"]) > 30:
        try:
            # Crear cliente sin loggear cada vez
            import logging
            logging.getLogger("src.ai.ollama_client").setLevel(logging.WARNING)
            
            client = OllamaClient()
            app_state["ollama_available"] = client.is_available()
            app_state["ollama_model"] = client.model
        except Exception as e:
            app_state["ollama_available"] = False
            app_state["ollama_model"] = f"Error: {str(e)}"
        app_state["ollama_last_check"] = current_time
    
    # Contar ofertas y CVs
    try:
        jobs_count = len(list((ROOT_DIR / "data" / "ofertas").glob("*.json")))
        cvs_count = len(list((ROOT_DIR / "data" / "cvs_generados").glob("*.html")))
    except:
        jobs_count = 0
        cvs_count = 0
    
    # Verificar perfil
    profile_exists = (ROOT_DIR / "data" / "mi_perfil.yaml").exists()
    
    return {
        "ollama_available": app_state["ollama_available"],
        "ollama_model": app_state["ollama_model"],
        "jobs_count": jobs_count,
        "cvs_count": cvs_count,
        "profile_configured": profile_exists,
        "current_task": app_state["current_task"],
        "task_progress": app_state["task_progress"],
        "task_message": app_state["task_message"]
    }


@app.get("/api/profile")
async def get_profile():
    """Obtiene el perfil actual."""
    try:
        profile_path = ROOT_DIR / "data" / "mi_perfil.yaml"
        pm = ProfileManager(str(profile_path))
        profile = pm.load_profile()
        
        # También devolver el YAML raw
        raw_yaml = ""
        if profile_path.exists():
            with open(profile_path, 'r', encoding='utf-8') as f:
                raw_yaml = f.read()
        
        return {
            "profile": profile,
            "raw_yaml": raw_yaml
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/profile")
async def update_profile(data: ProfileUpdate):
    """Actualiza el perfil."""
    try:
        # Validar YAML
        yaml.safe_load(data.content)
        
        profile_path = ROOT_DIR / "data" / "mi_perfil.yaml"
        with open(profile_path, 'w', encoding='utf-8') as f:
            f.write(data.content)
        
        return {"success": True, "message": "Perfil actualizado correctamente"}
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Error en formato YAML: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs")
async def get_jobs():
    """Lista todas las ofertas guardadas."""
    jobs = []
    jobs_dir = ROOT_DIR / "data" / "ofertas"
    
    for job_file in jobs_dir.glob("*.json"):
        try:
            with open(job_file, 'r', encoding='utf-8') as f:
                job = json.load(f)
                jobs.append(job)
        except:
            continue
    
    # Ordenar por fecha
    jobs.sort(key=lambda x: x.get('scraped_at', ''), reverse=True)
    return {"jobs": jobs}


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """Obtiene una oferta específica."""
    jobs_dir = ROOT_DIR / "data" / "ofertas"
    
    for job_file in jobs_dir.glob("*.json"):
        if job_id in job_file.stem:
            with open(job_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    raise HTTPException(status_code=404, detail="Oferta no encontrada")


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """Elimina una oferta."""
    jobs_dir = ROOT_DIR / "data" / "ofertas"
    
    for job_file in jobs_dir.glob("*.json"):
        if job_id in job_file.stem:
            job_file.unlink()
            return {"success": True, "message": "Oferta eliminada"}
    
    raise HTTPException(status_code=404, detail="Oferta no encontrada")


@app.post("/api/search")
async def search_jobs(data: SearchRequest, background_tasks: BackgroundTasks):
    """Inicia una búsqueda de ofertas."""
    if app_state["current_task"]:
        raise HTTPException(status_code=400, detail="Ya hay una tarea en ejecución")
    
    app_state["current_task"] = "search"
    app_state["task_progress"] = 0
    app_state["task_message"] = "Iniciando búsqueda..."
    app_state["task_logs"] = []
    
    background_tasks.add_task(
        _run_search,
        data.keywords,
        data.location,
        data.limit,
        data.fast_mode,
        data.fetch_descriptions
    )
    
    return {"success": True, "message": "Búsqueda iniciada"}


@app.post("/api/generate")
async def generate_cv(data: GenerateRequest, background_tasks: BackgroundTasks):
    """Genera un CV para una oferta."""
    if app_state["current_task"]:
        raise HTTPException(status_code=400, detail="Ya hay una tarea en ejecución")
    
    app_state["current_task"] = "generate"
    app_state["task_progress"] = 0
    app_state["task_message"] = "Iniciando generación..."
    app_state["task_logs"] = []
    
    background_tasks.add_task(
        _run_generate,
        data.job_id,
        data.include_cover_letter
    )
    
    return {"success": True, "message": "Generación iniciada"}


@app.get("/api/generated")
async def get_generated_cvs():
    """Lista todos los CVs generados."""
    cvs = []
    cvs_dir = ROOT_DIR / "data" / "cvs_generados"
    
    for cv_file in cvs_dir.glob("cv_*.html"):
        stat = cv_file.stat()
        cvs.append({
            "filename": cv_file.name,
            "path": str(cv_file),
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "size": stat.st_size,
            "type": "cv"
        })
    
    for letter_file in cvs_dir.glob("carta_*.html"):
        stat = letter_file.stat()
        cvs.append({
            "filename": letter_file.name,
            "path": str(letter_file),
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "size": stat.st_size,
            "type": "cover_letter"
        })
    
    cvs.sort(key=lambda x: x['created_at'], reverse=True)
    return {"files": cvs}


@app.get("/api/generated/{filename}")
async def get_generated_file(filename: str):
    """Obtiene un archivo generado."""
    file_path = ROOT_DIR / "data" / "cvs_generados" / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    return FileResponse(file_path)


@app.delete("/api/generated/{filename}")
async def delete_generated_file(filename: str):
    """Elimina un archivo generado."""
    file_path = ROOT_DIR / "data" / "cvs_generados" / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    file_path.unlink()
    return {"success": True, "message": "Archivo eliminado"}


@app.get("/api/settings")
async def get_settings():
    """Obtiene la configuración."""
    import sys
    import requests
    
    config = _load_config()
    linkedin_config = _load_linkedin_config()
    
    # Obtener modelos disponibles de Ollama
    available_models = []
    try:
        ollama_host = config.get('ollama', {}).get('host', 'http://localhost:11434')
        response = requests.get(f"{ollama_host}/api/tags", timeout=5)
        if response.status_code == 200:
            models_data = response.json()
            available_models = [m['name'] for m in models_data.get('models', [])]
    except:
        available_models = ['qwen3:4b', 'llama3.2', 'mistral', 'gemma2']  # Defaults
    
    # Convertir config a formato plano para el frontend
    flat_settings = {
        'ollama_base_url': config.get('ollama', {}).get('host', 'http://localhost:11434'),
        'ollama_model': config.get('ollama', {}).get('model', 'qwen3:4b'),
        'temperature': config.get('ollama', {}).get('temperature', 0.3),
        'max_results': config.get('linkedin', {}).get('search_limit', 10),
        'min_delay': config.get('linkedin', {}).get('delay_between_requests', 3),
        'max_delay': config.get('linkedin', {}).get('delay_between_requests', 3) + 2,
        'headless': config.get('linkedin', {}).get('headless', True),
        'output_format': config.get('cv_generation', {}).get('output_format', 'html'),
        'output_dir': config.get('paths', {}).get('generated_cvs', 'data/cvs_generados'),
        'generate_cover_letter': True
    }
    
    return {
        "settings": flat_settings,
        "linkedin": linkedin_config,
        "available_models": available_models,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "workspace_dir": str(ROOT_DIR)
    }


@app.post("/api/settings")
async def update_settings(data: dict):
    """Actualiza la configuración."""
    try:
        config_path = ROOT_DIR / "config" / "settings.yaml"
        
        # Cargar config actual
        config = _load_config()
        
        # Actualizar con los nuevos valores
        if 'ollama' not in config:
            config['ollama'] = {}
        config['ollama']['host'] = data.get('ollama_base_url', 'http://localhost:11434')
        config['ollama']['model'] = data.get('ollama_model', 'qwen3:4b')
        config['ollama']['temperature'] = float(data.get('temperature', 0.3))
        
        if 'linkedin' not in config:
            config['linkedin'] = {}
        config['linkedin']['search_limit'] = int(data.get('max_results', 10))
        config['linkedin']['delay_between_requests'] = int(data.get('min_delay', 3))
        config['linkedin']['headless'] = data.get('headless', True)
        
        if 'cv_generation' not in config:
            config['cv_generation'] = {}
        config['cv_generation']['output_format'] = data.get('output_format', 'html')
        
        # Guardar
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        
        # Invalidar caché de Ollama para que tome los nuevos valores
        app_state["ollama_last_check"] = 0
        
        return {"success": True, "message": "Configuración guardada"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/task/status")
async def get_task_status():
    """Estado de la tarea actual."""
    return {
        "current_task": app_state["current_task"],
        "progress": app_state["task_progress"],
        "message": app_state["task_message"],
        "logs": app_state["task_logs"][-20:]  # Últimos 20 logs
    }


# ============================================================================
# Funciones auxiliares
# ============================================================================

def _load_config() -> Dict[str, Any]:
    """Carga la configuración general."""
    config_path = ROOT_DIR / "config" / "settings.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


def _load_linkedin_config() -> Dict[str, Any]:
    """Carga la configuración de LinkedIn."""
    config_path = ROOT_DIR / "config" / "linkedin_config.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


def _log(message: str):
    """Añade un mensaje al log."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    app_state["task_logs"].append(f"[{timestamp}] {message}")
    app_state["task_message"] = message


def _sync_search(keywords: str, location: str, limit: int, fast_mode: bool = True, fetch_descriptions: bool = True):
    """Ejecuta la búsqueda de forma síncrona (para ejecutar en thread)."""
    try:
        mode_msg = "🚀 Modo rápido" if fast_mode else "🐢 Modo normal"
        _log(f"{mode_msg} - Buscando: {keywords} en {location}")
        app_state["task_progress"] = 10
        
        config = _load_config()
        # La configuración de headless está en linkedin, no en scraper
        headless = config.get('linkedin', {}).get('headless', True)
        # Usar navegador existente si no es headless (abre en pestaña del Chrome actual)
        use_existing_browser = config.get('linkedin', {}).get('use_existing_browser', not headless)
        
        if use_existing_browser:
            _log("Conectando a Chrome existente (puerto 9222)...")
        else:
            _log("Inicializando navegador...")
        app_state["task_progress"] = 20
        
        scraper = LinkedInScraper(headless=headless, use_existing_browser=use_existing_browser)
        
        _log("Buscando ofertas en LinkedIn...")
        app_state["task_progress"] = 30
        
        jobs = scraper.search_jobs(
            keywords=keywords,
            location=location,
            limit=limit,
            fast_mode=fast_mode,
            fetch_descriptions=fetch_descriptions
        )
        
        app_state["task_progress"] = 90
        _log(f"Se encontraron {len(jobs)} ofertas")
        
        scraper.close()
        
        app_state["task_progress"] = 100
        _log("Búsqueda completada")
        
        return jobs
        
    except Exception as e:
        _log(f"Error: {str(e)}")
        _log(f"Detalle: {traceback.format_exc()}")
        raise
    finally:
        app_state["current_task"] = None


async def _run_search(keywords: str, location: str, limit: int, fast_mode: bool = True, fetch_descriptions: bool = True):
    """Ejecuta la búsqueda en background usando un thread."""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        await loop.run_in_executor(
            executor,
            _sync_search,
            keywords,
            location,
            limit,
            fast_mode,
            fetch_descriptions
        )


def _sync_generate(job_id: str, include_cover_letter: bool):
    """Ejecuta la generación de forma síncrona (para ejecutar en thread)."""
    try:
        _log(f"Generando CV para oferta: {job_id}")
        app_state["task_progress"] = 10
        
        profile_path = ROOT_DIR / "data" / "mi_perfil.yaml"
        pm = ProfileManager(str(profile_path))
        profile = pm.load_profile()
        
        _log("Perfil cargado")
        app_state["task_progress"] = 20
        
        generator = CVGenerator()
        
        _log("Personalizando CV con IA...")
        app_state["task_progress"] = 30
        
        result = generator.generate(
            profile=profile,
            job_id=job_id,
            output_format="html",
            include_cover_letter=include_cover_letter
        )
        
        app_state["task_progress"] = 90
        _log(f"CV generado: {result.get('cv', 'N/A')}")
        
        if result.get('cover_letter'):
            _log(f"Carta generada: {result.get('cover_letter')}")
        
        app_state["task_progress"] = 100
        _log("Generación completada")
        
        return result
        
    except Exception as e:
        _log(f"Error: {str(e)}")
        _log(f"Detalle: {traceback.format_exc()}")
        raise
    finally:
        app_state["current_task"] = None


async def _run_generate(job_id: str, include_cover_letter: bool):
    """Ejecuta la generación en background usando un thread."""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        await loop.run_in_executor(
            executor,
            _sync_generate,
            job_id,
            include_cover_letter
        )


# ============================================================================
# Punto de entrada
# ============================================================================

def run_server(host: str = None, port: int = None):
    """Inicia el servidor web."""
    import webbrowser
    import socket
    
    # Cargar configuración
    config = _load_config()
    web_config = config.get('web', {})
    
    # Usar parámetros o configuración o valores por defecto
    if host is None:
        if web_config.get('allow_remote', False):
            host = "0.0.0.0"
        else:
            host = web_config.get('host', '127.0.0.1')
    
    if port is None:
        port = web_config.get('port', 8080)
    
    open_browser = web_config.get('open_browser', True)
    
    # Obtener IP local para mostrar
    local_ip = "127.0.0.1"
    if host == "0.0.0.0":
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except:
            pass
    
    print(f"\n🚀 AutoCV Web Interface")
    print(f"   ─────────────────────────────────────")
    if host == "0.0.0.0":
        print(f"   📍 Local:   http://127.0.0.1:{port}")
        print(f"   🌐 Red:     http://{local_ip}:{port}")
        print(f"   ⚠️  Acceso remoto ACTIVADO")
    else:
        print(f"   📍 URL:     http://{host}:{port}")
        print(f"   💡 Para acceso remoto, configura 'allow_remote: true' en settings.yaml")
    print(f"   ─────────────────────────────────────")
    print(f"   Presiona Ctrl+C para detener\n")
    
    # Abrir navegador automáticamente
    if open_browser:
        url = f"http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}"
        webbrowser.open(url)
    
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    run_server()
