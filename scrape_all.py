import os
import requests
import csv
from datetime import datetime, timedelta
import time
import itertools

SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
FILE_PATH = "massive_flight_dataset.csv"

CITIES = {
    "Mumbai": "BOM", "Delhi": "DEL", "Bengaluru": "BLR", 
    "Hyderabad": "HYD", "Chennai": "MAA", "Kolkata": "CCU", 
    "Pune": "PNQ", "Ahmedabad": "AMD", "Surat": "STV", 
    "Visakhapatnam": "VTZ", "Jaipur": "JAI", "Kochi": "COK", 
    "Chandigarh": "IXC", "Indore": "IDR", "Lucknow": "LKO"
}

def fetch_flight_data(src, dest, days_out):
    today = datetime.now()
    target_date = (today + timedelta(days=days_out)).strftime("%Y-%m-%d")
    
    params = {
        "engine": "google_flights",
        "departure_id": src,
        "arrival_id": dest,
        "outbound_date": target_date,
        "type": "2",
        "currency": "INR",
        "hl": "en",
        "gl": "in",
        "api_key": SERPAPI_KEY
    }
    
    try:
        res = requests.get("https://serpapi.com/search.json", params=params)
        data = res.json()
        best = data.get("best_flights", [])
        if not best:
            return None
            
        f = best[0]
        return {
            "Scrape_Timestamp": today.strftime("%Y-%m-%d %H:%M:%S"),
            "Days_to_Departure": days_out,
            "Departure_Date": target_date,
            "Source_City": src,
            "Destination_City": dest,
            "Airline": f.get("flights", [{}])[0].get("airline", "Unknown"),
            "Flight_Number": f.get("flights", [{}])[0].get("flight_number", "Unknown"),
            "Total_Duration_Mins": f.get("total_duration", 0),
            "Number_of_Stops": len(f.get("flights", [])) - 1,
            "CO2_Emissions_Grams": f.get("carbon_emissions", {}).get("this_flight", 0),
            "Price_INR": f.get("price", 0)
        }
    except Exception as e:
        print(f"Error on {src}->{dest}: {e}")
        return None

def main():
    if not SERPAPI_KEY:
        print("CRITICAL ERROR: SERPAPI_KEY missing!")
        return

    # Generate all 210 permutations (src != dest)
    all_routes = list(itertools.permutations(CITIES.values(), 2))
    all_routes.sort() # Ensure consistent ordering
    
    # --- 3-DAY ROTATION LOGIC ---
    # We divide the 210 routes into 3 batches of 70 routes each.
    # Depending on today's day of the year, we run exactly one batch.
    day_of_year = datetime.now().timetuple().tm_yday
    batch_index = day_of_year % 3
    
    # Slice the list into 3 chunks
    chunk_size = len(all_routes) // 3
    batches = [
        all_routes[0:chunk_size], 
        all_routes[chunk_size:chunk_size*2], 
        all_routes[chunk_size*2:]
    ]
    
    todays_routes = batches[batch_index]
    
    # --- PRO TARGET HORIZONS ---
    targets = [7, 14, 30, 60]
    
    new_rows = []
    
    total_calls = len(todays_routes) * len(targets)
    print(f"Starting Rotation Batch {batch_index + 1}/3")
    print(f"Processing {len(todays_routes)} routes x {len(targets)} dates = {total_calls} API calls today.")
    
    count = 1
    for src, dest in todays_routes:
        for days_out in targets:
            print(f"[{count}/{total_calls}] Fetching {src} -> {dest} for {days_out} days out...")
            data = fetch_flight_data(src, dest, days_out)
            if data:
                new_rows.append(data)
            count += 1
            time.sleep(0.5) # Gentle rate limiting for SerpApi
            
    if not new_rows:
        print("No data fetched today.")
        return
        
    # Write directly to local CSV (GitHub Actions will commit the file)
    file_exists = os.path.isfile(FILE_PATH)
    with open(FILE_PATH, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=new_rows[0].keys())
        if not file_exists:
            writer.writeheader()
        writer.writerows(new_rows)
        
    print(f"Successfully scraped {len(new_rows)} flights and updated {FILE_PATH}!")

if __name__ == "__main__":
    main()
