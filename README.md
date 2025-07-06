![WTFK Logo](wtfk-logo.png)

# WTFK (What The Foreign Key) - SQL Schema Analysis Pipeline

A comprehensive system for analyzing large SQL database schemas using AI-powered insights and intelligent visualizations. When you're staring at a massive schema wondering "what the foreign key is going on here?" - WTFK has the answers.

## Quick Start

**The easiest way to run the complete pipeline:**

```bash
# 1. Place your PostgreSQL dump in original/schema.sql
# 2. Set your Google API key
export GOOGLE_API_KEY="your-api-key-here"

# 3. Run the complete pipeline
./run_analysis.sh
```

That's it! The script will auto-detect your schema and run the complete analysis pipeline.

## Overview

This pipeline transforms complex database schemas into actionable insights through a multi-phase approach:

1. **Schema Processing**: Extract and compress schema structure
2. **Context Generation**: Generate deterministic statistics and classifications  
3. **AI Analysis**: LLM-powered comprehensive analysis using Google Gemini
4. **Visualization Intelligence**: AI-planned diagrams and charts
5. **Diagram Generation**: Professional charts and graphs
6. **Final Report**: Comprehensive documentation with embedded visualizations

## Project Structure

```
schema/
├── original/                    # Source database dumps
│   └── schema.sql              # Your PostgreSQL dump (auto-detected)
├── schemas/                     # Processed schema files
│   ├── schema_only.sql         # Schema structure only (no data)
│   └── schema_compressed.txt   # Compressed hierarchical format
├── context/                     # Generated analysis context
│   ├── context.json            # Full table and column context
│   └── stats.json              # Statistical summaries
├── output/                      # Complete analysis deliverables
│   ├── schema_analysis.md      # Initial analysis report
│   ├── final_report.md         # Final comprehensive report with diagrams
│   ├── visualization_plan.json # AI-generated visualization plan
│   ├── generation_report.json  # Diagram generation summary
│   └── diagrams/               # Generated visualizations
│       ├── executive_summary_*.png
│       ├── domain_analysis_*.png
│       ├── performance_*.png
│       ├── security_*.png
│       └── integration_*.png
├── scripts/                     # Processing pipeline
│   ├── 01_extract_schema.py    # Extract schema from dump
│   ├── 02_compress_schema.py   # Convert to hierarchical format
│   ├── 03_generate_context.py  # Generate analysis context
│   ├── 04_analyze_schema.py    # AI-powered analysis
│   ├── 05_plan_visualizations.py # AI visualization planning
│   ├── 06_generate_diagrams.py # Create charts and diagrams
│   └── 07_generate_final_report.py # Integrate diagrams into report
├── prompts/                     # AI prompt templates
│   ├── schema_analysis.txt     # Comprehensive analysis prompt
│   └── visualization_planning.txt # Visualization planning prompt


├── archive/                    # Archived completed analyses
│   ├── analysis_20241205_143022/ # Example timestamped archive
│   └── proptech_analysis_v1/   # Example named archive
├── run_analysis.sh             # Main pipeline script
├── archive_analysis.sh         # Archive and cleanup script
├── settings.json               # Configuration parameters
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Prerequisites

```bash
# Install all dependencies (includes AI, visualization, and data analysis packages)
pip install -r requirements.txt

# Set Google API key for Gemini
export GOOGLE_API_KEY="your-api-key-here"
# OR create .env file with: GOOGLE_API_KEY=your-api-key-here
```

## Usage Options

### Simple Usage (Recommended)

```bash
# Place your schema file in original/schema.sql, then:
./run_analysis.sh                    # Full pipeline
./run_analysis.sh --no-visuals       # Skip visualizations  
./run_analysis.sh --analysis-only    # Only AI analysis
./run_analysis.sh --visuals-only     # Only visualizations

# Archive completed analysis and clean working files
./archive_analysis.sh               # Auto-timestamped archive
./archive_analysis.sh my_analysis   # Named archive
./archive_analysis.sh --keep        # Archive but keep working files
./archive_analysis.sh --list        # List existing archives
```

### Pipeline Control

```bash
# Skip specific steps
./run_analysis.sh --skip-extract     # Use existing processed files
./run_analysis.sh --skip-compress    # Use existing compressed schema
./run_analysis.sh --skip-context     # Use existing context files

# Verbose output
./run_analysis.sh --verbose          # See detailed command execution

# Custom settings file
./run_analysis.sh --settings custom_settings.json
```

### Manual Pipeline (Advanced)

```bash
# Step 1: Extract schema structure
python3 scripts/01_extract_schema.py original/schema.sql

# Step 2: Compress to hierarchical format  
python3 scripts/02_compress_schema.py schemas/schema_only.sql

# Step 3: Generate analysis context
python3 scripts/03_generate_context.py schemas/schema_compressed.txt

# Step 4: AI-powered analysis
python3 scripts/04_analyze_schema.py schemas/schema_compressed.txt

# Step 5: Plan visualizations
python3 scripts/05_plan_visualizations.py schemas/schema_compressed.txt

# Step 6: Generate diagrams
python3 scripts/06_generate_diagrams.py --plan output/visualization_plan.json --schema schemas/schema_compressed.txt

