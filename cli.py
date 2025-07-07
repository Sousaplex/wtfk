#!/usr/bin/env python3
"""
WTFK (What The Foreign Key) - Command-Line Interface

A modern, Python-based CLI to orchestrate the entire schema analysis pipeline,
replacing the run_analysis.sh script for better maintainability and portability.
"""

import click
import sys
from pathlib import Path

# Ensure the scripts directory is in the Python path
sys.path.append(str(Path(__file__).parent / 'scripts'))

from scripts.step_01_extract_schema import extract_schema
from scripts.step_02_compress_schema import compress_schema
from scripts.step_03_generate_context import generate_context
from scripts.step_04_analyze_schema import analyze_schema_with_compliance
from scripts.step_05_plan_visualizations import plan_visualizations
from scripts.step_06_generate_diagrams import generate_diagrams
from scripts.step_07_generate_final_report import generate_final_report_with_diagrams
from scripts.step_08_generate_html import generate_html_report

@click.group()
def cli():
    """WTFK (What The Foreign Key) - SQL Schema Analysis Pipeline"""
    pass

def detect_schema_file() -> Path:
    """
    Finds the unique .sql file in the 'original' directory.
    Aborts if zero or more than one .sql files are found.
    """
    original_dir = Path("original")
    if not original_dir.is_dir():
        click.echo(click.style("Error: 'original/' directory not found.", fg='red'), err=True)
        click.echo("Please create it and place your schema.sql file inside.", err=True)
        raise click.Abort()

    sql_files = list(original_dir.glob("*.sql"))

    if not sql_files:
        click.echo(click.style("Error: No .sql file found in 'original/' directory.", fg='red'), err=True)
        raise click.Abort()

    if len(sql_files) > 1:
        click.echo(click.style(f"Error: Multiple .sql files found in 'original/':", fg='red'), err=True)
        for f in sql_files:
            click.echo(f"  - {f}", err=True)
        click.echo("Please ensure only one .sql file is present in the 'original/' directory.", err=True)
        raise click.Abort()
    
    found_file = sql_files[0]
    click.echo(click.style(f"✅ Found schema file: {found_file}", fg='green'))
    return found_file

