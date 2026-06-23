import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.scraper import login, fetch_listings, parse_listings
from src.state import load_state, save_state
from src.diff import find_new_openings
from src.notify import send_new_positions, send_no_changes, send_error


def main() -> None:
    username = os.environ.get("SIASISTEN_USERNAME", "")
    password = os.environ.get("SIASISTEN_PASSWORD", "")
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "")

    if not username or not password:
        print("ERROR: SIASISTEN_USERNAME / SIASISTEN_PASSWORD not set.", file=sys.stderr)
        sys.exit(1)
    if not webhook_url:
        print("ERROR: DISCORD_WEBHOOK_URL not set.", file=sys.stderr)
        sys.exit(1)

    # --- Login & fetch (or read mock file for testing) ---
    test_html_path = os.environ.get("TEST_HTML_PATH", "")
    if test_html_path:
        print(f"TEST MODE: reading from {test_html_path}")
        try:
            html = open(test_html_path, encoding="utf-8").read()
        except Exception as e:
            send_error(webhook_url, f"Could not read TEST_HTML_PATH: {e}")
            sys.exit(1)
    else:
        try:
            session = login(username, password)
            html = fetch_listings(session)
        except Exception as e:
            send_error(webhook_url, f"Failed to fetch listings: {e}")
            sys.exit(1)

    # --- Parse ---
    current = parse_listings(html)
    if not current:
        send_error(webhook_url, "Parsed 0 positions — the page layout may have changed.")
        sys.exit(1)
    print(f"Parsed {len(current)} positions.")

    # --- Load previous state ---
    previous = load_state()

    # --- First run: seed silently ---
    if not previous:
        save_state(current)
        print(f"First run: seeded state with {len(current)} positions. No notifications sent.")
        return

    # --- Diff ---
    new_openings = find_new_openings(current, previous)

    # --- No changes: notify quietly and update state ---
    if not new_openings:
        save_state(current)
        send_no_changes(len(current), webhook_url)
        print(f"No new openings. {len(current)} positions tracked.")
        return

    # --- Notify first, then save (so a failed send retries next run) ---
    send_new_positions(list(new_openings.values()), webhook_url)
    save_state(current)
    print(f"Notified about {len(new_openings)} new opening(s).")


if __name__ == "__main__":
    main()
