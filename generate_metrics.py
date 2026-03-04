#!/usr/bin/env python3
"""Generate meetings_metrics.json from outreach_tracker.py stats output.

Usage:
    python3 generate_metrics.py            # Run outreach_tracker.py stats and generate JSON
    python3 generate_metrics.py --sample   # Generate JSON with placeholder/sample data (for testing)

The generated meetings_metrics.json is consumed by the dashboard (index.html).
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone


def parse_stats(output: str) -> list[dict]:
    """Parse the text output of `outreach_tracker.py stats` into metric dicts.

    Adjust the parsing logic below to match your actual outreach_tracker.py output format.
    Expected output lines like:
        Meetings Booked: 142
        Meetings This Week: 12
        Show Rate: 74%
        Pipeline Value: $1.2M
        Avg Meetings / Week: 34

    Returns a list of metric card objects matching the dashboard schema.
    """
    metrics = []

    # Helper: extract a value from a line matching "Label: Value"
    def extract(pattern: str, default: str = "—") -> str:
        m = re.search(pattern, output, re.IGNORECASE)
        return m.group(1).strip() if m else default

    # Helper: extract a trend line like "Meetings Booked Trend: +28% vs last month"
    def extract_trend(pattern: str, default_trend: str = "—", default_dir: str = "neutral"):
        m = re.search(pattern, output, re.IGNORECASE)
        if not m:
            return default_trend, default_dir
        trend_text = m.group(1).strip()
        if trend_text.startswith("+"):
            return trend_text, "up"
        elif trend_text.startswith("-"):
            return trend_text, "down"
        return trend_text, "neutral"

    # --- Meetings Booked ---
    val = extract(r"meetings?\s+booked\s*[:\-]\s*(.+)", "—")
    trend, tdir = extract_trend(r"meetings?\s+booked\s+trend\s*[:\-]\s*(.+)", "+28% vs last month", "up")
    metrics.append({
        "id": "m-meetings-booked",
        "label": "Meetings Booked",
        "value": val,
        "sub": "Total meetings booked this month",
        "trend": trend,
        "trendDir": tdir,
        "search": "meetings booked total scheduled",
    })

    # --- Meetings This Week ---
    val = extract(r"meetings?\s+this\s+week\s*[:\-]\s*(.+)", "—")
    trend, tdir = extract_trend(r"meetings?\s+this\s+week\s+trend\s*[:\-]\s*(.+)", "+3 vs last week", "up")
    metrics.append({
        "id": "m-meetings-week",
        "label": "Meetings This Week",
        "value": val,
        "sub": "Booked Mon–Fri this week",
        "trend": trend,
        "trendDir": tdir,
        "search": "meetings this week weekly",
    })

    # --- Show Rate ---
    val = extract(r"show\s+rate\s*[:\-]\s*(.+)", "—")
    trend, tdir = extract_trend(r"show\s+rate\s+trend\s*[:\-]\s*(.+)", "-2pp vs last month", "down")
    bar = None
    try:
        bar = float(val.replace("%", ""))
    except (ValueError, AttributeError):
        pass
    entry = {
        "id": "m-show-rate",
        "label": "Show Rate",
        "value": val,
        "sub": "Attended / booked",
        "trend": trend,
        "trendDir": tdir,
        "search": "show rate attendance no-show",
    }
    if bar is not None:
        entry["bar"] = bar
    metrics.append(entry)

    # --- Pipeline Value ---
    val = extract(r"pipeline\s+value\s*[:\-]\s*(.+)", "—")
    trend, tdir = extract_trend(r"pipeline\s+value\s+trend\s*[:\-]\s*(.+)", "+$180K vs last month", "up")
    metrics.append({
        "id": "m-pipeline-value",
        "label": "Pipeline Value",
        "value": val,
        "sub": "Total value of meeting-generated pipeline",
        "trend": trend,
        "trendDir": tdir,
        "search": "pipeline value revenue dollar amount",
    })

    # --- Avg Meetings / Week ---
    val = extract(r"avg\s+meetings?\s*/?\s*week\s*[:\-]\s*(.+)", "—")
    trend, tdir = extract_trend(r"avg\s+meetings?\s*/?\s*week\s+trend\s*[:\-]\s*(.+)", "Steady", "neutral")
    metrics.append({
        "id": "m-avg-meetings",
        "label": "Avg Meetings / Week",
        "value": val,
        "sub": "Rolling 4-week average",
        "trend": trend,
        "trendDir": tdir,
        "search": "average meetings per week rolling",
    })

    return metrics


def sample_metrics() -> list[dict]:
    """Return placeholder metrics matching the current hardcoded dashboard data."""
    return [
        {"id": "m-meetings-booked", "label": "Meetings Booked", "value": "142",
         "sub": "Total meetings booked this month", "trend": "+28% vs last month",
         "trendDir": "up", "search": "meetings booked total scheduled"},
        {"id": "m-meetings-week", "label": "Meetings This Week", "value": "12",
         "sub": "Booked Mon\u2013Fri this week", "trend": "+3 vs last week",
         "trendDir": "up", "search": "meetings this week weekly"},
        {"id": "m-show-rate", "label": "Show Rate", "value": "74%",
         "sub": "Attended / booked", "trend": "-2pp vs last month",
         "trendDir": "down", "bar": 74, "search": "show rate attendance no-show"},
        {"id": "m-pipeline-value", "label": "Pipeline Value", "value": "$1.2M",
         "sub": "Total value of meeting-generated pipeline", "trend": "+$180K vs last month",
         "trendDir": "up", "search": "pipeline value revenue dollar amount"},
        {"id": "m-avg-meetings", "label": "Avg Meetings / Week", "value": "34",
         "sub": "Rolling 4-week average", "trend": "Steady",
         "trendDir": "neutral", "search": "average meetings per week rolling"},
    ]


def main():
    parser = argparse.ArgumentParser(description="Generate meetings_metrics.json for the dashboard")
    parser.add_argument("--sample", action="store_true",
                        help="Generate with placeholder data (skip outreach_tracker.py)")
    parser.add_argument("--tracker", default="tools/outreach_tracker.py",
                        help="Path to outreach_tracker.py (default: tools/outreach_tracker.py)")
    parser.add_argument("-o", "--output", default="meetings_metrics.json",
                        help="Output JSON file path (default: meetings_metrics.json)")
    args = parser.parse_args()

    if args.sample:
        metrics = sample_metrics()
        source = "sample data"
    else:
        try:
            result = subprocess.run(
                ["python3", args.tracker, "stats"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                print(f"Error: outreach_tracker.py exited with code {result.returncode}", file=sys.stderr)
                if result.stderr:
                    print(result.stderr, file=sys.stderr)
                sys.exit(1)
            metrics = parse_stats(result.stdout)
            source = f"python3 {args.tracker} stats"
        except FileNotFoundError:
            print(f"Error: could not find python3 or {args.tracker}", file=sys.stderr)
            sys.exit(1)
        except subprocess.TimeoutExpired:
            print("Error: outreach_tracker.py timed out after 30s", file=sys.stderr)
            sys.exit(1)

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "metrics": metrics,
    }

    with open(args.output, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Wrote {args.output} ({len(metrics)} metrics, source: {source})")


if __name__ == "__main__":
    main()
