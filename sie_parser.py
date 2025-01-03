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
        # Remove leading { and trailing }, preserve internal spaces
        line = line.lstrip('{').rstrip('}').strip()
        self.logger.info(f"Processing transaction line: '{line}'")

        # Handle empty lines
        if not line:
            raise ValueError("Empty transaction line")

        # Split on whitespace while preserving quoted strings
        parts = []
        current = []
        in_quote = False
        last_char = None

        for char in line:
            if char == '"' and last_char != '\\':  # Handle escaped quotes
                if in_quote:
                    parts.append(''.join(current))
                    current = []
                in_quote = not in_quote
            elif char.isspace() and not in_quote:
                if current:
                    parts.append(''.join(current))
                    current = []
            else:
                current.append(char)
            last_char = char

        if current:
            parts.append(''.join(current))

        # Clean up parts
        parts = [p.strip().strip('"') for p in parts if p.strip()]
        self.logger.info(f"Parsed transaction parts: {parts}")

        if len(parts) < 2:
            raise ValueError(f"Invalid transaction format, need at least 2 parts, got: {parts}")

        # Parse transaction components
        transaction = {
            'date': parts[0],
            'account': parts[1],
            'amount': 0.0,  # Default value
            'description': current_ver.get('text', ''),  # Default to verification text
            'ver_series': current_ver.get('series', ''),
            'ver_number': current_ver.get('number', '')
        }

        # Parse amount if present
        if len(parts) >= 3:
            try:
                amount_str = parts[2].replace(',', '.')
                transaction['amount'] = float(amount_str)
            except ValueError:
                self.logger.warning(f"Invalid amount format: {parts[2]}")

        # Add description if present
        if len(parts) > 3:
            transaction['description'] = ' '.join(parts[3:])

        return transaction

    def parse_sie_file(self, content: bytes) -> Tuple[pd.DataFrame, Dict]:
        """Parse SIE file content and return transactions and metadata."""
        try:
            # Decode with cp437 as it's known to work for SIE files
            decoded_content = content.decode('cp437')
            self.logger.info("Successfully decoded with cp437")

            lines = decoded_content.split('\n')
            self.logger.info(f"Found {len(lines)} lines")

            current_ver = None
            parsing_ver = False
            line_types = {}
            parsing_details = []

            # Process each line
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue

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
                    try:
                        transaction = self._parse_transaction_line(line, current_ver)
                        self.transactions.append(transaction)
                        self.logger.info(f"Added transaction: {transaction}")
                        parsing_details.append(
                            f"Added transaction: Account={transaction['account']}, "
                            f"Amount={transaction['amount']}, Date={transaction['date']}"
                        )
                    except Exception as e:
                        self.logger.error(f"Error parsing transaction at line {line_num}: {str(e)}")
                        self.logger.error(f"Line content: {repr(line)}")
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
                    elif identifier == "#RAR":
                        self.fiscal_year = parts[1] if len(parts) > 1 else ''
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