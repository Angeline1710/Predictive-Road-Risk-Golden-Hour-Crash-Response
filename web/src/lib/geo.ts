/** Distance from ([lat],[lon]) to the *nearest vertex* of [geometry]
 * ([lon, lat] pairs), not a true point-to-segment projection along the
 * polyline. Mirrors android/.../ui/drivemode/NearbySegment.kt's
 * `distanceToNearestVertexM` exactly -- same proxy, same reasoning: a
 * real "distance along the route" needs `/risk/route` (PRD.md §10.2
 * lists it as not implemented) or client-side map-matching, neither of
 * which this pass builds. Good enough to order "what's nearby the
 * corridor anchor," not to claim an exact route-km marker. */
export function distanceToNearestVertexKm(lat: number, lon: number, geometry: [number, number][]): number {
  let min = Infinity;
  for (const [vLon, vLat] of geometry) {
    const d = haversineKm(lat, lon, vLat, vLon);
    if (d < min) min = d;
  }
  return min;
}

const EARTH_RADIUS_KM = 6371;

function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return EARTH_RADIUS_KM * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function toRad(deg: number): number {
  return (deg * Math.PI) / 180;
}
