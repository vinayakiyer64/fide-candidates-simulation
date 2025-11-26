#!/usr/bin/env python3
"""
Scrape top 100 chess players from 2700chess.com and FIDE.

2700chess.com uses a React widget that only loads 20 players initially.
We fall back to the official FIDE ratings page which has a simple HTML table.
"""

import json
import re
import sys
from typing import List, Dict
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Required packages not found. Install with:")
    print("  pip install requests beautifulsoup4")
    sys.exit(1)


def scrape_2700chess() -> List[Dict]:
    """
    Scrape from 2700chess.com.
    
    The main page embeds ~20 players as JSON in the React widget initialization.
    Returns whatever players are available (usually top 20 with live ratings).
    """
    url = "https://2700chess.com/"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching 2700chess.com: {e}")
        return []
    
    # Extract embedded JSON data
    # Pattern: data: [{...}, {...}, ...]
    pattern = r'data:\s*(\[.*?\])'
    match = re.search(pattern, response.text)
    
    if not match:
        print("Could not find player data in 2700chess.com response")
        return []
    
    try:
        raw_data = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from 2700chess.com: {e}")
        return []
    
    players = []
    for item in raw_data:
        # Extract rating (may be string with decimal)
        rating_str = str(item.get("raiting", "0"))
        try:
            rating = float(rating_str)
        except ValueError:
            continue
            
        players.append({
            "id": item.get("fideid"),
            "name": item.get("name", "Unknown"),
            "elo": rating,
            "initial_rank": item.get("live_pos", len(players) + 1),
            "country": item.get("country_name", ""),
            "flag": item.get("flag", ""),
        })
    
    return players


def scrape_fide_top100() -> List[Dict]:
    """
    Scrape top 100 players from the official FIDE ratings page.
    
    This is more reliable than 2700chess.com for getting all 100 players,
    but uses the monthly published ratings (not live).
    """
    url = "https://ratings.fide.com/a_top.php?list=men"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching FIDE ratings: {e}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    players = []
    
    # Find all table rows
    rows = soup.find_all('tr')
    
    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 4:
            continue
            
        # Extract rank
        rank_span = cells[0].find('span', class_='rank_span')
        if not rank_span:
            continue
        try:
            rank = int(rank_span.get_text(strip=True))
        except ValueError:
            continue
            
        # Extract name and FIDE ID
        name_link = cells[1].find('a')
        if not name_link:
            continue
        name = name_link.get_text(strip=True)
        
        # Extract FIDE ID from href (e.g., /profile/1503014)
        href = name_link.get('href', '')
        fide_id_match = re.search(r'/profile/(\d+)', href)
        fide_id = int(fide_id_match.group(1)) if fide_id_match else rank
        
        # Extract federation
        fed = cells[2].get_text(strip=True)
        
        # Extract rating
        try:
            rating = int(cells[3].get_text(strip=True))
        except ValueError:
            continue
            
        players.append({
            "id": fide_id,
            "name": name,
            "elo": float(rating),
            "initial_rank": rank,
            "country": fed,
        })
        
        if len(players) >= 100:
            break
    
    return players


def merge_sources(fide_players: List[Dict], live_players: List[Dict]) -> List[Dict]:
    """
    Merge FIDE (official monthly) and 2700chess (live) data.
    
    Uses FIDE as the base and updates with live ratings where available.
    """
    if not fide_players:
        return live_players
    
    if not live_players:
        return fide_players
    
    # Create lookup by FIDE ID
    live_lookup = {p["id"]: p for p in live_players}
    
    merged = []
    for player in fide_players:
        fide_id = player["id"]
        
        if fide_id in live_lookup:
            # Use live rating
            live = live_lookup[fide_id]
            merged.append({
                "id": fide_id,
                "name": player["name"],
                "elo": live["elo"],  # Live rating
                "initial_rank": player["initial_rank"],  # Keep FIDE rank
                "country": player.get("country", live.get("country", "")),
            })
        else:
            merged.append(player)
    
    return merged


def main():
    print("Scraping chess player ratings...")
    print()
    
    # Try 2700chess.com first for live ratings
    print("Fetching from 2700chess.com (live ratings)...")
    live_players = scrape_2700chess()
    print(f"  Found {len(live_players)} players with live ratings")
    
    # Get full top 100 from FIDE
    print("Fetching from FIDE (official monthly ratings)...")
    fide_players = scrape_fide_top100()
    print(f"  Found {len(fide_players)} players from FIDE")
    
    # Merge sources
    if fide_players:
        players = merge_sources(fide_players, live_players)
        print(f"\nMerged: {len(players)} players (FIDE base + live updates)")
    else:
        players = live_players
        print(f"\nUsing 2700chess data only: {len(players)} players")
    
    if not players:
        print("ERROR: No players found from any source!")
        return 1
    
    # Sort by rating (descending) and reassign ranks
    players.sort(key=lambda p: p["elo"], reverse=True)
    for i, player in enumerate(players, 1):
        player["initial_rank"] = i
    
    # Save to data/players.json
    output_path = Path(__file__).parent.parent / "data" / "players.json"
    output_path.parent.mkdir(exist_ok=True)
    
    # Remove country field for cleaner output (optional)
    output_players = [
        {
            "id": p["id"],
            "name": p["name"],
            "elo": p["elo"],
            "initial_rank": p["initial_rank"],
        }
        for p in players
    ]
    
    with open(output_path, "w") as f:
        json.dump(output_players, f, indent=2)
    
    print(f"\nSaved {len(output_players)} players to {output_path}")
    print()
    print("Top 10 players:")
    for p in output_players[:10]:
        print(f"  {p['initial_rank']:3}. {p['name']:<30} {p['elo']:.1f}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

