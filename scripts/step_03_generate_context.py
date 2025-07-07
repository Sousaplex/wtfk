#!/usr/bin/env python3
"""
PostgreSQL Schema Context Generator

This script analyzes a compressed database schema and generates deterministic 
statistics and metadata that can be used as context for LLM analysis.

LLMs are great at interpretation but poor at precise counting and analysis,
so this script pre-computes all the numerical and structural data.
"""

import argparse
import sys
import json
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime


class SchemaContextGenerator:
    def __init__(self, settings_file="settings.json"):
        self.tables = {}
        self.relationships = []
        self.statistics = {}
        self.settings = self.load_settings(settings_file)
    
    def load_settings(self, settings_file):
        """Load settings from JSON file with fallback to defaults."""
        default_settings = {
            "context_generation": {
                "max_displayed_items": 10,
                "enable_ai_categorization": True,
                "fallback_categorization": {
                    "auth_security": ["auth", "user", "permission", "role", "token", "session"],
                    "audit_logging": ["log", "audit", "change", "history", "event"],
                    "configuration": ["config", "setting", "param", "lookup", "type", "status", "category"],
                    "integration": ["api", "webhook", "external", "import", "export", "sync"],
                    "temporary_cache": ["temp", "cache", "queue", "pending"]
                }
            }
        }
        
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                user_settings = json.load(f)
            
            # Deep merge user settings with defaults
            if 'context_generation' in user_settings:
                for key, value in user_settings['context_generation'].items():
                    default_settings['context_generation'][key] = value
            
            print(f"Loaded context settings from: {settings_file}")
            return default_settings
            
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
        
    def parse_compressed_schema(self, schema_content):
        """Parse the compressed schema format and extract metadata."""
        
        lines = schema_content.strip().split('\n')
        current_table = None
        
        for i, line in enumerate(lines):
            try:
                original_line = line
                line = line.strip()
                
                if not line or line.startswith('--'):
                    continue
                
                if line.endswith(':') and not original_line.startswith(' '):
                    current_table = line[:-1]
                    self.tables[current_table] = {
                        'columns': [], 'primary_keys': [], 'foreign_keys': [],
                        'unique_constraints': [], 'indexes': [], 'column_types': Counter(),
                        'nullable_columns': 0, 'required_columns': 0
                    }
                    continue
                
                if current_table is None:
                    continue
                
                if (original_line.startswith('  ') and ':' in line and 
                    not any(line.startswith(p) for p in ['FK (', 'UNIQUE (', 'IDX (', 'PRIMARY KEY ('])):
                    self._parse_column(line, current_table)
                elif original_line.startswith('  FK ('):
                    self._parse_foreign_key(line, current_table)
                elif original_line.startswith('  UNIQUE ('):
                    self._parse_unique_constraint(line, current_table)
                elif original_line.startswith('  PRIMARY KEY ('):
                    self._parse_primary_key(line, current_table)
                elif original_line.startswith('  IDX ('):
                    self._parse_index(line, current_table)
            except Exception as e:
                print(f"Error parsing line {i+1}: '{original_line.strip()}'")
                print(f"  - Error: {e}")
                print(f"  - Current table context: {current_table}")
                # Continue to the next line to make it robust
                continue
    
    def _parse_column(self, line, table_name):
        """Parse a column definition."""
        # Format: "  column_name: type [NOT NULL] [DEFAULT value]"
        line = line.strip()
        
        if ': PK' in line:
            # Auto-incrementing primary key
            col_name = line.split(':')[0].strip().strip('"')  # Remove quotes if present
            self.tables[table_name]['columns'].append(col_name)
            self.tables[table_name]['primary_keys'].append(col_name)
            self.tables[table_name]['column_types']['integer'] += 1
            self.tables[table_name]['required_columns'] += 1
        else:
            # Regular column
            parts = line.split(':', 1)  # Split only on first colon
            if len(parts) >= 2:
                col_name = parts[0].strip().strip('"')  # Remove quotes if present
                col_def = parts[1].strip()
                
                self.tables[table_name]['columns'].append(col_name)
                
                # Extract data type (first word)
                if col_def:
                    data_type = col_def.split()[0].lower()
                    self.tables[table_name]['column_types'][data_type] += 1
                    
                    # Check if nullable
                    if 'NOT NULL' in col_def.upper():
                        self.tables[table_name]['required_columns'] += 1
                    else:
                        self.tables[table_name]['nullable_columns'] += 1
    
    def _parse_foreign_key(self, line, table_name):
        """Parse a foreign key relationship."""
        # Format: "  FK (local_col) > ref_table(ref_col) [DEFERRABLE]"
        import re
        
        match = re.search(r'FK \(([^)]+)\) > (\w+)\(([^)]+)\)', line)
        if match:
            local_col = match.group(1).strip()
            ref_table = match.group(2).strip()
            ref_col = match.group(3).strip()
            
            fk_info = {
                'from_table': table_name,
                'from_column': local_col,
                'to_table': ref_table,
                'to_column': ref_col,
                'deferrable': 'DEFERRABLE' in line.upper()
            }
            
            self.tables[table_name]['foreign_keys'].append(fk_info)
            self.relationships.append(fk_info)
    
    def _parse_unique_constraint(self, line, table_name):
        """Parse a unique constraint."""
        # Format: "  UNIQUE (col1, col2, ...)"
        import re
        
        match = re.search(r'UNIQUE \(([^)]+)\)', line)
        if match:
            columns = [col.strip() for col in match.group(1).split(',')]
            self.tables[table_name]['unique_constraints'].append(columns)
    
    def _parse_primary_key(self, line, table_name):
        """Parse a primary key constraint."""
        # Format: "  PRIMARY KEY (col1, col2, ...)"
        import re
        
        match = re.search(r'PRIMARY KEY \(([^)]+)\)', line)
        if match:
            columns = [col.strip() for col in match.group(1).split(',')]
            self.tables[table_name]['primary_keys'].extend(columns)
    
    def _parse_index(self, line, table_name):
        """Parse an index definition."""
        # Format: "  IDX (col1, col2, ...) [UNIQUE] [(LIKE)]"
        import re
        
        match = re.search(r'IDX \(([^)]+)\)', line)
        if match:
            columns = [col.strip() for col in match.group(1).split(',')]
            index_info = {
                'columns': columns,
                'unique': 'UNIQUE' in line.upper(),
                'like_ops': '(LIKE)' in line.upper()
            }
            self.tables[table_name]['indexes'].append(index_info)
    
    def generate_statistics(self):
        """Generate comprehensive statistics from the parsed schema."""
        
        # Basic counts
        self.statistics['table_count'] = len(self.tables)
        self.statistics['total_columns'] = sum(len(table['columns']) for table in self.tables.values())
        self.statistics['total_foreign_keys'] = len(self.relationships)
        
        # Column statistics
        self.statistics['total_required_columns'] = sum(table['required_columns'] for table in self.tables.values())
        self.statistics['total_nullable_columns'] = sum(table['nullable_columns'] for table in self.tables.values())
        
        # Data type distribution
        all_types = Counter()
        for table in self.tables.values():
            all_types.update(table['column_types'])
        self.statistics['data_type_distribution'] = dict(all_types.most_common())
        
        # Table size analysis
        table_sizes = [(name, len(table['columns'])) for name, table in self.tables.items()]
        table_sizes.sort(key=lambda x: x[1], reverse=True)
        
        max_items = self.settings['context_generation']['max_displayed_items']
        self.statistics['largest_tables'] = table_sizes[:max_items]
        self.statistics['smallest_tables'] = table_sizes[-max_items:] if len(table_sizes) > max_items else []
        
        # Foreign key analysis
        fk_counts = defaultdict(int)
        incoming_fk_counts = defaultdict(int)
        
        for fk in self.relationships:
            fk_counts[fk['from_table']] += 1
            incoming_fk_counts[fk['to_table']] += 1
        
        # Tables with most outgoing FKs
        most_connected_out = sorted(fk_counts.items(), key=lambda x: x[1], reverse=True)
        self.statistics['most_outgoing_fks'] = most_connected_out[:max_items]
        
        # Tables with most incoming FKs (most referenced)
        most_referenced = sorted(incoming_fk_counts.items(), key=lambda x: x[1], reverse=True)
        self.statistics['most_referenced_tables'] = most_referenced[:max_items]
        
        # Tables with no FKs (potential root entities)
        tables_without_fks = [name for name in self.tables.keys() if fk_counts[name] == 0]
        self.statistics['tables_without_outgoing_fks'] = tables_without_fks
        
        # Tables never referenced (potential leaf entities)
        never_referenced = [name for name in self.tables.keys() if incoming_fk_counts[name] == 0]
        self.statistics['never_referenced_tables'] = never_referenced
        
        # Constraint analysis
        total_unique_constraints = sum(len(table['unique_constraints']) for table in self.tables.values())
        total_indexes = sum(len(table['indexes']) for table in self.tables.values())
        
        self.statistics['total_unique_constraints'] = total_unique_constraints
        self.statistics['total_indexes'] = total_indexes
        
        # Primary key analysis
        tables_with_composite_pk = []
        tables_without_pk = []
        
        for name, table in self.tables.items():
            if len(table['primary_keys']) > 1:
                tables_with_composite_pk.append(name)
            elif len(table['primary_keys']) == 0:
                tables_without_pk.append(name)
        
        self.statistics['tables_with_composite_pk'] = tables_with_composite_pk
        self.statistics['tables_without_pk'] = tables_without_pk
        
        # Relationship patterns
        self.statistics['self_referencing_tables'] = []
        table_connections = defaultdict(set)
        
        for fk in self.relationships:
            if fk['from_table'] == fk['to_table']:
                self.statistics['self_referencing_tables'].append(fk['from_table'])
            table_connections[fk['from_table']].add(fk['to_table'])
        
        # Calculate average columns per table
        if self.statistics['table_count'] > 0:
            self.statistics['avg_columns_per_table'] = round(
                self.statistics['total_columns'] / self.statistics['table_count'], 2
            )
            self.statistics['avg_fks_per_table'] = round(
                self.statistics['total_foreign_keys'] / self.statistics['table_count'], 2
            )
        
        # Domain analysis based on table name patterns
        self.statistics['table_categories'] = self._categorize_tables()
    
    def _categorize_tables(self):
        """Categorize tables using AI-based analysis or fallback to generic patterns."""
        
        # Check if AI categorization is enabled
        if self.settings['context_generation'].get('enable_ai_categorization', False):
            return self._ai_categorize_tables()
        else:
            return self._fallback_categorize_tables()
    
    def _ai_categorize_tables(self):
        """Use AI to intelligently categorize tables in parallel batches."""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain.prompts import PromptTemplate
            from langchain.output_parsers import PydanticOutputParser
            from pydantic import BaseModel, Field
            import os
            from dotenv import load_dotenv
            from concurrent.futures import ThreadPoolExecutor, as_completed
            from tqdm import tqdm
            import threading
            from typing import List

            load_dotenv()
            api_key = os.getenv('GOOGLE_API_KEY')
            
            if not api_key:
                print("Warning: No Google API key found. Using fallback categorization.")
                return self._fallback_categorize_tables()

            # Pydantic model for a single table's categorization
            class TableCategory(BaseModel):
                table_name: str = Field(description="The name of the table being categorized.")
                category: str = Field(description="The single best functional category for the table.")

            # Pydantic model for the LLM's response, which is a list of categorizations
            class CategorizationList(BaseModel):
                categorizations: List[TableCategory] = Field(description="A list of table categorizations.")

            parser = PydanticOutputParser(pydantic_object=CategorizationList)
            llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", google_api_key=api_key, temperature=0.1)
            
            prompt_file = self.settings['context_generation']['table_categorization_prompt']
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_template_str = f.read()

            prompt = PromptTemplate(
                template=prompt_template_str,
                input_variables=["batch_info"],
                partial_variables={"format_instructions": parser.get_format_instructions()}
            )
            
            chain = prompt | llm

            print("🤖 Using AI to categorize tables in parallel batches...")
            
            log_path = Path("logs") / f"table_categorization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            log_lock = threading.Lock()
            categorized_tables = defaultdict(list)
            
            # Create batches of 5 tables
            table_items = list(self.tables.items())
            batch_size = 5
            batches = [table_items[i:i + batch_size] for i in range(0, len(table_items), batch_size)]

            def categorize_batch(batch):
                batch_info_str = ""
                for name, table in batch:
                    all_columns = ", ".join(table['columns'])
                    batch_info_str += f"Table Name: {name}\nColumns: {all_columns}\n\n"
                
                raw_response = ""
                error_message = ""
                parsed_results = []

                try:
                    response_obj = chain.invoke({"batch_info": batch_info_str})
                    raw_response = response_obj.content if hasattr(response_obj, 'content') else str(response_obj)
                    parsed_obj = parser.parse(raw_response)
                    parsed_results = parsed_obj.categorizations
                except Exception as e:
                    error_message = str(e)
                
                log_entry = (
                    f"--- Batch ---\n"
                    f"Tables Sent:\n{batch_info_str}"
                    f"LLM Raw Response:\n{raw_response}\n"
                    f"Status: {'SUCCESS' if not error_message else 'FAIL'}\n"
                    f"Error: {error_message if error_message else 'None'}\n"
                    f"---------------------------------\n\n"
                )
                return parsed_results, log_entry

            max_workers = self.settings.get("performance", {}).get("max_workers_categorization", 10)
            with open(log_path, 'w', encoding='utf-8') as log_file:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {executor.submit(categorize_batch, batch): batch for batch in batches}
                    
                    for future in tqdm(as_completed(futures), total=len(batches), desc="Categorizing Batches"):
                        results, log_entry = future.result()
                        with log_lock:
                            log_file.write(log_entry)
                        
                        if results:
                            for item in results:
                                categorized_tables[item.category].append(item.table_name)
                        else:
                            # Fallback for a failed batch
                            batch = futures[future]
                            for name, _ in batch:
                                categorized_tables['business_core'].append(name)


            print(f"✅ AI categorization complete. See full log at: {log_path}")
            
            return dict(categorized_tables)

        except Exception as e:
            print(f"Warning: AI categorization failed entirely: {e}")
            print("Using fallback categorization for all tables.")
            return self._fallback_categorize_tables()
    
    def _fallback_categorize_tables(self):
        """Fallback categorization using generic keyword patterns."""
        # Get fallback category keywords from settings
        category_keywords = self.settings['context_generation']['fallback_categorization']
        
        # Initialize categories
        categories = {category: [] for category in category_keywords.keys()}
        categories['business_core'] = []  # Always have business_core as fallback
        
        for table_name in self.tables.keys():
            name_lower = table_name.lower()
            categorized = False
            
            # Check each category against its keywords
            for category, keywords in category_keywords.items():
                if any(keyword in name_lower for keyword in keywords):
                    categories[category].append(table_name)
                    categorized = True
                    break
            
            # If not categorized, put in business_core
            if not categorized:
                categories['business_core'].append(table_name)
        
        return categories
    
    def save_context(self, output_dir, schema_file_name):
        """Save all context data to JSON files."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Generate base name from schema file
        base_name = Path(schema_file_name).stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        context_data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'source_schema': str(schema_file_name),
                'generator_version': '1.0.0'
            },
            'statistics': self.statistics,
            'tables': self.tables,
            'relationships': self.relationships
        }
        
        # Save main context file
        context_file = output_path / f"{base_name}_context.json"
        with open(context_file, 'w', encoding='utf-8') as f:
            json.dump(context_data, f, indent=2, ensure_ascii=False)
        
        # Save statistics summary (for easy prompt injection)
        stats_file = output_path / f"{base_name}_stats.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.statistics, f, indent=2, ensure_ascii=False)
        
        return context_file, stats_file
    
    def generate_summary_text(self):
        """Generate a human-readable summary for prompt injection."""
        summary = []
        max_items = self.settings['context_generation']['max_displayed_items']
        
        # For summary, use half the max_items for a more concise display
        summary_limit = max(3, max_items // 2)
        
        summary.append("## Schema Statistics Summary")
        summary.append(f"- **Total Tables**: {self.statistics['table_count']}")
        summary.append(f"- **Total Columns**: {self.statistics['total_columns']}")
        summary.append(f"- **Total Foreign Key Relationships**: {self.statistics['total_foreign_keys']}")
        summary.append(f"- **Average Columns per Table**: {self.statistics.get('avg_columns_per_table', 0)}")
        summary.append(f"- **Average Foreign Keys per Table**: {self.statistics.get('avg_fks_per_table', 0)}")
        summary.append("")
        
        summary.append("## Table Size Distribution")
        if self.statistics['largest_tables']:
            summary.append("**Largest Tables (by column count):**")
            for table, count in self.statistics['largest_tables'][:summary_limit]:
                summary.append(f"- {table}: {count} columns")
        summary.append("")
        
        summary.append("## Most Connected Tables")
        if self.statistics['most_referenced_tables']:
            summary.append("**Most Referenced Tables (incoming FKs):**")
            for table, count in self.statistics['most_referenced_tables'][:summary_limit]:
                summary.append(f"- {table}: {count} incoming foreign keys")
        summary.append("")
        
        summary.append("## Data Type Distribution")
        for data_type, count in list(self.statistics['data_type_distribution'].items())[:max_items]:
            summary.append(f"- {data_type}: {count} columns")
        summary.append("")
        
        summary.append("## Table Categories")
        for category, tables in self.statistics['table_categories'].items():
            if tables:
                summary.append(f"- **{category.replace('_', ' ').title()}**: {len(tables)} tables")
        
        return '\n'.join(summary)


def generate_context(schema_file, output_dir, settings_file="settings.json", verbose=False):
    """
    Generates context and statistics from a compressed schema file.
    Returns (True, context_file, stats_file) on success, (False, None, None) on failure.
    """
    schema_path = Path(schema_file)
    if not schema_path.exists():
        print(f"Error: Schema file '{schema_file}' not found.")
        return False, None, None

    print(f"Generating context from: {schema_path}")
    print(f"Output directory: {output_dir}")
    print()

    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_content = f.read()
    except Exception as e:
        print(f"Error reading schema file: {e}")
        return False, None, None

    generator = SchemaContextGenerator(settings_file=settings_file)
    generator.parse_compressed_schema(schema_content)
    generator.generate_statistics()

    context_file, stats_file = generator.save_context(output_dir, schema_file)

    print(f"Context generated successfully!")
    print(f"- Main context: {context_file}")
    print(f"- Statistics: {stats_file}")
    print()

    if verbose:
        print("=== SCHEMA STATISTICS ===")
        print(generator.generate_summary_text())
        print()
    else:
        stats = generator.statistics
        print(f"Summary: {stats['table_count']} tables, {stats['total_columns']} columns, {stats['total_foreign_keys']} relationships")

    print("Context files ready for AI analysis!")
    return True, context_file, stats_file


def main():
    parser = argparse.ArgumentParser(
        description="Generate context and statistics from compressed PostgreSQL schema"
    )
    parser.add_argument(
        "schema_file",
        help="Path to compressed schema file"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output directory for context files",
        default="context"
    )
    parser.add_argument(
        "-v", "--verbose",
        help="Print detailed statistics",
        action="store_true"
    )
    parser.add_argument(
        "-s", "--settings",
        help="Path to settings.json file",
        default="settings.json"
    )
    
    args = parser.parse_args()
    
    success, _, _ = generate_context(args.schema_file, args.output, args.settings, args.verbose)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main() 