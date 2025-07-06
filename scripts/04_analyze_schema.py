#!/usr/bin/env python3
"""
WTFK (What The Foreign Key) - Schema Analyzer

This script uses LangChain with Google Gemini to analyze a compressed database schema
and generate a comprehensive markdown analysis report.

Requirements:
- langchain
- langchain-google-genai
- python-dotenv (for API key management)
"""

import argparse
import sys
import os
import json
from pathlib import Path
from datetime import datetime

try:
    from langchain.prompts import PromptTemplate
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.schema import StrOutputParser
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Missing required packages. Please install:")
    print(f"pip install langchain langchain-google-genai python-dotenv")
    print(f"Error: {e}")
    sys.exit(1)


class SchemaAnalyzer:
    def __init__(self, api_key=None, model_name=None, settings_file="settings.json"):
        """Initialize the schema analyzer with Gemini."""
        
        # Load settings
        self.settings = self.load_settings(settings_file)
        
        # Override model name if provided
        if model_name:
            self.settings['model']['name'] = model_name
        
        # Load environment variables
        load_dotenv()
        
        # Get API key from parameter, environment, or prompt user
        if api_key:
            self.api_key = api_key
        elif os.getenv('GOOGLE_API_KEY'):
            self.api_key = os.getenv('GOOGLE_API_KEY')
        else:
            print("Google API Key not found.")
            print("You can:")
            print("1. Set GOOGLE_API_KEY environment variable")
            print("2. Create a .env file with GOOGLE_API_KEY=your_key")
            print("3. Pass --api-key parameter")
            sys.exit(1)
        
        # Initialize Gemini with settings
        try:
            self.llm = ChatGoogleGenerativeAI(
                model=self.settings['model']['name'],
                google_api_key=self.api_key,
                temperature=self.settings['model']['temperature'],
                max_output_tokens=self.settings['model']['max_output_tokens'],
                top_p=self.settings['model']['top_p'],
                top_k=self.settings['model']['top_k']
            )
        except Exception as e:
            print(f"Error initializing Gemini: {e}")
            print("Please check your API key and internet connection.")
            sys.exit(1)
    
    def load_settings(self, settings_file):
        """Load settings from JSON file with fallback to defaults."""
        default_settings = {
            "model": {
                "name": "gemini-2.5-pro",
                "temperature": 0.1,
                "max_output_tokens": 8192,
                "top_p": 0.95,
                "top_k": 40,
                "safety_settings": {
                    "hate_speech": "BLOCK_NONE",
                    "dangerous_content": "BLOCK_NONE",
                    "harassment": "BLOCK_NONE",
                    "sexually_explicit": "BLOCK_NONE"
                }
            },
            "paths": {
                "schemas_dir": "schemas",
                "context_dir": "context",
                "output_dir": "output",
                "prompts_dir": "prompts"
            },
            "analysis": {
                "default_prompt": "schema_analysis.txt",
                "include_context": True,
                "verbose_output": False
            }
        }
        
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                user_settings = json.load(f)
            
            # Deep merge user settings with defaults
            settings = self._deep_merge(default_settings, user_settings)
            print(f"Loaded settings from: {settings_file}")
            return settings
            
        except FileNotFoundError:
            print(f"Settings file '{settings_file}' not found. Using defaults.")
            return default_settings
        except json.JSONDecodeError as e:
            print(f"Error parsing settings file '{settings_file}': {e}")
            print("Using default settings.")
            return default_settings
        except Exception as e:
            print(f"Error loading settings file '{settings_file}': {e}")
            print("Using default settings.")
            return default_settings
    
    def _deep_merge(self, default_dict, override_dict):
        """Deep merge two dictionaries."""
        result = default_dict.copy()
        for key, value in override_dict.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def load_prompt_template(self, prompt_file):
        """Load the prompt template from file."""
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            return PromptTemplate(
                input_variables=["schema_content", "context_summary"],
                template=template_content
            )
        except FileNotFoundError:
            print(f"Error: Prompt template file '{prompt_file}' not found.")
            sys.exit(1)
        except Exception as e:
            print(f"Error loading prompt template: {e}")
            sys.exit(1)
    
    def load_schema(self, schema_file):
        """Load the compressed schema from file."""
        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Error: Schema file '{schema_file}' not found.")
            sys.exit(1)
        except Exception as e:
            print(f"Error loading schema file: {e}")
            sys.exit(1)
    
    def load_context_data(self, context_dir, schema_file):
        """Load context data for the schema analysis."""
        context_path = Path(context_dir)
        base_name = Path(schema_file).stem
        
        # Try to load statistics file
        stats_file = context_path / f"{base_name}_stats.json"
        context_summary = ""
        
        # Add generation metadata to prevent AI hallucination
        generation_date = datetime.now().strftime("%B %d, %Y")
        model_name = self.settings['model']['name']
        
        if stats_file.exists():
            try:
                with open(stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
                
                # Generate summary text
                summary_lines = []
                # Get project name from settings
                project_name = self.settings.get('project', {}).get('name', 'Database Schema Analysis')
                generated_by = self.settings.get('project', {}).get('generated_by', 'WTFK (What The Foreign Key)')
                
                summary_lines.append("## Report Generation Context")
                summary_lines.append(f"- **Analysis Date**: {generation_date}")
                summary_lines.append(f"- **AI Model**: {model_name}")
                summary_lines.append(f"- **Project**: {project_name}")
                summary_lines.append(f"- **Generated by**: {generated_by}")
                summary_lines.append("")
                summary_lines.append("## Pre-computed Schema Statistics")
                summary_lines.append(f"- **Total Tables**: {stats.get('table_count', 'N/A')}")
                summary_lines.append(f"- **Total Columns**: {stats.get('total_columns', 'N/A')}")
                summary_lines.append(f"- **Total Foreign Key Relationships**: {stats.get('total_foreign_keys', 'N/A')}")
                summary_lines.append(f"- **Average Columns per Table**: {stats.get('avg_columns_per_table', 'N/A')}")
                summary_lines.append(f"- **Average Foreign Keys per Table**: {stats.get('avg_fks_per_table', 'N/A')}")
                summary_lines.append("")
                
                # Most referenced tables
                if stats.get('most_referenced_tables'):
                    summary_lines.append("**Most Referenced Tables (incoming FKs):**")
                    for table, count in stats['most_referenced_tables'][:5]:
                        summary_lines.append(f"- {table}: {count} incoming foreign keys")
                    summary_lines.append("")
                
                # Table categories
                if stats.get('table_categories'):
                    summary_lines.append("**Table Categories:**")
                    for category, tables in stats['table_categories'].items():
                        if tables:
                            summary_lines.append(f"- **{category.replace('_', ' ').title()}**: {len(tables)} tables")
                    summary_lines.append("")
                
                # Data type distribution
                if stats.get('data_type_distribution'):
                    summary_lines.append("**Top Data Types:**")
                    for data_type, count in list(stats['data_type_distribution'].items())[:5]:
                        summary_lines.append(f"- {data_type}: {count} columns")
                
                context_summary = '\n'.join(summary_lines)
                print(f"Loaded context statistics: {stats_file}")
                
            except Exception as e:
                print(f"Warning: Could not load context file {stats_file}: {e}")
                print("Proceeding without pre-computed statistics...")
        else:
            print(f"No context file found at {stats_file}")
            print("Consider running: python3 scripts/03_generate_context.py {schema_file}")
            
            # Still provide generation context even without stats
            project_name = self.settings.get('project', {}).get('name', 'Database Schema Analysis')
            generated_by = self.settings.get('project', {}).get('generated_by', 'WTFK (What The Foreign Key)')
            
            summary_lines = []
            summary_lines.append("## Report Generation Context")
            summary_lines.append(f"- **Analysis Date**: {generation_date}")
            summary_lines.append(f"- **AI Model**: {model_name}")
            summary_lines.append(f"- **Project**: {project_name}")
            summary_lines.append(f"- **Generated by**: {generated_by}")
            context_summary = '\n'.join(summary_lines)
        
        return context_summary
    
    def analyze_schema(self, schema_content, prompt_template, context_summary=""):
        """Analyze the schema using Gemini and the prompt template."""
        
        # Create the chain
        chain = prompt_template | self.llm | StrOutputParser()
        
        print("Analyzing schema with Gemini...")
        print("This may take a moment for large schemas...")
        
        try:
            # Run the analysis with context
            result = chain.invoke({
                "schema_content": schema_content,
                "context_summary": context_summary
            })
            return result
        
        except Exception as e:
            print(f"Error during analysis: {e}")
            print("This might be due to:")
            print("- Schema too large for the model context")
            print("- API rate limits")
            print("- Network connectivity issues")
            sys.exit(1)
    
    def save_report(self, analysis_result, output_file, schema_file):
        """Save the analysis report to a markdown file."""
        
        # Get current timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Get project name and generator info from settings
        project_name = self.settings.get('project', {}).get('name', 'Database Schema Analysis')
        generated_by = self.settings.get('project', {}).get('generated_by', 'WTFK (What The Foreign Key)')
        
        # Create the full report with metadata
        report = f"""# {project_name} Report

**Generated:** {timestamp}  
**Source Schema:** {schema_file}  
**Analyzer:** {self.settings['model']['name']}

---

{analysis_result}

---

*Report generated using {generated_by}*
"""
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            print(f"Analysis report saved to: {output_file}")
            
        except Exception as e:
            print(f"Error saving report: {e}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze PostgreSQL schema using Google Gemini AI"
    )
    parser.add_argument(
        "schema_file",
        help="Path to compressed schema file"
    )
    parser.add_argument(
        "-p", "--prompt",
        help="Path to prompt template file",
        default=None
    )
    parser.add_argument(
        "-o", "--output",
        help="Output markdown file path",
        default=None
    )
    parser.add_argument(
        "-k", "--api-key",
        help="Google API key (or set GOOGLE_API_KEY env var)",
        default=None
    )
    parser.add_argument(
        "-m", "--model",
        help="Gemini model to use (overrides settings.json)",
        default=None
    )
    parser.add_argument(
        "-c", "--context",
        help="Path to context directory",
        default=None
    )
    parser.add_argument(
        "-s", "--settings",
        help="Path to settings.json file",
        default="settings.json"
    )
    
    args = parser.parse_args()
    
    # Validate input files
    schema_path = Path(args.schema_file)
    if not schema_path.exists():
        print(f"Error: Schema file '{args.schema_file}' not found.")
        sys.exit(1)
    
    # This will be set after analyzer initialization, so we'll validate later
    
    # Set output file path
    if args.output:
        output_path = Path(args.output)
    else:
        # Will be set after analyzer initialization
        output_path = None
    
    # Initialize analyzer first to get settings
    analyzer = SchemaAnalyzer(api_key=args.api_key, model_name=args.model, settings_file=args.settings)
    
    # Use settings for defaults if not provided via command line
    prompt_file = args.prompt or f"{analyzer.settings['paths']['prompts_dir']}/{analyzer.settings['analysis']['default_prompt']}"
    context_dir = args.context or analyzer.settings['paths']['context_dir']
    
    # Set output path using settings if not provided
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(analyzer.settings['paths']['output_dir']) / f"schema_analysis_{timestamp}.md"
        # Ensure output directory exists
        output_path.parent.mkdir(exist_ok=True)
    
    print(f"Schema Analyzer Configuration:")
    print(f"  Schema file: {schema_path}")
    print(f"  Prompt template: {prompt_file}")
    print(f"  Output file: {output_path}")
    print(f"  Model: {analyzer.settings['model']['name']}")
    print(f"  Context dir: {context_dir}")
    print()
    
    # Load prompt template and schema
    prompt_template = analyzer.load_prompt_template(prompt_file)
    schema_content = analyzer.load_schema(args.schema_file)
    
    print(f"Loaded schema: {len(schema_content)} characters")
    print(f"Schema preview: {schema_content[:200]}...")
    print()
    
    # Load context data
    context_summary = analyzer.load_context_data(context_dir, args.schema_file)
    
    # Analyze schema
    analysis_result = analyzer.analyze_schema(schema_content, prompt_template, context_summary)
    
    # Save report
    analyzer.save_report(analysis_result, output_path, args.schema_file)
    
    print(f"\nAnalysis complete!")
    print(f"Report saved to: {output_path}")
    print(f"Report size: {len(analysis_result)} characters")


if __name__ == "__main__":
    main() 