# Step 7: Generate final report with integrated diagrams
python3 scripts/07_generate_final_report.py
```

## Schema File Requirements

- **Location**: Must be in `original/` directory  
- **Quantity**: Exactly one `.sql` file allowed
- **Naming**: `schema.sql` recommended for consistency
- **Format**: Standard PostgreSQL dump file

The script will auto-detect and validate your schema file automatically.

## Pipeline Details

### Phase 1: Schema Processing

**01_extract_schema.py** - Extracts clean schema structure
- Removes `INSERT` and `COPY` statements
- Preserves `CREATE TABLE`, `ALTER TABLE`, constraints, indexes
- Handles multi-line statements and encoding issues
- Output: Clean SQL schema file

**02_compress_schema.py** - Converts to hierarchical format
- Transforms SQL into structured shorthand notation
- Format: `table_name: column PK, column FK > other_table, column UNIQUE`
- Preserves all structural relationships
- Achieves ~87% compression while maintaining completeness

### Phase 2: Context Generation

**03_generate_context.py** - Generates deterministic statistics
- Table and column inventories
- Foreign key relationship mappings
- Data type distributions
- Table categorization (business_core, auth_security, etc.)
- Performance risk assessments
- Output: JSON context files for AI analysis

### Phase 3: AI Analysis

**04_analyze_schema.py** - Comprehensive AI-powered analysis
- Uses Google Gemini for deep analysis
- Generates executive summaries and technical assessments
- Identifies architectural patterns and issues
- Provides actionable recommendations
- Output: Professional markdown report

### Phase 4: Intelligent Visualization

**05_plan_visualizations.py** - AI visualization planning
- LLM analyzes schema characteristics
- Recommends optimal diagrams for each analysis section
- Considers audience needs and data patterns
- Output: Strategic visualization plan

**06_generate_diagrams.py** - Professional diagram generation
- Creates publication-ready charts and graphs
- Network diagrams, heatmaps, distributions, breakdowns
- Handles failed diagram generation gracefully
- Output: PNG/SVG files with generation report

### Phase 5: Final Report Integration

**07_generate_final_report.py** - Comprehensive report with embedded diagrams
- Integrates successful diagrams into analysis report
- Generates AI-powered explanations for each visualization
- Smart placement based on section relevance
- Handles missing diagrams gracefully
- Output: Complete final report with contextual visualizations

## Key Features

### Schema Compression
- **87% size reduction** while preserving all relationships
- Hierarchical format with explicit foreign key mappings
- Maintains indexes, constraints, and structural integrity

### AI-Powered Analysis
- **Comprehensive domain insights** from schema structure
- **Architectural pattern recognition** and technical debt identification
- **Security and compliance analysis** with PII sensitivity mapping
- **Performance bottleneck identification** and optimization recommendations

### Intelligent Visualizations
- **AI-planned diagrams** based on schema characteristics
- **Context-aware chart selection** for different audiences
- **Professional styling** with consistent branding
- **Strategic placement** within analysis sections

### Automated Pipeline
- **One-command execution** with intelligent defaults
- **Automatic schema detection** and validation
- **Robust error handling** with helpful messages
- **Flexible control options** for different use cases

## Example Results

### Schema Compression
- **Original**: 35,000 lines SQL dump with data
- **Extracted**: 28,000 lines schema-only  
- **Compressed**: 4,300 lines hierarchical format
- **Preserved**: 254 tables, 2,799 columns, 401 foreign keys, 506 indexes

### AI Analysis Insights
- **Identified**: "auth_user" as god object with 96 incoming foreign keys
- **Categorized**: 180 business_core tables, 35 auth_security tables
- **Flagged**: Performance bottlenecks in wide tables (100+ columns)
- **Mapped**: PII sensitivity across functional areas

### Generated Visualizations
- **Executive Summary**: Global connectivity maps and complexity rankings
- **Domain Analysis**: Functional breakdowns and relationship heatmaps
- **Performance**: Table size distributions and index coverage analysis
- **Security**: PII sensitivity hotspots and compliance mapping
- **Integration**: Data type profiles and key integration points

## Configuration

### Model Parameters
```json
{
  "model": {
    "name": "gemini-2.5-pro",
    "temperature": 0.3,
    "max_output_tokens": 65000
  }
}
```

### Table Categorization
```json
{
  "table_categorization": {
    "business_core": ["tenant", "landlord", "property", "lease"],
    "auth_security": ["auth_", "user", "token", "permission"],
    "audit_logging": ["log", "change", "history", "event"]
  }
}
```

### Visualization Settings
```json
{
  "visualizations": {
    "max_graphs_per_section": 2,
    "image_format": "png",
    "image_quality": 300
  }
}
```

### PDF Generation Styles

WTFK supports multiple professional PDF styles for different audiences:

**🎨 Available Styles:**

| Style | Description | Best For |
|-------|-------------|----------|
| `business` | Professional business report style (12pt, report class) | Stakeholder presentations, business documentation |
| `executive` | Executive summary style with larger fonts (14pt) | Executive briefings, high-level summaries |
| `technical` | Technical documentation style (11pt, two-sided) | Developer documentation, technical reviews |
| `modern` | Modern clean design with teal accents | Contemporary reports, design-conscious audiences |
| `minimal` | Clean minimal style without colors | Print-friendly, conservative formatting |

**📋 List Available Styles:**
```bash
python3 scripts/08_generate_pdf.py --list-styles
```

**🎯 Generate PDFs with Specific Styles:**
```bash
# Generate executive-style PDF
python3 scripts/08_generate_pdf.py output/final_report.md --style executive

# Generate minimal-style PDF  
python3 scripts/08_generate_pdf.py output/final_report.md --style minimal -o custom_report.pdf

# Use with complete pipeline
./run_analysis.sh --pdf-style executive
```

**⚙️ Customize Styles:**
Edit the `pdf_generation.styles` section in `settings.json` to modify fonts, margins, colors, and LaTeX options for each style.

## Advanced Usage

### Custom Analysis Prompts
Modify `