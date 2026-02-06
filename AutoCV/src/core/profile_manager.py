"""
Gestor de Perfiles - Carga y valida la información del usuario.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, EmailStr, HttpUrl, validator
from loguru import logger
from datetime import datetime


class PersonalInformation(BaseModel):
    """Información personal del candidato."""
    nombre: str
    apellidos: str
    email: EmailStr
    telefono: str
    linkedin: Optional[HttpUrl] = None
    github: Optional[HttpUrl] = None
    portfolio: Optional[HttpUrl] = None
    fecha_nacimiento: Optional[str] = None
    ubicacion: Optional[Dict[str, Any]] = None


class Education(BaseModel):
    """Entrada de educación."""
    titulo: str
    institucion: str
    ubicacion: Optional[str] = None
    fecha_inicio: str
    fecha_fin: Optional[str] = None
    nota_media: Optional[str] = None
    logros: Optional[List[str]] = None
    cursos_relevantes: Optional[List[Dict[str, str]]] = None


class Experience(BaseModel):
    """Entrada de experiencia laboral."""
    puesto: str
    empresa: str
    ubicacion: Optional[str] = None
    fecha_inicio: str
    fecha_fin: Optional[str] = None  # None = Actualmente
    tipo_contrato: Optional[str] = None
    descripcion: Optional[str] = None
    responsabilidades: Optional[List[str]] = None
    logros: Optional[List[str]] = None
    tecnologias: Optional[List[str]] = None
    
    @property
    def is_current(self) -> bool:
        """Indica si es el trabajo actual."""
        return self.fecha_fin is None
    
    @property
    def duration_months(self) -> int:
        """Calcula la duración en meses."""
        try:
            start = datetime.strptime(self.fecha_inicio, "%Y-%m")
            if self.fecha_fin:
                end = datetime.strptime(self.fecha_fin, "%Y-%m")
            else:
                end = datetime.now()
            return (end.year - start.year) * 12 + (end.month - start.month)
        except:
            return 0


class ProfileManager:
    """Gestor de perfiles del usuario."""
    
    def __init__(self, profile_path: str = "data/mi_perfil.yaml"):
        self.profile_path = Path(profile_path)
        self._profile: Optional[Dict[str, Any]] = None
    
    def load_profile(self) -> Dict[str, Any]:
        """Carga el perfil desde el archivo YAML."""
        if not self.profile_path.exists():
            raise FileNotFoundError(f"Perfil no encontrado: {self.profile_path}")
        
        with open(self.profile_path, 'r', encoding='utf-8') as f:
            self._profile = yaml.safe_load(f)
        
        logger.info(f"Perfil cargado: {self.profile_path}")
        return self._profile
    
    def get_profile(self) -> Dict[str, Any]:
        """Obtiene el perfil cargado o lo carga si no está."""
        if self._profile is None:
            return self.load_profile()
        return self._profile
    
    def validate_profile(self, profile: Dict[str, Any] = None) -> List[str]:
        """Valida el perfil y retorna lista de problemas encontrados."""
        if profile is None:
            profile = self.get_profile()
        
        issues = []
        
        # Validar información personal
        personal = profile.get('personal_information', {})
        required_personal = ['nombre', 'apellidos', 'email', 'telefono']
        for field in required_personal:
            if not personal.get(field):
                issues.append(f"Falta campo requerido: personal_information.{field}")
        
        # Validar educación
        educacion = profile.get('educacion', [])
        if not educacion:
            issues.append("No hay entradas de educación")
        
        # Validar experiencia
        experiencia = profile.get('experiencia', [])
        if not experiencia:
            issues.append("No hay entradas de experiencia laboral")
        else:
            for i, exp in enumerate(experiencia):
                if not exp.get('puesto'):
                    issues.append(f"Experiencia #{i+1}: falta el puesto")
                if not exp.get('empresa'):
                    issues.append(f"Experiencia #{i+1}: falta la empresa")
                if not exp.get('responsabilidades'):
                    issues.append(f"Experiencia #{i+1}: faltan responsabilidades")
        
        # Validar habilidades
        habilidades = profile.get('habilidades_tecnicas', {})
        if not habilidades.get('lenguajes'):
            issues.append("No hay lenguajes de programación listados")
        
        return issues
    
    def get_personal_info(self) -> PersonalInformation:
        """Obtiene la información personal validada."""
        profile = self.get_profile()
        return PersonalInformation(**profile.get('personal_information', {}))
    
    def get_education(self) -> List[Education]:
        """Obtiene la lista de educación."""
        profile = self.get_profile()
        return [Education(**edu) for edu in profile.get('educacion', [])]
    
    def get_experience(self) -> List[Experience]:
        """Obtiene la lista de experiencia laboral."""
        profile = self.get_profile()
        return [Experience(**exp) for exp in profile.get('experiencia', [])]
    
    def get_all_skills(self) -> List[str]:
        """Obtiene todas las habilidades técnicas como lista plana."""
        profile = self.get_profile()
        skills = []
        
        tech = profile.get('habilidades_tecnicas', {})
        
        # Lenguajes
        for lang in tech.get('lenguajes', []):
            if isinstance(lang, dict):
                skills.append(lang.get('nombre', ''))
            else:
                skills.append(str(lang))
        
        # Frameworks
        for fw in tech.get('frameworks', []):
            if isinstance(fw, dict):
                skills.append(fw.get('nombre', ''))
            else:
                skills.append(str(fw))
        
        # Bases de datos
        skills.extend(tech.get('bases_datos', []))
        
        # DevOps/Cloud
        skills.extend(tech.get('devops_cloud', []))
        
        # Herramientas
        skills.extend(tech.get('herramientas', []))
        
        return [s for s in skills if s]  # Filtrar vacíos
    
    def get_total_experience_years(self) -> float:
        """Calcula el total de años de experiencia."""
        experiences = self.get_experience()
        total_months = sum(exp.duration_months for exp in experiences)
        return round(total_months / 12, 1)
    
    def get_keywords(self) -> List[str]:
        """Extrae palabras clave del perfil para matching."""
        profile = self.get_profile()
        keywords = set()
        
        # Skills
        keywords.update(self.get_all_skills())
        
        # Habilidades blandas
        keywords.update(profile.get('habilidades_blandas', []))
        
        # Tecnologías de cada experiencia
        for exp in profile.get('experiencia', []):
            keywords.update(exp.get('tecnologias', []))
        
        # Roles de interés
        preferences = profile.get('preferencias', {})
        keywords.update(preferences.get('roles_interes', []))
        
        return list(keywords)
    
    def to_plain_text(self) -> str:
        """Convierte el perfil a texto plano para el LLM."""
        profile = self.get_profile()
        
        lines = []
        
        # Personal
        personal = profile.get('personal_information', {})
        lines.append("=== INFORMACIÓN PERSONAL ===")
        lines.append(f"Nombre: {personal.get('nombre', '')} {personal.get('apellidos', '')}")
        lines.append(f"Email: {personal.get('email', '')}")
        lines.append(f"Teléfono: {personal.get('telefono', '')}")
        if personal.get('linkedin'):
            lines.append(f"LinkedIn: {personal.get('linkedin')}")
        if personal.get('github'):
            lines.append(f"GitHub: {personal.get('github')}")
        ubicacion = personal.get('ubicacion', {})
        lines.append(f"Ubicación: {ubicacion.get('ciudad', '')}, {ubicacion.get('pais', '')}")
        lines.append("")
        
        # Educación
        lines.append("=== EDUCACIÓN ===")
        for edu in profile.get('educacion', []):
            lines.append(f"• {edu.get('titulo')} - {edu.get('institucion')}")
            lines.append(f"  {edu.get('fecha_inicio')} - {edu.get('fecha_fin', 'Actual')}")
            if edu.get('nota_media'):
                lines.append(f"  Nota: {edu.get('nota_media')}")
        lines.append("")
        
        # Experiencia
        lines.append("=== EXPERIENCIA LABORAL ===")
        for exp in profile.get('experiencia', []):
            lines.append(f"• {exp.get('puesto')} en {exp.get('empresa')}")
            lines.append(f"  {exp.get('fecha_inicio')} - {exp.get('fecha_fin', 'Actual')}")
            if exp.get('descripcion'):
                lines.append(f"  {exp.get('descripcion')}")
            if exp.get('responsabilidades'):
                for resp in exp.get('responsabilidades', []):
                    lines.append(f"    - {resp}")
            if exp.get('tecnologias'):
                lines.append(f"  Tecnologías: {', '.join(exp.get('tecnologias', []))}")
        lines.append("")
        
        # Habilidades
        lines.append("=== HABILIDADES TÉCNICAS ===")
        skills = self.get_all_skills()
        lines.append(", ".join(skills))
        lines.append("")
        
        # Idiomas
        lines.append("=== IDIOMAS ===")
        for lang in profile.get('idiomas', []):
            cert = f" ({lang.get('certificacion')})" if lang.get('certificacion') else ""
            lines.append(f"• {lang.get('idioma')}: {lang.get('nivel')}{cert}")
        lines.append("")
        
        # Certificaciones
        if profile.get('certificaciones'):
            lines.append("=== CERTIFICACIONES ===")
            for cert in profile.get('certificaciones', []):
                lines.append(f"• {cert.get('nombre')} - {cert.get('emisor')} ({cert.get('fecha')})")
            lines.append("")
        
        # Proyectos
        if profile.get('proyectos'):
            lines.append("=== PROYECTOS ===")
            for proj in profile.get('proyectos', []):
                lines.append(f"• {proj.get('nombre')}: {proj.get('descripcion')}")
                if proj.get('tecnologias'):
                    lines.append(f"  Tecnologías: {', '.join(proj.get('tecnologias', []))}")
            lines.append("")
        
        return "\n".join(lines)
