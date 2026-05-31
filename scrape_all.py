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
    routes = list(itertools.permutations(CITIES.values(), 2))
    targets = [1, 15, 30]
    
    new_rows = []
    
    # 210 routes * 3 target dates = 630 iterations
    count = 1
    for src, dest in routes:
        for days_out in targets:
            print(f"[{count}/630] Fetching {src} -> {dest} for {days_out} days out...")
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
