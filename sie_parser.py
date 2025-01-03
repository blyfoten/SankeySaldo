import pandas as pd
from typing import Dict, List, Tuple
import io
import logging

class SIEParser:
    def __init__(self):
        self.accounts = {}
        self.transactions = []
        self.company_name = ""
        self.fiscal_year = ""
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def parse_sie_file(self, content: bytes) -> Tuple[pd.DataFrame, Dict]:
        """Parse SIE file content and return transactions and metadata."""
        try:
            lines = content.decode('cp437').split('\n')
            current_ver = None
            parsing_ver = False

            for line in lines:
                if not line.strip():
                    continue

                parts = line.strip().split(' ')
                identifier = parts[0]

                if identifier == "#FNAMN":
                    self.company_name = ' '.join(parts[1:]).strip('"')
                elif identifier == "#RAR":
                    self.fiscal_year = parts[2]
                elif identifier == "#KONTO":
                    account_num = parts[1]
                    account_name = ' '.join(parts[2:]).strip('"')
                    self.accounts[account_num] = account_name
                elif identifier == "#VER":
                    parsing_ver = True
                    current_ver = {
                        'series': parts[1],
                        'number': parts[2],
                        'date': parts[3],
                        'text': ' '.join(parts[4:]).strip('"') if len(parts) > 4 else ''
                    }
                elif parsing_ver and line.startswith('{'):
                    # Parse transaction row
                    trans_parts = line.strip('{}').split(' ')
                    if len(trans_parts) >= 3:
                        date = trans_parts[0]
                        account = trans_parts[1]
                        amount = float(trans_parts[2].replace(',', '.'))
                        description = ' '.join(trans_parts[3:]).strip('"') if len(trans_parts) > 3 else current_ver.get('text', '')

                        self.transactions.append({
                            'date': date,
                            'account': account,
                            'amount': amount,
                            'description': description,
                            'ver_series': current_ver['series'],
                            'ver_number': current_ver['number']
                        })
                elif parsing_ver and line.startswith('}'):
                    parsing_ver = False
                    current_ver = None

            # Convert transactions to DataFrame
            if self.transactions:
                df = pd.DataFrame(self.transactions)
                self.logger.info(f"Parsed {len(df)} transactions")
            else:
                df = pd.DataFrame(columns=['date', 'account', 'amount', 'description', 'ver_series', 'ver_number'])
                self.logger.warning("No transactions found in the file")

            metadata = {
                'company_name': self.company_name,
                'fiscal_year': self.fiscal_year,
                'accounts': self.accounts
            }

            return df, metadata
        except Exception as e:
            self.logger.error(f"Error parsing SIE file: {str(e)}")
            raise ValueError(f"Fel vid parsning av SIE-fil: {str(e)}")