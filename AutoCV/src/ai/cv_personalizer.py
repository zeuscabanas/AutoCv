"""
Personalizador de CVs - Usa IA para adaptar el CV a cada oferta.
"""

import json
from typing import Dict, Any, Optional, List
from loguru import logger
from pathlib import Path

from .ollama_client import OllamaClient
from .prompts import (
    SYSTEM_PROMPT,
    ANALYZE_JOB_PROMPT,
    MATCH_SCORE_PROMPT,
    GENERATE_SUMMARY_PROMPT,
    REORDER_EXPERIENCE_PROMPT,
    OPTIMIZE_SKILLS_PROMPT,
    OPTIMIZE_EDUCATION_PROMPT,
    COVER_LETTER_PROMPT,
    GENERATE_CV_HTML_PROMPT,
    format_prompt
)


class CVPersonalizer:
    """Personaliza CVs usando IA local (Ollama)."""
    
    def __init__(self, ollama_client: OllamaClient = None):
        """
        Inicializa el personalizador.
        
        Args:
            ollama_client: Cliente de Ollama (se crea uno nuevo si no se proporciona)
        """
        self.ollama = ollama_client or OllamaClient()
        self._job_analysis_cache: Dict[str, Any] = {}
    
    def analyze_job(self, job_description: str) -> Dict[str, Any]:
        """
        Analiza una oferta de trabajo y extrae información clave.
        
        Args:
            job_description: Texto de la descripción del trabajo
            
        Returns:
            Diccionario con el análisis de la oferta
        """
        logger.info("Analizando oferta de trabajo...")
        
        prompt = format_prompt(ANALYZE_JOB_PROMPT, job_description=job_description)
        
        response = self.ollama.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.2  # Bajo para análisis objetivo
        )
        
        try:
            # Intentar parsear como JSON
            # Buscar el JSON en la respuesta
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                analysis = json.loads(json_str)
            else:
                # Si no hay JSON, estructurar la respuesta
                analysis = {"raw_analysis": response}
        except json.JSONDecodeError:
            analysis = {"raw_analysis": response}
        
        logger.debug(f"Análisis completado: {list(analysis.keys())}")
        return analysis
    
    def calculate_match_score(
        self,
        profile: Dict[str, Any],
        job_description: str
    ) -> Dict[str, Any]:
        """
        Calcula el score de compatibilidad entre perfil y oferta.
        
        Args:
            profile: Diccionario con el perfil del candidato
            job_description: Descripción del trabajo
            
        Returns:
            Diccionario con el score y detalles
        """
        logger.info("Calculando match score...")
        
        # Convertir perfil a texto si es necesario
        if isinstance(profile, dict):
            from ..core.profile_manager import ProfileManager
            pm = ProfileManager()
            pm._profile = profile
            profile_text = pm.to_plain_text()
        else:
            profile_text = str(profile)
        
        prompt = format_prompt(
            MATCH_SCORE_PROMPT,
            profile=profile_text,
            job_description=job_description
        )
        
        response = self.ollama.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.1
        )
        
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
            else:
                # Intentar extraer score del texto
                import re
                score_match = re.search(r'(\d{1,3})%?', response)
                score = int(score_match.group(1)) if score_match else 50
                result = {"score_total": score, "raw_response": response}
        except:
            result = {"score_total": 50, "raw_response": response}
        
        logger.info(f"Match score: {result.get('score_total', 'N/A')}%")
        return result
    
    def generate_summary(
        self,
        profile: Dict[str, Any],
        job_description: str,
        job_analysis: Dict[str, Any] = None
    ) -> str:
        """
        Genera un resumen profesional personalizado.
        
        Args:
            profile: Perfil del candidato
            job_description: Descripción del trabajo
            job_analysis: Análisis previo de la oferta (opcional)
            
        Returns:
            Resumen profesional como string
        """
        logger.info("Generando resumen profesional...")
        
        from ..core.profile_manager import ProfileManager
        pm = ProfileManager()
        pm._profile = profile
        profile_text = pm.to_plain_text()
        
        if not job_analysis:
            job_analysis = self.analyze_job(job_description)
        
        prompt = format_prompt(
            GENERATE_SUMMARY_PROMPT,
            profile=profile_text,
            job_description=job_description,
            job_requirements=json.dumps(job_analysis, ensure_ascii=False, indent=2)
        )
        
        response = self.ollama.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.4
        )
        
        # Limpiar la respuesta
        summary = response.strip()
        # Eliminar posibles prefijos/sufijos no deseados
        if summary.startswith('"') and summary.endswith('"'):
            summary = summary[1:-1]
        
        logger.debug(f"Resumen generado ({len(summary)} chars)")
        return summary
    
    def optimize_experience(
        self,
        experience: List[Dict[str, Any]],
        job_description: str,
        job_analysis: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Reordena y optimiza la experiencia laboral para la oferta.
        
        Args:
            experience: Lista de experiencias laborales
            job_description: Descripción del trabajo
            job_analysis: Análisis previo de la oferta
            
        Returns:
            Lista de experiencias optimizadas
        """
        logger.info("Optimizando experiencia laboral...")
        
        if not job_analysis:
            job_analysis = self.analyze_job(job_description)
        
        # Formatear experiencia para el prompt
        exp_text = ""
        for i, exp in enumerate(experience, 1):
            exp_text += f"\n--- Experiencia {i} ---\n"
            exp_text += f"Puesto: {exp.get('puesto', 'N/A')}\n"
            exp_text += f"Empresa: {exp.get('empresa', 'N/A')}\n"
            exp_text += f"Fechas: {exp.get('fecha_inicio', '')} - {exp.get('fecha_fin', 'Actual')}\n"
            exp_text += f"Descripción: {exp.get('descripcion', '')}\n"
            exp_text += "Responsabilidades:\n"
            for resp in exp.get('responsabilidades', []):
                exp_text += f"  • {resp}\n"
            exp_text += f"Tecnologías: {', '.join(exp.get('tecnologias', []))}\n"
        
        prompt = format_prompt(
            REORDER_EXPERIENCE_PROMPT,
            experience=exp_text,
            job_description=job_description,
            job_requirements=json.dumps(job_analysis, ensure_ascii=False, indent=2)
        )
        
        response = self.ollama.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.3
        )
        
        # Parsear la respuesta y actualizar las experiencias
        # Por ahora retornamos el texto optimizado
        return {"optimized_text": response, "original": experience}
    
    def optimize_skills(
        self,
        skills: Dict[str, Any],
        job_description: str,
        job_analysis: Dict[str, Any] = None
    ) -> Dict[str, List[str]]:
        """
        Selecciona y organiza las habilidades relevantes.
        
        Args:
            skills: Diccionario de habilidades del candidato
            job_description: Descripción del trabajo
            job_analysis: Análisis previo de la oferta
            
        Returns:
            Habilidades organizadas por categoría
        """
        logger.info("Optimizando habilidades...")
        
        if not job_analysis:
            job_analysis = self.analyze_job(job_description)
        
        # Aplanar las habilidades
        all_skills = []
        for category, items in skills.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        all_skills.append(f"{item.get('nombre', '')} ({item.get('nivel', '')})")
                    else:
                        all_skills.append(str(item))
        
        prompt = format_prompt(
            OPTIMIZE_SKILLS_PROMPT,
            skills="\n".join(all_skills),
            job_description=job_description,
            job_requirements=json.dumps(job_analysis, ensure_ascii=False, indent=2)
        )
        
        response = self.ollama.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.2
        )
        
        return {"optimized_skills": response, "original": skills}
    
    def generate_cover_letter(
        self,
        profile: Dict[str, Any],
        job_description: str,
        company_name: str,
        job_title: str = "",
        job_analysis: Dict[str, Any] = None
    ) -> str:
        """
        Genera una carta de presentación personalizada.
        
        Args:
            profile: Perfil del candidato
            job_description: Descripción del trabajo
            company_name: Nombre de la empresa
            job_title: Título del puesto
            job_analysis: Análisis previo de la oferta
            
        Returns:
            Carta de presentación como string
        """
        logger.info(f"Generando carta de presentación para {company_name} - {job_title}...")
        
        from ..core.profile_manager import ProfileManager
        pm = ProfileManager()
        pm._profile = profile
        profile_text = pm.to_plain_text()
        
        # Obtener nombre del candidato
        personal_info = profile.get('personal_information', {})
        nombre_candidato = f"{personal_info.get('nombre', '')} {personal_info.get('apellidos', '')}".strip()
        
        # Obtener análisis si no existe
        if not job_analysis:
            job_analysis = self.analyze_job(job_description)
        
        prompt = format_prompt(
            COVER_LETTER_PROMPT,
            profile=profile_text,
            job_description=job_description,
            company_name=company_name,
            job_title=job_title or "el puesto ofertado",
            job_analysis=json.dumps(job_analysis, ensure_ascii=False, indent=2),
            nombre_candidato=nombre_candidato or "el candidato"
        )
        
        response = self.ollama.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.6  # Más creativo para la carta
        )
        
        logger.debug(f"Carta generada ({len(response)} chars)")
        return response.strip()
    
    def personalize_cv(
        self,
        profile: Dict[str, Any],
        job_description: str,
        job_id: str = None,
        company_name: str = "",
        job_title: str = "",
        generate_cover_letter: bool = True
    ) -> Dict[str, Any]:
        """
        Proceso completo de personalización del CV.
        
        Args:
            profile: Perfil completo del candidato
            job_description: Descripción del trabajo
            job_id: ID de la oferta (para cache)
            company_name: Nombre de la empresa
            job_title: Título del puesto
            generate_cover_letter: Si generar carta de presentación
            
        Returns:
            CV personalizado con todas las secciones
        """
        logger.info("Iniciando personalización completa del CV...")
        
        # 1. Analizar la oferta
        job_analysis = self.analyze_job(job_description)
        
        # 2. Calcular match score
        match_score = self.calculate_match_score(profile, job_description)
        
        # 3. Generar resumen personalizado
        summary = self.generate_summary(profile, job_description, job_analysis)
        
        # 4. Optimizar experiencia
        experience = self.optimize_experience(
            profile.get('experiencia', []),
            job_description,
            job_analysis
        )
        
        # 5. Optimizar habilidades
        skills = self.optimize_skills(
            profile.get('habilidades_tecnicas', {}),
            job_description,
            job_analysis
        )
        
        # 6. Generar carta de presentación
        cover_letter = None
        if generate_cover_letter:
            cover_letter = self.generate_cover_letter(
                profile=profile,
                job_description=job_description,
                company_name=company_name or "la empresa",
                job_title=job_title or "el puesto",
                job_analysis=job_analysis
            )
        
        result = {
            "job_analysis": job_analysis,
            "match_score": match_score,
            "personalized_summary": summary,
            "optimized_experience": experience,
            "optimized_skills": skills,
            "cover_letter": cover_letter,
            "personal_information": profile.get('personal_information', {}),
            "education": profile.get('educacion', []),
            "certifications": profile.get('certificaciones', []),
            "projects": profile.get('proyectos', []),
            "languages": profile.get('idiomas', []),
            "job_title": job_title,
            "company_name": company_name,
        }
        
        logger.info("Personalización completada")
        return result
