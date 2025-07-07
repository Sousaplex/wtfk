![WTFK Logo](wtfk-logo.png)

# WTFK (What The Foreign Key) - SQL Schema Analysis Pipeline

WTFK is a comprehensive system for analyzing large SQL database schemas using AI-powered insights and intelligent visualizations. When you're staring at a massive schema wondering "what the foreign key is going on here?" - WTFK has the answers.

This project transforms your database schema into a rich, contextualized dataset that an LLM can use to help you understand your application, your data, and even your organization's architecture. The final output is a beautiful, self-contained interactive HTML report.

## Features

*   **AI-Powered Analysis**: Uses Google Gemini to perform a deep, comprehensive analysis of your schema.
*   **Interactive CLI**: A user-friendly command-line interface guides you through the process.
*   **Compliance Analysis**: Analyze your schema against frameworks like GDPR, HIPAA, and more. Extensible for custom frameworks.
*   **Intelligent Visualizations**: Automatically generates a variety of diagrams, network graphs, and heatmaps to visualize your schema's structure and complexity.
*   **Interactive HTML Reports**: Delivers a polished, single-file HTML report with embedded, interactive diagrams and search functionality.
*   **Modular & Extensible**: The Python-based pipeline is designed to be easily understood, maintained, and extended.

## Quick Start

1.  **Install Dependencies**:
    ```bash
    # Create and activate a virtual environment
    python3 -m venv .venv
    source .venv/bin/activate
    
    # Install required packages
    pip install -r requirements.txt
    ```

2.  **Set API Key**:
    ```bash
    # Set your Google API key
    export GOOGLE_API_KEY="your-api-key-here"
    
    # Or create a .env file with:
    # GOOGLE_API_KEY=your-api-key
    ```

3.  **Run the Pipeline**:
    ```bash
    # Place your PostgreSQL dump in the original/ directory.
    # The script will auto-detect it.
    
    # Run the complete pipeline interactively
    python3 cli.py run
    ```
That's it! The script will guide you through the process, including selecting compliance frameworks. The final report will be generated in the `output/` directory.

## Usage

The primary way to use the tool is via the `cli.py` script.

### Running the Pipeline

```bash
# Run the full pipeline with an interactive prompt for compliance frameworks
python3 cli.py run

# Run with specific compliance frameworks (non-interactive)
python3 cli.py run --frameworks gdpr hipaa

# Skip visualization steps for a faster, text-only analysis
python3 cli.py run --skip-visuals

# See all available options
python3 cli.py run --help
```

### Cleaning Generated Files

To safely delete all generated files (`output/`, `schemas/`, `context/`, `logs/`) and reset the project, use the `clean` command.

```bash
# Clean the project (will ask for confirmation)
python3 cli.py clean
```

## The Final Report

The main deliverable is a single, self-contained, and interactive HTML file located at `output/final_report.html`.

*   **Interactive Diagrams**: Hover over data points and explore connections.
*   **Searchable Content**: Quickly find information on specific tables or columns.
*   **Responsive Design**: View the report on any device.
*   **Portable**: A single file that can be easily shared with your team.

## Pipeline Details

The pipeline is orchestrated by `cli.py` and consists of modular steps implemented in the `scripts/` directory.

| Step | Script | Description | Key Output(s) |
| :--- | :--- | :--- | :--- |
| 1 | `step_01_extract_schema.py` | Extracts the schema structure from the raw SQL dump. | `schemas/schema_only.sql` |
| 2 | `step_02_compress_schema.py` | Converts the SQL schema into a compact, hierarchical format. | `schemas/schema_compressed.txt` |
| 3 | `step_03_generate_context.py` | Generates statistics and categorizes tables using AI. | `context/*.json`, `logs/*.log` |
| 4 | `step_04_analyze_schema.py` | Performs the main, comprehensive AI analysis of the schema. | `output/schema_analysis.md` |
| 5 | `step_05_plan_visualizations.py` | Intelligently plans the most effective diagrams for the report. | `output/visualization_plan.json` |
| 6 | `step_06_generate_diagrams.py` | Creates interactive HTML diagrams using Plotly. | `output/diagrams/*.html` |
| 7 | `step_07_generate_final_report.py` | Integrates diagrams and explanations into a final markdown report. | `output/final_report.md` |
| 8 | `step_08_generate_html.py` | Converts the markdown report into a self-contained HTML file. | `output/final_report.html` |

## Compliance Analysis

This tool can analyze your schema against specific compliance frameworks. To add a new framework:

1.  **Add a Definition:** Create a `your_framework.md` file in the `compliance/` directory. This file should describe the framework's rules and data types.
2.  **Add a Snippet:** Create a `your_framework.txt` file in `prompts/compliance_snippets/`. This file should contain a short paragraph telling the AI what "hat" to wear when analyzing for this framework.

The framework will then be available in the interactive selector or via the `--frameworks` flag.

## Roadmap

The goal is to expand the analysis beyond the database schema to include the application code itself for richer context.

- **ORM & Code Analysis:** Extend the scanner to analyze application code (e.g., Django/TypeORM models) to understand how data is used, which provides more signal than the schema alone.
- **Endpoint Analysis:** Scan API endpoints to map data access patterns and identify how different parts of the application interact with the database.
- **Enhanced Compliance:** Add more built-in compliance frameworks and improve the depth of compliance-related analysis.

We welcome collaboration! If you're interested in contributing, please reach out to `mike.psousa+wtfk@gmail.com`.

## Project Structure

```
/
├── original/                    # Place your single source .sql dump here
├── compliance/                  # User-provided compliance framework definitions (.md)
├── prompts/                     # Prompts for the AI models
├── templates/                   # HTML, CSS, and JS templates for the final report
├── scripts/                     # The core Python scripts for each pipeline step
├── cli.py                       # The main Python-based CLI for running the pipeline
├── settings.json                # Configuration parameters
├── requirements.txt             # Python dependencies
└── README.md                    # This file
---
├── schemas/                     # (Generated) Processed schema files
├── context/                     # (Generated) Analysis context and statistics
├── output/                      # (Generated) All final deliverables (reports, diagrams)
└── logs/                        # (Generated) Detailed logs for debugging LLM calls
```
