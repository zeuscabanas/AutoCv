"""
LinkedIn Scraper - Extrae ofertas de trabajo de LinkedIn.
"""

import json
import time
import random
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
import hashlib
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.common.exceptions import (
        TimeoutException,
        NoSuchElementException,
        StaleElementReferenceException
    )
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("Selenium no instalado. El scraper no funcionará.")


class LinkedInScraper:
    """Scraper para extraer ofertas de trabajo de LinkedIn."""
    
    # Directorio raíz del proyecto (2 niveles arriba de este archivo)
    ROOT_DIR = Path(__file__).parent.parent.parent
    
    def __init__(self, headless: bool = True, use_existing_browser: bool = False):
        """
        Inicializa el scraper.
        
        Args:
            headless: Si ejecutar el navegador sin ventana visible
            use_existing_browser: Si conectarse a un navegador Chrome existente (puerto 9222)
        """
        self.headless = headless
        self.use_existing_browser = use_existing_browser
        self.driver: Optional[webdriver.Chrome] = None
        self.is_logged_in = False
        self.jobs_dir = self.ROOT_DIR / "data" / "ofertas"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar configuración
        self.config = self._load_config()
        
        # Delay entre requests para evitar ban
        self.min_delay = self.config.get('linkedin', {}).get('delay_between_requests', 1)
        self.max_delay = self.min_delay + 1
        
        # Configuración de velocidad
        self.fast_mode = self.config.get('linkedin', {}).get('fast_mode', True)
        self.max_workers = self.config.get('linkedin', {}).get('max_workers', 5)
    
    def _load_config(self) -> Dict[str, Any]:
        """Carga la configuración."""
        config_path = self.ROOT_DIR / "config" / "settings.yaml"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}
    
    def _load_linkedin_config(self) -> Dict[str, Any]:
        """Carga la configuración específica de LinkedIn."""
        config_path = self.ROOT_DIR / "config" / "linkedin_config.yaml"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}
    
    def _init_driver(self) -> None:
        """Inicializa el driver de Selenium."""
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium no está instalado")
        
        options = Options()
        
        # Si queremos conectar a un navegador existente (debe estar abierto con --remote-debugging-port=9222)
        if self.use_existing_browser:
            options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            try:
                self.driver = webdriver.Chrome(options=options)
                logger.info("Conectado a navegador Chrome existente en puerto 9222")
                # Abrir nueva pestaña
                self.driver.switch_to.new_window('tab')
                return
            except Exception as e:
                logger.warning(f"No se pudo conectar a Chrome existente: {e}")
                logger.info("Abriendo ventana nueva en su lugar...")
                # Continuar con ventana nueva como fallback
                options = Options()
        
        if self.headless:
            options.add_argument("--headless=new")
        
        # Opciones para evitar detección
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Preferencias
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        
        # Ejecutar script para ocultar webdriver
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        
        logger.info("Driver de Chrome inicializado")
    
    def _random_delay(self, min_delay: float = None, max_delay: float = None) -> None:
        """Espera un tiempo aleatorio para parecer humano."""
        min_d = min_delay if min_delay is not None else self.min_delay
        max_d = max_delay if max_delay is not None else self.max_delay
        delay = random.uniform(min_d, max_d)
        time.sleep(delay)
    
    def login(self, email: str = None, password: str = None) -> bool:
        """
        Inicia sesión en LinkedIn.
        
        Args:
            email: Email de LinkedIn
            password: Contraseña
            
        Returns:
            True si el login fue exitoso
        """
        if not self.driver:
            self._init_driver()
        
        # Cargar credenciales desde config si no se proporcionan
        if not email or not password:
            linkedin_config = self._load_linkedin_config()
            credentials = linkedin_config.get('credentials', {})
            email = email or credentials.get('email')
            password = password or credentials.get('password')
        
        if not email or not password:
            logger.error("No se proporcionaron credenciales de LinkedIn")
            return False
        
        try:
            logger.info("Iniciando sesión en LinkedIn...")
            self.driver.get("https://www.linkedin.com/login")
            self._random_delay()
            
            # Rellenar formulario
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            email_field.send_keys(email)
            
            password_field = self.driver.find_element(By.ID, "password")
            password_field.send_keys(password)
            
            # Click en login
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            
            self._random_delay()
            
            # Verificar si hay captcha o verificación
            if "checkpoint" in self.driver.current_url or "challenge" in self.driver.current_url:
                logger.warning("LinkedIn requiere verificación adicional. Por favor, complétala manualmente.")
                input("Presiona Enter cuando hayas completado la verificación...")
            
            # Verificar login exitoso
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-control-name='nav.settings'],.global-nav"))
            )
            
            self.is_logged_in = True
            logger.info("Login exitoso en LinkedIn")
            return True
            
        except TimeoutException:
            logger.error("Timeout durante el login. Verifica las credenciales.")
            return False
        except Exception as e:
            logger.error(f"Error durante el login: {e}")
            return False
    
    def search_jobs(
        self,
        keywords: str,
        location: str = None,
        limit: int = 20,
        filters: Dict[str, Any] = None,
        fetch_descriptions: bool = True,
        fast_mode: bool = None
    ) -> List[Dict[str, Any]]:
        """
        Busca ofertas de trabajo en LinkedIn.
        
        Args:
            keywords: Palabras clave de búsqueda
            location: Ubicación para filtrar
            limit: Número máximo de ofertas a obtener
            filters: Filtros adicionales
            
        Returns:
            Lista de ofertas encontradas
        """
        # Usar modo rápido si se especifica o usar el configurado
        use_fast_mode = fast_mode if fast_mode is not None else self.fast_mode
        
        if not SELENIUM_AVAILABLE:
            logger.warning("Selenium no disponible. Retornando datos de ejemplo.")
            return self._get_sample_jobs(keywords, limit)
        
        if not self.driver:
            self._init_driver()
        
        jobs = []
        
        if use_fast_mode:
            logger.info("🚀 Modo rápido activado - búsqueda optimizada")
        
        try:
            # Construir URL de búsqueda
            search_url = self._build_search_url(keywords, location, filters)
            logger.info(f"Buscando: {search_url}")
            
            self.driver.get(search_url)
            self._random_delay(0.5, 1) if use_fast_mode else self._random_delay()
            
            # Si no está logueado, intentar buscar de forma anónima
            # LinkedIn público usa selectores diferentes
            
            # Esperar a que la página cargue completamente
            time.sleep(1.5 if use_fast_mode else 3)
            
            # Scroll para cargar más ofertas (lazy loading)
            scroll_times = 2 if use_fast_mode else 3
            for _ in range(scroll_times):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.5 if use_fast_mode else 1)
            
            page = 0
            while len(jobs) < limit:
                logger.debug(f"Procesando página {page + 1}...")
                
                # Selectores para LinkedIn público (sin login)
                public_selectors = [
                    ".base-card",  # Selector principal público
                    ".job-search-card",
                    ".base-search-card",
                    "li.jobs-search-results__list-item",
                    ".job-card-container",
                    "[data-tracking-control-name='public_jobs_jserp-result_search-card']"
                ]
                
                # Esperar a que carguen las ofertas con múltiples selectores
                job_cards = []
                try:
                    for selector in public_selectors:
                        try:
                            WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                            )
                            found_cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            if found_cards:
                                job_cards = found_cards
                                logger.debug(f"Encontradas {len(job_cards)} ofertas con selector: {selector}")
                                break
                        except TimeoutException:
                            continue
                    
                    if not job_cards:
                        logger.warning("No se encontraron más ofertas")
                        break
                        
                except TimeoutException:
                    logger.warning("No se encontraron más ofertas")
                    break
                
                # Si aún no hay ofertas, intentar con el HTML directo
                if not job_cards:
                    page_source = self.driver.page_source
                    if "No matching jobs found" in page_source or "No se encontraron" in page_source:
                        logger.warning("LinkedIn indica que no hay resultados")
                        break
                
                for card in job_cards:
                    if len(jobs) >= limit:
                        break
                    
                    try:
                        job_data = self._extract_job_from_card(card)
                        if job_data:
                            jobs.append(job_data)
                            logger.debug(f"Extraída oferta: {job_data.get('title', 'N/A')}")
                    except StaleElementReferenceException:
                        continue
                    except Exception as e:
                        logger.debug(f"Error extrayendo oferta: {e}")
                
                # Ir a siguiente página
                if len(jobs) < limit:
                    if not self._go_to_next_page():
                        break
                    page += 1
                    self._random_delay()
            
            logger.info(f"Se encontraron {len(jobs)} ofertas")
            
            # Obtener descripciones
            if fetch_descriptions:
                if use_fast_mode:
                    # Modo rápido: obtener descripciones en paralelo con requests
                    logger.info("📥 Obteniendo descripciones en paralelo...")
                    jobs = self._fetch_descriptions_parallel(jobs)
                else:
                    # Modo normal: obtener descripciones secuencialmente
                    for job in jobs:
                        if job.get('url'):
                            description = self._get_job_description(job['url'])
                            job['description'] = description
                            self._random_delay(0.5, 1.5)
            else:
                logger.info("⚡ Omitiendo descripciones para búsqueda ultra-rápida")
                for job in jobs:
                    job['description'] = "Descripción no cargada - use vista detallada"
            
            # Guardar ofertas
            for job in jobs:
                self._save_job(job)
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error buscando ofertas: {e}")
            return jobs
    
    def _fetch_descriptions_parallel(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Obtiene las descripciones de múltiples ofertas en paralelo.
        
        Args:
            jobs: Lista de ofertas con URLs
            
        Returns:
            Lista de ofertas con descripciones
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        }
        
        def fetch_description(job: Dict[str, Any]) -> Dict[str, Any]:
            """Obtiene la descripción de una oferta usando requests."""
            url = job.get('url', '')
            if not url:
                job['description'] = "URL no disponible"
                return job
            
            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    html = response.text
                    
                    # Buscar la descripción en el HTML
                    import re
                    
                    # Patrones para extraer descripción
                    patterns = [
                        r'<div class="show-more-less-html__markup[^"]*"[^>]*>(.*?)</div>',
                        r'<div class="description__text[^"]*"[^>]*>(.*?)</div>',
                        r'"description":\s*"([^"]{100,})"',
                    ]
                    
                    description = ""
                    for pattern in patterns:
                        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
                        if match:
                            desc = match.group(1)
                            # Limpiar HTML tags
                            desc = re.sub(r'<[^>]+>', ' ', desc)
                            desc = re.sub(r'\s+', ' ', desc).strip()
                            # Decodificar entidades HTML
                            import html as html_lib
                            desc = html_lib.unescape(desc)
                            if len(desc) > len(description):
                                description = desc
                    
                    if description and len(description) > 50:
                        job['description'] = description[:5000]  # Limitar longitud
                    else:
                        # Fallback: usar Selenium para esta oferta
                        job['description'] = self._get_job_description(url) if self.driver else "Descripción no disponible"
                else:
                    job['description'] = "Error al obtener descripción"
                    
            except Exception as e:
                logger.debug(f"Error obteniendo descripción para {url}: {e}")
                job['description'] = "Descripción no disponible"
            
            return job
        
        # Ejecutar en paralelo
        completed = 0
        total = len(jobs)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_job = {executor.submit(fetch_description, job): job for job in jobs}
            results = []
            
            for future in as_completed(future_to_job):
                result = future.result()
                results.append(result)
                completed += 1
                if completed % 5 == 0 or completed == total:
                    logger.info(f"📊 Progreso: {completed}/{total} descripciones obtenidas")
        
        # Mantener el orden original
        job_dict = {job['id']: job for job in results}
        return [job_dict.get(j['id'], j) for j in jobs]
    
    def _build_search_url(
        self,
        keywords: str,
        location: str = None,
        filters: Dict[str, Any] = None
    ) -> str:
        """Construye la URL de búsqueda de LinkedIn."""
        base_url = "https://www.linkedin.com/jobs/search/?"
        params = [f"keywords={keywords.replace(' ', '%20')}"]
        
        if location:
            params.append(f"location={location.replace(' ', '%20')}")
        
        # Añadir filtros
        if filters:
            # Experiencia
            exp_mapping = {
                "Internship": "1",
                "Entry level": "2",
                "Associate": "3",
                "Mid-Senior level": "4",
                "Director": "5",
                "Executive": "6"
            }
            if 'experience_level' in filters:
                exp_values = [exp_mapping.get(e, "") for e in filters['experience_level']]
                exp_values = [v for v in exp_values if v]
                if exp_values:
                    params.append(f"f_E={'%2C'.join(exp_values)}")
            
            # Tipo de trabajo
            type_mapping = {
                "Full-time": "F",
                "Part-time": "P",
                "Contract": "C",
                "Temporary": "T",
                "Volunteer": "V",
                "Internship": "I"
            }
            if 'job_type' in filters:
                type_values = [type_mapping.get(t, "") for t in filters['job_type']]
                type_values = [v for v in type_values if v]
                if type_values:
                    params.append(f"f_JT={'%2C'.join(type_values)}")
            
            # Remoto
            remote_mapping = {
                "On-site": "1",
                "Remote": "2",
                "Hybrid": "3"
            }
            if 'remote' in filters:
                remote_values = [remote_mapping.get(r, "") for r in filters['remote']]
                remote_values = [v for v in remote_values if v]
                if remote_values:
                    params.append(f"f_WT={'%2C'.join(remote_values)}")
            
            # Fecha de publicación
            date_mapping = {
                "Past 24 hours": "r86400",
                "Past week": "r604800",
                "Past month": "r2592000"
            }
            if 'date_posted' in filters:
                date_value = date_mapping.get(filters['date_posted'], "")
                if date_value:
                    params.append(f"f_TPR={date_value}")
        
        return base_url + "&".join(params)
    
    def _extract_job_from_card(self, card) -> Optional[Dict[str, Any]]:
        """Extrae información de una tarjeta de trabajo."""
        try:
            # Selectores múltiples para compatibilidad
            title_selectors = [
                ".base-search-card__title",
                ".job-card-list__title",
                ".base-card__full-link",
                "h3.base-search-card__title",
                "[data-tracking-control-name='public_jobs_jserp-result_search-card'] h3",
                ".sr-only"
            ]
            
            company_selectors = [
                ".base-search-card__subtitle",
                ".job-card-container__company-name",
                "h4.base-search-card__subtitle",
                ".hidden-nested-link"
            ]
            
            location_selectors = [
                ".job-search-card__location",
                ".job-card-container__metadata-item",
                ".base-search-card__metadata span"
            ]
            
            # Título
            title = None
            for selector in title_selectors:
                try:
                    title_elem = card.find_element(By.CSS_SELECTOR, selector)
                    title = title_elem.text.strip()
                    if title:
                        break
                except:
                    continue
            
            if not title:
                # Intentar con el link
                try:
                    link_elem = card.find_element(By.CSS_SELECTOR, "a")
                    title = link_elem.get_attribute("aria-label") or link_elem.text.strip()
                except:
                    pass
            
            if not title:
                return None
            
            # Empresa
            company = "Empresa no especificada"
            for selector in company_selectors:
                try:
                    company_elem = card.find_element(By.CSS_SELECTOR, selector)
                    company = company_elem.text.strip()
                    if company:
                        break
                except:
                    continue
            
            # Ubicación
            location = "Ubicación no especificada"
            for selector in location_selectors:
                try:
                    location_elem = card.find_element(By.CSS_SELECTOR, selector)
                    location = location_elem.text.strip()
                    if location:
                        break
                except:
                    continue
            
            # URL
            try:
                link_elem = card.find_element(By.CSS_SELECTOR, "a")
                url = link_elem.get_attribute("href")
            except:
                url = ""
            
            # Generar ID único
            job_id = hashlib.md5(f"{title}{company}{url}".encode()).hexdigest()[:12]
            
            return {
                "id": job_id,
                "title": title,
                "company": company,
                "location": location,
                "url": url,
                "scraped_at": datetime.now().isoformat(),
                "source": "linkedin"
            }
            
        except Exception as e:
            logger.debug(f"Error extrayendo datos de tarjeta: {e}")
            return None
    
    def _get_job_description(self, job_url: str) -> str:
        """Obtiene la descripción completa de una oferta visitando su página."""
        try:
            logger.debug(f"Obteniendo descripción de: {job_url}")
            self.driver.get(job_url)
            time.sleep(3)  # Esperar carga completa
            
            # Scroll para cargar contenido lazy
            self.driver.execute_script("window.scrollTo(0, 500);")
            time.sleep(1)
            
            # Intentar hacer clic en "Ver más" si existe
            show_more_selectors = [
                "button.show-more-less-html__button",
                "[class*='show-more']",
                "button[aria-label*='more']",
                ".show-more-less-html__button--more"
            ]
            for selector in show_more_selectors:
                try:
                    btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    btn.click()
                    time.sleep(0.5)
                    break
                except:
                    continue
            
            # Selectores para la descripción del trabajo (LinkedIn público)
            description_selectors = [
                # LinkedIn público - descripción principal
                ".show-more-less-html__markup",
                ".description__text .show-more-less-html__markup",
                # Contenedor de descripción
                ".decorated-job-posting__details",
                ".jobs-description-content__text",
                ".jobs-description__content",
                # Selectores alternativos
                "section.show-more-less-html",
                "[class*='description'] .show-more-less-html",
                ".description__text",
                ".job-description",
                ".jobs-box__html-content",
                # Sección de criterios
                ".description__job-criteria-list",
                # Artículo principal
                "article.jobs-description",
                "article .description",
                # Div genérico con clase description
                "div[class*='description']"
            ]
            
            description = ""
            for selector in description_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        text = elem.text.strip()
                        if text and len(text) > len(description):
                            description = text
                except:
                    continue
            
            # Si la descripción es corta, buscar en todo el body
            if len(description) < 100:
                try:
                    # Buscar secciones que contengan palabras clave de ofertas
                    sections = self.driver.find_elements(By.TAG_NAME, "section")
                    for section in sections:
                        text = section.text.strip()
                        keywords = ["responsabilidades", "requisitos", "experiencia", 
                                   "buscamos", "ofrecemos", "requirements", "responsibilities",
                                   "qualifications", "skills", "about the role"]
                        if any(kw in text.lower() for kw in keywords) and len(text) > len(description):
                            description = text
                except:
                    pass
            
            # Último intento: buscar cualquier div grande con texto relevante
            if len(description) < 100:
                try:
                    all_divs = self.driver.find_elements(By.CSS_SELECTOR, "div")
                    for div in all_divs:
                        text = div.text.strip()
                        if len(text) > 200 and len(text) < 5000:
                            keywords = ["salesforce", "developer", "experience", "requisitos", 
                                       "responsabilidades", "skills", "apex", "lightning"]
                            if any(kw in text.lower() for kw in keywords):
                                if len(text) > len(description):
                                    description = text
                                    break
                except:
                    pass
            
            if description and len(description) > 50:
                logger.info(f"✅ Descripción obtenida: {len(description)} caracteres")
            else:
                logger.warning(f"⚠️ Descripción corta o no encontrada para: {job_url}")
                description = "Descripción no disponible - visita la URL para más detalles"
            
            return description
            
        except Exception as e:
            logger.debug(f"Error obteniendo descripción: {e}")
            return "Descripción no disponible"
    
    def _go_to_next_page(self) -> bool:
        """Intenta ir a la siguiente página de resultados."""
        try:
            # Scroll al final para cargar más resultados
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            # Buscar botón de siguiente página
            next_button = self.driver.find_element(
                By.CSS_SELECTOR,
                "button[aria-label='Next'], .artdeco-pagination__button--next"
            )
            
            if next_button.is_enabled():
                next_button.click()
                return True
            
            return False
            
        except NoSuchElementException:
            return False
        except Exception as e:
            logger.debug(f"No se pudo ir a la siguiente página: {e}")
            return False
    
    def get_job_details(self, job_url: str) -> Dict[str, Any]:
        """
        Obtiene los detalles completos de una oferta.
        
        Args:
            job_url: URL de la oferta
            
        Returns:
            Diccionario con todos los detalles
        """
        if not self.driver:
            self._init_driver()
        
        try:
            logger.info(f"Obteniendo detalles de: {job_url}")
            self.driver.get(job_url)
            self._random_delay()
            
            details = {"url": job_url}
            
            # Esperar a que cargue el contenido
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".jobs-description, .description"))
            )
            
            # Título
            try:
                title_elem = self.driver.find_element(
                    By.CSS_SELECTOR,
                    ".job-details-jobs-unified-top-card__job-title, .top-card-layout__title"
                )
                details["title"] = title_elem.text.strip()
            except:
                pass
            
            # Empresa
            try:
                company_elem = self.driver.find_element(
                    By.CSS_SELECTOR,
                    ".job-details-jobs-unified-top-card__company-name, .topcard__org-name-link"
                )
                details["company"] = company_elem.text.strip()
            except:
                pass
            
            # Ubicación
            try:
                location_elem = self.driver.find_element(
                    By.CSS_SELECTOR,
                    ".job-details-jobs-unified-top-card__bullet, .topcard__flavor--bullet"
                )
                details["location"] = location_elem.text.strip()
            except:
                pass
            
            # Descripción completa
            try:
                desc_elem = self.driver.find_element(
                    By.CSS_SELECTOR,
                    ".jobs-description__content, .description__text"
                )
                details["description"] = desc_elem.text.strip()
            except:
                pass
            
            # Detalles adicionales (salario, tipo, etc.)
            try:
                insights = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    ".job-details-jobs-unified-top-card__job-insight"
                )
                for insight in insights:
                    text = insight.text.strip()
                    if "€" in text or "$" in text:
                        details["salary"] = text
                    elif any(word in text.lower() for word in ["full-time", "part-time", "contract"]):
                        details["job_type"] = text
            except:
                pass
            
            details["scraped_at"] = datetime.now().isoformat()
            
            # Guardar
            self._save_job(details)
            
            return details
            
        except Exception as e:
            logger.error(f"Error obteniendo detalles: {e}")
            return {"url": job_url, "error": str(e)}
    
    def _save_job(self, job: Dict[str, Any]) -> None:
        """Guarda una oferta en disco."""
        job_id = job.get('id', hashlib.md5(str(job).encode()).hexdigest()[:12])
        filepath = self.jobs_dir / f"{job_id}.json"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(job, f, ensure_ascii=False, indent=2)
        
        logger.debug(f"Oferta guardada: {filepath}")
    
    def _get_sample_jobs(self, keywords: str, limit: int) -> List[Dict[str, Any]]:
        """Retorna ofertas de ejemplo para pruebas."""
        logger.info("Generando ofertas de ejemplo...")
        
        sample_jobs = [
            {
                "id": "sample_001",
                "title": "Senior Python Developer",
                "company": "TechCorp España",
                "location": "Madrid, Spain (Remote)",
                "url": "https://www.linkedin.com/jobs/view/sample1",
                "description": """
                Buscamos un Senior Python Developer para unirse a nuestro equipo de desarrollo.
                
                Requisitos:
                - 5+ años de experiencia con Python
                - Experiencia con Django o FastAPI
                - Conocimientos de PostgreSQL y Redis
                - Experiencia con Docker y Kubernetes
                - Inglés B2 o superior
                
                Ofrecemos:
                - Trabajo 100% remoto
                - Salario competitivo (50-70k€)
                - Horario flexible
                - Stock options
                """,
                "source": "sample",
                "scraped_at": datetime.now().isoformat()
            },
            {
                "id": "sample_002",
                "title": "Backend Engineer",
                "company": "Startup Innovadora",
                "location": "Barcelona, Spain (Hybrid)",
                "url": "https://www.linkedin.com/jobs/view/sample2",
                "description": """
                Startup fintech en crecimiento busca Backend Engineer.
                
                Tech Stack:
                - Python, FastAPI
                - PostgreSQL, MongoDB
                - AWS (Lambda, ECS, S3)
                - CI/CD con GitHub Actions
                
                Requisitos:
                - 3+ años de experiencia
                - Conocimientos de arquitectura de microservicios
                - Experiencia con APIs REST
                
                Beneficios:
                - Modelo híbrido (2 días oficina)
                - Salario: 45-55k€
                - Formación continua
                """,
                "source": "sample",
                "scraped_at": datetime.now().isoformat()
            },
            {
                "id": "sample_003",
                "title": "Full Stack Developer",
                "company": "Consultora Digital",
                "location": "Remote, Spain",
                "url": "https://www.linkedin.com/jobs/view/sample3",
                "description": """
                Buscamos Full Stack Developer para proyectos innovadores.
                
                Stack:
                - Backend: Python/Node.js
                - Frontend: React/Vue
                - Base de datos: PostgreSQL
                - Cloud: AWS
                
                Se valorará:
                - Experiencia con TypeScript
                - Conocimientos de DevOps
                - Metodologías ágiles
                
                Oferta:
                - 100% remoto
                - 40-50k€ según experiencia
                """,
                "source": "sample",
                "scraped_at": datetime.now().isoformat()
            }
        ]
        
        # Filtrar por keywords si es posible
        filtered = []
        for job in sample_jobs:
            if keywords.lower() in job['title'].lower() or keywords.lower() in job['description'].lower():
                filtered.append(job)
        
        # Si no hay matches, devolver todos
        result = filtered if filtered else sample_jobs
        
        # Guardar samples
        for job in result[:limit]:
            self._save_job(job)
        
        return result[:limit]
    
    def close(self) -> None:
        """Cierra el navegador."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("Driver cerrado")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
