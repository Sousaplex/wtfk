from .base_diagram import BaseDiagram
import plotly.express as px
import pandas as pd

class RelationshipIntensityHeatmap(BaseDiagram):
    def generate(self):
        """Generates a heatmap of relationship intensity between table categories."""
        stats = self.context_data.get('summary_stats', {})
        categories = stats.get('table_categories', {})
        relationships = self.context_data.get('relationships', [])
        if not categories or not relationships: return None

        category_map = {table: cat for cat, tables in categories.items() for table in tables}
        
        matrix = pd.DataFrame(0, index=categories.keys(), columns=categories.keys())
        for rel in relationships:
            from_cat = category_map.get(rel['from_table'])
            to_cat = category_map.get(rel['to_table'])
            if from_cat and to_cat:
                matrix.loc[from_cat, to_cat] += 1
        
        fig = px.imshow(matrix, text_auto=True, title=self.title, template=self.template)
        return fig
