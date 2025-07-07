from .base_diagram import BaseDiagram
import plotly.express as px
import pandas as pd
from collections import Counter

class DenormalizationHeatmap(BaseDiagram):
    def generate(self):
        """Generates a heatmap showing potentially denormalized (duplicated) columns."""
        tables = self.context_data.get('tables', {})
        if not tables: return None

        column_counts = Counter()
        for table_data in tables.values():
            column_counts.update(table_data['columns'])
            
        # Find columns that appear in more than one table
        duplicated_columns = {col: count for col, count in column_counts.items() if count > 1}
        
        if not duplicated_columns: return None
        
        # For simplicity, we'll just show the top 20 most duplicated columns
        top_duplicated = dict(sorted(duplicated_columns.items(), key=lambda item: item[1], reverse=True)[:20])

        matrix_data = []
        for col_name, count in top_duplicated.items():
            for table_name, table_data in tables.items():
                if col_name in table_data['columns']:
                    matrix_data.append({'column': col_name, 'table': table_name, 'present': 1})

        if not matrix_data: return None

        df = pd.DataFrame(matrix_data)
        pivot = df.pivot_table(index='column', columns='table', values='present', fill_value=0)

        fig = px.imshow(pivot, text_auto=False, title=self.title, aspect="auto", template=self.template)
        fig.update_layout(xaxis_title="Table", yaxis_title="Duplicated Column Name")
        return fig
