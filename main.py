import streamlit as st
import pandas as pd
from sie_parser import SIEParser
from sankey_generator import SankeyGenerator
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="SIE-fil Visualisering", layout="wide")

def calculate_financial_ratios(df: pd.DataFrame, accounts: dict) -> dict:
    """Calculate key financial ratios from the transaction data."""
    # Group by account and sum amounts
    account_balances = df.groupby('account')['amount'].sum()

    # Initialize categories
    current_assets = 0  # Omsättningstillgångar (1100-1999)
    current_liabilities = 0  # Kortfristiga skulder (2000-2999)
    total_assets = 0  # Totala tillgångar (1000-1999)
    equity = 0  # Eget kapital (2000-2099)
    total_liabilities = 0  # Totala skulder (2000-2999)

    # Calculate sums for each category
    for account, balance in account_balances.items():
        account_num = int(account)
        if 1100 <= account_num <= 1999:
            current_assets += balance
            total_assets += balance
        elif 1000 <= account_num <= 1099:
            total_assets += balance
        elif 2000 <= account_num <= 2999:
            current_liabilities += abs(balance)
            total_liabilities += abs(balance)
        elif 2000 <= account_num <= 2099:
            equity += abs(balance)

    # Calculate ratios
    liquidity_ratio = current_assets / current_liabilities if current_liabilities != 0 else 0
    solvency_ratio = (total_assets - total_liabilities) / total_assets if total_assets != 0 else 0

    return {
        'liquidity_ratio': liquidity_ratio,
        'solvency_ratio': solvency_ratio,
        'current_assets': current_assets,
        'current_liabilities': current_liabilities,
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'equity': equity
    }

def create_monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Create monthly transaction summary."""
    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
    monthly_summary = df.groupby(df['date'].dt.strftime('%Y-%m'))\
                       .agg({
                           'amount': ['count', 'sum', 'mean'],
                           'account': 'nunique'
                       })
    monthly_summary.columns = ['Antal transaktioner', 'Total belopp', 'Genomsnitt belopp', 'Antal konton']
    return monthly_summary

def main():
    st.title("SIE-fil Visualisering")

    st.markdown("""
    ### Välkommen till SIE-fil Visualiseringsverktyget
    Ladda upp din SIE-fil för att se en visualisering av bokföringsbalansen som ett Sankey-diagram.
    """)

    # File upload section
    uploaded_file = st.file_uploader("Välj en SIE-fil", type=['se', 'si', 'sie'])

    if uploaded_file is not None:
        try:
            # Read file content
            content = uploaded_file.read()

            # Parse SIE file with progress indicator
            with st.spinner('Läser in SIE-fil...'):
                parser = SIEParser()
                progress_text = st.empty()
                progress_text.text("Analyserar fil...")

                try:
                    df, metadata = parser.parse_sie_file(content)
                    progress_text.empty()

                    # Display company information
                    if metadata.get('company_name'):
                        st.subheader("Företagsinformation")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write(f"**Företag:** {metadata['company_name']}")
                            st.write(f"**Antal konton:** {len(metadata.get('accounts', {}))}")
                        with col2:
                            st.write(f"**Räkenskapsår:** {metadata.get('fiscal_year', 'N/A')}")
                        with col3:
                            if 'file_content' in metadata:
                                st.write("**Fil innehåller:**")
                                for key, count in metadata['file_content'].items():
                                    st.write(f"- {key}: {count} rader")

                    # Display parsing results
                    if not df.empty:
                        st.success(f"Hittade {len(df)} transaktioner!")

                        # Calculate financial ratios
                        ratios = calculate_financial_ratios(df, metadata['accounts'])

                        # Display key figures in expanded section
                        with st.expander("Visa nyckeltal", expanded=True):
                            st.subheader("Finansiella nyckeltal")
                            col1, col2 = st.columns(2)

                            with col1:
                                st.metric("Likviditetsgrad", f"{ratios['liquidity_ratio']:.2f}")
                                st.metric("Soliditet", f"{ratios['solvency_ratio']:.2f}")
                            with col2:
                                st.metric("Omsättningstillgångar", f"{ratios['current_assets']:,.2f} kr")
                                st.metric("Kortfristiga skulder", f"{abs(ratios['current_liabilities']):,.2f} kr")

                        # Monthly summary
                        st.subheader("Månadsöversikt")
                        monthly_df = create_monthly_summary(df)
                        st.dataframe(monthly_df)

                        # Create monthly transaction volume chart
                        fig = px.line(monthly_df, 
                                    y='Antal transaktioner',
                                    title='Transaktionsvolym per månad')
                        st.plotly_chart(fig, use_container_width=True)

                        # Generate and display Sankey diagram
                        with st.spinner('Genererar Sankey-diagram...'):
                            sankey = SankeyGenerator(df, metadata['accounts'])
                            try:
                                fig = sankey.generate_sankey_data()
                                st.plotly_chart(fig, use_container_width=True)
                            except Exception as e:
                                st.error(f"Fel vid generering av Sankey-diagram: {str(e)}")

                        # Display summary statistics
                        st.subheader("Sammanfattning")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Antal transaktioner", len(df))
                            st.metric("Antal konton", len(metadata.get('accounts', {})))
                        with col2:
                            total_positive = df[df['amount'] > 0]['amount'].sum()
                            total_negative = df[df['amount'] < 0]['amount'].sum()
                            st.metric("Total debet", f"{total_positive:,.2f} kr")
                            st.metric("Total kredit", f"{abs(total_negative):,.2f} kr")

                        # Display accounts in expandable section
                        with st.expander("Visa kontoplan"):
                            if metadata.get('accounts'):
                                accounts_df = pd.DataFrame(
                                    [(k, v) for k, v in metadata['accounts'].items()],
                                    columns=['Kontonummer', 'Kontonamn']
                                )
                                st.dataframe(accounts_df)

                        # Display raw data in expandable section
                        with st.expander("Visa transaktioner"):
                            st.dataframe(df)
                    else:
                        st.warning("Inga transaktioner hittades i filen.")
                        if 'parsing_details' in metadata:
                            st.write("### Parsing Detaljer")
                            st.write(metadata['parsing_details'])

                except Exception as parse_error:
                    st.error(f"Fel vid parsing av fil: {str(parse_error)}")

        except Exception as e:
            st.error(f"Ett fel uppstod vid hantering av filen: {str(e)}")

    # Add footer with instructions
    st.markdown("---")
    st.markdown("""
    ### Instruktioner
    1. Ladda upp en SIE-fil genom att klicka på 'Välj en SIE-fil' ovan
    2. Visualiseringen genereras automatiskt
    3. Använd mushjulet för att zooma in/ut i diagrammet
    4. Klicka och dra för att panorera i diagrammet
    """)

if __name__ == "__main__":
    main()