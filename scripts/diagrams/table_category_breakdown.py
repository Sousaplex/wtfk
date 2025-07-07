from .base_diagram import BaseDiagram
import plotly.express as px
import pandas as pd

class TableCategoryBreakdown(BaseDiagram):
    def generate(self):
        """Generates an interactive pie chart of table categories."""
        stats = self.context_data.get('summary_stats', {})
        categories = stats.get('table_categories', {})
        if not categories:
            print(f"Warning: No table categories found for '{self.title}'")
            return None

        df = pd.DataFrame([{'category': cat, 'count': len(tables)} for cat, tables in categories.items() if tables])
        if df.empty:
            return None
            
        fig = px.pie(df, names='category', values='count', title=self.title, template=self.template)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        return fig
