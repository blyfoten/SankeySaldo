import streamlit as st
import pandas as pd
from sie_parser import SIEParser
from sankey_generator import SankeyGenerator

st.set_page_config(page_title="SIE-fil Visualisering", layout="wide")

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

            # Add debug information
            st.write("### Debug Information")
            st.write(f"Filstorlek: {len(content)} bytes")
            st.write(f"Filnamn: {uploaded_file.name}")

            # Show file content samples with different encodings
            encodings = ['cp437', 'utf-8', 'iso-8859-1']
            for encoding in encodings:
                try:
                    sample_content = content[:500].decode(encoding)
                    with st.expander(f"Visa filens första rader ({encoding})"):
                        st.code(sample_content, language=None)
                except UnicodeDecodeError:
                    st.warning(f"Kunde inte visa filinnehåll med {encoding} encoding")

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

                        # Generate and display Sankey diagram
                        with st.spinner('Genererar Sankey-diagram...'):
                            sankey = SankeyGenerator(df, metadata['accounts'])
                            try:
                                fig = sankey.generate_sankey_data()
                                st.plotly_chart(fig, use_container_width=True)
                            except Exception as e:
                                st.error(f"Fel vid generering av Sankey-diagram: {str(e)}")
                                st.write("Debug information:")
                                st.write(f"DataFrame shape: {df.shape}")
                                st.write("DataFrame columns:", df.columns.tolist())

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
                        st.write("Kontrollera att:")
                        st.write("1. Filen är i korrekt SIE-format")
                        st.write("2. Filen innehåller verifikationer (börjar med #VER)")
                        st.write("3. Verifikationerna innehåller transaktioner (rader som börjar med {)")

                except Exception as parse_error:
                    st.error(f"Fel vid parsing av fil: {str(parse_error)}")
                    st.write("Debug information:")
                    st.write(f"File size: {len(content)} bytes")
                    st.write(f"First 100 bytes: {repr(content[:100])}")

        except Exception as e:
            st.error(f"Ett fel uppstod vid hantering av filen: {str(e)}")
            st.write("Debug information:")
            st.write(f"Error type: {type(e).__name__}")
            st.write(f"Error details: {str(e)}")

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