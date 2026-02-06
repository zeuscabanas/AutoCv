"""
Menú interactivo para AutoCV.
"""

import inquirer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from loguru import logger
from pathlib import Path
import json

console = Console()


def run_interactive_menu():
    """Ejecuta el menú interactivo principal."""
    
    while True:
        console.print("\n")
        
        questions = [
            inquirer.List(
                'action',
                message="¿Qué quieres hacer?",
                choices=[
                    ('📋 Ver mi perfil', 'profile'),
                    ('🔍 Buscar ofertas de trabajo', 'search'),
                    ('📄 Ver ofertas guardadas', 'list_jobs'),
                    ('✨ Generar CV personalizado', 'generate'),
                    ('📤 Aplicar a una oferta', 'apply'),
                    ('⚙️  Configuración', 'settings'),
                    ('❓ Ayuda', 'help'),
                    ('🚪 Salir', 'exit'),
                ],
            )
        ]
        
        answer = inquirer.prompt(questions)
        
        if not answer:
            break
        
        action = answer['action']
        
        if action == 'exit':
            console.print("\n👋 ¡Hasta luego! Buena suerte con tu búsqueda de empleo.\n", style="cyan")
            break
        elif action == 'profile':
            _show_profile()
        elif action == 'search':
            _search_jobs()
        elif action == 'list_jobs':
            _list_saved_jobs()
        elif action == 'generate':
            _generate_cv()
        elif action == 'apply':
            _apply_to_job()
        elif action == 'settings':
            _show_settings()
        elif action == 'help':
            _show_help()


def _show_profile():
    """Muestra el perfil del usuario."""
    from ..core.profile_manager import ProfileManager
    
    try:
        pm = ProfileManager()
        profile = pm.load_profile()
        
        personal = profile.get('personal_information', {})
        
        console.print(Panel(
            f"""
[bold cyan]👤 {personal.get('nombre', 'N/A')} {personal.get('apellidos', '')}[/bold cyan]

📧 Email: {personal.get('email', 'N/A')}
📱 Teléfono: {personal.get('telefono', 'N/A')}
📍 Ubicación: {personal.get('ubicacion', {}).get('ciudad', 'N/A')}, {personal.get('ubicacion', {}).get('pais', 'N/A')}

[bold]Resumen:[/bold]
• Educación: {len(profile.get('educacion', []))} entradas
• Experiencia: {len(profile.get('experiencia', []))} empleos
• Años totales: ~{pm.get_total_experience_years()} años
• Habilidades técnicas: {len(pm.get_all_skills())} skills
• Idiomas: {len(profile.get('idiomas', []))} idiomas
• Certificaciones: {len(profile.get('certificaciones', []))} certificaciones
            """,
            title="Tu Perfil",
            border_style="green"
        ))
        
        # Validar
        issues = pm.validate_profile(profile)
        if issues:
            console.print("\n⚠️ [bold yellow]Problemas encontrados:[/bold yellow]")
            for issue in issues:
                console.print(f"   • {issue}", style="yellow")
        else:
            console.print("\n✅ Perfil válido y completo", style="green")
            
    except FileNotFoundError:
        console.print("\n❌ Perfil no encontrado. Edita el archivo data/mi_perfil.yaml", style="red")
    except Exception as e:
        console.print(f"\n❌ Error: {e}", style="red")


def _search_jobs():
    """Busca ofertas de trabajo."""
    questions = [
        inquirer.Text('keywords', message="Palabras clave (ej: Python Developer)"),
        inquirer.Text('location', message="Ubicación (opcional)", default=""),
        inquirer.List(
            'limit',
            message="¿Cuántas ofertas buscar?",
            choices=[('10', 10), ('20', 20), ('50', 50)],
            default=20
        )
    ]
    
    answers = inquirer.prompt(questions)
    if not answers or not answers['keywords']:
        return
    
    console.print(f"\n🔍 Buscando '{answers['keywords']}'...", style="cyan")
    
    from ..scraper.linkedin_scraper import LinkedInScraper
    
    try:
        scraper = LinkedInScraper()
        jobs = scraper.search_jobs(
            keywords=answers['keywords'],
            location=answers['location'] or None,
            limit=int(answers['limit'])
        )
        
        if jobs:
            _display_jobs_table(jobs)
            console.print(f"\n💾 Ofertas guardadas en: data/ofertas/", style="green")
        else:
            console.print("\n⚠️ No se encontraron ofertas", style="yellow")
            
    except Exception as e:
        console.print(f"\n❌ Error: {e}", style="red")


def _list_saved_jobs():
    """Lista las ofertas guardadas."""
    jobs_dir = Path("data/ofertas")
    
    if not jobs_dir.exists():
        console.print("\n📭 No hay ofertas guardadas", style="yellow")
        return
    
    job_files = list(jobs_dir.glob("*.json"))
    
    if not job_files:
        console.print("\n📭 No hay ofertas guardadas", style="yellow")
        return
    
    jobs = []
    for job_file in job_files:
        try:
            with open(job_file, 'r', encoding='utf-8') as f:
                job = json.load(f)
                jobs.append(job)
        except:
            continue
    
    _display_jobs_table(jobs)


