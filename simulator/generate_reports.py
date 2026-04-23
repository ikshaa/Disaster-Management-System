"""
Demo report simulator — fires 20 fake disaster reports to the API.
Usage:  python simulator/generate_reports.py
        python simulator/generate_reports.py --count 30 --delay 0.5
"""
import argparse
import random
import time
import requests

API = "http://localhost:8000/api/v1/reports"

# RIT / Rochester, NY area
BASE_LAT, BASE_LNG = 43.0831, -76.1474

REPORTS = [
    ("Building collapsed on Main St, 3 people trapped inside, cannot move", "CRITICAL"),
    ("Fire spreading rapidly through apartment complex, residents evacuating", "CRITICAL"),
    ("Person unconscious and bleeding after car accident on I-490", "CRITICAL"),
    ("Multiple people trapped under debris after structural collapse downtown", "CRITICAL"),
    ("Severe flooding on University Ave, water rising fast, people stranded", "HIGH"),
    ("Two people stuck in elevator in flooded basement parking garage", "CRITICAL"),
    ("Large fire at warehouse on Industrial Blvd, smoke visible for miles", "CRITICAL"),
    ("Bridge partially collapsed, vehicles at risk, urgent rescue needed", "HIGH"),
    ("Person buried under rubble after building wall fell", "CRITICAL"),
    ("Flooding in residential area, families need evacuation immediately", "HIGH"),
    ("Car overturned on highway, driver injured and conscious", "MEDIUM"),
    ("Fire at small business, contained but spreading to adjacent buildings", "HIGH"),
    ("Downed power line in park area, sparking near populated zone", "MEDIUM"),
    ("Minor flooding in underpass, road impassable but no injuries", "MEDIUM"),
    ("Traffic accident with minor injuries, ambulance already called", "MEDIUM"),
    ("Tree fell on house, family safe but roof damaged", "MEDIUM"),
    ("Road debris blocking one lane after storm, minor hazard", "LOW"),
    ("Small fire in trash bin, already extinguished by bystanders", "LOW"),
    ("Request for sandbags, expecting flooding but no emergency yet", "LOW"),
    ("Pothole causing issues near school zone, minor road damage", "LOW"),
]

def random_coords():
    dlat = random.uniform(-0.03, 0.03)
    dlng = random.uniform(-0.04, 0.04)
    return round(BASE_LAT + dlat, 6), round(BASE_LNG + dlng, 6)


def send_report(text: str, delay: float):
    lat, lng = random_coords()
    data = {
        "text_message": text,
        "latitude": lat,
        "longitude": lng,
    }
    try:
        r = requests.post(API, data=data, timeout=30)
        if r.status_code == 200:
            result = r.json()
            print(f"  ✓ [{result['final_priority']:4.1f}] {result['nlp_category']:<30} {text[:50]}")
        else:
            print(f"  ✗ HTTP {r.status_code}: {r.text[:80]}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    time.sleep(delay)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--delay", type=float, default=0.8)
    parser.add_argument("--shuffle", action="store_true", default=True)
    args = parser.parse_args()

    pool = REPORTS * ((args.count // len(REPORTS)) + 1)
    if args.shuffle:
        random.shuffle(pool)
    selected = pool[:args.count]

    print(f"\nFiring {args.count} reports to {API}\n")
    print(f"{'PRIORITY':<10} {'NLP CLASS':<30} {'TEXT':<50}")
    print("-" * 90)

    for text, _ in selected:
        send_report(text, args.delay)

    print("\nDone! Check the dashboard at http://localhost:3000")


if __name__ == "__main__":
    main()
