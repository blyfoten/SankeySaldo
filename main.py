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
            # Parse SIE file
            parser = SIEParser()
            df, metadata = parser.parse_sie_file(uploaded_file.read())

            # Display company information
            st.subheader("Företagsinformation")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Företag:** {metadata['company_name']}")
            with col2:
                st.write(f"**Räkenskapsår:** {metadata['fiscal_year']}")

            # Generate and display Sankey diagram
            if not df.empty:
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

                # Display raw data in expandable section
                with st.expander("Visa rådata"):
                    st.dataframe(df)

            else:
                st.warning("Inga transaktioner hittades i filen.")

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
