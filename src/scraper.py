import re
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict

BASE_URL = "https://siasisten.cs.ui.ac.id"

# h4 IDs that delimit each term's table on the listings page
TERM_HEADER_IDS = ["next-term-header", "short-term-header", "term-header"]


@dataclass
class Position:
    id: str            # lowongan ID string, or "fallback|term|course_key|dosen"
    term: str          # e.g. "Ganjil 2026/2027"
    course: str        # e.g. "CSGE601021 - 01.00.12.01-2020 — Dasar-Dasar Pemrograman 2"
    dosen: str
    status: str        # "Buka" | "Tutup"
    can_apply: bool    # True when a "Daftar" link is present
    slots: str
    applicants: str
    accepted: str
    apply_url: str | None  # relative URL, e.g. "/lowongan/daftarLowongan/2476/"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Position":
        return cls(**d)


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
}


def login(username: str, password: str) -> requests.Session:
    s = requests.Session()
    s.headers.update(_HEADERS)
    r = s.get(f"{BASE_URL}/login/", timeout=15)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")
    token_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
    if not token_input:
        raise RuntimeError("Could not find csrfmiddlewaretoken on login page.")
    token = token_input["value"]

    r = s.post(
        f"{BASE_URL}/login/",
        data={
            "csrfmiddlewaretoken": token,
            "username": username,
            "password": password,
            "next": "",
        },
        headers={"Referer": f"{BASE_URL}/login/"},
        allow_redirects=False,
        timeout=15,
    )

    if r.status_code != 302 or r.headers.get("Location") != "/index/":
        raise RuntimeError(
            f"Login failed (HTTP {r.status_code}). Check SIASISTEN_USERNAME / SIASISTEN_PASSWORD."
        )

    return s


def fetch_listings(session: requests.Session) -> str:
    r = session.get(f"{BASE_URL}/lowongan/listLowongan/", timeout=15)
    r.raise_for_status()
    if "Logout" not in r.text:
        raise RuntimeError("Listings page looks unauthenticated — session may have expired.")
    return r.text


def _build_col_map(headers: list[str]) -> dict[str, int]:
    col = {}
    for i, h in enumerate(headers):
        h_low = h.lower()
        # "Prodi Mata Kuliah" also contains "mata kuliah" — exclude it explicitly
        if "mata kuliah" in h_low and "prodi" not in h_low:
            col["course"] = i
        elif "dosen" in h_low:
            col["dosen"] = i
        elif "status lowongan" in h_low:
            col["status"] = i
        elif "diterima" in h_low:
            col["accepted"] = i
        elif "pelamar" in h_low:
            col["applicants"] = i
        elif "jumlah lowongan" in h_low:
            col["slots"] = i
        elif "daftar" in h_low:
            col["link"] = i
    return col


def _extract_link(td) -> tuple[str | None, str | None, bool]:
    """Returns (lowongan_id, apply_url, can_apply)."""
    a = td.find("a", href=True)
    if not a:
        return None, None, False
    href = a["href"]
    m = re.search(r"/daftarLowongan/(\d+)/", href)
    if m:
        return m.group(1), href, True
    m = re.search(r"/detailLamaran/(\d+)/", href)
    if m:
        return m.group(1), href, False
    return None, None, False


def _cell_text(cells: list, i: int) -> str:
    if i < 0 or i >= len(cells):
        return ""
    return " ".join(cells[i].get_text(separator=" ", strip=True).split())


def _course_text(td) -> str:
    parts = [p.strip() for p in td.stripped_strings if p.strip()]
    return " — ".join(parts) if parts else ""


def parse_listings(html: str) -> dict[str, Position]:
    soup = BeautifulSoup(html, "lxml")
    positions: dict[str, Position] = {}

    for header_id in TERM_HEADER_IDS:
        h4 = soup.find("h4", id=header_id)
        if not h4:
            continue
        term_label = h4.get_text(strip=True)
        table = h4.find_next_sibling("table")
        if not table:
            continue

        rows = table.find_all("tr")
        if not rows:
            continue

        headers = [th.get_text(strip=True) for th in rows[0].find_all("th")]
        col = _build_col_map(headers)

        if "course" not in col or "status" not in col:
            continue  # unrecognised table layout, skip rather than crash

        for row in rows[1:]:
            cells = row.find_all("td")
            if not cells:
                continue

            course = _course_text(cells[col["course"]]) if "course" in col else ""
            dosen = _cell_text(cells, col.get("dosen", -1))
            status = _cell_text(cells, col.get("status", -1))
            slots = _cell_text(cells, col.get("slots", -1))
            applicants = _cell_text(cells, col.get("applicants", -1))
            accepted = _cell_text(cells, col.get("accepted", -1))

            pos_id, apply_url, can_apply = (
                _extract_link(cells[col["link"]]) if "link" in col else (None, None, False)
            )

            if pos_id is None:
                # Stable fallback key for rows without a lowongan ID
                course_key = course.split("—")[0].strip()[:40]
                pos_id = f"fallback|{term_label}|{course_key}|{dosen}"

            positions[pos_id] = Position(
                id=pos_id,
                term=term_label,
                course=course,
                dosen=dosen,
                status=status,
                can_apply=can_apply,
                slots=slots,
                applicants=applicants,
                accepted=accepted,
                apply_url=apply_url,
            )

    return positions
