"""Step 1: fetch the source file with retries and a clear fallback. Nothing here changes the data."""
import csv
import io
import logging
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path

import requests

from scripts.config import EXPECTED_COLUMNS, EXPECTED_ROWS, Settings

log = logging.getLogger("ingest.fetch")


class SourceError(Exception):
    """The source could not be read, or its structure is not the expected one."""


@dataclass
class FetchResult:
    content: bytes        # the file exactly as received
    origin: str           # URL or local path the bytes came from
    source_status: str    # 'http_200' or 'fallback_local'


def _download(url: str, retries: int, backoff: float, timeout: float) -> bytes:
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            log.info("Downloading %s (attempt %d/%d)", url, attempt, retries)
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as exc:
            last_error = exc
            log.warning("Download failed: %s", exc)
            if attempt < retries:
                time.sleep(backoff * attempt)
    raise SourceError("download failed after %d attempts: %s" % (retries, last_error))


def _member_from_zip(zip_bytes: bytes, member: str) -> bytes:
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            names = {n.split("/")[-1]: n for n in zf.namelist()}
            if member not in names:
                raise SourceError("%s not found in the zip (found: %s)" % (member, sorted(names)))
            return zf.read(names[member])
    except zipfile.BadZipFile as exc:
        raise SourceError("downloaded file is not a valid zip: %s" % exc)


def fetch_source(s: Settings) -> FetchResult:
    """Try the UCI URL first; fall back to the repo copy of hour.csv only if allowed (and say so in the log)."""
    try:
        content = _member_from_zip(_download(s.source_url, s.max_retries, s.retry_backoff_s, s.timeout_s), s.source_member)
        return FetchResult(content, s.source_url, "http_200")
    except SourceError as exc:
        log.error("Source unavailable: %s", exc)
        path = Path(s.local_fallback_path)
        if s.allow_local_fallback and path.is_file():
            log.warning("Using local fallback copy %s (source_status=fallback_local)", path)
            return FetchResult(path.read_bytes(), str(path), "fallback_local")
        raise


def parse_csv(content: bytes):
    """Split the file into a header and rows of strings. Values stay text, exactly as written in the file."""
    text = content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text, newline=""))
    rows = [r for r in reader if r]
    if not rows:
        raise SourceError("the file is empty")
    return rows[0], rows[1:]


def check_structure(header, rows) -> None:
    """Structure checks only (is this the file we expect?). Data quality is left to Phase 3."""
    if header != EXPECTED_COLUMNS:
        raise SourceError("unexpected header: %s" % header)
    bad = [i for i, r in enumerate(rows, start=2) if len(r) != len(EXPECTED_COLUMNS)]
    if bad:
        raise SourceError("%d rows do not have %d fields (first at line %d)" % (len(bad), len(EXPECTED_COLUMNS), bad[0]))
    if not rows:
        raise SourceError("the file has a header but no data rows")
    if len(rows) != EXPECTED_ROWS:
        log.warning("Row count %d differs from the expected %d", len(rows), EXPECTED_ROWS)
