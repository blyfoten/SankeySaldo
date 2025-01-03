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
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)

    def parse_sie_file(self, content: bytes) -> Tuple[pd.DataFrame, Dict]:
        """Parse SIE file content and return transactions and metadata."""
        try:
            # Try cp437 first as it's known to work
            try:
                decoded_content = content.decode('cp437')
                self.logger.info("Successfully decoded with cp437")
            except UnicodeDecodeError:
                # Fallback encodings
                for encoding in ['utf-8', 'iso-8859-1']:
                    try:
                        decoded_content = content.decode(encoding)
                        self.logger.info(f"Successfully decoded with {encoding}")
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raise ValueError("Could not decode file with any supported encoding")

            lines = decoded_content.split('\n')
            self.logger.debug(f"Found {len(lines)} lines")

            current_ver = None
            parsing_ver = False
            line_types = {}
            parsing_details = []

            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue

                self.logger.debug(f"Processing line {line_num}: {repr(line)}")

                # Handle verification start
                if line.startswith('#VER'):
                    parsing_ver = True
                    parts = [p.strip('"') for p in line.split(' ')]
                    current_ver = {
                        'series': parts[1] if len(parts) > 1 else '',
                        'number': parts[2] if len(parts) > 2 else '',
                        'date': parts[3] if len(parts) > 3 else '',
                        'text': ' '.join(parts[4:]) if len(parts) > 4 else ''
                    }
                    self.logger.info(f"Started parsing verification: {current_ver}")
                    parsing_details.append(f"Found verification: {current_ver['series']}-{current_ver['number']}")

                # Handle transaction line
                elif parsing_ver and line.startswith('{'):
                    self.logger.debug(f"Found transaction line: {repr(line)}")
                    try:
                        # Remove { and } and split the line
                        trans_line = line.strip('{}').strip()

                        # Split parts while preserving quoted strings
                        parts = []
                        current = []
                        in_quote = False

                        for char in trans_line:
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

                        self.logger.debug(f"Transaction parts: {parts}")

                        if len(parts) >= 2:  # At least date and account required
                            date = parts[0].strip('"')
                            account = parts[1].strip('"')

                            # Parse amount if present
                            amount = 0.0
                            if len(parts) >= 3:
                                amount_str = parts[2].strip('"')
                                # Handle both comma and period as decimal separator
                                amount = float(amount_str.replace(',', '.'))

                            # Get description
                            description = ' '.join(parts[3:]).strip('"') if len(parts) > 3 else current_ver['text']

                            transaction = {
                                'date': date,
                                'account': account,
                                'amount': amount,
                                'description': description,
                                'ver_series': current_ver['series'],
                                'ver_number': current_ver['number']
                            }

                            self.transactions.append(transaction)
                            self.logger.info(f"Added transaction: {transaction}")
                            parsing_details.append(f"Added transaction: Account={account}, Amount={amount}")
                    except Exception as e:
                        self.logger.error(f"Error parsing transaction at line {line_num}: {str(e)}")
                        self.logger.error(f"Line content: {repr(line)}")
                        parsing_details.append(f"Error parsing transaction at line {line_num}: {str(e)}")

                # Handle verification end
                elif parsing_ver and line.startswith('}'):
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
                        parsing_details.append(f"Found company: {self.company_name}")
                    elif identifier == "#RAR":
                        try:
                            self.fiscal_year = parts[2] if len(parts) > 2 else parts[1]
                            self.logger.info(f"Found fiscal year: {self.fiscal_year}")
                            parsing_details.append(f"Found fiscal year: {self.fiscal_year}")
                        except IndexError:
                            self.logger.warning(f"Invalid #RAR line: {parts}")
                    elif identifier == "#KONTO":
                        if len(parts) >= 2:
                            account_num = parts[1]
                            account_name = ' '.join(parts[2:]).strip('"')
                            self.accounts[account_num] = account_name
                            self.logger.debug(f"Added account {account_num}: {account_name}")

            # Create DataFrame
            if self.transactions:
                df = pd.DataFrame(self.transactions)
                self.logger.info(f"Successfully parsed {len(df)} transactions")
                self.logger.debug("Sample of transactions:")
                self.logger.debug(df.head().to_string())
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
            self.logger.exception("Full stack trace:")
            raise ValueError(f"Error parsing SIE file: {str(e)}")