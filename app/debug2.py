"""
debug3.py — python debug3.py

Every filter test returned 0 with no errors — meaning the endpoint
accepts the query but has no data to serve. The URL is wrong.

This script tries every known Tesla GraphQL host to find which one
actually returns supercharger site data for your location.
"""
import os, uuid, json
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN    = os.getenv("TESLA_AUTH_TOKEN")
HOME_LAT = float(os.getenv("HOME_LAT", "37.7256"))
HOME_LNG = float(os.getenv("HOME_LNG", "-121.9327"))

SEP = "─" * 60

# Minimal query to check if a host returns site data at all
QUERY = """
query getSiteList($siteFilter: SiteFilterInput!, $vehicleMakeType: VehicleMakeType!) {
  chargingNetwork {
    siteList(siteFilter: $siteFilter) {
      __typename
      ...SiteBaseFragment
      ... on MapSiteROW {
        pricing(vehicleMakeType: $vehicleMakeType) {
          ...MapSitePricingFragment
        }
      }
    }
  }
}
fragment SiteBaseFragment on SiteBase {
  ... on SiteBase {
    displayName
    haversineDistanceMiles
    availableStalls
    totalStalls
    centroid { latitude longitude }
  }
}
fragment MapSitePricingFragment on SitePricing {
  userRates {
    activePricebook {
      charging { currencyCode rates uom }
    }
  }
}
"""

VARIABLES = {
    "siteFilter": {
        "userLocation":    {"latitude": HOME_LAT, "longitude": HOME_LNG},
        "northwestCorner": {"latitude": HOME_LAT + 3.0, "longitude": HOME_LNG - 3.0},
        "southeastCorner": {"latitude": HOME_LAT - 3.0, "longitude": HOME_LNG + 3.0},
        "filters": [],
        "experience": "TSLA",
    },
    "vehicleMakeType": "TSLA",
}

# Every Tesla GraphQL endpoint the community has found
CANDIDATES = [
    # From your mitmproxy capture
    "https://apigateway-charging-bff.tesla.com/api/graphql",
    # Common community-discovered endpoints
    "https://ownership.tesla.com/graphql",
    "https://akamai-apigateway-charging-ownership.tesla.com/graphql",
    "https://owner-api.teslamotors.com/graphql",
    # Fleet API
    "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/dx/charging/graphql",
    # Older paths on the bff host
    "https://apigateway-charging-bff.tesla.com/graphql",
    "https://apigateway-charging-bff.tesla.com/api/1/graphql",
    # Charging-specific hosts
    "https://charging.tesla.com/graphql",
    "https://akamai-apigateway-charging.tesla.com/graphql",
]


def try_endpoint(url):
    rid = str(uuid.uuid4())
    headers = {
        "Authorization":      f"Bearer {TOKEN}",
        "Content-Type":       "application/json",
        "Accept-Language":    "en",
        "x-tesla-user-agent": "TeslaApp/4.55.0/796c9b49/ios/26.3.1",
        "User-Agent":         "TeslaV4/4166 CFNetwork/3860.400.51 Darwin/25.3.0",
        "x-request-id":       rid,
        "x-txid":             rid,
    }
    try:
        resp = requests.post(
            url,
            headers=headers,
            json={"operationName": "getSiteList", "query": QUERY, "variables": VARIABLES},
            timeout=8,
        )
        status = resp.status_code
        size   = len(resp.content)

        if status == 404:
            return status, "404 Not Found", 0, []
        if status == 401:
            return status, "401 Unauthorized — token rejected by this host", 0, []
        if status == 403:
            return status, "403 Forbidden", 0, []

        try:
            data = resp.json()
        except Exception:
            return status, f"non-JSON response ({size} bytes): {resp.text[:80]}", 0, []

        if "errors" in data:
            msgs = [e.get("message", str(e)) for e in data["errors"]]
            return status, f"GraphQL errors: {'; '.join(msgs)}", 0, []

        sites = (data.get("data") or {}).get("chargingNetwork", {}).get("siteList", [])
        priced = [s for s in sites if s.get("pricing")]
        return status, "OK", len(sites), priced

    except requests.exceptions.ConnectionError:
        return 0, "Connection refused / DNS failure", 0, []
    except requests.exceptions.Timeout:
        return 0, "Timeout (8s)", 0, []
    except Exception as e:
        return 0, str(e), 0, []


print(SEP)
print(f"Hunting for the correct GraphQL endpoint")
print(f"Home: {HOME_LAT}, {HOME_LNG}  |  Viewport: ±3.0°  |  No filters")
print(SEP)

winner = None

for url in CANDIDATES:
    status, note, n_sites, priced = try_endpoint(url)
    host = url.replace("https://", "")

    if n_sites > 0:
        print(f"\n  ✅ FOUND IT: {host}")
        print(f"     {n_sites} sites returned  |  {len(priced)} with pricing")
        for s in priced[:3]:
            try:
                rates = s["pricing"]["userRates"]["activePricebook"]["charging"]["rates"]
                uom   = s["pricing"]["userRates"]["activePricebook"]["charging"]["uom"]
                print(f"     • {s.get('displayName','?'):<40} ${rates[0]}/{uom}  {s.get('haversineDistanceMiles','?')} mi")
            except Exception:
                print(f"     • {s.get('displayName','?')} (pricing parse error)")
        winner = url
    else:
        status_str = f"HTTP {status}" if status else "     "
        print(f"  ✗  {host:<60} {status_str}  {note}")

print(f"\n{SEP}")
if winner:
    print(f"✅ Set this in your .env:")
    print(f"   TESLA_GRAPHQL_URL={winner}")
else:
    print("❌ No endpoint returned sites.")
    print()
    print("Most likely cause: your Bearer token works for one Tesla service")
    print("but the charging map uses a DIFFERENT token scope or cookie.")
    print()
    print("Action: re-run mitmproxy while tapping a supercharger in the")
    print("Tesla app and look VERY carefully at:")
    print("  1. The exact host (could be a dated/regional variant)")
    print("  2. Whether it sends cookies in addition to Authorization header")
    print("  3. Whether there's an 'x-correlation-id' or other required header")
    print()
    print("Run mitmproxy with:")
    print("  mitmproxy --listen-port 8080 --flow-detail 4")
    print("Then in the flow details, press Tab to see full request headers.")