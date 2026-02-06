"""
Prompts para la IA - Plantillas para personalización de CVs.
"""

# =============================================================================
# PROMPT DEL SISTEMA PRINCIPAL
# =============================================================================

SYSTEM_PROMPT = """Eres un experto en recursos humanos y redacción de currículums con más de 15 años de experiencia ayudando a candidatos a conseguir entrevistas. Tu especialidad es:

1. Crear CVs que pasen filtros ATS (Applicant Tracking Systems)
2. Destacar logros cuantificables y resultados de impacto
3. Adaptar el lenguaje al sector, empresa y puesto específico
4. Usar palabras clave relevantes del anuncio de trabajo de forma natural
5. Conectar emocionalmente la experiencia del candidato con las necesidades del puesto

REGLAS FUNDAMENTALES (NUNCA ROMPER):
- NUNCA inventes experiencia, habilidades o logros que no estén en la información proporcionada
- NUNCA añadas tecnologías o herramientas que el candidato no haya mencionado
- NUNCA exageres fechas o duración de experiencias
- NUNCA incluyas información personal falsa

LO QUE SÍ PUEDES Y DEBES HACER:
- REORGANIZAR la información para destacar lo más relevante primero
- REFORMULAR responsabilidades usando verbos de acción potentes y específicos
- TRADUCIR habilidades: conectar lo que el candidato sabe con lo que la empresa busca
- DESTACAR logros que sean más relevantes para esta posición específica
- AJUSTAR el tono (más técnico, más corporativo, más startup, más consultora, etc.)
- CUANTIFICAR logros cuando sea posible usando información existente
- USAR SINÓNIMOS que aparezcan en la oferta (ej: si dicen "desarrollo" y el candidato dice "programación")
- CREAR NARRATIVA: contar la historia profesional del candidato conectándola con el puesto
- ENFATIZAR transferable skills cuando la experiencia no es 100% directa

IDIOMA: Responde SIEMPRE en español (España) a menos que se indique lo contrario.
"""

# =============================================================================
# PROMPT PARA ANALIZAR OFERTA DE TRABAJO
# =============================================================================

ANALYZE_JOB_PROMPT = """Analiza la siguiente oferta de trabajo y extrae información clave:

OFERTA DE TRABAJO:
{job_description}

Por favor, extrae y organiza la siguiente información en formato estructurado:

1. **REQUISITOS TÉCNICOS OBLIGATORIOS**: Lista las tecnologías, lenguajes y herramientas que son imprescindibles
2. **REQUISITOS TÉCNICOS DESEABLES**: Lista las tecnologías que son "nice to have"
3. **EXPERIENCIA REQUERIDA**: Años de experiencia y en qué áreas específicas
4. **HABILIDADES BLANDAS**: Competencias personales mencionadas
5. **PALABRAS CLAVE ATS**: Las palabras que probablemente use el sistema ATS para filtrar
6. **TIPO DE EMPRESA**: Startup, corporación, consultora, etc.
7. **CULTURA/TONO**: Formal, casual, innovador, tradicional, etc.
8. **BENEFICIOS DESTACADOS**: Lo que ofrecen
9. **BANDERAS ROJAS** (si las hay): Señales de alerta

Formato de respuesta: JSON estructurado
"""

# =============================================================================
# PROMPT PARA CALCULAR MATCH SCORE
# =============================================================================

MATCH_SCORE_PROMPT = """Compara el perfil del candidato con la oferta de trabajo y calcula un score de compatibilidad.

PERFIL DEL CANDIDATO:
{profile}

OFERTA DE TRABAJO:
{job_description}

Analiza:
1. ¿Qué porcentaje de requisitos técnicos obligatorios cumple? (0-100)
2. ¿Qué porcentaje de requisitos deseables cumple? (0-100)
3. ¿Tiene la experiencia requerida? (Sí/No/Parcial)
4. ¿Las habilidades blandas coinciden? (0-100)

IMPORTANTE: Sé honesto y objetivo. No infles el score.

Responde con:
- score_total: número del 0 al 100
- requisitos_cumplidos: lista de requisitos que SÍ cumple
- requisitos_faltantes: lista de requisitos que NO cumple
- recomendacion: "Altamente recomendado" / "Recomendado" / "Aplicar con cautela" / "No recomendado"
- justificacion: breve explicación
"""

# =============================================================================
# PROMPT PARA GENERAR RESUMEN PROFESIONAL
# =============================================================================

GENERATE_SUMMARY_PROMPT = """Genera un resumen profesional personalizado para este candidato y esta oferta específica.

INFORMACIÓN DEL CANDIDATO:
{profile}

OFERTA DE TRABAJO:
{job_description}

REQUISITOS DE LA OFERTA (ANALIZADOS):
{job_requirements}

Genera un resumen profesional de 3-4 líneas que:
1. Mencione los años totales de experiencia
2. Destaque las 2-3 habilidades MÁS relevantes para ESTA oferta
3. Incluya un logro cuantificable relevante
4. Use palabras clave de la oferta (sin forzarlas)
5. Tenga un tono apropiado para el tipo de empresa

RECUERDA: Solo usa información REAL del perfil. No inventes nada.

Responde SOLO con el resumen, sin explicaciones adicionales.
"""

