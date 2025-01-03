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

    def _parse_trans_line(self, line: str, current_ver: Dict) -> Dict:
        """Parse a #TRANS line format."""
        # Format: #TRANS [account] {} [amount] [date] ["description"]
        parts = line.split(' ')

        if len(parts) < 5:  # Need at least #TRANS, account, {}, amount, date
            raise ValueError(f"Invalid #TRANS line format: {line}")

        # Get account number (index 1)
        account = parts[1]

        # Get amount (index 3)
        try:
            amount_str = parts[3].strip()
            amount = float(amount_str.replace(',', '.'))
        except (ValueError, IndexError) as e:
            self.logger.warning(f"Could not parse amount '{parts[3]}': {str(e)}")
            amount = 0.0

        # Get date (index 4)
        date = parts[4]

        # Get description (rest of the line)
        description = ' '.join(parts[5:]).strip('"') if len(parts) > 5 else current_ver.get('text', '')

        return {
            'date': date,
            'account': account,
            'amount': amount,
            'description': description,
            'ver_series': current_ver.get('series', ''),
            'ver_number': current_ver.get('number', '')
        }

    def _parse_regular_transaction(self, line: str, current_ver: Dict) -> Dict:
        """Parse a regular transaction line (starting with {)."""
        # Remove braces and leading/trailing whitespace
        clean_line = line.strip().lstrip('{').rstrip('}').strip()

        if not clean_line:
            raise ValueError("Empty transaction line")

        # Split parts while preserving quoted content
        parts = []
        current = []
        in_quote = False

        for char in clean_line:
            if char == '"':
                in_quote = not in_quote
            elif char.isspace() and not in_quote:
                if current:
                    parts.append(''.join(current))
                    current = []
            else:
                current.append(char)

        if current:
            parts.append(''.join(current))

        # Clean up parts
        parts = [p.strip().strip('"') for p in parts if p.strip()]

        if len(parts) < 2:
            raise ValueError(f"Invalid transaction format, need at least 2 parts, got: {parts}")

        transaction = {
            'date': parts[0],
            'account': parts[1],
            'amount': 0.0,
            'description': current_ver.get('text', ''),
            'ver_series': current_ver.get('series', ''),
            'ver_number': current_ver.get('number', '')
        }

        # Parse amount if present
        if len(parts) >= 3:
            try:
                amount_str = parts[2].replace(',', '.')
                transaction['amount'] = float(amount_str)
            except ValueError as e:
                self.logger.warning(f"Could not parse amount '{parts[2]}': {str(e)}")

        # Add description if present
        if len(parts) > 3:
            transaction['description'] = ' '.join(parts[3:])

        return transaction

    def parse_sie_file(self, content: bytes) -> Tuple[pd.DataFrame, Dict]:
        """Parse SIE file content and return transactions and metadata."""
        try:
            # Decode with cp437 encoding (standard for SIE files)
            decoded_content = content.decode('cp437')
            self.logger.info("Successfully decoded file with cp437")

            # Split into lines and process each line
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
                    parts = line.split(' ')
                    current_ver = {
                        'series': parts[1] if len(parts) > 1 else '',
                        'number': parts[2] if len(parts) > 2 else '',
                        'date': parts[3] if len(parts) > 3 else '',
                        'text': ' '.join(parts[4:]).strip('"') if len(parts) > 4 else ''
                    }
                    self.logger.info(f"Found verification: {current_ver}")
                    parsing_details.append(f"Found verification: {current_ver['series']}-{current_ver['number']}")

                # Handle #TRANS lines
                elif line.startswith('#TRANS'):
                    try:
                        transaction = self._parse_trans_line(line, current_ver)
                        self.transactions.append(transaction)
                        self.logger.info(f"Added #TRANS transaction: {transaction}")
                    except Exception as e:
                        self.logger.error(f"Error parsing #TRANS at line {line_num}: {str(e)}")
                        parsing_details.append(f"Error parsing #TRANS at line {line_num}: {str(e)}")

                # Handle regular transaction lines
                elif parsing_ver and line.startswith('{'):
                    try:
                        transaction = self._parse_regular_transaction(line, current_ver)
                        self.transactions.append(transaction)
                        self.logger.info(f"Added transaction: {transaction}")
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
                    elif identifier == "#RAR":
                        self.fiscal_year = parts[1] if len(parts) > 1 else ''
                    elif identifier == "#KONTO":
                        if len(parts) >= 3:
                            account_num = parts[1]
                            account_name = ' '.join(parts[2:]).strip('"')
                            self.accounts[account_num] = account_name

            # Create DataFrame from transactions
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