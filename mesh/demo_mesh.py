"""
Phase 2 demo script — shows full mesh relay flow end-to-end.

Usage:
    python mesh/demo_mesh.py
    python mesh/demo_mesh.py --relay http://localhost:8001 --hub http://localhost:8000
    python mesh/demo_mesh.py --reset   # clear relay queue first
"""
import argparse
import time
import requests

RELAY_REPORTS = [
    "Building collapsed on Oak Street, at least 4 people trapped under debris",
    "Severe flooding on Campus Drive, families stranded on rooftops, need rescue",
    "Fire spreading through warehouse district, multiple buildings affected",
    "Person with serious injuries after bridge structural failure, unconscious",
    "Large gas leak near school, children need immediate evacuation",
]


def step(n, msg):
    print(f"\n\033[1;36mStep {n}\033[0m  {msg}")
    time.sleep(0.8)


def ok(msg):
    print(f"        \033[32m✓\033[0m  {msg}")


def info(msg):
    print(f"        \033[33m→\033[0m  {msg}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--relay", default="http://localhost:8001")
    parser.add_argument("--hub", default="http://localhost:8000")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    print("\n\033[1;31m╔══════════════════════════════════════════════╗\033[0m")
    print("\033[1;31m║  AI Disaster Response — Phase 2 Mesh Demo   ║\033[0m")
    print("\033[1;31m╚══════════════════════════════════════════════╝\033[0m")
    print(f"  Relay: {args.relay}")
    print(f"  Hub:   {args.hub}")

    # Optional reset
    if args.reset:
        step("0", "Clearing relay queue for fresh demo...")
        try:
            requests.post(f"{args.relay}/reset")
            ok("Queue cleared")
        except Exception as e:
            print(f"  ✗ Could not reset: {e}")

    # Step 1: Check relay health
    step(1, "Checking relay node is running...")
    try:
        r = requests.get(f"{args.relay}/status", timeout=5)
        s = r.json()
        ok(f"Relay online  —  {s['pending']} pending · {s['synced']} synced")
    except Exception as e:
        print(f"\n\033[31m  ✗ Relay not reachable at {args.relay}\033[0m")
        print(f"     Start it with:  uvicorn mesh.relay:app --port 8001")
        return

    # Step 2: Submit reports to relay (no internet required)
    step(2, f"Citizens submitting {len(RELAY_REPORTS)} reports to relay via local WiFi...")
    info("(Relay stores locally — AI hub does NOT see these yet)")
    for text in RELAY_REPORTS:
        lat = 43.0831 + (hash(text) % 100) / 5000
        lng = -76.1474 + (hash(text[:10]) % 100) / 5000
        try:
            r = requests.post(
                f"{args.relay}/submit",
                data={"text_message": text, "latitude": lat, "longitude": lng},
                timeout=10,
            )
            d = r.json()
            ok(f"Queued [{d['queue_id'][:8]}...] {text[:55]}")
        except Exception as e:
            print(f"  ✗ Failed: {e}")
        time.sleep(0.3)

    # Step 3: Show relay queue
    step(3, "Relay queue status (before sync)...")
    r = requests.get(f"{args.relay}/status")
    s = r.json()
    info(f"{s['pending']} reports queued locally on relay — {s['synced']} previously synced")

    # Step 4: Check hub hasn't seen them yet
    step(4, "Checking hub dashboard — reports should NOT appear yet...")
    try:
        r = requests.get(f"{args.hub}/api/v1/stats", timeout=5)
        stats = r.json()
        info(f"Hub has {stats['total']} total reports (mesh reports not included yet)")
    except Exception as e:
        print(f"  ✗ Hub not reachable: {e}")
        return

    # Step 5: Relay gains connectivity — sync to hub
    step(5, "Relay reaches responder hub — syncing all queued reports...")
    info("Running: POST /sync → forwarding each report through AI pipeline...")
    print()
    try:
        r = requests.post(
            f"{args.relay}/sync",
            params={"hub_url": args.hub},
            timeout=120,
        )
        result = r.json()
        ok(f"Sync complete: {result['synced']} synced · {result['failed']} failed")
    except Exception as e:
        print(f"  ✗ Sync failed: {e}")
        return

    # Step 6: Queue now empty
    step(6, "Relay queue status (after sync)...")
    r = requests.get(f"{args.relay}/status")
    s = r.json()
    ok(f"{s['pending']} pending · {s['synced']} synced")

    # Step 7: Show hub prioritized list
    step(7, "Top reports on hub dashboard (AI-ranked)...")
    r = requests.get(f"{args.hub}/api/v1/prioritized", timeout=10)
    reports = r.json()
    print()
    print(f"  {'PRIORITY':<10} {'NLP CLASS':<28} TEXT")
    print(f"  {'─'*70}")
    for rpt in reports[:8]:
        print(f"  {rpt['final_priority']:<10.1f} {(rpt['nlp_category'] or '—'):<28} {rpt['text_message'][:45]}")

    # Done
    print(f"\n\033[1;32m  ✓ Phase 2 complete!\033[0m")
    print(f"  Dashboard: \033[4m{args.hub.replace('8000','3000')}\033[0m")
    print(f"  Citizen form (relay): \033[4m{args.relay}\033[0m")
    print()


if __name__ == "__main__":
    main()