# =============================================================================
# PROMPT PARA REORDENAR EXPERIENCIA
# =============================================================================

REORDER_EXPERIENCE_PROMPT = """Reorganiza y mejora la sección de experiencia laboral para esta oferta específica.

EXPERIENCIA LABORAL DEL CANDIDATO:
{experience}

OFERTA DE TRABAJO:
{job_description}

REQUISITOS CLAVE DE LA OFERTA:
{job_requirements}

Para cada experiencia, debes:
1. MANTENER: empresa, fechas, puesto (NO cambiar)
2. REORDENAR: las responsabilidades poniendo primero las más relevantes para esta oferta
3. REFORMULAR: usar verbos de acción más potentes y palabras clave de la oferta
4. DESTACAR: logros cuantificables relevantes

FORMATO DE SALIDA (para cada experiencia):
```
PUESTO: [puesto original]
EMPRESA: [empresa original]  
UBICACIÓN: [ubicación original]
FECHAS: [fechas originales]
RESPONSABILIDADES:
• [responsabilidad más relevante para esta oferta]
• [segunda más relevante]
• [tercera más relevante]
• ... (máximo 5-6 bullets)
TECNOLOGÍAS: [solo las que coincidan con la oferta, separadas por comas]
```

IMPORTANTE: 
- NO añadas responsabilidades que no estén en la información original
- NO cambies las fechas ni la empresa
- Solo REORGANIZA y REFORMULA lo existente
"""

# =============================================================================
# PROMPT PARA OPTIMIZAR HABILIDADES
# =============================================================================

OPTIMIZE_SKILLS_PROMPT = """Selecciona y organiza las habilidades más relevantes para esta oferta.

TODAS LAS HABILIDADES DEL CANDIDATO:
{skills}

OFERTA DE TRABAJO:
{job_description}

REQUISITOS TÉCNICOS DE LA OFERTA:
{job_requirements}

Organiza las habilidades en estas categorías, priorizando las que aparecen en la oferta:

1. **Lenguajes de Programación**: (máximo 6, ordenados por relevancia para la oferta)
2. **Frameworks & Librerías**: (máximo 6)
3. **Bases de Datos**: (máximo 4)
4. **Cloud & DevOps**: (máximo 6)
5. **Herramientas**: (máximo 4)

REGLAS:
- Solo incluye habilidades que el candidato REALMENTE tiene (están en la lista)
- Pon primero las que aparecen en la oferta
- Usa el nombre exacto que usa la oferta (ej: si la oferta dice "AWS" y el candidato tiene "Amazon Web Services", usa "AWS")
- Omite habilidades irrelevantes para esta oferta específica

Formato de salida: listas separadas por categoría
"""

# =============================================================================
# PROMPT PARA GENERAR SECCIÓN DE EDUCACIÓN
# =============================================================================

OPTIMIZE_EDUCATION_PROMPT = """Optimiza la sección de educación para esta oferta.

EDUCACIÓN DEL CANDIDATO:
{education}

OFERTA DE TRABAJO:
{job_description}

Para cada entrada educativa:
1. Mantén título, institución y fechas exactos
2. Si hay cursos relevantes para la oferta, destácalos
3. Si hay logros académicos relevantes (becas, premios), inclúyelos
4. Si la nota es buena (>8/10 o equivalente), inclúyela

Formato de salida para cada entrada:
```
TÍTULO: [título exacto]
INSTITUCIÓN: [nombre exacto]
UBICACIÓN: [ubicación]
FECHAS: [fecha inicio] - [fecha fin]
NOTA: [si es relevante]
CURSOS RELEVANTES: [solo si son relevantes para la oferta]
LOGROS: [solo si son relevantes]
```
"""

# =============================================================================
# PROMPT PARA CARTA DE PRESENTACIÓN
# =============================================================================

