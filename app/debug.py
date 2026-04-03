"""
debug.py  —  run from the project root: python debug.py

Walks through every stage that could produce "0 nearby chargers"
and prints exactly what the API returns at each step.
"""
import os, json, uuid, sys
import requests
from math import radians, sin, cos, sqrt, atan2
from dotenv import load_dotenv

load_dotenv()

TOKEN    = os.getenv("TESLA_AUTH_TOKEN", "")
URL      = os.getenv("TESLA_GRAPHQL_URL", "https://ownership.tesla.com/graphql")
HOME_LAT = float(os.getenv("HOME_LAT", "37.7644"))
HOME_LNG = float(os.getenv("HOME_LNG", "-121.9530"))
RADIUS   = float(os.getenv("SEARCH_RADIUS_MILES", "5"))

SEP = "─" * 60

def haversine(lat1, lon1, lat2, lon2):
    R = 3958.8
    dlat = radians(lat2-lat1); dlon = radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))

# ── 0. Sanity check env ───────────────────────────────────────
print(SEP)
print("STEP 0 — environment")
print(f"  URL      : {URL}")
print(f"  TOKEN    : {'SET (' + TOKEN[:12] + '…)' if TOKEN else '❌ MISSING — set TESLA_AUTH_TOKEN in .env'}")
print(f"  HOME     : {HOME_LAT}, {HOME_LNG}")
print(f"  RADIUS   : {RADIUS} mi")

if not TOKEN:
    print("\n❌ Cannot continue without TESLA_AUTH_TOKEN")
    sys.exit(1)

VIEWPORT_DELTA = 1.085

QUERY = """
query getSiteList($siteFilter: SiteFilterInput!, $vehicleMakeType: VehicleMakeType!) {
  chargingNetwork {
    siteList(siteFilter: $siteFilter) {
      __typename
      ...SiteBaseFragment
      ... on MapSiteROW {
        isThirdPartySite
        isCanvasSite
        ownershipType
        pricing(vehicleMakeType: $vehicleMakeType) {
          ...MapSitePricingFragment
        }
      }
    }
  }
}
fragment SiteBaseFragment on SiteBase {
  ... on SiteBase {
    name displayName locationGUID haversineDistanceMiles
    availableStalls totalStalls siteType
    centroid { latitude longitude }
  }
}
fragment MapSitePricingFragment on SitePricing {
  userRates {
    activePricebook {
      charging {
        currencyCode rates
        dynamicRates { enabled level }
        uom
      }
    }
  }
}
"""

payload = {
    "operationName": "getSiteList",
    "query": QUERY,
    "variables": {
        "siteFilter": {
            "userLocation":    {"latitude": HOME_LAT, "longitude": HOME_LNG},
            "northwestCorner": {"latitude": HOME_LAT + VIEWPORT_DELTA, "longitude": HOME_LNG - VIEWPORT_DELTA},
            "southeastCorner": {"latitude": HOME_LAT - VIEWPORT_DELTA, "longitude": HOME_LNG + VIEWPORT_DELTA},
            "filters": [
                {"name": "rate",     "type": "LIST",     "value": ["2"]},
                {"name": "siteType", "type": "CHECKBOX", "value": {
                    "teslaSuperchargers":          True,
                    "teslaDestinationChargers":    True,
                    "3rdPartyDestinationChargers": True,
                    "openToNonTesla":              True,
                    "externalChargers":            False,
                    "privateDestinationChargers":  False,
                }},
            ],
            "experience": "TSLA",
        },
        "vehicleMakeType": "TSLA",
    },
}

rid = str(uuid.uuid4())
headers = {
    "Authorization":    f"Bearer {TOKEN}",
    "Content-Type":     "application/json",
    "Accept-Language":  "en",
    "Cache-Control":    "no-cache",
    "x-tesla-user-agent": "TeslaApp/4.55.0/796c9b49/ios/26.3.1",
    "User-Agent":       "TeslaV4/4166 CFNetwork/3860.400.51 Darwin/25.3.0",
    "x-request-id":     rid,
    "x-txid":           rid,
}

# ── 1. Raw HTTP response ──────────────────────────────────────
print(f"\n{SEP}")
print("STEP 1 — raw HTTP call")
try:
    resp = requests.post(URL, headers=headers, json=payload, timeout=15)
    print(f"  Status  : {resp.status_code}")
    print(f"  Size    : {len(resp.content)} bytes")
except Exception as e:
    print(f"  ❌ Request failed: {e}")
    sys.exit(1)

if resp.status_code == 401:
    print("  ❌ 401 Unauthorised — your TESLA_AUTH_TOKEN is expired or wrong")
    print("     Re-intercept with mitmproxy to get a fresh token")
    sys.exit(1)

if resp.status_code != 200:
    print(f"  ❌ Unexpected status. Body:\n{resp.text[:500]}")
    sys.exit(1)

# ── 2. Parse JSON ─────────────────────────────────────────────
print(f"\n{SEP}")
print("STEP 2 — JSON structure")
try:
    data = resp.json()
