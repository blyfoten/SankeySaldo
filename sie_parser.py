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

    def _parse_transaction_line(self, line: str, current_ver: Dict) -> Dict:
        """Parse a single transaction line."""
        # Remove { and } and split the line, preserving quoted content
        line = line.strip('{}').strip()
        parts = []
        current = []
        in_quote = False

        for char in line:
            if char == '"':
                in_quote = not in_quote
                if current:  # Add accumulated part when quote ends
                    parts.append(''.join(current))
                    current = []
            elif char.isspace() and not in_quote:
                if current:
                    parts.append(''.join(current))
                    current = []
            else:
                current.append(char)

        if current:
            parts.append(''.join(current))

        self.logger.info(f"Parsed transaction parts: {parts}")

        if len(parts) < 2:
            raise ValueError(f"Invalid transaction format, need at least 2 parts, got: {parts}")

        # Parse transaction components
        date = parts[0].strip('"')
        account = parts[1].strip('"')

        # Handle amount
        amount = 0.0
        if len(parts) >= 3:
            amount_str = parts[2].strip('"')
            # Handle both comma and period as decimal separator
            try:
                amount = float(amount_str.replace(',', '.'))
            except ValueError:
                self.logger.warning(f"Invalid amount format: {amount_str}")
                amount = 0.0

        # Get description
        description = ' '.join(parts[3:]).strip('"') if len(parts) > 3 else current_ver.get('text', '')

        return {
            'date': date,
            'account': account,
            'amount': amount,
            'description': description,
            'ver_series': current_ver.get('series', ''),
            'ver_number': current_ver.get('number', '')
        }

    def parse_sie_file(self, content: bytes) -> Tuple[pd.DataFrame, Dict]:
        """Parse SIE file content and return transactions and metadata."""
        try:
            # Try cp437 first as it's known to work
            decoded_content = content.decode('cp437')
            self.logger.info("Successfully decoded with cp437")

            lines = decoded_content.split('\n')
            self.logger.info(f"Found {len(lines)} lines")

            current_ver = None
            parsing_ver = False
            line_types = {}
            parsing_details = []

            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue

                self.logger.debug(f"Processing line {line_num}: {line}")

                # Handle verification start
                if line.startswith('#VER'):
                    parsing_ver = True
                    parts = [p.strip('"') for p in line.split(' ')]
                    current_ver = {
                        'series': parts[1] if len(parts) > 1 else '',
                        'number': parts[2] if len(parts) > 2 else '',
                        'date': parts[3] if len(parts) > 3 else '',
                        'text': ' '.join(parts[4:]).strip('"') if len(parts) > 4 else ''
                    }
                    self.logger.info(f"Started parsing verification: {current_ver}")
                    parsing_details.append(f"Found verification: {current_ver['series']}-{current_ver['number']}")

                # Handle transaction line
                elif parsing_ver and line.startswith('{'):
                    self.logger.info(f"Found transaction line: {line}")
                    try:
                        transaction = self._parse_transaction_line(line, current_ver)
                        self.transactions.append(transaction)
                        parsing_details.append(f"Added transaction: Account={transaction['account']}, Amount={transaction['amount']}")
                    except Exception as e:
                        self.logger.error(f"Error parsing transaction at line {line_num}: {str(e)}")
                        parsing_details.append(f"Error parsing transaction at line {line_num}: {str(e)}")

                # Handle verification end
                elif line.startswith('}'):
                    parsing_ver = False
                    current_ver = None

                # Handle metadata lines
                elif line.startswith('#'):
                    parts = line.split(' ')
                    identifier = parts[0]
                    line_types[identifier] = line_types.get(identifier, 0) + 1

                    if identifier == "#FNAMN":
                        self.company_name = ' '.join(parts[1:]).strip('"')
                        self.logger.info(f"Found company name: {self.company_name}")
                    elif identifier == "#RAR":
                        self.fiscal_year = parts[1] if len(parts) > 1 else ''
                        self.logger.info(f"Found fiscal year: {self.fiscal_year}")
                    elif identifier == "#KONTO":
                        if len(parts) >= 3:
                            account_num = parts[1]
                            account_name = ' '.join(parts[2:]).strip('"')
                            self.accounts[account_num] = account_name

            # Create DataFrame
            if self.transactions:
                df = pd.DataFrame(self.transactions)
                self.logger.info(f"Successfully parsed {len(df)} transactions")
            else:
                df = pd.DataFrame(columns=['date', 'account', 'amount', 'description', 'ver_series', 'ver_number'])
                self.logger.warning("No transactions found in the file")

            metadata = {
                'company_name': self.company_name,
                'fiscal_year': self.fiscal_year,
                'accounts': self.accounts,
                'file_content': line_types,
                'parsing_details': '\n'.join(parsing_details)
            }

            return df, metadata

        except Exception as e:
            self.logger.error(f"Error parsing SIE file: {str(e)}")
            raise ValueError(f"Error parsing SIE file: {str(e)}")