#!/usr/bin/env python3
"""
PostgreSQL Schema Interactive Diagram Generator (Orchestrator)

This script reads a visualization plan and uses a registry of diagram
generators to create interactive HTML diagrams.
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# This will import the registry from the __init__.py file
from diagrams import DIAGRAM_REGISTRY

class InteractiveDiagramGenerator:
    def __init__(self, settings_file="settings.json"):
        self.settings = self.load_settings(settings_file)

    def load_settings(self, settings_file):
        try:
            with open(settings_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def load_context_data(self, context_dir, schema_file):
        """Load context data and statistics."""
        base_name = Path(schema_file).stem
        context_file = Path(context_dir) / f"{base_name}_context.json"
        stats_file = Path(context_dir) / f"{base_name}_stats.json"
        
        context_data = {}
        if context_file.exists():
            with open(context_file, 'r') as f:
                context_data = json.load(f)
        
        if stats_file.exists():
            with open(stats_file, 'r') as f:
                stats_data = json.load(f)
            # This is the critical fix:
            context_data['summary_stats'] = stats_data
        
        return context_data

    def save_diagram(self, figure, filename):
        if figure is None: return None
        
        diagrams_dir = Path(self.settings.get("paths", {}).get("diagrams_dir", "output/diagrams"))
        diagrams_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = diagrams_dir / f"{filename}.html"
        figure.write_html(file_path, full_html=False, include_plotlyjs='cdn')
        
        print(f"Saved interactive diagram: {file_path}")
        return file_path

    def generate_all_diagrams(self, plan_file, schema_file):
        try:
            with open(plan_file, 'r') as f:
                plan = json.load(f)
        except Exception as e:
            print(f"Error loading plan file: {e}")
            return {}

        context_data = self.load_context_data(self.settings.get("paths", {}).get("context_dir", "context"), schema_file)
        if not context_data:
            print("Error: No context data found.")
            return {}

        generated_files = defaultdict(list)
        total_graphs = 0

        for section, graphs in plan.get('section_plans', {}).items():
            for i, graph_info in enumerate(graphs):
                graph_type = graph_info['graph_type']
                title = graph_info['title']
                
                if graph_type in DIAGRAM_REGISTRY:
                    print(f"Generating {graph_type} for {section}: {title}")
                    DiagramClass = DIAGRAM_REGISTRY[graph_type]
                    diagram_instance = DiagramClass(context_data, title, self.settings)
                    figure = diagram_instance.generate()
                    
                    if figure:
                        filename = f"{section}_{graph_type}_{i+1:02d}"
                        file_path = self.save_diagram(figure, filename)
                        if file_path:
                            generated_files[section].append({
                                'file_path': str(file_path),
                                'title': title,
                                'graph_type': graph_type
                            })
                            total_graphs += 1
                else:
                    print(f"Warning: Diagram type '{graph_type}' not found in registry. Skipping.")
        
        print(f"\n✅ Generated {total_graphs} interactive diagrams successfully!")
        return dict(generated_files)

def generate_diagrams(plan_file, schema_file, settings_file="settings.json"):
    generator = InteractiveDiagramGenerator(settings_file=settings_file)
    generated_files = generator.generate_all_diagrams(plan_file, schema_file)
    
    if generated_files:
        report_path = Path(generator.settings.get("paths", {}).get("output_dir", "output")) / 'generation_report.json'
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_diagrams": sum(len(files) for files in generated_files.values()),
            "sections": generated_files
        }
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nGeneration report saved to: {report_path}")
    
    return generated_files

def main():
    parser = argparse.ArgumentParser(description="Generate interactive diagrams from a visualization plan.")
    parser.add_argument("--plan", required=True, help="Path to visualization plan JSON file")
    parser.add_argument("--schema", required=True, help="Path to compressed schema file")
    parser.add_argument("-s", "--settings", default="settings.json", help="Path to settings.json file")
    args = parser.parse_args()
    
    generate_diagrams(args.plan, args.schema, args.settings)

if __name__ == "__main__":
    main()
