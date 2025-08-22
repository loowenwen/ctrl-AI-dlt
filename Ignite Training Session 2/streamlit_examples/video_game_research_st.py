import concurrent.futures
import json
import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st
from nova_act import NovaAct
from pydantic import BaseModel


# Data models for game information
class GameInfo(BaseModel):
    title: str
    system: str
    release_date: Optional[str] = None
    genre: Optional[str] = None
    developer: Optional[str] = None
    rating: Optional[float] = None
    description: Optional[str] = None
    amazon_url: Optional[str] = None
    amazon_price: Optional[str] = None
    image_url: Optional[str] = None


class GameSearchResults(BaseModel):
    run_id: str
    search_params: Dict[str, Any]
    games: List[GameInfo]


# Create searches directory if it doesn't exist
os.makedirs("game_searches", exist_ok=True)


# Function to find top games for a system from GameFAQs
def find_top_games(system, num_games=5, headless=False, status_update_callback=None):
    """
    Find the top N games for a specified system on GameFAQs
    """
    if status_update_callback:
        status_update_callback(
            f"Searching for top {num_games} games for {system} on GameFAQs..."
        )

    with NovaAct(
        starting_page="https://gamefaqs.gamespot.com/games/systems", headless=headless
    ) as n:

        # Click on the system link
        print("Current URL:", n.page.url)
        n.act(f"Click on the link for the '{system}'")

        n.act("Scroll down to view the list of top games")

        # Extract the top N games
        result = n.act(
            f"Extract information for the top {num_games} games from this list. For each game, include the title, release date, genre, and rating if available.",
            schema={"type": "array", "items": GameInfo.model_json_schema()},
        )

        if not result.matches_schema:
            if status_update_callback:
                status_update_callback(
                    f"Failed to extract game information for {system}"
                )
            return []

        # Parse the results
        games = [GameInfo.model_validate(g) for g in result.parsed_response]

        # Make sure each game has the system field populated
        for game in games:
            game.system = system

        if status_update_callback:
            status_update_callback(f"Found {len(games)} games for {system}")

        return games


# Function to search for a game on Amazon and get details
def search_amazon_for_game(game, run_id, headless=False):
    """
    Search for a game on Amazon and extract product information
    """
    search_dir = os.path.join("game_searches", run_id)
    game_dir = os.path.join(
        search_dir, game.title.replace(" ", "_").replace("/", "_").replace(":", "")
    )
    os.makedirs(game_dir, exist_ok=True)

    with NovaAct(starting_page="https://www.amazon.com", headless=headless) as n:
        # Search for the game with system name for better results
        n.act(f"Search for '{game.title} {game.system}'")

        # Take screenshot of search results
        screenshot = n.page.screenshot()
        with open(os.path.join(game_dir, "amazon_search.png"), "wb") as f:
            f.write(screenshot)

        # Click on the most relevant result
        n.act(
            f"Find and click on the most relevant search result for '{game.title}' for {game.system}"
        )

        # Take screenshot of the product page
        screenshot = n.page.screenshot()
        with open(os.path.join(game_dir, "amazon_product.png"), "wb") as f:
            f.write(screenshot)

        # Extract product information
        result = n.act(
            f"Extract the following information about this {game.title} product: current price, detailed description, and the current URL. Return the data in JSON format.",
            schema={
                "type": "object",
                "properties": {
                    "amazon_price": {"type": "string"},
                    "description": {"type": "string"},
                },
            },
        )

        game.amazon_url = n.page.url

        if result.matches_schema:
            # Update the game object with Amazon information
            if "amazon_price" in result.parsed_response:
                game.amazon_price = result.parsed_response["amazon_price"]
            if "description" in result.parsed_response:
                game.description = result.parsed_response["description"]

            # Save the game data
            with open(os.path.join(game_dir, "game_data.json"), "w") as f:
                f.write(game.model_dump_json(indent=2))

        return game


