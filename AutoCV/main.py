"""
AutoCV - Punto de entrada principal
===================================
Sistema automatizado para generar CVs personalizados y aplicar a ofertas de trabajo.
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from loguru import logger
import sys
from pathlib import Path

# Configurar logging
logger.remove()
logger.add(
    "logs/autocv_{time}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG"
)
logger.add(sys.stderr, level="INFO")

# Añadir el directorio src al path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.profile_manager import ProfileManager
from src.core.cv_generator import CVGenerator
from src.scraper.linkedin_scraper import LinkedInScraper
from src.ai.ollama_client import OllamaClient
from src.utils.config_loader import load_config

console = Console()


def show_banner():
    """Muestra el banner de la aplicación."""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║     █████╗ ██╗   ██╗████████╗ ██████╗  ██████╗██╗   ██╗   ║
    ║    ██╔══██╗██║   ██║╚══██╔══╝██╔═══██╗██╔════╝██║   ██║   ║
    ║    ███████║██║   ██║   ██║   ██║   ██║██║     ██║   ██║   ║
    ║    ██╔══██║██║   ██║   ██║   ██║   ██║██║     ╚██╗ ██╔╝   ║
    ║    ██║  ██║╚██████╔╝   ██║   ╚██████╔╝╚██████╗ ╚████╔╝    ║
    ║    ╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═════╝  ╚═════╝  ╚═══╝     ║
    ║                                                           ║
    ║        🚀 Generador Automático de CVs Personalizados      ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


@click.group()
@click.option('--debug', is_flag=True, help='Activar modo debug')
@click.pass_context
def cli(ctx, debug):
    """AutoCV - Sistema de generación automática de CVs personalizados."""
    ctx.ensure_object(dict)
    ctx.obj['debug'] = debug
    if debug:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")


@cli.command()
def status():
    """Muestra el estado del sistema y verifica las dependencias."""
    show_banner()
    
    table = Table(title="Estado del Sistema")
    table.add_column("Componente", style="cyan")
    table.add_column("Estado", style="green")
    table.add_column("Detalles", style="yellow")
    
    # Verificar perfil
    profile_path = Path("data/mi_perfil.yaml")
    if profile_path.exists():
        table.add_row("📋 Perfil", "✅ OK", str(profile_path))
    else:
        table.add_row("📋 Perfil", "❌ Error", "No encontrado")
    
    # Verificar Ollama
    try:
        ollama = OllamaClient()
        if ollama.check_connection():
            models = ollama.list_models()
            table.add_row("🤖 Ollama", "✅ OK", f"Modelos: {', '.join(models[:3])}")
        else:
            table.add_row("🤖 Ollama", "❌ Error", "No conectado")
    except Exception as e:
        table.add_row("🤖 Ollama", "❌ Error", str(e))
    
    # Verificar configuración
    try:
        config = load_config()
        table.add_row("⚙️ Configuración", "✅ OK", "Cargada correctamente")
    except Exception as e:
        table.add_row("⚙️ Configuración", "❌ Error", str(e))
    
    console.print(table)


@cli.command()
@click.argument('query')
@click.option('--location', '-l', default=None, help='Ubicación para buscar')
@click.option('--limit', '-n', default=20, help='Número máximo de ofertas')
def search(query, location, limit):
    """Busca ofertas de trabajo en LinkedIn."""
    show_banner()
    
    console.print(f"\n🔍 Buscando: [bold]{query}[/bold]", style="cyan")
    if location:
        console.print(f"📍 Ubicación: [bold]{location}[/bold]", style="cyan")
    
    try:
        scraper = LinkedInScraper()
        jobs = scraper.search_jobs(query, location=location, limit=limit)
        
        if not jobs:
            console.print("\n⚠️ No se encontraron ofertas", style="yellow")
            return
        
        # Mostrar resultados
        table = Table(title=f"Ofertas Encontradas ({len(jobs)})")
        table.add_column("ID", style="dim")
        table.add_column("Puesto", style="cyan")
        table.add_column("Empresa", style="green")
        table.add_column("Ubicación", style="yellow")
        table.add_column("Match", style="magenta")
        
        for job in jobs:
            table.add_row(
                job.get('id', 'N/A')[:8],
                job.get('title', 'N/A')[:40],
                job.get('company', 'N/A')[:25],
                job.get('location', 'N/A')[:20],
                f"{job.get('match_score', 0)}%"
            )
        
        console.print(table)
        console.print(f"\n💾 Ofertas guardadas en: data/ofertas/", style="green")
        
    except Exception as e:
        console.print(f"\n❌ Error: {e}", style="red")
        logger.exception("Error en búsqueda")


@cli.command()
@click.argument('job_id')
@click.option('--format', '-f', type=click.Choice(['pdf', 'html']), default='pdf')
@click.option('--preview', is_flag=True, help='Ver preview antes de guardar')
def generate(job_id, format, preview):
    """Genera un CV personalizado para una oferta específica."""
    show_banner()
    
    console.print(f"\n📝 Generando CV para oferta: [bold]{job_id}[/bold]", style="cyan")
    
    try:
        # Cargar perfil
        profile_manager = ProfileManager()
        profile = profile_manager.load_profile()
        
        # Cargar oferta
        # TODO: Cargar oferta desde cache
        
        # Generar CV y carta de presentación
        generator = CVGenerator()
        result = generator.generate(
            profile=profile,
            job_id=job_id,
            output_format=format,
            preview=preview,
            include_cover_letter=True
        )
        
        console.print(f"\n✅ CV generado: [bold]{result['cv']}[/bold]", style="green")
        
        if result.get('cover_letter'):
            console.print(f"✅ Carta de presentación: [bold]{result['cover_letter']}[/bold]", style="green")
        
    except Exception as e:
        console.print(f"\n❌ Error: {e}", style="red")
        logger.exception("Error generando CV")


@cli.command()
@click.argument('job_id')
@click.option('--dry-run', is_flag=True, help='Simular sin aplicar realmente')
def apply(job_id, dry_run):
    """Aplica a una oferta de trabajo."""
    show_banner()
    
    if dry_run:
        console.print("\n🧪 [bold yellow]MODO SIMULACIÓN[/bold yellow] - No se aplicará realmente\n")
    
    console.print(f"📤 Aplicando a oferta: [bold]{job_id}[/bold]", style="cyan")
    
    # TODO: Implementar lógica de aplicación
    console.print("\n⚠️ Funcionalidad en desarrollo", style="yellow")


@cli.command()
@click.option('--auto', is_flag=True, help='Modo totalmente automático')
@click.option('--confirm', is_flag=True, default=True, help='Pedir confirmación')
def batch(auto, confirm):
    """Modo batch: busca, genera y aplica automáticamente."""
    show_banner()
    
    if auto:
        console.print("\n⚠️ [bold red]MODO AUTOMÁTICO[/bold red]", style="red")
        if confirm:
            if not click.confirm("¿Estás seguro de continuar en modo automático?"):
                return
    
    console.print("\n🔄 Iniciando proceso batch...", style="cyan")
    
    # TODO: Implementar modo batch
    console.print("\n⚠️ Funcionalidad en desarrollo", style="yellow")


@cli.command()
def profile():
    """Muestra y valida tu perfil actual."""
    show_banner()
    
    try:
        profile_manager = ProfileManager()
        profile = profile_manager.load_profile()
        
        # Mostrar resumen del perfil
        console.print(Panel(
            f"""