def _display_jobs_table(jobs):
    """Muestra una tabla de ofertas."""
    table = Table(title=f"Ofertas ({len(jobs)})")
    table.add_column("ID", style="dim", width=10)
    table.add_column("Puesto", style="cyan", width=30)
    table.add_column("Empresa", style="green", width=20)
    table.add_column("Ubicación", style="yellow", width=20)
    
    for job in jobs:
        table.add_row(
            str(job.get('id', 'N/A'))[:8],
            job.get('title', 'N/A')[:28],
            job.get('company', 'N/A')[:18],
            job.get('location', 'N/A')[:18]
        )
    
    console.print(table)


def _generate_cv():
    """Genera un CV personalizado."""
    jobs_dir = Path("data/ofertas")
    job_files = list(jobs_dir.glob("*.json"))
    
    if not job_files:
        console.print("\n⚠️ Primero busca ofertas de trabajo", style="yellow")
        return
    
    # Listar ofertas disponibles
    job_choices = []
    for job_file in job_files:
        try:
            with open(job_file, 'r', encoding='utf-8') as f:
                job = json.load(f)
                label = f"{job.get('title', 'N/A')[:30]} @ {job.get('company', 'N/A')[:20]}"
                job_choices.append((label, job.get('id', str(job_file.stem))))
        except:
            continue
    
    questions = [
        inquirer.List(
            'job_id',
            message="Selecciona la oferta para personalizar el CV",
            choices=job_choices
        ),
        inquirer.List(
            'format',
            message="Formato de salida",
            choices=[('PDF', 'pdf'), ('HTML', 'html')],
            default='pdf'
        )
    ]
    
    answers = inquirer.prompt(questions)
    if not answers:
        return
    
    console.print(f"\n⏳ Generando CV personalizado...", style="cyan")
    
    try:
        from ..core.profile_manager import ProfileManager
        from ..core.cv_generator import CVGenerator
        
        pm = ProfileManager()
        profile = pm.load_profile()
        
        generator = CVGenerator()
        output_path = generator.generate(
            profile=profile,
            job_id=answers['job_id'],
            output_format=answers['format']
        )
        
        console.print(f"\n✅ CV generado: [bold]{output_path}[/bold]", style="green")
        
    except Exception as e:
        console.print(f"\n❌ Error: {e}", style="red")
        logger.exception("Error generando CV")


def _apply_to_job():
    """Aplica a una oferta."""
    console.print("\n⚠️ Funcionalidad en desarrollo", style="yellow")
    console.print("Por ahora, usa el CV generado para aplicar manualmente.", style="dim")


def _show_settings():
    """Muestra y permite editar configuración."""
    from ..utils.config_loader import load_config
    
    try:
        config = load_config()
        
        console.print(Panel(
            f"""
[bold]Configuración actual:[/bold]

[cyan]Ollama:[/cyan]
  • Host: {config.get('ollama', {}).get('host', 'N/A')}
  • Modelo: {config.get('ollama', {}).get('model', 'N/A')}
  • Temperatura: {config.get('ollama', {}).get('temperature', 'N/A')}

[cyan]CV:[/cyan]
  • Formato: {config.get('cv_generation', {}).get('output_format', 'N/A')}
  • Template: {config.get('cv_generation', {}).get('template', 'N/A')}

[cyan]LinkedIn:[/cyan]
  • Límite búsqueda: {config.get('linkedin', {}).get('search_limit', 'N/A')}
  • Headless: {config.get('linkedin', {}).get('headless', 'N/A')}

[dim]Edita config/settings.yaml para cambiar la configuración[/dim]
            """,
            title="Configuración",
            border_style="blue"
        ))
        
    except Exception as e:
        console.print(f"\n❌ Error cargando configuración: {e}", style="red")


def _show_help():
    """Muestra ayuda."""
    console.print(Panel(
        """
[bold cyan]AutoCV - Ayuda[/bold cyan]

[bold]¿Cómo usar AutoCV?[/bold]

1. [cyan]Configura tu perfil[/cyan]
   Edita el archivo [bold]data/mi_perfil.yaml[/bold] con tu información real.
   Es importante que sea información verdadera y verificable.

2. [cyan]Busca ofertas[/cyan]
   Usa la opción "Buscar ofertas" para encontrar trabajos en LinkedIn.
   Las ofertas se guardarán automáticamente.

3. [cyan]Genera CVs personalizados[/cyan]
   Selecciona una oferta y genera un CV adaptado a ese puesto.
   La IA reorganizará tu información para destacar lo más relevante.

4. [cyan]Aplica a las ofertas[/cyan]
   Usa el CV generado para aplicar a los trabajos.

[bold]Requisitos:[/bold]
• Ollama instalado y ejecutándose (para la IA local)
• Python 3.10+
• Chrome instalado (para el scraping)

[bold]Archivos importantes:[/bold]
• data/mi_perfil.yaml - Tu información personal
• config/settings.yaml - Configuración general
• config/linkedin_config.yaml - Configuración de LinkedIn

[bold]¿Problemas?[/bold]
Ejecuta [bold]python main.py status[/bold] para verificar el sistema.
        """,
        title="Ayuda",
        border_style="cyan"
    ))
