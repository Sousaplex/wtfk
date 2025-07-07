from .base_diagram import BaseDiagram
import plotly.express as px
import pandas as pd

class JunctionTableBreakdown(BaseDiagram):
    def generate(self):
        """Generates a bar chart of potential junction tables."""
        tables = self.context_data.get('tables', {})
        if not tables: return None

        junctions = []
        for name, data in tables.items():
            # Heuristic: tables with 2 foreign keys and a composite primary key of those 2 fks
            if len(data.get('foreign_keys', [])) == 2:
                fk_cols = {fk['from_column'] for fk in data['foreign_keys']}
                pk_cols = set(data.get('primary_keys', []))
                if fk_cols == pk_cols:
                    junctions.append(name)
        
        if not junctions: return None

        df = pd.DataFrame({'table': junctions, 'count': 1})

        fig = px.bar(df, x='table', y='count', title=self.title, template=self.template)
        fig.update_layout(xaxis_title="Junction Table", yaxis_title="Count")
        return fig
