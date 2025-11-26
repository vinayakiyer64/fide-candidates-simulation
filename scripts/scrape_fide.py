#!/usr/bin/env python3
"""
Scrape top 100 chess players from the official FIDE ratings page.
"""

import json
import re
import sys
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Required packages not found. Install with:")
    print("  pip install requests beautifulsoup4")
    sys.exit(1)


def scrape_fide_top100():
    """
    Scrape top 100 players from the official FIDE ratings page.
    
    Returns:
        List of player dicts with id, name, elo, initial_rank.
    """
    url = "https://ratings.fide.com/a_top.php?list=men"
    
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    players = []
    
    for row in soup.find_all('tr'):
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
        })
        
        if len(players) >= 100:
            break
    
    return players


def main():
    print("Fetching FIDE Top 100...")
    players = scrape_fide_top100()
    
    if not players:
        print("ERROR: No players found!")
        return 1
    
    # Save to data/players.json
    output_path = Path(__file__).parent.parent / "data" / "players.json"
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(players, f, indent=2)
    
    print(f"Saved {len(players)} players to {output_path}")
    print()
    print("Top 10:")
    for p in players[:10]:
        print(f"  {p['initial_rank']:3}. {p['name']:<30} {p['elo']:.0f}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

