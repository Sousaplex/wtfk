#!/usr/bin/env python3
"""
PostgreSQL Schema Compressor

This script takes a PostgreSQL schema file and compresses it into a highly efficient
hierarchical format that significantly reduces token count while preserving all
essential structural information.

Format:
- Header: Default owner and schema
- Table blocks with shorthand notation:
  - id: PK (auto-incrementing primary key)
  - FK (column) > foreign_table(column)
  - UNIQUE (column)
  - IDX (column)
"""

import re
import argparse
import sys
from pathlib import Path
from collections import defaultdict, OrderedDict


class SchemaCompressor:
    def __init__(self, debug=False):
        self.tables = OrderedDict()
        self.sequences = {}
        self.default_owner = None
        self.default_schema = 'public'
        self.current_table = None
        self.debug = debug
        
    def parse_schema(self, lines):
        """Parse the SQL schema and extract table definitions."""
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Extract default owner
            if line.startswith('ALTER TABLE') and 'OWNER TO' in line:
                match = re.search(r'OWNER TO (\w+)', line)
                if match and not self.default_owner:
                    self.default_owner = match.group(1)
            
            # Parse CREATE TABLE statements
            if line.startswith('CREATE TABLE'):
                i = self._parse_create_table(lines, i)
            
            # Parse CREATE SEQUENCE statements
            elif line.startswith('CREATE SEQUENCE'):
                i = self._parse_create_sequence(lines, i)
            
            # Parse ALTER SEQUENCE OWNED BY statements
            elif 'SEQUENCE' in line and 'OWNED BY' in line:
                self._parse_sequence_owned_by(line)
            
            # Parse ALTER TABLE ADD CONSTRAINT statements (can be multi-line)
            elif line.startswith('ALTER TABLE') and 'ADD CONSTRAINT' in line:
                self._parse_alter_table_constraint(line)
            elif line.startswith('ALTER TABLE'):
                # Check if next line has ADD CONSTRAINT
                if i + 1 < len(lines) and 'ADD CONSTRAINT' in lines[i + 1]:
                    # Combine the lines
                    combined_line = line + ' ' + lines[i + 1].strip()
                    self._parse_alter_table_constraint(combined_line)
                    i += 1  # Skip the next line since we processed it
            
            # Parse CREATE INDEX statements
            elif line.startswith('CREATE') and 'INDEX' in line:
                self._parse_create_index(line)
            
            i += 1
        
        # Post-process to identify auto-incrementing primary keys
        self._identify_auto_pk_columns()
    
    def _parse_create_table(self, lines, start_idx):
        """Parse CREATE TABLE statement."""
        line = lines[start_idx].strip()
        
        # Extract table name
        match = re.search(r'CREATE TABLE (\w+\.)?(\w+)', line)
        if not match:
            return start_idx
        
        table_name = match.group(2)
        self.current_table = table_name
        
        if table_name not in self.tables:
            self.tables[table_name] = {
                'columns': OrderedDict(),
                'constraints': [],
                'indexes': []
            }
        
        # Parse column definitions
        i = start_idx + 1
        while i < len(lines):
            line = lines[i].strip()
            
            if line == ');' or line.startswith(');'):
                break
            
            if line and not line.startswith('--'):
                self._parse_column_definition(line, table_name)
            
            i += 1
        
        return i
    
    def _parse_column_definition(self, line, table_name):
        """Parse individual column definition."""
        line = line.rstrip(',')
        
        # Skip constraint definitions within CREATE TABLE
        if any(keyword in line.upper() for keyword in ['CONSTRAINT', 'PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE', 'CHECK']):
            return
        
        # Parse column: name type [NOT NULL] [DEFAULT value]
        parts = line.split()
        if len(parts) >= 2:
            col_name = parts[0]
            col_type = parts[1]
            
            # Simplify common types
            col_type = self._simplify_type(col_type)
            
            # Check for NOT NULL
            not_null = 'NOT NULL' in line.upper()
            
            # Check for DEFAULT
            default_value = None
            if 'DEFAULT' in line.upper():
                default_match = re.search(r'DEFAULT\s+([^,\s]+)', line.upper())
                if default_match:
                    default_value = default_match.group(1)
            
            self.tables[table_name]['columns'][col_name] = {
                'type': col_type,
                'not_null': not_null,
                'default': default_value
            }
    
    def _simplify_type(self, col_type):
        """Simplify PostgreSQL column types."""
        # Remove character varying lengths, etc.
        col_type = re.sub(r'character varying\(\d+\)', 'varchar', col_type)
        col_type = re.sub(r'character\(\d+\)', 'char', col_type)
        col_type = re.sub(r'timestamp with time zone', 'timestamptz', col_type)
        col_type = re.sub(r'timestamp without time zone', 'timestamp', col_type)
        return col_type
    
    def _parse_create_sequence(self, lines, start_idx):
        """Parse CREATE SEQUENCE statement."""
        line = lines[start_idx].strip()
        
        match = re.search(r'CREATE SEQUENCE (\w+\.)?(\w+)', line)
        if match:
            seq_name = match.group(2)
            self.sequences[seq_name] = {'owned_by': None}
        
        return start_idx
    
    def _parse_sequence_owned_by(self, line):
        """Parse ALTER SEQUENCE OWNED BY statement."""
        match = re.search(r'ALTER SEQUENCE (\w+\.)?(\w+) OWNED BY (\w+\.)?(\w+)\.(\w+)', line)
        if match:
            seq_name = match.group(2)
            table_name = match.group(4)
            col_name = match.group(5)
            
            if seq_name in self.sequences:
                self.sequences[seq_name]['owned_by'] = (table_name, col_name)
    
    def _parse_alter_table_constraint(self, line):
        """Parse ALTER TABLE ADD CONSTRAINT statement."""
        # Extract table name (handle qualified names like public.table_name)
        table_match = re.search(r'ALTER TABLE (?:ONLY )?(\w+\.)?(\w+)', line)
        if not table_match:
            if self.debug:
                print(f"No table match for: {line[:100]}...")
            return
        
        table_name = table_match.group(2)
        
        if table_name not in self.tables:
            if self.debug:
                print(f"Table {table_name} not found in tables. Available: {list(self.tables.keys())[:5]}...")
            return
        
        # Primary key constraint
        if 'PRIMARY KEY' in line.upper():
            pk_match = re.search(r'PRIMARY KEY \(([^)]+)\)', line)
            if pk_match:
                columns = [col.strip() for col in pk_match.group(1).split(',')]
                self.tables[table_name]['constraints'].append({
                    'type': 'PRIMARY KEY',
                    'columns': columns
                })
        
        # Foreign key constraint
        elif 'FOREIGN KEY' in line.upper():
            fk_match = re.search(r'FOREIGN KEY \(([^)]+)\) REFERENCES (\w+\.)?(\w+)\(([^)]+)\)', line)
            if fk_match:
                local_cols = [col.strip() for col in fk_match.group(1).split(',')]
                ref_table = fk_match.group(3)  # This gets the table name without schema prefix
                ref_cols = [col.strip() for col in fk_match.group(4).split(',')]
                
                deferrable = 'DEFERRABLE' in line.upper()
                
                constraint = {
                    'type': 'FOREIGN KEY',
                    'columns': local_cols,
                    'ref_table': ref_table,
                    'ref_columns': ref_cols,
                    'deferrable': deferrable
                }
                
                self.tables[table_name]['constraints'].append(constraint)
                
                if self.debug:
                    print(f"Added FK to {table_name}: {local_cols} -> {ref_table}({ref_cols})")
            else:
                if self.debug:
                    print(f"FK regex failed for: {line[:100]}...")
        
        # Unique constraint
        elif 'UNIQUE' in line.upper():
            unique_match = re.search(r'UNIQUE \(([^)]+)\)', line)
            if unique_match:
                columns = [col.strip() for col in unique_match.group(1).split(',')]
                self.tables[table_name]['constraints'].append({
                    'type': 'UNIQUE',
                    'columns': columns
                })
    
    def _parse_create_index(self, line):
        """Parse CREATE INDEX statement."""
        # Extract index info
        index_match = re.search(r'CREATE (?:UNIQUE )?INDEX (\w+) ON (\w+\.)?(\w+)', line)
        if not index_match:
            if self.debug:
                print(f"Index regex failed for: {line[:80]}...")
            return
        
        index_name = index_match.group(1)
        table_name = index_match.group(3)
        unique = 'UNIQUE' in line.upper()
        
        if self.debug:
            print(f"Processing index {index_name} on table {table_name}")
            print(f"Available tables: {list(self.tables.keys())[:5]}...")
        
        if table_name not in self.tables:
            if self.debug:
                print(f"Table {table_name} not found in tables!")
            return
        
        # Extract columns
        cols_match = re.search(r'USING \w+ \(([^)]+)\)', line)
        if cols_match:
            columns = [col.strip() for col in cols_match.group(1).split(',')]
            
            # Check for special operators like varchar_pattern_ops
            like_ops = any('_pattern_ops' in col for col in columns)
            if like_ops:
                columns = [re.sub(r'\s+varchar_pattern_ops|\s+text_pattern_ops', '', col) for col in columns]
            
            if self.debug:
                print(f"Added index {index_name} with columns {columns} (like_ops: {like_ops})")
            
            self.tables[table_name]['indexes'].append({
                'name': index_name,
                'columns': columns,
                'unique': unique,
                'like_ops': like_ops
            })
        else:
            if self.debug:
                print(f"Column extraction failed for index: {line[:80]}...")
    
    def _identify_auto_pk_columns(self):
        """Identify columns that are auto-incrementing primary keys."""
        for table_name, table_info in self.tables.items():
            # Find primary key constraints
            pk_constraints = [c for c in table_info['constraints'] if c['type'] == 'PRIMARY KEY']
            
            for pk_constraint in pk_constraints:
                if len(pk_constraint['columns']) == 1:
                    pk_col = pk_constraint['columns'][0]
                    
                    # Check if there's a sequence owned by this column
                    for seq_name, seq_info in self.sequences.items():
                        if (seq_info['owned_by'] and 
                            seq_info['owned_by'][0] == table_name and 
                            seq_info['owned_by'][1] == pk_col):
                            
                            # Mark this column as auto PK
                            if pk_col in table_info['columns']:
                                table_info['columns'][pk_col]['auto_pk'] = True
                            
                            # Remove the PK constraint since it's implied by "id: PK"
                            table_info['constraints'].remove(pk_constraint)
                            break
    
    def generate_compressed_schema(self):
        """Generate the compressed schema format."""
        
        output = []
        
        # Header
        header = f"-- Schema: {self.default_schema}"
        if self.default_owner:
            header += f", Owner: {self.default_owner}"
        output.append(header)
        output.append("")
        
        # Tables
        for table_name, table_info in self.tables.items():
            output.append(f"{table_name}:")
            
            # Columns
            for col_name, col_info in table_info['columns'].items():
                if col_info.get('auto_pk'):
                    output.append(f"  {col_name}: PK")
                else:
                    col_def = f"  {col_name}: {col_info['type']}"
                    if col_info['not_null']:
                        col_def += " NOT NULL"
                    if col_info['default']:
                        col_def += f" DEFAULT {col_info['default']}"
                    output.append(col_def)
            
            # Constraints
            for constraint in table_info['constraints']:
                if constraint['type'] == 'FOREIGN KEY':
                    for i, local_col in enumerate(constraint['columns']):
                        ref_col = constraint['ref_columns'][i] if i < len(constraint['ref_columns']) else constraint['ref_columns'][0]
                        fk_def = f"  FK ({local_col}) > {constraint['ref_table']}({ref_col})"
                        if constraint.get('deferrable'):
                            fk_def += " DEFERRABLE"
                        output.append(fk_def)
                
                elif constraint['type'] == 'UNIQUE':
                    cols = ', '.join(constraint['columns'])
                    output.append(f"  UNIQUE ({cols})")
                
                elif constraint['type'] == 'PRIMARY KEY':
                    cols = ', '.join(constraint['columns'])
                    output.append(f"  PRIMARY KEY ({cols})")
            
            # Indexes
            for index in table_info['indexes']:
                cols = ', '.join(index['columns'])
                idx_def = f"  IDX ({cols})"
                if index.get('like_ops'):
                    idx_def += " (LIKE)"
                if index.get('unique'):
                    idx_def += " UNIQUE"
                output.append(idx_def)
            
            output.append("")
        
        return '\n'.join(output)


def main():
    parser = argparse.ArgumentParser(
        description="Compress PostgreSQL schema into hierarchical format"
    )
    parser.add_argument(
        "input_file",
        help="Input schema SQL file path"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: input_file_compressed.txt)",
        default=None
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file '{args.input_file}' does not exist.")
        sys.exit(1)
    
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path("schemas") / "schema_compressed.txt"
        # Ensure schemas directory exists
        output_path.parent.mkdir(exist_ok=True)
    
    print(f"Reading schema from: {input_path}")
    print(f"Writing compressed schema to: {output_path}")
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading input file: {e}")
        sys.exit(1)
    
    # Parse and compress
    compressor = SchemaCompressor(debug=False)  # Set to True for debugging
    compressor.parse_schema(lines)
    compressed_schema = compressor.generate_compressed_schema()
    
    # Write output
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(compressed_schema)
        
        print(f"Compression complete!")
        print(f"Original file: {len(lines)} lines")
        print(f"Compressed file: {len(compressed_schema.splitlines())} lines")
        print(f"Compression ratio: {len(compressed_schema.splitlines()) / len(lines) * 100:.1f}%")
        
    except Exception as e:
        print(f"Error writing output file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 