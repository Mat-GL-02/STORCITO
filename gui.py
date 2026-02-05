"""
File processing system with interactive menu
Installation:
    pip install rich questionary
"""

import questionary

from FR.rutinas.setup import check_valid_entries
from FR.GCI import gci_folder
from FR.NDVI import ndvi_folder

from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from questionary import Style

console = Console()

# Custom style
custom_style = Style([
    ('qmark', 'fg:#673ab7 bold'),
    ('question', 'fg:#ffffff bold'),
    ('answer', 'fg:#00ff00 bold'),
    ('pointer', 'fg:#673ab7 bold'),
    ('highlighted', 'fg:#673ab7 bold'),
    ('selected', 'fg:#00ff00'),
    ('separator', 'fg:#cc5454'),
    ('instruction', 'fg:#858585'),
    ('text', 'fg:#ffffff'),
])

# Global variables for paths
input_folder: str = "INPUT"
output_folder: str = "OUTPUT"

def validate_folder(path):
    """Validates that the folder exists"""
    if not path:
        return "Path cannot be empty"

    path_obj = Path(path)
    if not path_obj.exists():
        return "Folder does not exist"
    if not path_obj.is_dir():
        return "Path must be a folder"
    return True

def read_input_files():
    """Reads file names from the input folder"""
    if not input_folder:
        return []

    input_path = Path(input_folder)
    if not input_path.exists():
        return []

    try:
        files = [f.name for f in input_path.iterdir() if f.is_file()]
        return files
    except Exception as e:
        console.print(f"[red]Error reading files: {e}[/red]")
        return []

def calculate_folder_metrics():
    """Calculates metrics for the input folder"""
    if not input_folder:
        return None

    input_path = Path(input_folder)
    if not input_path.exists():
        return None

    try:
        items = list(input_path.iterdir())
        files = [f for f in items if f.is_file()]

        # Calculate metrics
        metrics = {
            'total_files': len(files),
            'total_size': sum(f.stat().st_size for f in files),
            'extensions': {},
        }

        # Count extensions
        for file in files:
            ext = file.suffix.lower() or 'no extension'
            metrics['extensions'][ext] = metrics['extensions'].get(ext, 0) + 1

        return metrics

    except Exception as e:
        console.print(f"[red]Error calculating metrics: {e}[/red]")
        return None

