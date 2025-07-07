from .base_diagram import BaseDiagram
import plotly.graph_objects as go
import networkx as nx

class ForeignKeyNetwork(BaseDiagram):
    def generate(self):
        """Generates an interactive foreign key network diagram."""
        relationships = self.context_data.get('relationships', [])
        if not relationships:
            print(f"Warning: No foreign key relationships found for '{self.title}'")
            return None

        G = nx.DiGraph()
        for rel in relationships:
            G.add_edge(rel['from_table'], rel['to_table'])

        if not G.nodes():
            return None

        pos = nx.spring_layout(G, k=0.5, iterations=50)
        
        edge_x, edge_y = [], []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=0.5, color='#888'), hoverinfo='none', mode='lines')

        node_x, node_y, node_text, node_size = [], [], [], []
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            degree = G.degree(node)
            node_text.append(f"{node}<br>Connections: {degree}")
            node_size.append(10 + (degree * 2))

        node_trace = go.Scatter(
            x=node_x, y=node_y, mode='markers+text', text=[n for n in G.nodes()], textposition="top center",
            hoverinfo='text', hovertext=node_text,
            marker=dict(
                showscale=True,
                colorscale='YlGnBu',
                size=node_size,
                colorbar=dict(
                    thickness=15,
                    title='Node Connections',
                    xanchor='left',
                    title_side='right' # Corrected property
                )
            )
        )
        
        fig = go.Figure(data=[edge_trace, node_trace],
                        layout=go.Layout(
                            title=dict(text=self.title, font=dict(size=16)),
                            showlegend=False,
                            hovermode='closest',
                            margin=dict(b=20,l=5,r=5,t=40),
                            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            template=self.template
                        ))
        return fig
