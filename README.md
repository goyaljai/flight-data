# ✈️ The India Flight Prices Dataset

Welcome to the **Automated Indian Aviation Dataset**. This repository hosts a massive, continuously growing database of flight prices across the 15 largest cities in India. 

This dataset is designed specifically for **Deep Learning, Time-Series Forecasting, and Machine Learning** projects.

## ⚙️ Architecture & Methodology
Unlike static Kaggle datasets that suffer from "data decay", this dataset updates itself **every single day autonomously**.

* **The Engine:** A GitHub Actions cron job pings the SerpApi (Google Flights) engine daily at exactly 12:00 UTC.
* **The Target Matrix:** It tracks flights across 15 major cities (210 total permutations).
* **The Rotation Strategy:** To optimize API limits while capturing rolling data, the scraper uses a **3-Day Rotation Matrix**. It divides the 210 routes into 3 batches, scraping one batch per day.
* **The Horizon:** For every route, it captures the price exactly **7, 14, 30, and 60 days out** to map the "Surge Zone" and "Advance Booking" curves.

---

## 📊 Data Dictionary (Column Breakdown)

The `massive_flight_dataset.csv` file contains highly detailed, multivariate features for every single flight. Here is exactly what each column represents:

| Column Name | Type | Description |
| :--- | :--- | :--- |
| **`Scrape_Timestamp`** | `Datetime` | The exact time the scraper queried the API. This is crucial for tracking "when" the price was recorded. |
| **`Days_to_Departure`** | `Integer` | The number of days between the scrape date and the flight date. Guaranteed to be exactly `7`, `14`, `30`, or `60`. |
| **`Departure_Date`** | `Date` | The actual calendar date the flight takes off (Format: YYYY-MM-DD). |
| **`Day_of_Week`** | `String` | The day of the week for the departure date (e.g., `Monday`, `Friday`). Highly useful for weekend surge pricing analysis. |
| **`Departure_Time`** | `String` | The time of day the flight takes off (e.g., `10:00`). |
| **`Arrival_Time`** | `String` | The time of day the flight lands at its destination (e.g., `12:20`). |
| **`Source_City`** | `String` | The 3-letter IATA Airport Code of the departure city (e.g., `BLR` for Bengaluru). |
| **`Destination_City`** | `String` | The 3-letter IATA Airport Code of the arrival city (e.g., `JAI` for Jaipur). |
| **`Airline`** | `String` | The carrier operating the flight (e.g., `IndiGo`, `Air India`, `Akasa Air`). |
| **`Flight_Number`** | `String` | The unique alphanumeric identifier for the flight (e.g., `6E 5212`). |
| **`Total_Duration_Mins`** | `Integer` | The total duration of the trip from takeoff to final landing, measured in minutes. |
| **`Number_of_Stops`** | `Integer` | `0` indicates a direct flight. `1` or more indicates layovers. |
| **`CO2_Emissions_Grams`** | `Integer` | The estimated carbon footprint of the flight. Excellent for complex multi-variable Deep Learning models. |
| **`Price_Level`** | `String` | Google's internal classification of the fare (`high`, `typical`, or `low`). Extremely powerful categorical feature for ML. |
| **`Price_INR`** | `Integer` | The absolute cheapest fare available on Google Flights at the exact moment of scraping, in Indian Rupees (₹). |

---

## 🏙️ Cities Tracked
* Mumbai (`BOM`), Delhi (`DEL`), Bengaluru (`BLR`), Hyderabad (`HYD`), Chennai (`MAA`), Kolkata (`CCU`), Pune (`PNQ`), Ahmedabad (`AMD`), Surat (`STV`), Visakhapatnam (`VTZ`), Jaipur (`JAI`), Kochi (`COK`), Chandigarh (`IXC`), Indore (`IDR`), Lucknow (`LKO`).
