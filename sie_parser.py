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
            # Try different encodings
            encodings = ['cp437', 'utf-8', 'iso-8859-1']
            decoded_content = None
            used_encoding = None

            for encoding in encodings:
                try:
                    decoded_content = content.decode(encoding)
                    used_encoding = encoding
                    self.logger.info(f"Successfully decoded with {encoding}")
                    break
                except UnicodeDecodeError:
                    continue

            if not decoded_content:
                raise ValueError("Could not decode file with any supported encoding")

            lines = decoded_content.split('\n')
            self.logger.debug(f"File decoded with {used_encoding}, found {len(lines)} lines")

            # Debug: Show first few lines
            for i, line in enumerate(lines[:10]):
                self.logger.debug(f"Line {i+1}: {repr(line)}")

            current_ver = None
            parsing_ver = False
            line_types = {}
            parsing_details = []

            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue

                self.logger.debug(f"Processing line {line_num}: {repr(line)}")

                # Split line into parts, preserving quoted strings
                parts = []
                current_part = []
                in_quotes = False

                for char in line:
                    if char == '"':
                        in_quotes = not in_quotes
                    elif char.isspace() and not in_quotes:
                        if current_part:
                            parts.append(''.join(current_part))
                            current_part = []
                    else:
                        current_part.append(char)

                if current_part:
                    parts.append(''.join(current_part))

                if not parts:
                    continue

                identifier = parts[0]
                line_types[identifier] = line_types.get(identifier, 0) + 1

                # Parse different line types
                if identifier == "#FNAMN":
                    self.company_name = ' '.join(parts[1:]).strip('"')
                    self.logger.info(f"Found company name: {self.company_name}")
                    parsing_details.append(f"Found company: {self.company_name}")

                elif identifier == "#RAR":
                    try:
                        self.fiscal_year = parts[1] if len(parts) > 1 else parts[2]
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

                elif identifier == "#VER":
                    parsing_ver = True
                    ver_parts = [p.strip('"') for p in parts[1:]]
                    current_ver = {
                        'series': ver_parts[0] if len(ver_parts) > 0 else '',
                        'number': ver_parts[1] if len(ver_parts) > 1 else '',
                        'date': ver_parts[2] if len(ver_parts) > 2 else '',
                        'text': ' '.join(ver_parts[3:]) if len(ver_parts) > 3 else ''
                    }
                    self.logger.info(f"Started parsing verification: {current_ver}")
                    parsing_details.append(f"Found verification: {current_ver['series']}-{current_ver['number']}")

                elif parsing_ver and line.startswith('{'):
                    self.logger.debug(f"Parsing transaction line: {repr(line)}")
                    try:
                        # Remove { and } and split on whitespace while preserving quotes
                        trans_line = line.strip('{}').strip()
                        trans_parts = []
                        current_part = []
                        in_quotes = False

                        # More precise parsing of transaction line
                        for i, char in enumerate(trans_line):
                            if char == '"':
                                in_quotes = not in_quotes
                                if i > 0 and trans_line[i-1] != ' ':  # Handle quotes without spaces
                                    if current_part:
                                        trans_parts.append(''.join(current_part))
                                        current_part = []
                            elif char.isspace() and not in_quotes:
                                if current_part:
                                    trans_parts.append(''.join(current_part))
                                    current_part = []
                            else:
                                current_part.append(char)

                        if current_part:
                            trans_parts.append(''.join(current_part))

                        self.logger.debug(f"Parsed transaction parts: {trans_parts}")

                        if len(trans_parts) >= 2:  # Changed from 3 to 2 as some lines might have implicit amounts
                            # Handle dates with or without quotes
                            date = trans_parts[0].strip('"')
                            account = trans_parts[1].strip('"')

                            # Handle amount with better error checking
                            amount = 0.0
                            if len(trans_parts) >= 3:
                                amount_str = trans_parts[2].strip('"')
                                # Handle both comma and period as decimal separator
                                amount = float(amount_str.replace(',', '.'))

                            # Get description, defaulting to verification text if none provided
                            description = ' '.join(trans_parts[3:]).strip('"') if len(trans_parts) > 3 else current_ver['text']

                            transaction = {
                                'date': date,
                                'account': account,
                                'amount': amount,
                                'description': description,
                                'ver_series': current_ver['series'],
                                'ver_number': current_ver['number']
                            }
                            self.transactions.append(transaction)
                            self.logger.debug(f"Added transaction: {transaction}")
                            parsing_details.append(f"Added transaction: Account={account}, Amount={amount}")
                    except Exception as e:
                        self.logger.error(f"Error parsing transaction at line {line_num}: {str(e)}")
                        self.logger.error(f"Line content: {repr(line)}")
                        parsing_details.append(f"Error parsing transaction at line {line_num}: {str(e)}")

                elif parsing_ver and line.startswith('}'):
                    parsing_ver = False
                    current_ver = None

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