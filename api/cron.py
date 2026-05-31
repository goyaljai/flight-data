import os
import requests
import base64
import csv
from io import StringIO
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            run_scraper()
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write('Cron Job Successful: Scraped deep learning flight data and committed to GitHub.'.encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f'Cron Job Failed: {str(e)}'.encode())

def run_scraper():
    # Environment Variables configured in Vercel Dashboard
    SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
    GITHUB_REPO = os.environ.get("GITHUB_REPO") # e.g. "JaiGoyal/flight-data"
    FILE_PATH = "dataset_deep_learning.csv"
    
    if not all([SERPAPI_KEY, GITHUB_TOKEN, GITHUB_REPO]):
        raise Exception("Missing Environment Variables!")

    today = datetime.now()
    targets = [1, 15, 30] # Track prices 1 day out, 15 days out, and 30 days out
    
    new_rows = []
    
    for days_out in targets:
        target_date = (today + timedelta(days=days_out)).strftime("%Y-%m-%d")
        
        params = {
            "engine": "google_flights",
            "departure_id": "BLR",
            "arrival_id": "JAI",
            "outbound_date": target_date,
            "type": "2",
            "currency": "INR",
            "hl": "en",
            "api_key": SERPAPI_KEY
        }
        
        res = requests.get("https://serpapi.com/search.json", params=params)
        data = res.json()
        
        best = data.get("best_flights", [])
        if not best:
            continue
            
        cheapest_flight = best[0] # Grab all multivariate features for Deep Learning
        
        # Deep Learning Ready Multivariate Row
        row = {
            "Scrape_Timestamp": today.strftime("%Y-%m-%d %H:%M:%S"),
            "Days_to_Departure": days_out,
            "Departure_Date": target_date,
            "Airline": cheapest_flight.get("flights", [{}])[0].get("airline", "Unknown"),
            "Flight_Number": cheapest_flight.get("flights", [{}])[0].get("flight_number", "Unknown"),
            "Departure_Time": cheapest_flight.get("flights", [{}])[0].get("departure_airport", {}).get("time", "Unknown"),
            "Arrival_Time": cheapest_flight.get("flights", [{}])[-1].get("arrival_airport", {}).get("time", "Unknown"),
            "Total_Duration_Mins": cheapest_flight.get("total_duration", 0),
            "Number_of_Stops": len(cheapest_flight.get("flights", [])) - 1,
            "CO2_Emissions_Grams": cheapest_flight.get("carbon_emissions", {}).get("this_flight", 0),
            "Price_INR": cheapest_flight.get("price", 0)
        }
        new_rows.append(row)
        
    if not new_rows:
        return # No data found today
        
    # --- GITHUB API COMMIT LOGIC ---
    # 1. Get existing CSV from Github to find its SHA
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    existing_content = ""
    sha = None
    
    get_res = requests.get(url, headers=headers)
    if get_res.status_code == 200:
        file_data = get_res.json()
        sha = file_data["sha"]
        existing_content = base64.b64decode(file_data["content"]).decode('utf-8')
    
    # 2. Append new rows using CSV writer
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=new_rows[0].keys())
    
    if not existing_content:
        writer.writeheader() # Write header if file is totally new
    else:
        output.write(existing_content) # Keep existing data
        if not existing_content.endswith("\n"):
            output.write("\n")
            
    writer.writerows(new_rows)
    updated_csv_content = output.getvalue()
    
    # 3. Commit back to GitHub
    commit_data = {
        "message": f"Daily DL Data Scrape: {today.strftime('%Y-%m-%d')}",
        "content": base64.b64encode(updated_csv_content.encode('utf-8')).decode('utf-8')
    }
    if sha:
        commit_data["sha"] = sha
        
    put_res = requests.put(url, headers=headers, json=commit_data)
    if put_res.status_code not in [200, 201]:
        raise Exception(f"Failed to commit to GitHub: {put_res.text}")

if __name__ == "__main__":
    run_scraper()
