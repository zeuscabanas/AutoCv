"""
Generador de CVs - Crea PDFs y HTML a partir del CV personalizado.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from jinja2 import Environment, FileSystemLoader
import hashlib

# Directorio raíz del proyecto
ROOT_DIR = Path(__file__).parent.parent.parent


class CVGenerator:
    """Genera CVs en diferentes formatos (PDF, HTML)."""
    
    def __init__(self, templates_dir: str = None):
        """
        Inicializa el generador.
        
        Args:
            templates_dir: Directorio con los templates
        """
        self.templates_dir = Path(templates_dir) if templates_dir else ROOT_DIR / "src" / "templates"
        self.output_dir = ROOT_DIR / "data" / "cvs_generados"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar Jinja2
        if self.templates_dir.exists():
            self.jinja_env = Environment(
                loader=FileSystemLoader(str(self.templates_dir)),
                autoescape=True
            )
        else:
            self.jinja_env = None
            logger.warning(f"Templates directory not found: {self.templates_dir}")
    
    def generate(
        self,
        profile: Dict[str, Any],
        job_id: str,
        output_format: str = "pdf",
        preview: bool = False,
        include_cover_letter: bool = True
    ) -> Dict[str, str]:
        """
        Genera un CV personalizado y carta de presentación.
        
        Args:
            profile: Perfil del candidato
            job_id: ID de la oferta de trabajo
            output_format: Formato de salida (pdf, html)
            preview: Si mostrar preview antes de guardar
            include_cover_letter: Si incluir carta de presentación
            
        Returns:
            Diccionario con rutas: {'cv': path, 'cover_letter': path}
        """
        logger.info(f"Generando CV en formato {output_format}...")
        
        # Cargar la oferta de trabajo
        job = self._load_job(job_id)
        if not job:
            raise ValueError(f"Oferta no encontrada: {job_id}")
        
        # Personalizar el CV
        from ..ai.cv_personalizer import CVPersonalizer
        personalizer = CVPersonalizer()
        personalized_cv = personalizer.personalize_cv(
            profile=profile,
            job_description=job.get('description', ''),
            job_id=job_id,
            company_name=job.get('company', 'la empresa'),
            job_title=job.get('title', 'el puesto'),
            generate_cover_letter=include_cover_letter
        )
        
        # Generar HTML del CV
        html_content = self._generate_html(personalized_cv, job)
        
        # Generar nombre de archivo único
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_hash = hashlib.md5(job_id.encode()).hexdigest()[:8]
        filename = f"cv_{job_hash}_{timestamp}"
        
        result = {}
        
        if output_format == "html":
            output_path = self.output_dir / f"{filename}.html"
            self._save_html(html_content, output_path)
        else:
            output_path = self.output_dir / f"{filename}.pdf"
            self._generate_pdf(html_content, output_path)
        
        result['cv'] = str(output_path)
        logger.info(f"CV generado: {output_path}")
        
        # Generar carta de presentación si está disponible
        if include_cover_letter and personalized_cv.get('cover_letter'):
            cover_letter_html = self._generate_cover_letter_html(
                personalized_cv['cover_letter'],
                personalized_cv,
                job
            )
            cover_path = self.output_dir / f"carta_{job_hash}_{timestamp}.html"
            self._save_html(cover_letter_html, cover_path)
            result['cover_letter'] = str(cover_path)
            logger.info(f"Carta de presentación generada: {cover_path}")
        
        return result
    
    def _load_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Carga una oferta de trabajo desde el cache."""
        jobs_dir = ROOT_DIR / "data" / "ofertas"
        
        # Buscar por ID
        for job_file in jobs_dir.glob("*.json"):
            try:
                with open(job_file, 'r', encoding='utf-8') as f:
                    job = json.load(f)
                    if job.get('id', '').startswith(job_id) or job_id in str(job_file):
                        return job
            except:
                continue
        
        # Si no se encuentra, crear un job de prueba
        logger.warning(f"Oferta {job_id} no encontrada en {jobs_dir}, usando datos de prueba")
        return {
            "id": job_id,
            "title": "Software Developer",
            "company": "Test Company",
            "description": "Looking for a skilled developer...",
            "location": "Remote"
        }
    
    def _generate_html(
        self,
        personalized_cv: Dict[str, Any],
        job: Dict[str, Any]
    ) -> str:
        """Genera el HTML del CV."""
        
        if self.jinja_env:
            try:
                template = self.jinja_env.get_template("cv_template.html")
                return template.render(
                    cv=personalized_cv,
                    job=job,
                    generated_at=datetime.now().strftime("%Y-%m-%d %H:%M")
                )
            except Exception as e:
                logger.warning(f"Error con template Jinja2: {e}")
        
        # Fallback: generar HTML básico
        return self._generate_basic_html(personalized_cv, job)
    
    def _generate_basic_html(
        self,
        cv: Dict[str, Any],
        job: Dict[str, Any]
    ) -> str:
        """Genera HTML básico sin template."""
        
        personal = cv.get('personal_information', {})
        
        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CV - {personal.get('nombre', '')} {personal.get('apellidos', '')}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            line-height: 1.6;
            color: #1a1a1a;
            max-width: 210mm;
            margin: 0 auto;
            padding: 20mm;
            background: white;
        }}
        
        header {{
            border-bottom: 2px solid #2563eb;
            padding-bottom: 20px;
            margin-bottom: 25px;
        }}
        
        h1 {{
            font-size: 28px;
            font-weight: 700;
            color: #1e3a5f;
            margin-bottom: 8px;
        }}
        
        .contact-info {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            font-size: 13px;
            color: #4b5563;
        }}
        
        .contact-info a {{
            color: #2563eb;
            text-decoration: none;
        }}
        
        .summary {{
            background: #f8fafc;
            padding: 15px 20px;
            border-left: 4px solid #2563eb;
            margin-bottom: 25px;
            font-size: 14px;
        }}
        
        section {{
            margin-bottom: 25px;
        }}
        
        h2 {{
            font-size: 16px;
            font-weight: 600;
            color: #1e3a5f;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 1px solid #e5e7eb;
            padding-bottom: 8px;
            margin-bottom: 15px;
        }}
        
        .experience-item, .education-item {{
            margin-bottom: 18px;
        }}
        
        .item-header {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-bottom: 5px;
        }}
        
        .job-title {{
            font-weight: 600;
            font-size: 15px;
            color: #1f2937;
        }}
        
        .company {{
            color: #2563eb;
            font-size: 14px;
        }}
        
        .dates {{
            font-size: 13px;
            color: #6b7280;
        }}
        
        .responsibilities {{
            list-style: none;
            padding-left: 0;
        }}
        
        .responsibilities li {{
            position: relative;
            padding-left: 18px;
            margin-bottom: 5px;
            font-size: 13px;
        }}
        
        .responsibilities li::before {{
            content: "•";
            position: absolute;
            left: 0;
            color: #2563eb;
            font-weight: bold;
        }}
        
        .skills-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }}
        
        .skill-category h3 {{
            font-size: 13px;
            font-weight: 600;
            color: #374151;
            margin-bottom: 8px;
        }}
        
        .skill-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }}
        
        .skill-tag {{
            background: #eff6ff;
            color: #1d4ed8;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
        }}
        
        .languages {{
            display: flex;
            gap: 20px;
        }}
        
        .language-item {{
            font-size: 13px;
        }}
        
        .language-item strong {{
            color: #1f2937;
        }}
        
        @media print {{
            body {{
                padding: 15mm;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>{personal.get('nombre', '')} {personal.get('apellidos', '')}</h1>
        <div class="contact-info">
            <span>📧 {personal.get('email', '')}</span>
            <span>📱 {personal.get('telefono', '')}</span>
            <span>📍 {personal.get('ubicacion', {}).get('ciudad', '')}, {personal.get('ubicacion', {}).get('pais', '')}</span>
            {f'<a href="{personal.get("linkedin", "")}">LinkedIn</a>' if personal.get('linkedin') else ''}
            {f'<a href="{personal.get("github", "")}">GitHub</a>' if personal.get('github') else ''}
        </div>
    </header>
    
    <div class="summary">
        {cv.get('personalized_summary', 'Profesional con experiencia...')}
    </div>
"""
        
        # Experiencia laboral
        experience = cv.get('optimized_experience', {})
        if isinstance(experience, dict) and 'original' in experience:
            exp_list = experience['original']
        else:
            exp_list = experience if isinstance(experience, list) else []
        
        if exp_list:
            html += """
    <section>
        <h2>Experiencia Profesional</h2>
"""
            for exp in exp_list:
                fecha_fin = exp.get('fecha_fin', 'Actual') or 'Actual'
                html += f"""
        <div class="experience-item">
            <div class="item-header">
                <div>
                    <span class="job-title">{exp.get('puesto', '')}</span>
                    <span class="company"> @ {exp.get('empresa', '')}</span>
                </div>
                <span class="dates">{exp.get('fecha_inicio', '')} - {fecha_fin}</span>
            </div>
            <ul class="responsibilities">
"""
                for resp in exp.get('responsabilidades', [])[:5]:
                    html += f"                <li>{resp}</li>\n"
                
                html += """            </ul>
        </div>
"""
            html += "    </section>\n"
        
        # Educación
        education = cv.get('education', [])
        if education:
            html += """
    <section>
        <h2>Educación</h2>
"""
            for edu in education:
                html += f"""
        <div class="education-item">
            <div class="item-header">
                <div>
                    <span class="job-title">{edu.get('titulo', '')}</span>
                    <span class="company"> - {edu.get('institucion', '')}</span>
                </div>
                <span class="dates">{edu.get('fecha_inicio', '')} - {edu.get('fecha_fin', '')}</span>
            </div>
        </div>
"""
            html += "    </section>\n"
        
        # Habilidades
        html += """
    <section>
        <h2>Habilidades Técnicas</h2>
        <div class="skills-grid">
"""
        
        skills = cv.get('optimized_skills', {})
        if isinstance(skills, dict) and 'original' in skills:
            original_skills = skills['original']
            
            # Lenguajes
            if original_skills.get('lenguajes'):
                html += """            <div class="skill-category">
                <h3>Lenguajes</h3>
                <div class="skill-list">
"""
                for lang in original_skills.get('lenguajes', [])[:6]:
                    name = lang.get('nombre', lang) if isinstance(lang, dict) else lang
                    html += f'                    <span class="skill-tag">{name}</span>\n'
                html += """                </div>
            </div>
"""
            
            # Frameworks
            if original_skills.get('frameworks'):
                html += """            <div class="skill-category">
                <h3>Frameworks</h3>
                <div class="skill-list">
"""
                for fw in original_skills.get('frameworks', [])[:6]:
                    name = fw.get('nombre', fw) if isinstance(fw, dict) else fw
                    html += f'                    <span class="skill-tag">{name}</span>\n'
                html += """                </div>
            </div>
"""
        
        html += """        </div>
    </section>
"""
        
        # Idiomas
        languages = cv.get('languages', [])
        if languages:
            html += """
    <section>
        <h2>Idiomas</h2>
        <div class="languages">
"""
            for lang in languages:
                html += f'            <div class="language-item"><strong>{lang.get("idioma", "")}</strong>: {lang.get("nivel", "")}</div>\n'
            html += """        </div>
    </section>
"""
        
        html += """
</body>
</html>"""
        
        return html
    
    def _generate_cover_letter_html(
        self,
        cover_letter_text: str,
        cv: Dict[str, Any],
        job: Dict[str, Any]
    ) -> str:
        """Genera HTML para la carta de presentación."""
        
        personal = cv.get('personal_information', {})
        nombre = f"{personal.get('nombre', '')} {personal.get('apellidos', '')}"
        email = personal.get('email', '')
        telefono = personal.get('telefono', '')
        
        # Meses en español
        meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
        hoy = datetime.now()
        fecha_es = f"{hoy.day} de {meses[hoy.month - 1]} de {hoy.year}"
        
        # Formatear el texto de la carta (convertir saltos de línea a párrafos)
        # También eliminar posibles firmas generadas por la IA
        paragraphs = cover_letter_text.strip().split('\n\n')
        # Filtrar párrafos que parezcan firmas
        skip_words = ['atentamente', 'saludos', 'cordialmente', 'un saludo']
        filtered_paragraphs = []
        for p in paragraphs:
            p_lower = p.strip().lower()
            # Si es un párrafo corto que parece firma, saltarlo
            if len(p.strip()) < 50 and any(w in p_lower for w in skip_words):
                continue
            filtered_paragraphs.append(p)
        
        formatted_content = ''.join(f'<p>{p.strip()}</p>' for p in filtered_paragraphs if p.strip())
        
        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Carta de Presentación - {nombre}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            line-height: 1.7;
            color: #1a1a1a;
            max-width: 210mm;
            margin: 0 auto;
            padding: 25mm 30mm;
            background: white;
        }}
        
        .header {{
            margin-bottom: 30px;
        }}
        
        .sender-info {{
            margin-bottom: 25px;
        }}
        
        .sender-name {{
            font-size: 20px;
            font-weight: 600;
            color: #1e3a5f;
            margin-bottom: 5px;
        }}
        
        .sender-contact {{
            font-size: 13px;
            color: #4b5563;
            line-height: 1.5;
        }}
        
        .recipient-info {{
            margin-bottom: 20px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
        }}
        
        .company-name {{
            font-weight: 600;
            color: #1f2937;
        }}
        
        .job-title {{
            color: #2563eb;
            font-size: 14px;
        }}
        
        .date {{
            font-size: 13px;
            color: #6b7280;
            margin-bottom: 25px;
        }}
        
        .letter-content {{
            margin-top: 25px;
        }}
        
        .letter-content p {{
            margin-bottom: 18px;
            text-align: justify;
            font-size: 14px;
        }}
        
        .signature {{
            margin-top: 35px;
        }}
        
        .signature-name {{
            font-weight: 600;
            color: #1e3a5f;
            margin-top: 25px;
        }}
        
        @media print {{
            body {{
                padding: 20mm;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="sender-info">
            <div class="sender-name">{nombre}</div>
            <div class="sender-contact">
                {email}<br>
                {telefono}
            </div>
        </div>
        
        <div class="recipient-info">
            <div class="company-name">{job.get('company', 'Empresa')}</div>
            <div class="job-title">Re: {job.get('title', 'Puesto ofertado')}</div>
        </div>
        
        <div class="date">{fecha_es}</div>
    </div>
    
    <div class="letter-content">
        {formatted_content}
    </div>
    
    <div class="signature">
        <p>Atentamente,</p>
        <p class="signature-name">{nombre}</p>
    </div>
</body>
</html>"""
        
        return html
    
    def _save_html(self, html_content: str, output_path: Path) -> None:
        """Guarda el contenido HTML en un archivo."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.debug(f"HTML guardado: {output_path}")
    
    def _generate_pdf(self, html_content: str, output_path: Path) -> None:
        """Genera un PDF a partir del HTML."""
        pdf_generated = False
        
        # Intentar con pdfkit primero (más fácil en Windows)
        try:
            import pdfkit
            # Configurar ruta de wkhtmltopdf si está instalado
            config = None
            wkhtmltopdf_paths = [
                r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
                r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe",
            ]
            for path in wkhtmltopdf_paths:
                if Path(path).exists():
                    config = pdfkit.configuration(wkhtmltopdf=path)
                    break
            
            if config:
                pdfkit.from_string(html_content, str(output_path), configuration=config)
                pdf_generated = True
                logger.debug(f"PDF generado con pdfkit: {output_path}")
            else:
                logger.warning("wkhtmltopdf no encontrado. Descarga de: https://wkhtmltopdf.org/downloads.html")
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"pdfkit falló: {e}")
        
        # Intentar con WeasyPrint si pdfkit falló
        if not pdf_generated:
            try:
                from weasyprint import HTML
                HTML(string=html_content).write_pdf(str(output_path))
                pdf_generated = True
                logger.debug(f"PDF generado con WeasyPrint: {output_path}")
            except ImportError:
                logger.warning("WeasyPrint no instalado.")
            except Exception as e:
                logger.error(f"Error generando PDF: {e}")
        
        # Fallback a HTML si todo falla
        if not pdf_generated:
            logger.info("Guardando como HTML en lugar de PDF")
            html_path = output_path.with_suffix('.html')
            self._save_html(html_content, html_path)
            # Copiar también como "PDF" para que el mensaje no confunda
            output_path = html_path
    
    def generate_from_template(
        self,
        template_name: str,
        cv_data: Dict[str, Any],
        output_format: str = "pdf"
    ) -> str:
        """
        Genera un CV usando un template específico.
        
        Args:
            template_name: Nombre del template
            cv_data: Datos del CV personalizado
            output_format: Formato de salida
            
        Returns:
            Ruta al archivo generado
        """
        if not self.jinja_env:
            raise ValueError("No se encontró el directorio de templates")
        
        template = self.jinja_env.get_template(f"{template_name}.html")
        html_content = template.render(**cv_data)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cv_{template_name}_{timestamp}"
        
        if output_format == "pdf":
            output_path = self.output_dir / f"{filename}.pdf"
            self._generate_pdf(html_content, output_path)
        else:
            output_path = self.output_dir / f"{filename}.html"
            self._save_html(html_content, output_path)
        
        return str(output_path)