# Function to run game search
def run_game_search(system, headless=False, max_threads=5, num_games=5):
    # Generate a unique run ID
    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    # Create run directory
    search_dir = os.path.join("game_searches", run_id)
    os.makedirs(search_dir, exist_ok=True)

    # Save search parameters
    search_params = {
        "system": system,
        "num_games": num_games,
        "max_threads": max_threads,
    }

    metadata = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "search_params": search_params,
    }

    with open(os.path.join(search_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    results = {"run_id": run_id, "search_params": search_params, "games": []}

    # Status update function
    def update_status(message):
        status_container.info(message)

    # Step 1: Find top games on GameFAQs
    update_status(f"Finding top {num_games} games for {system} on GameFAQs...")
    progress_bar.progress(0.1)

    top_games = find_top_games(
        system=system,
        num_games=num_games,
        headless=headless,
        status_update_callback=update_status,
    )

    if not top_games:
        update_status(f"No games found for {system}")
        return results

    progress_bar.progress(0.4)

    # Step 2: Search Amazon for each game in parallel
    update_status("Searching Amazon for game information in parallel...")

    # Ensure we have at least 1 worker
    total_games = len(top_games)
    max_workers = max(1, min(total_games, max_threads))

    detailed_games = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all Amazon search tasks
        future_to_game = {
            executor.submit(search_amazon_for_game, game, run_id, headless): game
            for game in top_games
        }

        # Collect results as they complete
        for i, future in enumerate(
            concurrent.futures.as_completed(future_to_game.keys())
        ):
            game = future_to_game[future]
            try:
                detailed_game = future.result()
                detailed_games.append(detailed_game)

                # Update progress
                update_status(
                    f"Completed Amazon research for {game.title} ({i+1}/{total_games})"
                )
                progress_bar.progress(0.4 + (0.5 * (i + 1) / total_games))
            except Exception as exc:
                print(f"Game {game.title} research failed: {exc}")
                # Fall back to original game data
                detailed_games.append(game)

    # Save the results
    results["games"] = detailed_games

    with open(os.path.join(search_dir, "results.json"), "w") as f:
        results_json = {
            "run_id": run_id,
            "search_params": search_params,
            "games": [g.model_dump() for g in detailed_games],
        }
        json.dump(results_json, f, indent=2)

    update_status("Game search complete!")
    progress_bar.progress(1.0)

    return results


# Function to load previous search data
def load_search_data(run_id):
    search_dir = os.path.join("game_searches", run_id)

    # Load metadata
    try:
        with open(os.path.join(search_dir, "metadata.json"), "r") as f:
            metadata = json.load(f)
    except:
        return None, None

    # Load game results
    try:
        with open(os.path.join(search_dir, "results.json"), "r") as f:
            results_json = json.load(f)
            results = {"run_id": run_id}
            results["games"] = [
                GameInfo.model_validate(g) for g in results_json["games"]
            ]
            results["search_params"] = results_json["search_params"]
    except:
        return None, metadata

    return results, metadata


# Function to get available search IDs
def get_available_searches():
    searches = []
    if os.path.exists("game_searches"):
        for run_id in os.listdir("game_searches"):
            search_dir = os.path.join("game_searches", run_id)
            if os.path.isdir(search_dir) and os.path.exists(
                os.path.join(search_dir, "metadata.json")
            ):
                try:
                    with open(os.path.join(search_dir, "metadata.json"), "r") as f:
                        metadata = json.load(f)

                    # Create a display name with timestamp and system
                    timestamp = metadata.get("timestamp", "").split("T")[0]
                    search_params = metadata.get("search_params", {})
                    system = search_params.get("system", "Unknown")
                    num_games = search_params.get("num_games", 5)

                    display_name = (
                        f"{timestamp} - {system} (Top {num_games}) ({run_id})"
                    )

                    searches.append(
                        {"id": run_id, "display": display_name, "metadata": metadata}
                    )
                except:
                    searches.append({"id": run_id, "display": run_id, "metadata": {}})

    # Sort by timestamp (newest first)
    searches.sort(key=lambda x: x["metadata"].get("timestamp", ""), reverse=True)
    return searches


# App layout
st.set_page_config(layout="wide", page_title="Video Game Research Tool")
st.title("Video Game Research Tool")
st.subheader("Find Top Games and Amazon Information")

# Create two main tabs - one for new search and one for browsing past searches
main_tabs = st.tabs(["New Search", "Browse Previous Searches"])

with main_tabs[0]:  # New Search tab
    # Sidebar for inputs
    with st.sidebar:
        st.header("Search Parameters")

        system = st.selectbox(
            "Gaming System",
            [
                "PlayStation 5",
                "PlayStation 4",
                "Xbox Series X",
                "Nintendo Switch",
                "PC",
            ],
            key="new_system",
        )

        num_games = st.slider(
            "Number of Games", min_value=1, max_value=10, value=5, key="num_games"
        )

        headless = st.checkbox("Run Browser Headless", value=False, key="new_headless")

        max_threads = st.slider(
            "Max Parallel Searches",
            min_value=1,
            max_value=10,
            value=5,
            key="max_threads",
        )

        search_button = st.button(
            "Search Games", type="primary", key="new_search_button"
        )

    # Search workflow row
    st.header("Search Workflow")
    workflow_container = st.container()
    with workflow_container:
        status_container = st.empty()
        progress_bar = st.progress(0)

    # Create a separator
    st.divider()

    # Results container
    results_container = st.container()

with main_tabs[1]:  # Browse Previous Searches tab
    # Get and display available searches
    available_searches = get_available_searches()

    if not available_searches:
        st.info("No previous searches found. Run a new search to create one.")
    else:
        st.subheader("Select a Previous Search")

        # Create a dropdown to select a search
        search_options = {
            search["display"]: search["id"] for search in available_searches
        }
        selected_search_display = st.selectbox(
            "Available Searches",
            options=list(search_options.keys()),
            key="browse_search_select",
        )

        selected_search_id = search_options[selected_search_display]

        # Display search info
        st.success(f"Loaded Search: {selected_search_id}")

        # Load the search data
        search_data, search_metadata = load_search_data(selected_search_id)

        if search_data:
            # Display metadata
            search_params = search_data.get("search_params", {})
            col1, col2 = st.columns(2)
            with col1:
                st.metric("System", search_params.get("system", "Unknown"))
            with col2:
                st.metric("Number of Games", search_params.get("num_games", 5))

            # Display the games table
            if "games" in search_data and search_data["games"]:
                st.subheader("Top Games")

                # Convert to DataFrame for display
                df = pd.DataFrame(
                    [
                        {
                            "Title": game.title,
                            "Genre": game.genre or "Unknown",
                            "Release Date": game.release_date or "Unknown",
                            "Rating": game.rating or "N/A",
                            "Price": game.amazon_price or "N/A",
                            "Amazon Link": game.amazon_url or "Not Found",
                        }
                        for game in search_data["games"]
                    ]
                )

                # Display the table
                st.dataframe(df, use_container_width=True)

                # Display detailed game information
                st.subheader("Game Details")
                for game in search_data["games"]:
                    with st.expander(f"{game.title} - Details"):
                        col1, col2 = st.columns([2, 1])

                        with col1:
                            st.markdown(f"**Title:** {game.title}")
                            st.markdown(f"**System:** {game.system}")
                            if game.release_date:
                                st.markdown(f"**Release Date:** {game.release_date}")
                            if game.genre:
                                st.markdown(f"**Genre:** {game.genre}")
                            if game.developer:
                                st.markdown(f"**Developer:** {game.developer}")
                            if game.rating:
                                st.markdown(f"**Rating:** {game.rating}")

                            st.markdown("### Description")
                            if game.description:
                                st.markdown(game.description)
                            else:
                                st.markdown("_No description available_")

                        with col2:
                            if game.amazon_price:
                                st.markdown(f"**Price:** {game.amazon_price}")
                            if game.amazon_url:
                                st.markdown(f"[View on Amazon]({game.amazon_url})")

        else:
            st.error(
                "Could not load search data. The search directory may be corrupted or incomplete."
            )

# Run the search when button is clicked
if search_button:
    start_time = time.time()

    with st.spinner(f"Searching for top games for {system}..."):
        results = run_game_search(
            system, headless=headless, max_threads=max_threads, num_games=num_games
        )

    end_time = time.time()

    # Display results
    with results_container:
        st.header("Search Results")

        if "games" in results and results["games"]:
            games = results["games"]

            # Convert to DataFrame for display
            df = pd.DataFrame(
                [
                    {
                        "Title": game.title,
                        "Genre": game.genre or "Unknown",
                        "Release Date": game.release_date or "Unknown",
                        "Rating": game.rating or "N/A",
                        "Price": game.amazon_price or "N/A",
                        "Amazon Link": game.amazon_url or "Not Found",
                    }
                    for game in games
                ]
            )

            # Display the table
            st.dataframe(df, use_container_width=True)

            # Display detailed game information
            st.subheader("Game Details")
            for game in games:
                with st.expander(f"{game.title} - Details"):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.markdown(f"**Title:** {game.title}")
                        st.markdown(f"**System:** {game.system}")
                        if game.release_date:
                            st.markdown(f"**Release Date:** {game.release_date}")
                        if game.genre:
                            st.markdown(f"**Genre:** {game.genre}")
                        if game.developer:
                            st.markdown(f"**Developer:** {game.developer}")
                        if game.rating:
                            st.markdown(f"**Rating:** {game.rating}")

                        st.markdown("### Description")
                        if game.description:
                            st.markdown(game.description)
                        else:
                            st.markdown("_No description available_")

                    with col2:
                        if game.amazon_price:
                            st.markdown(f"**Price:** {game.amazon_price}")
                        if game.amazon_url:
                            st.markdown(f"[View on Amazon]({game.amazon_url})")
        else:
            st.warning(f"No games found for {system}. Try another system.")

        # Display time saved and run ID
        st.success(
            f"Search completed in {end_time - start_time:.1f} seconds (would take ~15-30 minutes manually)"
        )
        st.info(f"Search Run ID: {results['run_id']}")

        # Create a summary section at the bottom
        st.divider()
        st.subheader("Search Summary")
        st.write(f"Completed game search for {system}")
        st.write(f"Number of games: {num_games}")
        st.write(f"Data saved to game_searches/{results['run_id']}/")
