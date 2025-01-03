import pandas as pd
import plotly.graph_objects as go
from typing import Dict, List

class SankeyGenerator:
    def __init__(self, df: pd.DataFrame, accounts: Dict[str, str]):
        self.df = df
        self.accounts = accounts

    def generate_sankey_data(self) -> go.Figure:
        """Generate Sankey diagram from transaction data."""
        # Group transactions by account and calculate net flow
        account_flows = self.df.groupby('account')['amount'].sum()

        # Create nodes list
        nodes = ["Ingående balans"]  # First node is always "Ingående balans"
        account_nodes = [f"{acc} - {self.accounts.get(acc, 'Okänt konto')}" 
                        for acc in account_flows.index]
        nodes.extend(account_nodes)

        # Create links data
        sources = []
        targets = []
        values = []
        colors = []

        # Process each account's flow
        for account in account_flows.index:
            amount = account_flows[account]
            account_name = f"{account} - {self.accounts.get(account, 'Okänt konto')}"
            account_idx = nodes.index(account_name)

            if amount > 0:
                # Positive flow: from "Ingående balans" to account
                sources.append(0)  # "Ingående balans" is always at index 0
                targets.append(account_idx)
                values.append(abs(float(amount)))
                colors.append('rgba(44, 160, 44, 0.5)')  # Green for positive
            else:
                # Negative flow: from account to "Ingående balans"
                sources.append(account_idx)
                targets.append(0)  # "Ingående balans" is always at index 0
                values.append(abs(float(amount)))
                colors.append('rgba(214, 39, 40, 0.5)')  # Red for negative

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
                source=sources,
                target=targets,
                value=values,
                color=colors
            )
        )])

        # Update layout
        fig.update_layout(
            title_text="Ekonomiska flöden",
            font_size=10,
            height=800
        )

        return fig