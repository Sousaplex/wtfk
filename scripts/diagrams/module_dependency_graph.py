from .base_diagram import BaseDiagram
import plotly.graph_objects as go
import networkx as nx

class ModuleDependencyGraph(BaseDiagram):
    def generate(self):
        """Generates a directed graph showing dependencies between application modules/apps."""
        relationships = self.context_data.get('relationships', [])
        if not relationships: return None

        module_deps = {}
        for rel in relationships:
            from_module = rel['from_table'].split('_')[0]
            to_module = rel['to_table'].split('_')[0]
            if from_module != to_module:
                if from_module not in module_deps:
                    module_deps[from_module] = {}
                module_deps[from_module][to_module] = module_deps[from_module].get(to_module, 0) + 1
        
        if not module_deps: return None

        G = nx.DiGraph()
        for from_module, deps in module_deps.items():
            for to_module, weight in deps.items():
                G.add_edge(from_module, to_module, weight=weight)

        pos = nx.spring_layout(G, k=0.8, iterations=50)

        edge_trace = go.Scatter(x=[], y=[], line=dict(width=0.5, color='#888'), hoverinfo='none', mode='lines')
        node_trace = go.Scatter(x=[], y=[], mode='markers+text', text=[], textposition="top center", hoverinfo='text', marker=dict(size=10, color='lightblue'))

        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_trace['x'] += tuple([x0, x1, None])
            edge_trace['y'] += tuple([y0, y1, None])

        for node in G.nodes():
            x, y = pos[node]
            node_trace['x'] += tuple([x])
            node_trace['y'] += tuple([y])
            node_trace['text'] += tuple([node])

        fig = go.Figure(data=[edge_trace, node_trace], layout=go.Layout(
            title=self.title, showlegend=False, hovermode='closest',
            margin=dict(b=20,l=5,r=5,t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            template=self.template))
            
        return fig
