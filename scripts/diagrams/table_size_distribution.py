from .base_diagram import BaseDiagram
import plotly.express as px
import pandas as pd

class TableSizeDistribution(BaseDiagram):
    def generate(self):
        """Generates a histogram of table sizes by column count."""
        stats = self.context_data.get('summary_stats', {})
        largest_tables = stats.get('largest_tables', [])
        if not largest_tables: return None

        df = pd.DataFrame(largest_tables, columns=['table', 'column_count'])
        
        fig = px.histogram(df, x='column_count', title=self.title, nbins=20, template=self.template)
        fig.update_layout(xaxis_title="Number of Columns", yaxis_title="Number of Tables")
        return fig
