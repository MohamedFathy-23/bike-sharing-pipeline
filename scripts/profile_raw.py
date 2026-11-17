"""Step 5: profile the RAW data and print the data quality issues to fix in Phase 3. Read-only.
  python -m scripts.profile_raw                    reads staging.stg_bike_hourly
  python -m scripts.profile_raw --csv PATH         reads a CSV file instead (no database needed)"""
import argparse
import sys
from pathlib import Path

import pandas as pd

from scripts.config import EXPECTED_COLUMNS, Settings

DOMAINS = {"season": (1, 4), "yr": (0, 1), "mnth": (1, 12), "hr": (0, 23), "holiday": (0, 1), "weekday": (0, 6),
           "workingday": (0, 1), "weathersit": (1, 4)}
NORMALIZED = ["temp", "atemp", "hum", "windspeed"]


def load(csv_path):
    if csv_path:
        return pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    from scripts import raw_store
    s = Settings.from_env(); conn = raw_store.connect(s)
    with conn.cursor() as cur:
        cur.execute("SELECT %s FROM staging.stg_bike_hourly ORDER BY instant::int" % ", ".join(EXPECTED_COLUMNS))
        df = pd.DataFrame(cur.fetchall(), columns=EXPECTED_COLUMNS, dtype=str)
    conn.close(); return df.fillna("")


def profile(raw: pd.DataFrame):
    out = []; say = out.append
    n = len(raw)
    say("## Raw data profile (%d rows, %d columns)" % (n, raw.shape[1]))
    missing = {c: int((raw[c].str.strip() == "").sum()) for c in raw.columns}
    say("- Missing values: %s" % ("none" if not any(missing.values()) else {k: v for k, v in missing.items() if v}))
    num = raw.drop(columns=["dteday"]).apply(pd.to_numeric, errors="coerce")
    bad_type = {c: int(num[c].isna().sum()) for c in num.columns if num[c].isna().sum()}
    say("- Non-numeric values in numeric columns: %s" % (bad_type or "none"))
    say("- Duplicate rows: %d; duplicate instant: %d" % (raw.duplicated().sum(), raw.instant.duplicated().sum()))
    dates = pd.to_datetime(raw.dteday, format="%Y-%m-%d", errors="coerce")
    say("- dteday values not in YYYY-MM-DD format: %d (range %s to %s)" % (dates.isna().sum(), dates.min().date(), dates.max().date()))
    oor = {c: int(((num[c] < lo) | (num[c] > hi)).sum()) for c, (lo, hi) in DOMAINS.items()}
    say("- Values outside the documented domains: %s" % ({k: v for k, v in oor.items() if v} or "none"))
    say("- Normalized columns outside [0, 1]: %d" % int(((num[NORMALIZED] < 0) | (num[NORMALIZED] > 1)).sum().sum()))
    say("- cnt != casual + registered: %d" % int((num.cnt != num.casual + num.registered).sum()))
    say("- windspeed = 0: %d rows (%.1f%%); hum = 0: %d rows (dates: %s); atemp = 0: %d rows"
        % ((num.windspeed == 0).sum(), 100 * (num.windspeed == 0).mean(), (num.hum == 0).sum(),
           sorted(set(raw.loc[num.hum == 0, "dteday"])), (num.atemp == 0).sum()))
    say("- weathersit counts: %s" % num.weathersit.value_counts().sort_index().to_dict())
    possible = (dates.max() - dates.min()).days * 24 + 24
    per_day = dates.groupby(dates).size()
    say("- Hours present: %d of %d possible (%d missing); days with all 24 hours: %d of %d"
        % (n, possible, possible - n, (per_day == 24).sum(), per_day.size))
    say("- Smallest days by hours present: %s" % {str(k.date()): int(v) for k, v in per_day.nsmallest(3).items()})
    say("- Season code ranges by date: %s" % {int(k): "%s to %s" % (v.min().date(), v.max().date())
                                            for k, v in dates.groupby(num.season)})
    return "\n".join(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--csv"); args = ap.parse_args()
    report = profile(load(args.csv)); print(report)
    if not args.csv:
        p = Path(Settings.from_env().landing_dir); p.mkdir(parents=True, exist_ok=True)
        (p / "profile_report.md").write_text(report + "\n", encoding="utf-8")