COVER_LETTER_PROMPT = """Genera una carta de presentación PERSONALIZADA y CONVINCENTE para esta oferta específica.

INFORMACIÓN DEL CANDIDATO:
{profile}

OFERTA DE TRABAJO:
{job_description}

EMPRESA: {company_name}
PUESTO: {job_title}

ANÁLISIS DE LA OFERTA:
{job_analysis}

---

INSTRUCCIONES DE PERSONALIZACIÓN:

1. **GANCHO INICIAL** (2-3 líneas):
   - NO uses frases genéricas como "Me dirijo a ustedes..." o "Por la presente..."
   - Empieza con algo que conecte: por qué ESTA empresa te interesa específicamente
   - Si conoces algo de la empresa (producto, cultura, noticia reciente), menciónalo
   - Muestra que has investigado, no que envías CVs masivos

2. **CONEXIÓN EXPERIENCIA-PUESTO** (párrafo principal):
   - Identifica el PROBLEMA que la empresa quiere resolver con esta contratación
   - Muestra cómo TU experiencia específica resuelve ESE problema
   - Incluye 1-2 LOGROS CUANTIFICABLES que demuestren tu capacidad
   - Usa las mismas palabras clave que usa la oferta
   - Si hay gaps entre tu experiencia y lo que piden, abórdalos con transferable skills

3. **VALOR DIFERENCIAL** (3-4 líneas):
   - ¿Qué te hace diferente de otros candidatos con experiencia similar?
   - Menciona algo único: combinación de habilidades, perspectiva, motivación
   - Conecta tus valores/objetivos con los de la empresa

4. **CIERRE** (2-3 líneas):
   - Llamada a la acción específica (entrevista, llamada, etc.)
   - Muestra disponibilidad y entusiasmo genuino
   - NO seas servil, sé profesional y seguro

TONO:
- Si es STARTUP/TECH: más informal, directo, apasionado
- Si es CONSULTORA: profesional, orientado a resultados, client-focused
- Si es CORPORACIÓN: formal pero no aburrido, destacar estabilidad y crecimiento
- Si es INETUM/similar (la empresa actual del candidato): cuidado, es competidor directo

FORMATO:
- Máximo 300 palabras
- Párrafos cortos y escaneables
- NO uses bullet points en la carta
- NO incluyas firma ni despedida al final (eso se añade automáticamente)
- NO escribas "Atentamente", "Saludos", ni el nombre - eso se genera aparte

RECUERDA: 
- SOLO usa información REAL del perfil
- El nombre del candidato es: {nombre_candidato} - úsalo si necesitas referenciarte
- La carta debe sentirse escrita específicamente para ESTA oferta
- Evita clichés de cartas de presentación genéricas
- Termina con el párrafo de cierre, SIN firma
"""

# =============================================================================
# PROMPT PARA GENERAR CV COMPLETO EN HTML
# =============================================================================

GENERATE_CV_HTML_PROMPT = """Genera el contenido HTML para las secciones del CV.

INFORMACIÓN DEL CANDIDATO:
{profile}

OFERTA DE TRABAJO:
{job_description}

ANÁLISIS DE LA OFERTA:
{job_analysis}

Genera el HTML para cada sección del CV, optimizado para esta oferta específica.
Usa clases CSS semánticas. El HTML debe ser limpio y profesional.

SECCIONES A GENERAR:

1. HEADER (nombre, contacto, links)
2. RESUMEN PROFESIONAL (3-4 líneas)
3. EXPERIENCIA LABORAL (cada trabajo con bullets)
4. EDUCACIÓN
5. HABILIDADES TÉCNICAS (organizadas por categoría)
6. CERTIFICACIONES (si aplica)
7. PROYECTOS DESTACADOS (si aplica)
8. IDIOMAS

Formato de respuesta: JSON con cada sección como clave y su HTML como valor.

IMPORTANTE:
- Usa solo información REAL del perfil
- Prioriza contenido relevante para esta oferta
- Mantén un diseño limpio y escaneable
- Incluye palabras clave de la oferta donde sea natural
"""

# =============================================================================
# PROMPT PARA RESPONDER PREGUNTAS DE APLICACIÓN
# =============================================================================

ANSWER_APPLICATION_QUESTION_PROMPT = """Responde esta pregunta de una aplicación de trabajo.

PREGUNTA:
{question}

INFORMACIÓN DEL CANDIDATO:
{profile}

OFERTA DE TRABAJO:
{job_description}

Genera una respuesta que:
1. Sea concisa pero completa
2. Use información REAL del perfil del candidato
3. Sea relevante para el puesto
4. Tenga un tono profesional
5. No exceda el límite de caracteres si se especifica: {char_limit}

Si la pregunta pide información que no está en el perfil, indica qué información falta en lugar de inventar.
"""

# =============================================================================
# FUNCIONES HELPER
# =============================================================================

def format_prompt(template: str, **kwargs) -> str:
    """Formatea un template de prompt con los argumentos dados."""
    return template.format(**kwargs)


def get_prompt_for_section(section: str) -> str:
    """Obtiene el prompt apropiado para una sección del CV."""
    prompts = {
        'summary': GENERATE_SUMMARY_PROMPT,
        'experience': REORDER_EXPERIENCE_PROMPT,
        'skills': OPTIMIZE_SKILLS_PROMPT,
        'education': OPTIMIZE_EDUCATION_PROMPT,
        'cover_letter': COVER_LETTER_PROMPT,
    }
    return prompts.get(section, '')
