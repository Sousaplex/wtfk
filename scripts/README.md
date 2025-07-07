# WTFK Pipeline Scripts

This directory contains the step-by-step scripts that transform your database schema into a comprehensive analysis report. Each script builds on the previous one, creating a complete picture of your database structure and relationships.

## 🚀 **How the Pipeline Works**

Think of this as a sophisticated **database detective** that examines your schema and creates a professional report. Here's what happens step by step:

---

## 📋 **Step 1: Extract Schema Structure**
**File**: `step_01_extract_schema.py`

**What it does**: Takes your messy database dump file and extracts just the important structural information.

**Human explanation**: 
Imagine you have a huge SQL file with thousands of lines including data, comments, and setup commands. This step is like having a librarian who reads through everything and carefully extracts only the "table of contents" - the CREATE TABLE statements, indexes, and constraints that define your database structure.

**Input**: Raw SQL dump file (e.g., `original/schema.sql`)
**Output**: Clean schema file (`schemas/schema_only.sql`)

**Why it's important**: Your original SQL file might be 50MB with sample data. This step creates a clean, focused version that's easier to analyze.

---

## 🗜️ **Step 2: Compress to Hierarchical Format**
**File**: `step_02_compress_schema.py`

**What it does**: Converts the SQL into a structured, easy-to-read format.

**Human explanation**:
This is like taking a legal document and creating a clear summary. Instead of reading through hundreds of lines of SQL syntax, it creates a clean outline format that shows:
- Each table and its purpose
- All columns with their types
- Relationships between tables
- Indexes and constraints

**Input**: Clean schema SQL (`schemas/schema_only.sql`)
**Output**: Structured text format (`schemas/schema_compressed.txt`)

**Why it's important**: Makes it possible for AI to quickly understand your database structure without getting lost in SQL syntax.

---

## 🧠 **Step 3: Generate Analysis Context**
**File**: `step_03_generate_context.py`

**What it does**: Creates smart summaries and statistics about your database.

**Human explanation**:
Think of this as a research assistant who studies your database and creates a detailed briefing document. It:
- Counts everything (tables, columns, relationships)
- Categorizes tables by their purpose (user management, business logic, etc.)
- Identifies patterns and important relationships
- Creates a "cheat sheet" for the AI analysis

**Input**: Compressed schema (`schemas/schema_compressed.txt`)
**Output**: Context files (`context/context.json`, `context/stats.json`)

**Why it's important**: Gives the AI analyst the background knowledge needed to provide intelligent insights.

---

## 🤖 **Step 4: AI-Powered Analysis**
**File**: `step_04_analyze_schema.py`

**What it does**: Uses artificial intelligence to analyze your database like a senior architect would.

**Human explanation**:
This is where the magic happens! The AI acts like a database expert who:
- Understands your business domain by studying the table names and relationships
- Identifies security concerns and data privacy issues
- Spots performance problems and optimization opportunities
- Explains complex relationships in plain English
- Provides actionable recommendations

**Input**: Compressed schema + context files
**Output**: Comprehensive analysis report (`output/schema_analysis_[timestamp].md`)

**Why it's important**: Gives you expert-level insights without needing to hire a database consultant.

---

## 📊 **Step 5: Plan Visualizations**
**File**: `step_05_plan_visualizations.py`

**What it does**: Decides what charts and diagrams would best illustrate your database structure.

**Human explanation**:
Like a graphic designer planning an infographic, this step:
- Analyzes your data to determine the most useful visualizations
- Plans network diagrams to show table relationships
- Designs charts to show data distribution and patterns
- Creates a "blueprint" for the visual elements

**Input**: Compressed schema + context files
**Output**: Visualization plan (`output/visualization_plan.json`)

**Why it's important**: Ensures the final report has meaningful visuals, not just generic charts.

---

## 🎨 **Step 6: Generate Diagrams**
**File**: `step_06_generate_diagrams.py`

**What it does**: Creates the actual charts, graphs, and network diagrams.

**Human explanation**:
This is the artist who brings the visualization plan to life:
- Creates network diagrams showing how tables connect
- Generates charts showing data patterns and distributions
- Builds relationship maps and dependency graphs
- Saves everything as high-quality images

**Input**: Visualization plan + schema data
**Output**: Diagram images (`output/diagrams/`)

**Why it's important**: Transforms complex data relationships into easy-to-understand visual representations.

---

## 📖 **Step 7: Generate Final Report**
**File**: `step_07_generate_final_report.py`

**What it does**: Combines the AI analysis with the generated diagrams into a complete report.

**Human explanation**:
Like a professional document editor, this step:
- Takes the AI analysis and polishes it
- Inserts the relevant diagrams at the right places
- Ensures consistent formatting and professional presentation
- Creates a comprehensive final document

**Input**: AI analysis + generated diagrams
**Output**: Final report (`output/final_report.md`)

**Why it's important**: Creates a polished, professional document that's ready to share with stakeholders.

---

## 🌐 **Step 8: Generate HTML Report**
**File**: `step_08_generate_html.py`

**What it does**: Converts the final report into an interactive web page.

**Human explanation**:
This is like a web developer who takes your document and creates a modern, interactive website:
- Converts markdown to beautiful HTML
- Adds professional styling and responsive design
- Includes search functionality and navigation
- Styles table names with your custom preferences (like highlighting `auth_user` in red)
- Makes it mobile-friendly and easy to share

**Input**: Final report markdown file
**Output**: Interactive HTML file (`output/final_report.html`)

**Why it's important**: Creates a modern, shareable format that's perfect for viewing and presenting.

---

## 📄 **Step 9: Convert to PDF (Optional)**
**File**: `09_html_to_pdf.py`

**What it does**: Converts the HTML report to PDF format for printing or formal distribution.

**Human explanation**:
Sometimes you need a traditional PDF for:
- Printing and physical distribution
- Formal documentation requirements
- Email attachments
- Archival purposes

This step takes your beautiful HTML report and creates a PDF that looks exactly the same.

**Input**: HTML report file
**Output**: PDF file (`output/final_report.pdf`)

**Why it's important**: Provides a traditional format when needed while maintaining the same professional appearance.

---

## 🔄 **How They Work Together**

```
Raw SQL File → Clean Structure → Smart Analysis → Visual Insights → Professional Report → Interactive Web Page
     ↓              ↓              ↓              ↓                ↓                    ↓
  Step 1         Step 2         Step 4         Step 6           Step 7            Step 8
                    ↓              ↑              ↑
                 Step 3         Step 5         (Optional)
                (Context)    (Planning)        Step 9
                                                (PDF)
```

## 🎯 **Key Benefits**

- **Automated**: Runs without human intervention
- **Intelligent**: Uses AI to provide expert-level insights
- **Visual**: Creates diagrams and charts automatically
- **Professional**: Generates report-quality documentation
- **Flexible**: Works with any PostgreSQL schema
- **Modern**: Creates interactive web-based reports

## 🚀 **Getting Started**

Run all steps with:
```bash
./run_analysis.sh
```

Or run individual steps:
```bash
python3 scripts/step_01_extract_schema.py original/schema.sql
python3 scripts/step_02_compress_schema.py schemas/schema_only.sql
# ... and so on
```

## 🔧 **Customization**

Each step can be customized through `settings.json`:
- AI model preferences
- Visualization styles
- Report formatting
- HTML themes
- PDF options

The pipeline is designed to be both powerful and user-friendly - you get enterprise-level database analysis with minimal effort! 