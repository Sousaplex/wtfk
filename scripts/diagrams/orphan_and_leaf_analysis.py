from .base_diagram import BaseDiagram
import plotly.graph_objects as go

class OrphanAndLeafAnalysis(BaseDiagram):
    def generate(self):
        """Generates a bar chart identifying orphan and leaf tables."""
        relationships = self.context_data.get('relationships', [])
        all_tables = set(self.context_data.get('tables', {}).keys())
        
        if not all_tables: return None

        referenced_tables = {rel['to_table'] for rel in relationships}
        referencing_tables = {rel['from_table'] for rel in relationships}

        orphan_tables = all_tables - referenced_tables - referencing_tables
        leaf_tables = referenced_tables - referencing_tables

        labels = ['Orphan Tables', 'Leaf Tables']
        values = [len(orphan_tables), len(leaf_tables)]

        fig = go.Figure(data=[go.Bar(x=labels, y=values, text=values, textposition='auto')])
        fig.update_layout(title_text=self.title, template=self.template)
        return fig
