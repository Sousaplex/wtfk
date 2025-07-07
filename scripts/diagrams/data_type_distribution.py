from .base_diagram import BaseDiagram
import plotly.express as px
import pandas as pd

class DataTypeDistribution(BaseDiagram):
    def generate(self):
        """Generates a bar chart of column data type distribution."""
        stats = self.context_data.get('summary_stats', {})
        dist = stats.get('data_type_distribution', {})
        if not dist: return None

        df = pd.DataFrame(list(dist.items()), columns=['type', 'count']).sort_values('count', ascending=False)

        fig = px.bar(df, x='type', y='count', title=self.title, template=self.template)
        fig.update_layout(xaxis_title="Data Type", yaxis_title="Number of Columns")
        return fig
