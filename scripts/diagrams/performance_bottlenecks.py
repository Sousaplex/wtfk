from .base_diagram import BaseDiagram
import plotly.express as px
import pandas as pd
from collections import defaultdict

class PerformanceBottlenecks(BaseDiagram):
    def generate(self):
        """Generates a chart showing potential performance bottlenecks."""
        stats = self.context_data.get('summary_stats', {})
        largest_tables = stats.get('largest_tables', [])
        most_referenced = stats.get('most_referenced_tables', [])
        
        scores = defaultdict(float)
        for table, cols in largest_tables:
            scores[table] += cols * 0.1
        for table, refs in most_referenced:
            scores[table] += refs * 1.0

        if not scores: return None

        df = pd.DataFrame(list(scores.items()), columns=['table', 'risk_score']).sort_values('risk_score', ascending=False).head(15)
        
        fig = px.bar(df, x='risk_score', y='table', orientation='h', title=self.title, template=self.template)
        fig.update_layout(yaxis={'categoryorder':'total ascending'})
        return fig
