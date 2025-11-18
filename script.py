import argparse
import datetime as dt
import json
import time

import requests
from veracode_api_signing.plugin_requests import RequestsAuthPluginVeracodeHMAC


BASE_URL = "https://api.veracode.com/appsec/v1/analytics/report"
MAX_WINDOW_DAYS = 180      # API supports up to ~6 months per request
DEFAULT_POLL_INTERVAL = 5  # 5s
DEFAULT_MAX_POLLS = 40     #  ~3.3 min


def parse_args():
    parser = argparse.ArgumentParser(
        description="Export Veracode AUDIT log data via Reporting REST API."
    )
    parser.add_argument(
        "--start-date",
        required=True,
        help="Start date (YYYY-MM-DD, inclusive).",
    )
    parser.add_argument(
        "--end-date",
        help="End date (YYYY-MM-DD, inclusive). Defaults to today.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=1.0,
        help="Sleep in seconds between windows (default: 1.0).",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=DEFAULT_POLL_INTERVAL,
        help="Seconds between report status checks (default: 5.0).",
    )
    parser.add_argument(
        "--max-polls",
        type=int,
        default=DEFAULT_MAX_POLLS,
        help="Max number of report status checks (default: 40).",
    )
    return parser.parse_args()


def to_date(value):
    return dt.date.fromisoformat(value)


def date_iteration_windows(start_date, end_date):
    delta = dt.timedelta(days=MAX_WINDOW_DAYS - 1)
    current = start_date

    while current <= end_date:
        window_end = min(current + delta, end_date)
        yield current, window_end
        current = window_end + dt.timedelta(days=1)


def build_audit_payload(window_start, window_end):
    payload = {
        "report_type": "AUDIT",
        "start_date": window_start.strftime("%Y-%m-%d"),
    }

    if window_end > window_start:
        payload["end_date"] = window_end.strftime("%Y-%m-%d")

    return payload


def request_report(session, payload):
    resp = session.post(
        BASE_URL,
        json=payload,
        auth=RequestsAuthPluginVeracodeHMAC(),
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()

    embedded = data.get("_embedded", {})
    report_id = data.get("id") or embedded.get("id")

    if not report_id:
        raise RuntimeError(
            f"No 'id' in response from {BASE_URL}: {json.dumps(data)}"
        )

    return report_id


def get_report_once(session, report_id):
    url = f"{BASE_URL}/{report_id}"
    resp = session.get(
        url,
        auth=RequestsAuthPluginVeracodeHMAC(),
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()


def wait_for_report(session, report_id, poll_interval, max_polls):
    for attempt in range(1, max_polls + 1):
        data = get_report_once(session, report_id)
        embedded = data.get("_embedded", {})
        status = embedded.get("status")

        print(f"  Poll {attempt}: status={status}")

        if status == "COMPLETED":
            return data

        if status not in ("SUBMITTED", "PROCESSING", None):
            raise RuntimeError(
                f"Report {report_id} ended in unexpected status {status}: "
                f"{json.dumps(data)}"
            )

        time.sleep(poll_interval)

    raise TimeoutError(
        f"Report {report_id} did not reach COMPLETED after {max_polls} polls"
    )


def fetch_audit_window(session, window_start, window_end, sleep_between_windows,
                       poll_interval, max_polls):
    payload = build_audit_payload(window_start, window_end)
    start_str = payload["start_date"]
    end_str = payload.get("end_date", start_str)

    print(f"Requesting AUDIT report from {start_str} to {end_str}...")

    report_id = request_report(session, payload)
    print(f"  Report id: {report_id}")

    report_data = wait_for_report(
        session=session,
        report_id=report_id,
        poll_interval=poll_interval,
        max_polls=max_polls,
    )
    print("  Report completed and retrieved.")

    time.sleep(sleep_between_windows)

    return {
        "window_start": start_str,
        "window_end": end_str,
        "report": report_data,
    }


def main():
    args = parse_args()

    start_date = to_date(args.start_date)
    end_date = to_date(args.end_date) if args.end_date else dt.date.today()

    if start_date > end_date:
        raise ValueError("start-date must be on or before end-date")

    print(f"Exporting AUDIT data from {start_date} to {end_date}...")

    session = requests.Session()
    all_windows = []

    for id, (w_start, w_end) in enumerate(date_iteration_windows(start_date, end_date), start=1):
        print(f"\n=== Data Window {id}: {w_start} to {w_end} ===")
        window_data = fetch_audit_window(
            session=session,
            window_start=w_start,
            window_end=w_end,
            sleep_between_windows=args.sleep,
            poll_interval=args.poll_interval,
            max_polls=args.max_polls,
        )
        all_windows.append(window_data)

    out_file = f"veracode_audit_{start_date}_to_{end_date}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_windows, f, indent=2)

    print(f"\nDone. Saved {len(all_windows)} window(s) to {out_file}")


if __name__ == "__main__":
    main()
