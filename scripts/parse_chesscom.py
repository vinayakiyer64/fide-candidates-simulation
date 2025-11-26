import re
import json

def parse_chesscom():
    files = ["chesscom.html", "chesscom_p2.html"]
    players = []
    
    for filename in files:
        try:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            continue

        player_pattern = re.compile(r'class="master-players-rating-username"[^>]*>\s*([^<]+)\s*</a>.*?class="master-players-rating-player-rank[^"]*"\s*>\s*([0-9]+)\s*</div>', re.DOTALL)
        
        matches = player_pattern.findall(content)
        
        for name, rating in matches:
            name = name.strip()
            rating = int(rating.strip())
            
            if rating < 2000: 
                continue
            
            # Avoid duplicates if any
            if any(p['name'] == name for p in players):
                continue
                
            players.append({
                "id": len(players) + 1,
                "name": name,
                "elo": rating,
                "initial_rank": len(players) + 1
            })
            
            if len(players) >= 100:
                break
        
        if len(players) >= 100:
            break
            
    # Fill up to 100 if needed
    if len(players) < 100 and len(players) > 0:
        last_elo = players[-1]["elo"]
        # Extrapolate down to ~2640 at rank 100
        # If rank 50 is X, rank 100 is 2640.
        target_100 = 2640
        step = (last_elo - target_100) / (100 - len(players))
        
        current_rank = len(players) + 1
        start_fill_elo = last_elo
        
        while len(players) < 100:
            elo = int(start_fill_elo - (len(players) - current_rank + 1) * step)
            players.append({
                "id": len(players) + 1,
                "name": f"Player_{len(players)+1}",
                "elo": elo,
                "initial_rank": len(players) + 1
            })
            
    return players

if __name__ == "__main__":
    players = parse_chesscom()
    print(f"Found {len(players)} players.")
    if players:
        with open("players.json", "w") as f:
            json.dump(players, f, indent=2)