@cli.command()
@click.option('--start-at', type=click.Choice(['extract', 'compress', 'context', 'analysis', 'visuals', 'report', 'html'], case_sensitive=False), help="Start execution at a specific step.")
@click.option('--skip', multiple=True, type=click.Choice(['extract', 'compress', 'context', 'analysis', 'visuals', 'report', 'html'], case_sensitive=False), help="Skip a specific step (can be used multiple times).")
@click.option('--frameworks', multiple=True, help="Specify compliance frameworks to analyze.")
@click.option('--settings', default='settings.json', help="Path to settings.json file.")
def run(start_at, skip, frameworks, settings):
    """Run the full analysis pipeline by auto-detecting the schema file."""
    
    click.echo(click.style("Starting WTFK Analysis Pipeline", fg='cyan', bold=True))

    # --- Framework Selection (moved to the top) ---
    if not frameworks:
        try:
            import questionary
            from scripts.step_04_analyze_schema import SchemaAnalyzer
            # We need a temporary analyzer to get the path to the compliance dir
            temp_analyzer = SchemaAnalyzer(settings_file=settings)
            compliance_dir = Path(temp_analyzer.settings['paths'].get('compliance_dir', 'compliance'))
            if compliance_dir.is_dir():
                choices = sorted([f.stem for f in compliance_dir.glob("*.md")])
                if choices:
                    frameworks = questionary.checkbox("Select compliance frameworks to analyze:", choices=choices).ask() or []
        except Exception as e:
            click.echo(click.style(f"Could not display interactive prompt: {e}", fg='red'), err=True)
            frameworks = []

    if frameworks:
        click.echo(click.style(f"Analyzing with frameworks: {', '.join(frameworks)}", fg='blue'))

    input_file = detect_schema_file()

    # --- Define file paths ---
    schema_only_sql = Path("schemas/schema_only.sql")
    schema_compressed_txt = Path("schemas/schema_compressed.txt")
    context_dir = Path("context")
    viz_plan_json = Path("output/visualization_plan.json")
    final_report_md = Path("output/final_report.md")
    final_report_html = Path("output/final_report.html")
    
    # --- Step Execution Logic ---
    steps = ['extract', 'compress', 'context', 'analysis', 'visuals', 'report', 'html']
    
    if start_at:
        try:
            start_index = steps.index(start_at)
            for i in range(start_index):
                if steps[i] not in skip:
                    skip += (steps[i],)
        except ValueError:
            pass

    # --- Create necessary directories ---
    schema_only_sql.parent.mkdir(exist_ok=True)
    viz_plan_json.parent.mkdir(exist_ok=True)
    context_dir.mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)

    # --- Execute Pipeline Steps ---
    try:
        if 'extract' not in skip:
            click.echo(click.style("\nStep 1: Extracting Schema...", fg='yellow'))
            if not extract_schema(input_file, schema_only_sql): raise click.Abort()
        else:
            click.echo(click.style("\nSkipping Step 1: Schema Extraction", fg='blue'))

        if 'compress' not in skip:
            click.echo(click.style("\nStep 2: Compressing Schema...", fg='yellow'))
            if not compress_schema(schema_only_sql, schema_compressed_txt): raise click.Abort()
        else:
            click.echo(click.style("\nSkipping Step 2: Schema Compression", fg='blue'))

        if 'context' not in skip:
            click.echo(click.style("\nStep 3: Generating Context...", fg='yellow'))
            if not generate_context(schema_compressed_txt, context_dir, settings)[0]: raise click.Abort()
        else:
            click.echo(click.style("\nSkipping Step 3: Context Generation", fg='blue'))

        if 'analysis' not in skip:
            click.echo(click.style("\nStep 4: Analyzing Schema with AI...", fg='yellow'))
            # The analysis step now uses the final context file from Step 3
            context_file = context_dir / f"{schema_compressed_txt.stem}_context.json"
            if not context_file.exists():
                click.echo(click.style(f"Error: Context file not found at {context_file}", fg='red'), err=True)
                raise click.Abort()
            
            if not analyze_schema_with_compliance(
                context_file=context_file,
                frameworks=list(frameworks),
                settings_file=settings
            ): raise click.Abort()
        else:
            click.echo(click.style("\nSkipping Step 4: AI Analysis", fg='blue'))

        if 'visuals' not in skip:
            click.echo(click.style("\nStep 5: Planning Visualizations...", fg='yellow'))
            if not plan_visualizations(schema_compressed_txt, viz_plan_json, settings): raise click.Abort()

            click.echo(click.style("\nStep 6: Generating Diagrams...", fg='yellow'))
            if not generate_diagrams(viz_plan_json, schema_compressed_txt, settings): raise click.Abort()
        else:
            click.echo(click.style("\nSkipping Visualization Steps (5 & 6)", fg='blue'))

        if 'report' not in skip:
            click.echo(click.style("\nStep 7: Generating Final Report...", fg='yellow'))
            if not generate_final_report_with_diagrams(settings_file=settings): raise click.Abort()
        else:
            click.echo(click.style("\nSkipping Step 7: Final Report Generation", fg='blue'))

        if 'html' not in skip:
            click.echo(click.style("\nStep 8: Generating HTML Report...", fg='yellow'))
            if not generate_html_report(final_report_md, final_report_html, settings_file=settings): raise click.Abort()
        else:
            click.echo(click.style("\nSkipping Step 8: HTML Report Generation", fg='blue'))

        click.echo(click.style("\n🎉 WTFK Analysis Pipeline Completed Successfully!", fg='green', bold=True))
        click.echo(f"Your final report is available at: {final_report_html}")

    except click.Abort:
        click.echo(click.style("\n💥 Pipeline execution aborted.", fg='red', bold=True), err=True)
        sys.exit(1)

@cli.command()
@click.option('--yes', is_flag=True, callback=lambda c, p, v: not v and c.abort(),
              expose_value=False,
              prompt='Are you sure you want to delete all generated files?')
def clean():
    """Remove all generated files, leaving the directory structure intact."""
    click.echo(click.style("🧹 Cleaning contents of generated directories...", fg='magenta'))
    
    dirs_to_clean = [
        Path("schemas"),
        Path("context"),
        Path("output"),
        Path("logs")
    ]
    
    for directory in dirs_to_clean:
        if directory.is_dir():
            click.echo(f"   - Cleaning directory: {directory}/")
            for item in directory.iterdir():
                try:
                    if item.is_dir():
                        # Keep .gitkeep files if they exist
                        if (item / ".gitkeep").exists():
                            for sub_item in item.iterdir():
                                if sub_item.name != ".gitkeep":
                                    if sub_item.is_dir():
                                        import shutil
                                        shutil.rmtree(sub_item)
                                    else:
                                        sub_item.unlink()
                        else:
                            import shutil
                            shutil.rmtree(item)
                    elif item.name != ".gitkeep":
                        item.unlink()
                except OSError as e:
                    click.echo(click.style(f"     - Error deleting {item}: {e}", fg='red'), err=True)
        else:
            click.echo(f"   - Directory not found, skipping: {directory}/")
            
    click.echo(click.style("✅ Cleanup complete.", fg='green'))

if __name__ == '__main__':
    cli()