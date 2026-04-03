import requests
import uuid

from app.config import TESLA_GRAPHQL_URL, TESLA_AUTH_TOKEN
from app.models.charger import Charger


GET_SITE_LIST_QUERY = """
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
    name
    centroid {
      ...LatLngFragment
    }
    locationGUID
    displayName
    haversineDistanceMiles
    availableStalls
    totalStalls
    hasHighCongestion
  }
}

fragment LatLngFragment on LatLng {
  latitude
  longitude
}

fragment MapSitePricingFragment on SitePricing {
  userRates {
    activePricebook {
      charging {
        currencyCode
        rates
        dynamicRates {
          enabled
          level
        }
        uom
      }
    }
  }
}
"""


def fetch_nearby_superchargers(lat, lng):
    request_id = str(uuid.uuid4())
    COOKIE_STRING = (
        "bm_sv=5E7BA45F2C9CA71150E8BD5297CA35FB~YAAQkS0+FzdiD0WdAQAAtHFfTB9yH3lFgQhOdvDz+2V+b/Uln5sdvnZgWD+ELyJ2smdGRvUDEJXYWRu1/bBamuHack39nvxZGjzGLbUK60z81VsoFVjj68oYWREXdvJ/TeiRyHmcqILxh09K6Z8YDl3RISPebX+M1GKBiWrx+dlE0C+9op3GaTutZ194dpZXgKRX9SwrivY8PxCJJwI2LrHauk7r+yuDOwJrlU1ugmTVr4faOjDHjd05WqOT4Yg=~1; "
        "ak_bmsc=6ACA7E6515B384B3322AE528C4DA92FD~000000000000000000000000000000~YAAQkS0+F8BSD0WdAQAA8klfTB8rPAmMF2uNO6qS1LCevNX6J2z6NRGFAiOPZusGU7QP7HF+d46cU6VwjvExUdMXYza16CXu+AlsdHvSlY0nqlt2hJwe98tYj+Zb+BGf0OLKYPbGRzS2LudwxqTZ0g0AzSUIPhcPtPG/5PzmvNOm2mRX0Ry4Jl8Totba2xlSXaUe1gMzmHVbNvIC/WF2XJv0/ukerdnEjb1hJ6dR6SfjCh7nJYP4YWlZ+Six/NPJCCJfzJUFM448A2vwDgWlNrkF3J6rXI1e9dOaVqt0VjqpTFzE3nGEXE8KhZmUzWktoPmdIibzUmuWh7fyzD3r+/UiQGUH7z2FAHZRRfUUrESZjqpwdFBs8VNHRgBD7JNBKBGGvrZ/nBKhXBwLBOMqQIplPm+nmv5cDU2MevurWQTlrYxr; "
        "_abck=0A07DB0ECDAA77C21BED121FC571BE76~-1~YAAQkS0+F8/ZvESdAQAAvciaSw9UgOHDMeQGEQNeuDO5Q87IC/BQd5eHC37Nw/uyb+Y5lFhpZrKL70g5mz4EDhssa9mF/9etYa2IdSRGGUPj9Cl+9WOV7Xm+TT0Tz5HFh79XljMOr9e9eZ/rM4/tEwCxSz39X3Anr3chhssHshFtFDquGY1XVNzaZfIoKyW8GglCaH9aJNWV0zstxnZ5Z6yG6GejFFa2kCin2PRRtwnQbR1v5MWrlPtt6MB0stndOZS2IsWVXNdqidatQninLsuI84vyIl1jo9zoqBUfu2pdINJ/CwHDR7i9zCJoyQnuTWdoMWPxhepuaDfDKtV+p3VE/tqoosMj/s6maJp0DKs2tfYupB4fDCZ8yTi7eGb1SgW+lrFH8tzlRWsJCs8jZrHhWmDThy1gSdqgHokPzabwTMPYs+DlAbctc3ub401uejOLCTCWTNrQa4MZoCG7OHqJ~-1~-1~-1~-1~-1; "
        "bm_sz=107D7974B75EFBF749F061FF1845A826~YAAQkS0+F9DZvESdAQAAvciaSx+T+OH8Kb2r2+YAfzAa01O9jju1dNq+xknlacw33XBKm36KUNasAuoPURNRraTCkOr4/Ex0oUB7dQ/jVlVptUrY9a8Sa0XEvZ5qxZqqwF5414REtqAOQUUhMHzKla3qVI0UEctzCFeYaplFLt93Gl+DEz6T5sVPYvEwhIP54bmwqV6JOiT69JNmmmuKc8hEiPxXKbXyjkwkkQXYSed8MY3YOPNAZGHHgcHr+Xx1aDf+aJp2Ax3VPw6SqYu7E5ih6unMueFrBOAHQ222M0vUcWzPvvAjeI7yTHEXHK+Ax2AODOSNLD4mda77PYx3OAntMEvJL15aPzcjhjEaZYC2RNGOPJYuBau4/2P7jBwsEgmzI0yr0FK1HK2lmKE=~4604466~3748151; "
    )

    headers = {
        "Authorization": f"Bearer {TESLA_AUTH_TOKEN}",
        "Content-Type": "application/json",
        "Accept-Language": "en",
        "Cache-Control": "no-cache",
        "Accept-Encoding": "gzip, deflate, br",

        "x-tesla-user-agent": "TeslaApp/4.55.0/796c9b49/ios/26.3.1",
        "User-Agent": "TeslaV4/4166 CFNetwork/3860.400.51 Darwin/25.3.0",

        "x-request-id": request_id,
        "x-txid": request_id,

        # 🔥 most likely final unlock
        "Cookie": COOKIE_STRING,
    }

    VIEWPORT_DELTA = 3.0

    payload = {
        "operationName": "getSiteList",
        "variables": {
            "siteFilter": {
                "userLocation": {
                    "latitude": lat,
                    "longitude": lng,
                },
                "northwestCorner": {
                    "latitude": lat + VIEWPORT_DELTA,
                    "longitude": lng - VIEWPORT_DELTA,
                },
                "southeastCorner": {
                    "latitude": lat - VIEWPORT_DELTA,
                    "longitude": lng + VIEWPORT_DELTA,
                },
                "filters": [
                    {
                        "name": "siteType",
                        "type": "CHECKBOX",
                        "value": {
                            "teslaSuperchargers": True,
                            "teslaDestinationChargers": False,
                            "3rdPartyDestinationChargers": False,
                            "openToNonTesla": True,
                            "externalChargers": False,
                            "privateDestinationChargers": False,
                        },
                    }
                ],
                "experience": "TSLA",
            },
            "vehicleMakeType": "TSLA",
        },
        "query": GET_SITE_LIST_QUERY,
    }

    response = requests.post(
        TESLA_GRAPHQL_URL,
        headers=headers,
        json=payload,
        timeout=15,
    )

    json_data = response.json()

    if "errors" in json_data:
        print("GraphQL errors:")
        print(json_data)
        return []

    sites = json_data.get("data", {}).get("chargingNetwork", {}).get("siteList", [])
    print(f"Total raw sites returned: {len(sites)}")

    chargers = []

    for site in sites:
        pricing = site.get("pricing")
        if not pricing:
            continue

        try:
            charging = pricing["userRates"]["activePricebook"]["charging"]
            rates = charging.get("rates", [])

            if not rates:
                continue

            current_rate = rates[0]

            chargers.append(
                Charger(
                    station_id=site["locationGUID"],
                    name=site.get("displayName") or site.get("name"),
                    latitude=site["centroid"]["latitude"],
                    longitude=site["centroid"]["longitude"],
                    distance_miles=site["haversineDistanceMiles"],
                    current_price=current_rate,
                    usual_low_price=current_rate,
                    typical_price=current_rate,
                    available_stalls=site["availableStalls"],
                )
            )
        except Exception as e:
            print(f"Skipping malformed site: {e}")
            continue

    print(f"Parsed chargers: {len(chargers)}")
    return chargers