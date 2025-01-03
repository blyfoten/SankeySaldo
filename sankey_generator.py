import pandas as pd
import plotly.graph_objects as go
from typing import Dict, List

class SankeyGenerator:
    def __init__(self, df: pd.DataFrame, accounts: Dict[str, str]):
        self.df = df
        self.accounts = accounts

    def generate_sankey_data(self) -> go.Figure:
        """Generate Sankey diagram from transaction data."""
        # Group transactions by account
        account_flows = self.df.groupby('account')['amount'].sum()

        # Separate positive and negative flows
        positive_flows = account_flows[account_flows > 0]
        negative_flows = account_flows[account_flows < 0]

        # Create nodes and links
        nodes = []
        links = {
            'source': [],
            'target': [],
            'value': [],
            'color': []
        }

        # Add source node (Start)
        nodes.append("Ingående balans")
        
        # Add account nodes
        for account, name in self.accounts.items():
            nodes.append(f"{account} - {name}")

        # Create links
        for account, amount in positive_flows.items():
            account_name = f"{account} - {self.accounts.get(account, 'Okänt konto')}"
            source_idx = nodes.index("Ingående balans")
            target_idx = nodes.index(account_name)
            
            links['source'].append(source_idx)
            links['target'].append(target_idx)
            links['value'].append(abs(float(amount)))
            links['color'].append('rgba(44, 160, 44, 0.5)')  # Green for positive

        for account, amount in negative_flows.items():
            account_name = f"{account} - {self.accounts.get(account, 'Okänt konto')}"
            source_idx = nodes.index(account_name)
            target_idx = nodes.index("Ingående balans")
            
            links['source'].append(source_idx)
            links['target'].append(target_idx)
            links['value'].append(abs(float(amount)))
            links['color'].append('rgba(214, 39, 40, 0.5)')  # Red for negative

        # Create Sankey diagram
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=nodes,
                color="lightblue"
            ),
            link=dict(
                source=links['source'],
                target=links['target'],
                value=links['value'],
                color=links['color']
            )
        )])

        fig.update_layout(
            title_text="Balansflöden",
            font_size=10,
            height=800
        )

        return fig
