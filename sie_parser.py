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
        logging.basicConfig(level=logging.DEBUG)  # DEBUG-nivå för maximal information
        self.logger = logging.getLogger(__name__)

    def parse_sie_file(self, content: bytes) -> Tuple[pd.DataFrame, Dict]:
        """Parse SIE file content and return transactions and metadata."""
        try:
            # Logga rådata för debugging
            self.logger.debug("Raw content (first 500 bytes):")
            self.logger.debug(content[:500])

            # Testa olika encodings om cp437 misslyckas
            try:
                decoded_content = content.decode('cp437')
            except UnicodeDecodeError:
                self.logger.warning("cp437 decoding failed, trying utf-8")
                try:
                    decoded_content = content.decode('utf-8')
                except UnicodeDecodeError:
                    self.logger.warning("utf-8 decoding failed, trying iso-8859-1")
                    decoded_content = content.decode('iso-8859-1', errors='ignore')

            lines = decoded_content.split('\n')
            self.logger.debug(f"Antal rader i filen: {len(lines)}")
            self.logger.debug("Första 5 rader i filen:")
            for i, line in enumerate(lines[:5]):
                self.logger.debug(f"Rad {i+1}: {repr(line)}")

            current_ver = None
            parsing_ver = False

            for line_num, line in enumerate(lines, 1):
                if not line.strip():
                    continue

                self.logger.debug(f"Processar rad {line_num}: {repr(line)}")
                parts = line.strip().split(' ')
                identifier = parts[0] if parts else ''

                if identifier == "#FNAMN":
                    self.company_name = ' '.join(parts[1:]).strip('"')
                    self.logger.info(f"Hittat företagsnamn: {self.company_name}")
                elif identifier == "#RAR":
                    self.fiscal_year = parts[2]
                    self.logger.info(f"Hittat räkenskapsår: {self.fiscal_year}")
                elif identifier == "#KONTO":
                    account_num = parts[1]
                    account_name = ' '.join(parts[2:]).strip('"')
                    self.accounts[account_num] = account_name
                    self.logger.debug(f"Lagt till konto {account_num}: {account_name}")
                elif identifier == "#VER":
                    parsing_ver = True
                    current_ver = {
                        'series': parts[1],
                        'number': parts[2],
                        'date': parts[3],
                        'text': ' '.join(parts[4:]).strip('"') if len(parts) > 4 else ''
                    }
                    self.logger.info(f"Börjar parse verifikation: {current_ver}")
                elif parsing_ver and line.startswith('{'):
                    self.logger.debug(f"Processar transaktion: {repr(line)}")
                    try:
                        # Parse transaction row
                        trans_parts = line.strip('{}').split(' ')
                        if len(trans_parts) >= 3:
                            date = trans_parts[0]
                            account = trans_parts[1]
                            amount = float(trans_parts[2].replace(',', '.'))
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
                            self.logger.debug(f"Lade till transaktion: {transaction}")
                    except Exception as e:
                        self.logger.error(f"Fel vid parsing av transaktion på rad {line_num}: {str(e)}")
                        self.logger.error(f"Line content: {repr(line)}")
                elif parsing_ver and line.startswith('}'):
                    self.logger.debug("Avslutar verifikation")
                    parsing_ver = False
                    current_ver = None

            # Convert transactions to DataFrame
            if self.transactions:
                df = pd.DataFrame(self.transactions)
                self.logger.info(f"Parsed {len(df)} transactions")
                self.logger.debug("Sample of transactions:")
                self.logger.debug(df.head().to_string())
            else:
                df = pd.DataFrame(columns=['date', 'account', 'amount', 'description', 'ver_series', 'ver_number'])
                self.logger.warning("No transactions found in the file")
                self.logger.debug("File content summary:")
                line_types = {}
                for line in lines:
                    if line.strip():
                        line_type = line.split(' ')[0] if ' ' in line else line
                        line_types[line_type] = line_types.get(line_type, 0) + 1
                self.logger.debug(f"Line types found: {line_types}")

            metadata = {
                'company_name': self.company_name,
                'fiscal_year': self.fiscal_year,
                'accounts': self.accounts
            }

            return df, metadata
        except Exception as e:
            self.logger.error(f"Error parsing SIE file: {str(e)}")
            self.logger.exception("Full stack trace:")
            raise ValueError(f"Fel vid parsning av SIE-fil: {str(e)}")