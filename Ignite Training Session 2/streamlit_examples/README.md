# Streamlit Nova Act Examples

This repository contains example applications demonstrating the power of Amazon Nova Act, a Python SDK for building reliable web automation agents.

## Video Game Research Tool

The `video_game_research_st.py` example demonstrates how to use Nova Act to automate game research and price comparison. This tool:

1. Finds top games for any selected gaming system
2. Searches Amazon in parallel for each game to find prices and descriptions
3. Compiles results into a beautiful, interactive table
4. Saves all research for future reference

### Features

- **Parallel Processing**: Search Amazon for multiple games simultaneously
- **Interactive UI**: Built with Streamlit for a user-friendly experience
- **Data Persistence**: Save research results for future reference
- **Detailed Information**: Get comprehensive game details including:
  - Title and system
  - Release date
  - Genre
  - Developer
  - Rating
  - Description
  - Amazon price and link

### How It Works

1. **GameFAQs Research**:
   - Finds top games for the selected system
   - Extracts game information using Nova Act's schema support

2. **Amazon Research**:
   - Searches Amazon for each game
   - Extracts pricing and detailed descriptions
   - Takes screenshots of search results and product pages

3. **Results Compilation**:
   - Combines data from both sources
   - Creates an interactive table view
   - Saves all research data for future reference

### Usage

Visit https://nova.amazon.com/act to generate an API key

1. Install dependencies from main folder:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
streamlit run video_game_research_st.py
```

3. Use the interface to:
   - Select a gaming system
   - Choose number of games to research
   - Configure search parameters
   - View and save results

### Data Storage

Research results are saved in the `game_searches` directory, organized by run ID. Each run includes:
- Metadata about the search
- Game information
- Screenshots
- Amazon product details

## About Nova Act

Amazon Nova Act is an early research preview of an SDK + model for building agents designed to reliably take actions in web browsers. It enables developers to:

- Break down complex workflows into smaller, reliable commands
- Add more detail where needed
- Call APIs
- Intersperse direct browser manipulation
- Interleave Python code for tests, breakpoints, asserts, or threadpooling

For more information, visit: https://labs.amazon.science/blog/nova-act 