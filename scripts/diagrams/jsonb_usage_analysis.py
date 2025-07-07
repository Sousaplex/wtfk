from .base_diagram import BaseDiagram
import plotly.express as px
import pandas as pd

class JsonbUsageAnalysis(BaseDiagram):
    def generate(self):
        """Generates a bar chart of tables using JSONB columns."""
        tables = self.context_data.get('tables', {})
        if not tables: return None

        jsonb_users = []
        for name, data in tables.items():
            if 'jsonb' in data.get('column_types', {}):
                jsonb_users.append({'table': name, 'count': data['column_types']['jsonb']})
        
        if not jsonb_users: return None

        df = pd.DataFrame(jsonb_users).sort_values('count', ascending=False).head(20)

        fig = px.bar(df, x='table', y='count', title=self.title, template=self.template)
        fig.update_layout(xaxis_title="Table", yaxis_title="Number of JSONB Columns")
        return fig
