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
    address {
      ...AddressFragment
    }
    centroid {
      ...LatLngFragment
    }
    entryPoint {
      ...LatLngFragment
    }
    openToPublic
    amenities
    accessCode
    activeOutageMessage
    maxPowerKw
    timeZone
    locationGUID
    trtId
    powerType
    accessType
    openToNonTeslas
    fastchargedbID
    waitEstimateBucket
    siteUsabilityArchetype
    hasMagicDockAdapter
    chargingAccessibility
    displayName
    displaySubTitle
    localizedSiteName
    isMagicDockSupportedSite
    isMagicDockSupportedV2Site
    haversineDistanceMiles
    availableStalls
    totalStalls
    siteType
    hasHighCongestion
    openHour {
      hour
      openNow
      shouldDisplay
    }
    additionalNavInstructions
    teslaExclusive
    siteCapabilities
    owner
    operator
    payToPark
    payToParkInstructions
    parkingLevel
    parkingLevelType
    valetOnly
    noRestrooms
    accessRestriction
    accessInstruction
    criticalInfo
  }
}

fragment AddressFragment on Address {
  street
  streetNumber
  city
  district
  state
  countryCode
  country
  postalCode
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
        currencyComparisons {
          toCurrency
          exchangeRate
        }
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
    headers = {
        "Authorization": f"Bearer {TESLA_AUTH_TOKEN}",
        "Content-Type": "application/json",

        "Accept-Language": "en",
        "Cache-Control": "no-cache",
        "Charset": "utf-8",
        "Accept-Encoding": "gzip, deflate, br",

        "x-tesla-user-agent": "TeslaApp/4.55.0/796c9b49/ios/26.3.1",
        "User-Agent": "TeslaV4/4166 CFNetwork/3860.400.51 Darwin/25.3.0",

        "x-request-id": request_id,
        "x-txid": request_id,
    }

    # Degrees around search center; must match userLocation or the API returns
    # sites far from HOME_LAT/HOME_LNG and local radius filtering yields nothing.
    VIEWPORT_DELTA = 1.085

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
                      "name": "rate",
                      "type": "LIST",
                      "value": ["2"]
                  },
                  {
                      "name": "siteType",
                      "type": "CHECKBOX",
                      "value": {
                          "3rdPartyDestinationChargers": True,
                          "externalChargers": False,
                          "openToNonTesla": True,
                          "privateDestinationChargers": False,
                          "teslaDestinationChargers": True,
                          # Superchargers are not destination chargers; without this,
                          # siteList can be empty when you expect stalls + kWh pricing.
                          "teslaSuperchargers": True,
                      }
                  }
              ],
              "experience": "TSLA"
          },
          "vehicleMakeType": "TSLA"
      },
      "query": GET_SITE_LIST_QUERY
  }

    response = requests.post(
        TESLA_GRAPHQL_URL,
        headers=headers,
        json=payload,
        timeout=10,
    )

    json_data = response.json()

    if "errors" in json_data:
        print(json_data)
        return []

    sites = json_data["data"]["chargingNetwork"]["siteList"]
    print(f"Total raw sites returned: {len(sites)}")

    chargers = []

    for site in sites:
        print("TYPE:", site.get("__typename"))
        print("NAME:", site.get("displayName"))
        print("HAS PRICING:", "pricing" in site)

        pricing = site.get("pricing")
        if not pricing:
            continue

        charging = pricing["userRates"]["activePricebook"]["charging"]

        current_rate = charging["rates"][0]

        chargers.append(
            Charger(
                station_id=site["locationGUID"],
                name=site["displayName"],
                latitude=site["centroid"]["latitude"],
                longitude=site["centroid"]["longitude"],
                distance_miles=site["haversineDistanceMiles"],
                current_price=current_rate,
                usual_low_price=current_rate,
                typical_price=current_rate,
                available_stalls=site["availableStalls"],
            )
        )

    print(f"Parsed chargers: {len(chargers)}")
    return chargers