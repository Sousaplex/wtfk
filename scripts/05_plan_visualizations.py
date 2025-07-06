#!/usr/bin/env python3
"""
PostgreSQL Schema Visualization Planner

This script analyzes a compressed database schema and intelligently selects
the most valuable visualizations for each analysis section. The LLM considers
schema characteristics, complexity, and available graph types to create an
optimal visualization plan.

Output: visualization_plan.json for use by 06_generate_diagrams.py
"""

import argparse
import sys
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


class VisualizationPlanner:
    def __init__(self, settings_file="settings.json"):
        """Initialize the visualization planner."""
        self.settings = self.load_settings(settings_file)
        self.llm = self._initialize_llm()
        
    def load_settings(self, settings_file):
        """Load settings from JSON file with fallback to defaults."""
        default_settings = {
            "model": {
                "name": "gemini-2.5-pro",
                "temperature": 0.2,  # Lower temperature for more focused planning
                "max_output_tokens": 4096
            },
            "paths": {
                "context_dir": "context",
                "diagrams_dir": "diagrams",
                "prompts_dir": "prompts"
            },
            "visualizations": {
                "enable_generation": True,
                "max_graphs_per_section": 2,
                "graph_library": {},
                "section_mappings": {}
            }
        }
        
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                user_settings = json.load(f)
            
            # Deep merge settings
            settings = self._deep_merge(default_settings, user_settings)
            print(f"Loaded visualization settings from: {settings_file}")
            return settings
            
        except FileNotFoundError:
            print(f"Settings file '{settings_file}' not found. Using defaults.")
            return default_settings
        except Exception as e:
            print(f"Error loading settings: {e}. Using defaults.")
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
    
    def _initialize_llm(self):
        """Initialize the LLM for planning."""
        load_dotenv()
        
        import os
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            print("Error: GOOGLE_API_KEY not found in environment variables.")
            print("Please set it in .env file or environment.")
            sys.exit(1)
        
        return ChatGoogleGenerativeAI(
            model=self.settings['model']['name'],
            google_api_key=api_key,
            temperature=self.settings['model']['temperature'],
            max_output_tokens=self.settings['model']['max_output_tokens']
        )
    
    def load_context_data(self, context_dir, schema_file):
        """Load context data and statistics."""
        context_path = Path(context_dir)
        base_name = Path(schema_file).stem
        
        # Load full context
        context_file = context_path / f"{base_name}_context.json"
        stats_file = context_path / f"{base_name}_stats.json"
        
        context_data = {}
        
        if context_file.exists():
            try:
                with open(context_file, 'r', encoding='utf-8') as f:
                    context_data = json.load(f)
                print(f"Loaded context data: {context_file}")
            except Exception as e:
                print(f"Warning: Could not load context file {context_file}: {e}")
        
        if stats_file.exists():
            try:
                with open(stats_file, 'r', encoding='utf-8') as f:
                    stats_data = json.load(f)
                context_data['summary_stats'] = stats_data
                print(f"Loaded statistics: {stats_file}")
            except Exception as e:
                print(f"Warning: Could not load stats file {stats_file}: {e}")
        
        return context_data
    
    def load_prompt_template(self, prompt_file):
        """Load the prompt template from file."""
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            return PromptTemplate(
                input_variables=[
                    "graph_library", "section_mappings", "statistics_summary", 
                    "table_count", "total_columns", "total_foreign_keys", 
                    "most_referenced", "table_categories", "max_graphs_per_section"
                ],
                template=template_content
            )
        except FileNotFoundError:
            print(f"Error: Prompt template file '{prompt_file}' not found.")
            sys.exit(1)
        except Exception as e:
            print(f"Error loading prompt template: {e}")
            sys.exit(1)

    def create_planning_prompt(self):
        """Create the prompt template for visualization planning."""
        
        # Load template from file
        prompt_file = f"{self.settings['paths'].get('prompts_dir', 'prompts')}/visualization_planning.txt"
        return self.load_prompt_template(prompt_file)
    
    def save_prompt_log(self, prompt_content, output_dir):
        """Save the actual prompt used for debugging."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = Path(output_dir) / f"visualization_prompt_log_{timestamp}.txt"
            
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("# Visualization Planning Prompt Log\n")
                f.write(f"# Generated: {datetime.now().isoformat()}\n\n")
                f.write(prompt_content)
            
            print(f"Prompt log saved to: {log_file}")
            return log_file
            
        except Exception as e:
            print(f"Warning: Could not save prompt log: {e}")
            return None
    
    def generate_plan(self, context_data, schema_file):
        """Generate the visualization plan using LLM."""
        
        # Extract key data for the prompt
        stats = context_data.get('summary_stats', {})
        
        # Format graph library
        graph_library_str = "\n".join([
            f"- **{name}**: {description}" 
            for name, description in self.settings['visualizations']['graph_library'].items()
        ])
        
        # Format section mappings
        section_mappings_str = "\n".join([
            f"- **{section}**: {', '.join(graphs)}"
            for section, graphs in self.settings['visualizations']['section_mappings'].items()
        ])
        
        # Format most referenced tables
        most_referenced = stats.get('most_referenced_tables', [])[:5]
        most_referenced_str = ", ".join([f"{table} ({count} FKs)" for table, count in most_referenced])
        
        # Format table categories  
        categories = stats.get('table_categories', {})
        categories_str = ", ".join([f"{cat}: {len(tables)}" for cat, tables in categories.items() if tables])
        
        # Create summary
        statistics_summary = f"""
