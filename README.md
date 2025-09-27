# Scoreboard API Web Viewer

## Getting Started

1. **Create and activate a virtual environment (optional but recommended):**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   > If no `requirements.txt` exists yet, install the standard library only approach used here or add your own dependencies and update the file accordingly.
3. **Run the HTTP server:**
   ```bash
   python3 server.py
   ```
4. **Open the web interface:**
   Visit `http://127.0.0.1:8000/` in your browser. The navigation bar links to upcoming games, team lists, league rankings, and health status.

## Project Overview

This project provides a lightweight web interface over the SAMS scoreboard API. It fetches the configured JSON feed, exposes helpers for downloading or inspecting the payload, and renders several pages:

- **Upcoming Games:** lists scheduled matches with status information.
- **Teams:** lets you select a league and explore registered teams.
- **Rankings:** shows league standings, including played, wins, and losses.
- **Series Directory:** summarises all available leagues and links directly to their rankings.

All data originates from the remote API at runtime; no persistent storage is required. The code stays dependency-light, relying primarily on Python's standard library.