[bold cyan]👤 {profile.get('personal_information', {}).get('nombre', 'N/A')} {profile.get('personal_information', {}).get('apellidos', '')}[/bold cyan]
📧 {profile.get('personal_information', {}).get('email', 'N/A')}
📍 {profile.get('personal_information', {}).get('ubicacion', {}).get('ciudad', 'N/A')}

[bold]📚 Educación:[/bold] {len(profile.get('educacion', []))} entradas
[bold]💼 Experiencia:[/bold] {len(profile.get('experiencia', []))} empleos
[bold]🛠️ Habilidades:[/bold] {len(profile.get('habilidades_tecnicas', {}).get('lenguajes', []))} lenguajes
[bold]🌍 Idiomas:[/bold] {len(profile.get('idiomas', []))} idiomas
[bold]📜 Certificaciones:[/bold] {len(profile.get('certificaciones', []))} certificaciones
            """,
            title="Tu Perfil",
            border_style="green"
        ))
        
        # Validar perfil
        issues = profile_manager.validate_profile(profile)
        if issues:
            console.print("\n⚠️ Problemas encontrados:", style="yellow")
            for issue in issues:
                console.print(f"  • {issue}", style="yellow")
        else:
            console.print("\n✅ Perfil válido y completo", style="green")
            
    except FileNotFoundError:
        console.print("\n❌ Perfil no encontrado. Crea el archivo data/mi_perfil.yaml", style="red")
    except Exception as e:
        console.print(f"\n❌ Error: {e}", style="red")


@cli.command()
def interactive():
    """Modo interactivo con menú guiado."""
    show_banner()
    
    from src.utils.interactive_menu import run_interactive_menu
    run_interactive_menu()


def main():
    """Función principal."""
    # Crear directorios necesarios
    directories = [
        "data/ofertas",
        "data/cvs_generados",
        "logs"
    ]
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    # Ejecutar CLI
    cli()


if __name__ == "__main__":
    main()