def format_size(bytes):
    """Formats bytes to a readable unit"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} TB"

def generate_metrics_subtitle(metrics, show_files=False):
    """Generates a subtitle with folder metrics"""
    if not metrics:
        return "[red]No files found in input folder[/red]"

    lines = []

    # Basic information
    lines.append(f"[dim]Total files: [bold]{metrics['total_files']}[/bold][/dim]")
    lines.append(f"[dim]Total size: [bold]{format_size(metrics['total_size'])}[/bold][/dim]")

    # Extensions
    if metrics['extensions']:
        ext_text = ", ".join([f"{ext}: {count}" for ext, count in sorted(metrics['extensions'].items())])
        lines.append(f"[dim]Extensions: {ext_text}[/dim]")


    # File list (optional)
    if show_files:
        files = read_input_files()
        if files:
            lines.append("\n[dim]Files:[/dim]")
            files_text = "\n".join([f"  • {file}" for file in files[:10]])
            if len(files) > 10:
                files_text += f"\n  [dim]... and {len(files) - 10} more file(s)[/dim]"
            lines.append(files_text)

    return "\n".join(lines)

def show_current_config():
    """Shows the current configuration in a table"""
    table = Table(title="⚙️ Current Configuration", box=box.ROUNDED)
    table.add_column("Parameter", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")

    input_text = input_folder if input_folder else "[red]Not configured[/red]"
    output_text = output_folder if output_folder else "[red]Not configured[/red]"

    table.add_row("Input folder", input_text)
    table.add_row("Output folder", output_text)

    # Count files if folder is configured
    if input_folder:
        files = read_input_files()
        table.add_row("Files found", str(len(files)))

    console.print(table)

def initial_configuration():
    """Initial configuration menu"""
    global input_folder, output_folder

    while True:
        console.clear()
        console.print(Panel(
            "[bold cyan]Configure working folders[/bold cyan]\n"
            "[dim]Enter the full paths of the folders[/dim]",
            title="📁 Initial Configuration",
            border_style="cyan"
        ))

        show_current_config()

        option = questionary.select(
            "\nWhat would you like to do?",
            choices=[
                questionary.Choice("📂 Configure input folder", value="input"),
                questionary.Choice("📁 Configure output folder", value="output"),
                questionary.Separator(),
                questionary.Choice("✓ Continue to main menu", value="continue"),
                questionary.Choice("← Back", value="back"),
            ],
            style=custom_style
        ).ask()

        if option == "back" or option is None:
            return False

        if option == "continue":
            if not input_folder or not output_folder:
                console.print("\n[red]⚠ You must configure both folders before continuing[/red]")
                input("\nPress Enter to continue...")
                continue
            return True

        if option == "input":
            path = questionary.path(
                "Input folder path:",
                default=input_folder if input_folder else "./INPUT",
                validate=validate_folder,
                style=custom_style
            ).ask()

            if path:
                input_folder = path
                console.print(f"\n[green]✓ Input folder configured: {input_folder}[/green]")
                files = read_input_files()
                console.print(f"[cyan]Found {len(files)} file(s)[/cyan]")
                # input("\nPress Enter to continue...")

        elif option == "output":
            path = questionary.path(
                "Output folder path:",
                default=output_folder if output_folder else "./OUTPUT",
                validate=validate_folder,
                style=custom_style
            ).ask()

            if path:
                output_folder = path
                console.print(f"\n[green]✓ Output folder configured: {output_folder}[/green]")
                # input("\nPress Enter to continue...")

def single_case_menu():
    """Single Case menu with processing options"""

    while True:
        console.clear()

        # Calculate metrics
        metrics = calculate_folder_metrics()
        subtitle = generate_metrics_subtitle(metrics, show_files=False)

        console.print(Panel(
            f"[bold green]Individual case processing[/bold green]\n\n{subtitle}",
            title="🔧 Single Case",
            border_style="green"
        ))

        option = questionary.select(
            "\nSelect a processing option:",
            choices=[
                questionary.Choice("1️⃣  Option 1: GCI", value="option1"),
                questionary.Choice("2️⃣  Option 2: NDVI", value="option2"),
                questionary.Choice("3️⃣  Option 3: NDMI", value="option3"),
                questionary.Separator("─" * 50),
                questionary.Choice("⚙️  Reconfigure folders", value="config"),
                questionary.Choice("← Back to main menu", value="back"),
            ],
            style=custom_style,
            instruction="(Use arrows to navigate)"
        ).ask()

        if option == "back" or option is None:
            break

        if option == "config":
            initial_configuration()
            continue

        # Verify there are files before processing
        if not metrics or metrics['total_files'] == 0:
            console.print("\n[red]⚠ No files to process in input folder[/red]")
            input("\nPress Enter to continue...")
            continue

        # Process according to selected option
        console.clear()

        def band_calc_info(inputs: list[str]):
            valids, _ = check_valid_entries(inputs, input_folder=input_folder)  # type: ignore

            time_intervals = [f' {v.fecha_inicio}  -->  {v.fecha_fin}' for v in valids]

            console.print(Panel(
                f"[cyan]Working bands: {inputs}\n[/cyan]"
                f"Detected {len(valids)} time instances  ",
            ))

            intervals_chosen = (questionary.checkbox(
            " Select a processing option: \n",
            choices=[questionary.Choice(title=name, value=id) for id, name in enumerate(time_intervals)],
            style=custom_style,
            instruction="(Use arrows to navigate and space to select)"
            ).ask())

            return intervals_chosen


        if option == "option1":

            inputs = ["B03", "B08"]

            chosen_intervals_idxs = band_calc_info(inputs)
            gci_folder(input_folder=input_folder, output_folder=output_folder, indices=chosen_intervals_idxs, export_image=True)


        elif option == "option2":
            inputs = ["B04", "B08"]

            chosen_intervals_idxs = band_calc_info(inputs)
            ndvi_folder(input_folder=input_folder, output_folder=output_folder, indices=chosen_intervals_idxs, export_image=True)

        elif option == "option3":
            inputs = ["B08", "B11"]

            chosen_intervals_idxs = band_calc_info(inputs)


        # console.print("\n[green]✓ Process completed successfully![/green]")
        input("\nPress Enter to return to menu...")

def static_case_menu():
    pass

def dynamic_case_menu():
    pass

def main_menu():
    """Main system menu"""

    # First run initial configuration
    if not initial_configuration():
        console.print("\nConfiguration cancelled. Exiting...\n")
        return

    while True:
        console.clear()
        console.print(Panel(
            "[bold green]File Processing System[/bold green]\n"
            "[dim]Use arrows ↑↓ to navigate and Enter to select[/dim]",
            title="🎯 Main Menu",
            border_style="green"
        ))

        show_current_config()

        option = questionary.select(
            "\nWhat would you like to do?",
            choices=[
                questionary.Choice("🔧 Raw Inputs", value="single"),
                questionary.Choice("⏱️ Static Case", value="static"),
                questionary.Choice("⏱️ Dinamic Case", value="dynamic"),
                questionary.Choice("⚙️ Reconfigure folders", value="config"),
                questionary.Separator("─" * 50),
                questionary.Choice("🚪 Exit", value="exit"),
            ],
            style=custom_style
        ).ask()

        if option is None or option == "exit":
            if option == "exit":
                confirm = questionary.confirm(
                    "Are you sure you want to exit?",
                    default=False,
                    style=custom_style
                ).ask()

                if confirm:
                    console.print("\n[bold red]👋 Goodbye![/bold red]\n")
                    break
            else:
                # Ctrl+C in main_menu - propagate
                raise KeyboardInterrupt()

        elif option == "single":
            single_case_menu()

        elif option == "static":
            static_case_menu()
        
        elif option == "dynamic":
            dynamic_case_menu()

        elif option == "config":
            initial_configuration()


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print("\n\n[bold red]👋 Program interrupted. Goodbye![/bold red]\n")
