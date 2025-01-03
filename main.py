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
        # Add debug information
        st.write("### Debug Information")
        content = uploaded_file.read()
        st.write(f"Filstorlek: {len(content)} bytes")

        # Show first few lines of the file
        try:
            sample_content = content[:500].decode('cp437')
            with st.expander("Visa filens första rader"):
                st.code(sample_content, language=None)
        except UnicodeDecodeError:
            st.warning("Kunde inte visa filinnehåll med cp437 encoding")
            try:
                sample_content = content[:500].decode('utf-8')
                with st.expander("Visa filens första rader (UTF-8)"):
                    st.code(sample_content, language=None)
            except UnicodeDecodeError:
                sample_content = content[:500].decode('iso-8859-1', errors='ignore')
                with st.expander("Visa filens första rader (ISO-8859-1)"):
                    st.code(sample_content, language=None)

        try:
            # Parse SIE file with progress indicator
            with st.spinner('Läser in SIE-fil...'):
                parser = SIEParser()
                df, metadata = parser.parse_sie_file(content)

            # Display company information
            st.subheader("Företagsinformation")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Företag:** {metadata['company_name']}")
                st.write(f"**Antal konton:** {len(metadata['accounts'])}")
            with col2:
                st.write(f"**Räkenskapsår:** {metadata['fiscal_year']}")

            # Display parsing results
            if not df.empty:
                st.success(f"Hittade {len(df)} transaktioner!")

                # Generate and display Sankey diagram
                with st.spinner('Genererar Sankey-diagram...'):
                    sankey = SankeyGenerator(df, metadata['accounts'])
                    fig = sankey.generate_sankey_data()
                    st.plotly_chart(fig, use_container_width=True)

                # Display summary statistics
                st.subheader("Sammanfattning")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Antal transaktioner", len(df))
                    st.metric("Antal konton", len(metadata['accounts']))
                with col2:
                    total_positive = df[df['amount'] > 0]['amount'].sum()
                    total_negative = df[df['amount'] < 0]['amount'].sum()
                    st.metric("Total debet", f"{total_positive:,.2f} kr")
                    st.metric("Total kredit", f"{abs(total_negative):,.2f} kr")

                # Display accounts in expandable section
                with st.expander("Visa kontoplan"):
                    accounts_df = pd.DataFrame(
                        [(k, v) for k, v in metadata['accounts'].items()],
                        columns=['Kontonummer', 'Kontonamn']
                    )
                    st.dataframe(accounts_df)

                # Display raw data in expandable section
                with st.expander("Visa transaktioner"):
                    st.dataframe(df)
            else:
                st.error("Inga transaktioner hittades i filen.")
                st.write("Kontrollera att:")
                st.write("1. Filen är i korrekt SIE-format")
                st.write("2. Filen innehåller verifikationer (börjar med #VER)")
                st.write("3. Verifikationerna innehåller transaktioner (rader som börjar med {)")

        except Exception as e:
            st.error(f"Ett fel uppstod vid bearbetning av filen: {str(e)}")
            st.write("Kontrollera att filen är i korrekt SIE-format.")

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