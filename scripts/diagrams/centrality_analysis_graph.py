from .base_diagram import BaseDiagram
import plotly.graph_objects as go
import networkx as nx

class CentralityAnalysisGraph(BaseDiagram):
    def generate(self):
        """Generates a network diagram with node size based on table centrality."""
        relationships = self.context_data.get('relationships', [])
        if not relationships: return None

        G = nx.DiGraph()
        for rel in relationships:
            G.add_edge(rel['from_table'], rel['to_table'])

        if not G.nodes(): return None

        centrality = nx.degree_centrality(G)
        
        # Prepare node properties
        node_x, node_y, node_text, node_size, node_color = [], [], [], [], []
        for node in G.nodes():
            degree = G.degree(node)
            node_x.append(None) # We'll set positions later
            node_y.append(None)
            node_text.append(f"{node}<br>Centrality: {centrality.get(node, 0):.2f}<br>Connections: {degree}")
            node_size.append(15 + (centrality.get(node, 0) * 50))
            node_color.append(centrality.get(node, 0))

        pos = nx.spring_layout(G, k=0.8, iterations=50)
        for i, node in enumerate(G.nodes()):
            node_x[i], node_y[i] = pos[node]

        node_trace = go.Scatter(
            x=node_x, y=node_y, mode='markers+text', text=[n for n in G.nodes()],
            textposition="top center", hoverinfo='text', hovertext=node_text,
            marker=dict(
                showscale=True, colorscale='YlGnBu', size=node_size, color=node_color,
                colorbar=dict(thickness=15, title='Node Centrality'),
                line_width=2
            )
        )

        # Prepare edge properties
        edge_x, edge_y = [], []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=0.5, color='#888'), hoverinfo='none', mode='lines')

        fig = go.Figure(data=[edge_trace, node_trace], layout=go.Layout(
            title=self.title, showlegend=False, hovermode='closest',
            margin=dict(b=20,l=5,r=5,t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            template=self.template))
            
        return fig