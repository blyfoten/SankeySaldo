import pandas as pd
from typing import Dict, List, Tuple
import io

class SIEParser:
    def __init__(self):
        self.accounts = {}
        self.transactions = []
        self.company_name = ""
        self.fiscal_year = ""

    def parse_sie_file(self, content: bytes) -> Tuple[pd.DataFrame, Dict]:
        """Parse SIE file content and return transactions and metadata."""
        try:
            lines = content.decode('cp437').split('\n')
            for line in lines:
                if not line.strip():
                    continue
                
                parts = line.strip().split(' ')
                identifier = parts[0]

                if identifier == "#FNAMN":
                    self.company_name = ' '.join(parts[1:])
                elif identifier == "#RAR":
                    self.fiscal_year = parts[2]
                elif identifier == "#KONTO":
                    account_num = parts[1]
                    account_name = ' '.join(parts[2:]).strip('"')
                    self.accounts[account_num] = account_name
                elif identifier == "#VER":
                    self._parse_transaction(lines)

            # Convert transactions to DataFrame
            df = pd.DataFrame(self.transactions)
            if not df.empty:
                df.columns = ['date', 'account', 'amount', 'description']

            metadata = {
                'company_name': self.company_name,
                'fiscal_year': self.fiscal_year,
                'accounts': self.accounts
            }

            return df, metadata
        except Exception as e:
            raise ValueError(f"Fel vid parsning av SIE-fil: {str(e)}")

    def _parse_transaction(self, lines: List[str]):
        """Parse transaction entries from SIE file."""
        for line in lines:
            if line.startswith('{'):
                parts = line.strip('{}').split(' ')
                if len(parts) >= 3:
                    date = parts[0]
                    account = parts[1]
                    amount = float(parts[2].replace(',', '.'))
                    description = ' '.join(parts[3:]) if len(parts) > 3 else ''
                    self.transactions.append([date, account, amount, description])