except Exception as e:
    print(f"  ❌ Could not parse JSON: {e}")
    print(f"  Raw: {resp.text[:300]}")
    sys.exit(1)

if "errors" in data:
    print(f"  ❌ GraphQL errors returned:")
    for err in data["errors"]:
        print(f"     • {err.get('message', err)}")
    sys.exit(1)

sites = data.get("data", {}).get("chargingNetwork", {}).get("siteList", [])
print(f"  Total sites returned by API : {len(sites)}")

if not sites:
    print("\n  ❌ API returned 0 sites — likely causes:")
    print("     a) Token is valid but your viewport delta is wrong")
    print("        → Try a MUCH larger viewport (change VIEWPORT_DELTA to 5.0 below)")
    print("     b) The 'rate' filter value '2' is too restrictive for this region")
    print("        → Try removing the rate filter entirely")
    print("     c) The ownership.tesla.com URL is wrong for your region")
    print("        → Check your mitmproxy capture for the exact host used")
    sys.exit(1)

# ── 3. Inspect each site ──────────────────────────────────────
print(f"\n{SEP}")
print("STEP 3 — site-by-site breakdown")

for i, site in enumerate(sites):
    name     = site.get("displayName") or site.get("name", "?")
    typename = site.get("__typename", "?")
    clat     = (site.get("centroid") or {}).get("latitude")
    clng     = (site.get("centroid") or {}).get("longitude")
    avail    = site.get("availableStalls", "?")
    total    = site.get("totalStalls", "?")
    dist_api = site.get("haversineDistanceMiles", "?")
    has_price = "pricing" in site
    pricing  = site.get("pricing")

    dist_calc = round(haversine(HOME_LAT, HOME_LNG, clat, clng), 2) if clat else "?"

    within = (isinstance(dist_calc, float) and dist_calc <= RADIUS)

    print(f"\n  [{i+1}] {name}")
    print(f"       type          : {typename}")
    print(f"       coords        : {clat}, {clng}")
    print(f"       dist (API)    : {dist_api} mi")
    print(f"       dist (calc)   : {dist_calc} mi  {'✅ within radius' if within else '❌ outside ' + str(RADIUS) + ' mi radius'}")
    print(f"       stalls        : {avail}/{total}")
    print(f"       has pricing   : {has_price}")

    if has_price and pricing:
        try:
            charging = pricing["userRates"]["activePricebook"]["charging"]
            rates    = charging.get("rates", [])
            dynamic  = charging.get("dynamicRates", {})
            uom      = charging.get("uom", "?")
            print(f"       rates         : {rates}  ({uom})")
            print(f"       dynamic       : enabled={dynamic.get('enabled')} level={dynamic.get('level')}")
        except Exception as e:
            print(f"       pricing parse error: {e}")
            print(f"       raw pricing: {json.dumps(pricing)[:200]}")
    elif has_price:
        print(f"       pricing key present but value: {pricing}")

# ── 4. Radius summary ─────────────────────────────────────────
print(f"\n{SEP}")
print("STEP 4 — radius filter summary")
in_radius  = []
no_pricing = []
has_price  = []

for site in sites:
    clat = (site.get("centroid") or {}).get("latitude")
    clng = (site.get("centroid") or {}).get("longitude")
    if not clat:
        continue
    d = haversine(HOME_LAT, HOME_LNG, clat, clng)
    name = site.get("displayName") or site.get("name", "?")
    if d <= RADIUS:
        in_radius.append((name, round(d,2), site))
        if site.get("pricing"):
            has_price.append((name, round(d,2)))
        else:
            no_pricing.append((name, round(d,2)))

print(f"  Within {RADIUS} mi       : {len(in_radius)}")
print(f"  With pricing        : {len(has_price)}")
print(f"  Without pricing     : {len(no_pricing)}")

if in_radius and not has_price:
    print(f"\n  ⚠️  Sites ARE within radius but NONE have pricing.")
    print(f"     This means they returned as a base type (not MapSiteROW)")
    print(f"     and the pricing fragment didn't apply.")
    print(f"\n     Sites in radius without pricing:")
    for name, d in no_pricing:
        print(f"       • {name} ({d} mi) — __typename: ", end="")
        for s in sites:
            if (s.get("displayName") or s.get("name")) == name:
                print(s.get("__typename", "?"))
                break

if not in_radius:
    nearest = min(
        [(site, haversine(HOME_LAT, HOME_LNG,
                          (site.get("centroid") or {}).get("latitude", HOME_LAT),
                          (site.get("centroid") or {}).get("longitude", HOME_LNG)))
         for site in sites if (site.get("centroid") or {}).get("latitude")],
        key=lambda x: x[1],
        default=(None, None)
    )
    if nearest[0]:
        print(f"\n  ⚠️  No sites within {RADIUS} mi.")
        print(f"     Nearest site: {nearest[0].get('displayName')} at {round(nearest[1],2)} mi")
        print(f"     → Increase SEARCH_RADIUS_MILES in your .env")

print(f"\n{SEP}")
print("DONE — paste this full output when asking for help debugging")
