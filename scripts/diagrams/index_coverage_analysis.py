from .base_diagram import BaseDiagram
import plotly.graph_objects as go

class IndexCoverageAnalysis(BaseDiagram):
    def generate(self):
        """Generates a bar chart showing index coverage on foreign key columns."""
        relationships = self.context_data.get('relationships', [])
        tables = self.context_data.get('tables', {})
        if not relationships or not tables: return None

        indexed_fks = 0
        unindexed_fks = 0

        for rel in relationships:
            table_data = tables.get(rel['from_table'], {})
            fk_col = rel['from_column']
            is_indexed = False
            for index in table_data.get('indexes', []):
                # Check if the FK column is the first column in any index
                if index['columns'] and index['columns'][0] == fk_col:
                    is_indexed = True
                    break
            if is_indexed:
                indexed_fks += 1
            else:
                unindexed_fks += 1
        
        total_fks = indexed_fks + unindexed_fks
        if total_fks == 0: return None

        labels = ['Indexed FKs', 'Unindexed FKs']
        values = [indexed_fks, unindexed_fks]
        
        fig = go.Figure(data=[go.Bar(x=labels, y=values, text=values, textposition='auto')])
        fig.update_layout(title_text=self.title, template=self.template)
        return fig
