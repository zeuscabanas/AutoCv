# 🚀 AutoCV - Generador Automático de Currículums Personalizados

## Descripción

AutoCV es un sistema inteligente que automatiza el proceso de búsqueda de empleo:

1. **📋 Almacena tu información real** - Tu experiencia, educación, habilidades, etc.
2. **🔍 Scraping de LinkedIn** - Extrae ofertas de trabajo que te interesan
3. **🤖 Personalización con IA** - Usa Ollama para adaptar tu CV a cada oferta
4. **📄 Generación de PDFs** - Crea currículums profesionales y ATS-friendly
5. **📤 Aplicación automática** - Aplica a los trabajos automáticamente

## Arquitectura del Proyecto

```
AutoCV/
├── config/
│   ├── settings.yaml          # Configuración general
│   └── linkedin_config.yaml   # Configuración de LinkedIn
├── data/
│   ├── mi_perfil.yaml         # Tu información REAL
│   ├── ofertas/               # Ofertas scrapeadas
│   └── cvs_generados/         # CVs personalizados
├── src/
│   ├── core/
│   │   ├── profile_manager.py # Gestión de tu perfil
│   │   ├── job_parser.py      # Parser de ofertas
│   │   └── cv_generator.py    # Generador de CVs
│   ├── scraper/
│   │   ├── linkedin_scraper.py # Scraper de LinkedIn
│   │   └── job_extractor.py   # Extractor de detalles
│   ├── ai/
│   │   ├── ollama_client.py   # Cliente de Ollama
│   │   ├── cv_personalizer.py # Personalizador de CVs
│   │   └── prompts.py         # Prompts para la IA
│   ├── templates/
│   │   ├── cv_template.html   # Template HTML del CV
│   │   └── styles/            # Estilos CSS
│   ├── applicator/
│   │   └── linkedin_apply.py  # Aplicador automático
│   └── utils/
│       ├── pdf_generator.py   # Generador de PDFs
│       └── helpers.py         # Utilidades varias
├── tests/
├── requirements.txt
├── main.py                    # Punto de entrada principal
└── README.md
```

## Características Principales

### 🎯 Personalización Inteligente (NO MIENTE)
- La IA **NO inventa** experiencia ni habilidades
- Solo **reorganiza y enfatiza** tu información real según la oferta
- Usa palabras clave de la oferta para mejorar el ATS score
- Adapta el tono y formato al tipo de empresa

### 🔐 Privacidad
- Toda la información se almacena localmente
- Usa Ollama (IA local) para no enviar datos a terceros

## Instalación

```bash
# 1. Clonar/Crear el proyecto
cd "c:\Users\zeusc\Desktop\Busqueda de trabajo\AutoCV"

# 2. Crear entorno virtual
python -m venv venv
.\venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Instalar Ollama (si no lo tienes)
# Descarga desde: https://ollama.ai/

# 5. Descargar modelo recomendado
ollama pull llama3.1
# O para mejor calidad:
ollama pull llama3.1:70b
```

## Uso Rápido

```bash
# 1. Primero, completa tu perfil en data/mi_perfil.yaml

# 2. Ejecutar el programa
python main.py

# Opciones disponibles:
python main.py --search "Python Developer Madrid"  # Buscar ofertas
python main.py --generate-cv <job_id>              # Generar CV para oferta
python main.py --apply <job_id>                    # Aplicar a oferta
python main.py --batch                             # Modo automático
```

## Flujo de Trabajo

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Tu Perfil      │────▶│  Oferta LinkedIn │────▶│   IA (Ollama)   │
│  (YAML real)    │     │  (Scrapeada)     │     │   Personaliza   │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Aplicación     │◀────│   PDF Generado   │◀────│  CV Adaptado    │
│  Automática     │     │   Profesional    │     │  (HTML/PDF)     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Tecnologías

- **Python 3.10+**
- **Selenium/Playwright** - Web scraping
- **Ollama** - IA local (LLaMA, Mistral, etc.)
- **Jinja2** - Templates HTML
- **WeasyPrint/Playwright** - Generación PDF
- **PyYAML** - Gestión de configuración
- **Rich** - CLI bonita

## Disclaimer

⚠️ **Uso Responsable**: Este proyecto es para uso personal. LinkedIn tiene términos de servicio que limitan el scraping automatizado. Úsalo con moderación y responsabilidad.

## Contribuir

¡Las contribuciones son bienvenidas! Abre un issue o PR.

## Licencia

MIT License