- {stats.get('table_count', 0)} tables with {stats.get('total_columns', 0)} total columns
- {stats.get('total_foreign_keys', 0)} foreign key relationships
- Largest tables: {', '.join([f"{name} ({cols} cols)" for name, cols in stats.get('largest_tables', [])[:3]])}
- Most connected: {most_referenced_str}
- Categories: {categories_str}
        """.strip()
        
        # Create prompt variables
        prompt_vars = {
            "graph_library": graph_library_str,
            "section_mappings": section_mappings_str,
            "statistics_summary": statistics_summary,
            "table_count": stats.get('table_count', 0),
            "total_columns": stats.get('total_columns', 0),
            "total_foreign_keys": stats.get('total_foreign_keys', 0),
            "most_referenced": most_referenced_str,
            "table_categories": categories_str,
            "max_graphs_per_section": self.settings['visualizations']['max_graphs_per_section']
        }
        
        # Create and execute the planning chain
        prompt_template = self.create_planning_prompt()
        
        # Generate the actual prompt for logging
        actual_prompt = prompt_template.format(**prompt_vars)
        
        # Save prompt log for debugging
        output_dir = self.settings['paths'].get('output_dir', 'output')
        self.save_prompt_log(actual_prompt, output_dir)
        
        chain = prompt_template | self.llm | StrOutputParser()
        
        print("Analyzing schema characteristics...")
        print("Planning optimal visualizations for each section...")
        
        try:
            result = chain.invoke(prompt_vars)
            
            # Parse the JSON response
            plan = self._parse_plan_response(result)
            return plan
            
        except Exception as e:
            print(f"Error during planning: {e}")
            return self._create_fallback_plan()
    
    def _parse_plan_response(self, response):
        """Parse the LLM response into a structured plan."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response[json_start:json_end]
            plan = json.loads(json_str)
            
            # Validate structure
            if 'section_plans' not in plan:
                raise ValueError("Missing section_plans in response")
            
            # Add metadata if missing
            if 'metadata' not in plan:
                plan['metadata'] = {
                    "generated_at": datetime.now().isoformat(),
                    "schema_analysis": "Parsed from LLM response",
                    "total_graphs_planned": self._count_total_graphs(plan)
                }
            
            print(f"✅ Plan generated: {plan['metadata']['total_graphs_planned']} total visualizations planned")
            return plan
            
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            print("Creating fallback plan...")
            return self._create_fallback_plan()
    
    def _count_total_graphs(self, plan):
        """Count total graphs planned across all sections."""
        total = 0
        for section, graphs in plan.get('section_plans', {}).items():
            total += len(graphs) if isinstance(graphs, list) else 0
        return total
    
    def _create_fallback_plan(self):
        """Create a basic fallback plan if LLM planning fails."""
        return {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "schema_analysis": "Fallback plan due to LLM parsing error",
                "total_graphs_planned": 2
            },
            "section_plans": {
                "executive_summary": [
                    {
                        "graph_type": "table_category_breakdown",
                        "title": "Schema Architecture Overview",
                        "reasoning": "Fallback: Basic architecture overview",
                        "priority": 1,
                        "data_focus": "table_categories"
                    }
                ],
                "performance": [
                    {
                        "graph_type": "table_size_distribution", 
                        "title": "Table Complexity Distribution",
                        "reasoning": "Fallback: Shows relative table sizes",
                        "priority": 1,
                        "data_focus": "largest_tables"
                    }
                ],
                "domain_analysis": [],
                "security": [],
                "pii_audit": [],
                "technical_issues": [],
                "integration": []
            }
        }
    
    def save_plan(self, plan, output_file):
        """Save the visualization plan to JSON file."""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(plan, f, indent=2, ensure_ascii=False)
            
            print(f"Visualization plan saved to: {output_file}")
            
            # Display summary
            print(f"\n📊 Planning Summary:")
            print(f"Total visualizations planned: {plan['metadata']['total_graphs_planned']}")
            
            for section, graphs in plan['section_plans'].items():
                if graphs:
                    print(f"  {section}: {len(graphs)} graph(s)")
                    for graph in graphs:
                        print(f"    - {graph['graph_type']}: {graph['title']}")
            
        except Exception as e:
            print(f"Error saving plan: {e}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Plan optimal visualizations for database schema analysis"
    )
    parser.add_argument(
        "schema_file",
        help="Path to compressed schema file"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output plan file path",
        default="visualization_plan.json"
    )
    parser.add_argument(
        "-s", "--settings",
        help="Path to settings.json file",
        default="settings.json"
    )
    
    args = parser.parse_args()
    
    # Validate input file
    schema_path = Path(args.schema_file)
    if not schema_path.exists():
        print(f"Error: Schema file '{args.schema_file}' not found.")
        sys.exit(1)
    
    print(f"Visualization Planner Configuration:")
    print(f"  Schema file: {schema_path}")
    print(f"  Output plan: {args.output}")
    print(f"  Settings: {args.settings}")
    print()
    
    # Initialize planner
    planner = VisualizationPlanner(settings_file=args.settings)
    
    # Check if visualizations are enabled
    if not planner.settings['visualizations']['enable_generation']:
        print("Visualizations are disabled in settings. Exiting.")
        sys.exit(0)
    
    # Load context data
    context_data = planner.load_context_data(
        planner.settings['paths']['context_dir'], 
        args.schema_file
    )
    
    if not context_data:
        print("Error: No context data found. Please run 03_generate_context.py first.")
        sys.exit(1)
    
    # Generate visualization plan
    plan = planner.generate_plan(context_data, args.schema_file)
    
    # Save plan
    planner.save_plan(plan, args.output)
    
    print(f"\n✅ Visualization planning complete!")
    print(f"Next step: python3 scripts/06_generate_diagrams.py --plan {args.output}")


if __name__ == "__main__":
    main() 