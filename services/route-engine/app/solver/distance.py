import math
import httpx
import structlog
from app.config import get_settings

settings = get_settings()
log      = structlog.get_logger()


async def build_distance_matrix(
    locations: list[tuple[float, float]]
) -> list[list[float]]:
    """
    Get travel time matrix from OSRM Table API.
    locations: list of (lat, lon) tuples — depot at index 0
    Returns: NxN seconds matrix
    """
    if len(locations) < 2:
        return [[0]]

    # OSRM expects lon,lat order
    coords = ';'.join(f'{lon},{lat}' for lat, lon in locations)
    url    = f'{settings.osrm_base_url}/table/v1/driving/{coords}'

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params={'annotations': 'duration'})
            resp.raise_for_status()
            data = resp.json()
            if data.get('code') == 'Ok':
                log.info('osrm.matrix.built', size=len(locations))
                return data['durations']
            log.warning('osrm.bad_response', code=data.get('code'))
    except Exception as e:
        log.warning('osrm.unavailable', error=str(e), using='euclidean_fallback')

    return _euclidean_fallback(locations)


def _euclidean_fallback(locations: list[tuple[float, float]]) -> list[list[float]]:
    n = len(locations)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                lat1, lon1 = locations[i]
                lat2, lon2 = locations[j]
                dist_km    = math.sqrt((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) * 111
                matrix[i][j] = dist_km * 120  # assume 30 km/h → seconds
    return matrix
