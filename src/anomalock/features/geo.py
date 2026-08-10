"""Offline city/country -> (lat, lon) lookup, used to turn the dataset's
Country/City strings into coordinates for the login-velocity feature.

The RBA dataset has no lat/lon columns, only Country (ISO alpha-2) and City
(free-text). We resolve coordinates from GeoNames' `cities15000.txt` dump
(all cities with population >= 15,000; CC BY 4.0, downloaded once into
data/external/ and not re-fetched over the network at feature-build time):

  - City match: (city name lower-cased, country code) -> that city's
    lat/lon. When a city name is ambiguous within a country, the most
    populous match wins (a reasonable prior with no other signal).
  - Country fallback: when the city is missing, "-", or has no match,
    we fall back to a population-weighted centroid of all GeoNames cities
    in that country — computed from the same file, so there's no separate
    country-centroid dataset (and license) to track.

This is intentionally coarse (city-level, not IP-level, geolocation) — good
enough to catch "impossible travel" (a login from Norway followed 10
minutes later by one from Brazil), which is the feature's actual purpose.
"""

from __future__ import annotations

import unicodedata
from functools import lru_cache
from pathlib import Path

import pandas as pd


def _asciify(s: str) -> str:
    """Strip diacritics to match GeoNames' `asciiname` convention (e.g. 'Ålesund' -> 'alesund')."""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii").strip().lower()

GEONAMES_PATH = Path(__file__).resolve().parents[3] / "data" / "external" / "cities15000.txt"

_COLUMNS = [
    "geonameid", "name", "asciiname", "alternatenames", "latitude", "longitude",
    "feature_class", "feature_code", "country_code", "cc2", "admin1", "admin2",
    "admin3", "admin4", "population", "elevation", "dem", "timezone", "modified",
]


@lru_cache(maxsize=1)
def _load_cities() -> pd.DataFrame:
    df = pd.read_csv(
        GEONAMES_PATH,
        sep="\t",
        header=None,
        names=_COLUMNS,
        usecols=["asciiname", "latitude", "longitude", "country_code", "population"],
        quoting=3,  # QUOTE_NONE — GeoNames alternatenames can contain stray quote chars
    )
    df["city_key"] = df["asciiname"].str.lower().str.strip()
    return df


@lru_cache(maxsize=1)
def _city_lookup() -> dict[tuple[str, str], tuple[float, float]]:
    df = _load_cities()
    # Highest population wins for (city, country) collisions.
    best = df.sort_values("population", ascending=False).drop_duplicates(subset=["city_key", "country_code"])
    return {
        (row.city_key, row.country_code): (row.latitude, row.longitude)
        for row in best.itertuples(index=False)
    }


@lru_cache(maxsize=1)
def _country_centroid() -> dict[str, tuple[float, float]]:
    df = _load_cities()
    df = df.assign(
        w_lat=df["latitude"] * df["population"].clip(lower=1),
        w_lon=df["longitude"] * df["population"].clip(lower=1),
        w=df["population"].clip(lower=1),
    )
    grouped = df.groupby("country_code")[["w_lat", "w_lon", "w"]].sum()
    return {
        country: (row.w_lat / row.w, row.w_lon / row.w)
        for country, row in grouped.iterrows()
    }


def resolve_coords(city: str | None, country: str | None) -> tuple[float, float] | None:
    """Best-effort (lat, lon) for a (city, country) pair, or None if the
    country itself is unresolvable."""
    if not country or not isinstance(country, str):
        return None
    country = country.strip().upper()

    if city and isinstance(city, str) and city.strip() not in ("", "-"):
        coords = _city_lookup().get((_asciify(city), country))
        if coords is not None:
            return coords

    return _country_centroid().get(country)
