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

    def _parse_line_parts(self, line: str) -> List[str]:
        """Parse a line into parts, preserving quoted content."""
        parts = []
        current = []
        in_quote = False
        skip_next = False

        for i, char in enumerate(line):
            if skip_next:
                skip_next = False
                continue

            if char == '"':
                if i > 0 and line[i-1] == '\\':  # Handle escaped quotes
                    current.append(char)
                else:
                    in_quote = not in_quote
            elif char.isspace() and not in_quote:
                if current:
                    parts.append(''.join(current))
                    current = []
            else:
                current.append(char)

        if current:
            parts.append(''.join(current))

        return [p.strip().strip('"') for p in parts if p.strip()]

    def _parse_transaction_line(self, line: str, current_ver: Dict) -> Dict:
        """Parse a single transaction line."""
        # Show raw line for debugging
        self.logger.info(f"Raw transaction line: {repr(line)}")

        # Remove braces and leading/trailing whitespace
        clean_line = line.strip().lstrip('{').rstrip('}').strip()
        self.logger.info(f"Cleaned line: {repr(clean_line)}")

        if not clean_line:
            raise ValueError("Empty transaction line")

        # Parse line parts
        parts = self._parse_line_parts(clean_line)
        self.logger.info(f"Parsed parts: {parts}")

        if len(parts) < 2:
            raise ValueError(f"Invalid transaction format, need at least 2 parts, got: {parts}")

        # Create transaction with required fields
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
            except ValueError:
                self.logger.warning(f"Invalid amount format: {parts[2]}")

        # Add description if present
        if len(parts) > 3:
            transaction['description'] = ' '.join(parts[3:])

        return transaction

    def parse_sie_file(self, content: bytes) -> Tuple[pd.DataFrame, Dict]:
        """Parse SIE file content and return transactions and metadata."""
        try:
            # Decode with cp437 encoding
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
                    parts = self._parse_line_parts(line)
                    current_ver = {
                        'series': parts[1] if len(parts) > 1 else '',
                        'number': parts[2] if len(parts) > 2 else '',
                        'date': parts[3] if len(parts) > 3 else '',
                        'text': ' '.join(parts[4:]) if len(parts) > 4 else ''
                    }
                    self.logger.info(f"Found verification: {current_ver}")
                    parsing_details.append(f"Found verification: {current_ver['series']}-{current_ver['number']}")

                # Handle transaction lines
                elif parsing_ver and '{' in line:
                    try:
                        transaction = self._parse_transaction_line(line, current_ver)
                        self.transactions.append(transaction)
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
                    parts = self._parse_line_parts(line)
                    identifier = parts[0]
                    line_types[identifier] = line_types.get(identifier, 0) + 1

                    if identifier == "#FNAMN":
                        self.company_name = ' '.join(parts[1:])
                    elif identifier == "#RAR":
                        self.fiscal_year = parts[1] if len(parts) > 1 else ''
                    elif identifier == "#KONTO":
                        if len(parts) >= 3:
                            account_num = parts[1]
                            account_name = ' '.join(parts[2:])
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