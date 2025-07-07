from .base_diagram import BaseDiagram
import plotly.express as px
import pandas as pd

class PiiSensitivityHeatmap(BaseDiagram):
    def generate(self):
        """Generates a heatmap of PII sensitivity."""
        # This is a placeholder implementation as true PII detection is complex.
        stats = self.context_data.get('summary_stats', {})
        categories = stats.get('table_categories', {})
        if not categories: return None

        pii_keywords = ['user', 'profile', 'address', 'email', 'phone', 'auth', 'session']
        
        data = []
        for cat, tables in categories.items():
            for table in tables:
                score = sum(1 for keyword in pii_keywords if keyword in table.lower())
                data.append({'table': table, 'category': cat, 'pii_score': score})
        
        if not data: return None

        df = pd.DataFrame(data)
        pivot = df.pivot_table(index='table', columns='category', values='pii_score', fill_value=0)
        
        fig = px.imshow(pivot, text_auto=True, title=self.title, template=self.template)
        return fig
