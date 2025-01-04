
# SIE-fil Visualisering

A Streamlit application for visualizing Swedish SIE (Standard Import/Export) accounting files using Sankey diagrams and financial analytics.

## Features

- Upload and parse SIE files
- Generate interactive Sankey diagrams of financial flows
- Calculate key financial ratios
- Display monthly transaction summaries
- Visualize transaction volumes over time

## Requirements

- Python 3.11+
- Dependencies listed in `pyproject.toml`

## Usage

1. Open the application in Replit
2. Click "Välj en SIE-fil" to upload your SIE file
3. View the generated visualizations and financial analysis

## Financial Metrics

The application calculates and displays:
- Liquidity ratio
- Solvency ratio
- Current assets and liabilities
- Total assets and liabilities
- Equity

## File Structure

- `main.py`: Main Streamlit application
- `sie_parser.py`: SIE file parser implementation
- `sankey_generator.py`: Sankey diagram generation logic
