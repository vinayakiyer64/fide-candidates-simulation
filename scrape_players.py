import requests
from bs4 import BeautifulSoup
import json
import re

def fetch_top_100():
    url = "https://ratings.fide.com/top.phtml?list=men"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching URL: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    
    players = []
    # The table usually has class "contentpaneopen" or similar, or just look for the main table
    # FIDE site structure can be messy. Let's look for rows with rating data.
    
    # Tables often contain the data.
    tables = soup.find_all('table')
    
    found_table = None
    for table in tables:
        # Look for header "Name" or "Rating"
        if "Name" in table.get_text() and "Rating" in table.get_text():
            found_table = table
            break
            
    if not found_table:
        print("Could not find the data table.")
        return []

    rows = found_table.find_all('tr')
    
    # Skip header rows
    for row in rows:
        cols = row.find_all('td')
        # Typical row: Rank, Name, Title, Country, Rating, Games, B-Year
        # Check if valid data row
        if len(cols) < 4:
            continue
            
        txts = [c.get_text(strip=True) for c in cols]
        
        # Check if first column is a number (Rank)
        if not txts[0].isdigit():
            continue
            
        rank = int(txts[0])
        name = txts[1]
        # sometimes name is inside 'a' tag
        if cols[1].find('a'):
            name = cols[1].find('a').get_text(strip=True)
            
        try:
            rating = int(txts[4]) # Index might vary, let's be careful
            # Often: Rank, Name, Country, Rating, ... 
            # FIDE top list: Rank, Name, Title, Country, Rating, Games, B-Year
            # Let's verify indices.
            # 0: Rank
            # 1: Name
            # 2: Title (g, m, etc)
            # 3: Country
            # 4: Rating
            rating = int(txts[4])
        except ValueError:
            # Maybe different column
            continue
            
        players.append({
            "id": rank, # Use rank as ID for now, or generate one
            "name": name,
            "elo": rating,
            "rank": rank
        })
        
        if len(players) >= 100:
            break
            
    return players

if __name__ == "__main__":
    players = fetch_top_100()
    if players:
        print(f"Fetched {len(players)} players.")
        with open("players.json", "w") as f:
            json.dump(players, f, indent=2)
    else:
        print("No players fetched.")

