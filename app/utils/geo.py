"""
Geographic utilities for SafeAlert
"""
import math
from typing import Tuple, List, Optional


# Earth's radius in kilometers
EARTH_RADIUS_KM = 6371.0


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth using the Haversine formula.
    
    Args:
        lat1: Latitude of point 1 (in degrees)
        lon1: Longitude of point 1 (in degrees)
        lat2: Latitude of point 2 (in degrees)
        lon2: Longitude of point 2 (in degrees)
    
    Returns:
        Distance in kilometers
    """
    # Convert to radians
    lat1_rad = math.radians(float(lat1))
    lat2_rad = math.radians(float(lat2))
    lon1_rad = math.radians(float(lon1))
    lon2_rad = math.radians(float(lon2))
    
    # Differences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine formula
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return EARTH_RADIUS_KM * c


def is_within_radius(
    point_lat: float, 
    point_lon: float, 
    center_lat: float, 
    center_lon: float, 
    radius_km: float
) -> bool:
    """
    Check if a point is within a given radius of a center point.
    
    Args:
        point_lat: Latitude of the point to check
        point_lon: Longitude of the point to check
        center_lat: Latitude of the center point
        center_lon: Longitude of the center point
        radius_km: Radius in kilometers
    
    Returns:
        True if point is within radius, False otherwise
    """
    distance = calculate_distance(point_lat, point_lon, center_lat, center_lon)
    return distance <= radius_km


def get_bounding_box(
    center_lat: float, 
    center_lon: float, 
    radius_km: float
) -> Tuple[float, float, float, float]:
    """
    Calculate a bounding box around a center point.
    Useful for database queries to filter candidates before precise distance calculation.
    
    Args:
        center_lat: Latitude of the center point
        center_lon: Longitude of the center point
        radius_km: Radius in kilometers
    
    Returns:
        Tuple of (min_lat, max_lat, min_lon, max_lon)
    """
    # Approximate degree changes for the given radius
    # 1 degree latitude ≈ 111 km
    lat_delta = radius_km / 111.0
    
    # 1 degree longitude varies with latitude
    lon_delta = radius_km / (111.0 * math.cos(math.radians(float(center_lat))))
    
    min_lat = float(center_lat) - lat_delta
    max_lat = float(center_lat) + lat_delta
    min_lon = float(center_lon) - lon_delta
    max_lon = float(center_lon) + lon_delta
    
    return (min_lat, max_lat, min_lon, max_lon)


def sort_by_distance(
    items: List,
    reference_lat: float,
    reference_lon: float,
    lat_attr: str = 'headquarters_lat',
    lon_attr: str = 'headquarters_lng'
) -> List[Tuple[any, float]]:
    """
    Sort a list of objects by distance from a reference point.
    
    Args:
        items: List of objects with latitude/longitude attributes
        reference_lat: Reference point latitude
        reference_lon: Reference point longitude
        lat_attr: Name of the latitude attribute on the objects
        lon_attr: Name of the longitude attribute on the objects
    
    Returns:
        List of tuples (item, distance_km) sorted by distance ascending
    """
    results = []
    
    for item in items:
        item_lat = getattr(item, lat_attr, None)
        item_lon = getattr(item, lon_attr, None)
        
        if item_lat is not None and item_lon is not None:
            distance = calculate_distance(reference_lat, reference_lon, float(item_lat), float(item_lon))
            results.append((item, distance))
    
    # Sort by distance (ascending)
    results.sort(key=lambda x: x[1])
    
    return results


def filter_by_distance(
    items: List,
    reference_lat: float,
    reference_lon: float,
    max_distance_km: float,
    lat_attr: str = 'headquarters_lat',
    lon_attr: str = 'headquarters_lng'
) -> List[Tuple[any, float]]:
    """
    Filter items by maximum distance and return sorted by distance.
    
    Args:
        items: List of objects with latitude/longitude attributes
        reference_lat: Reference point latitude
        reference_lon: Reference point longitude
        max_distance_km: Maximum distance in kilometers
        lat_attr: Name of the latitude attribute on the objects
        lon_attr: Name of the longitude attribute on the objects
    
    Returns:
        List of tuples (item, distance_km) for items within max_distance, sorted ascending
    """
    all_sorted = sort_by_distance(items, reference_lat, reference_lon, lat_attr, lon_attr)
    return [(item, dist) for item, dist in all_sorted if dist <= max_distance_km]


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the initial bearing from point 1 to point 2.
    
    Args:
        lat1: Latitude of starting point
        lon1: Longitude of starting point
        lat2: Latitude of destination point
        lon2: Longitude of destination point
    
    Returns:
        Bearing in degrees (0-360, where 0 is north)
    """
    lat1_rad = math.radians(float(lat1))
    lat2_rad = math.radians(float(lat2))
    dlon_rad = math.radians(float(lon2) - float(lon1))
    
    x = math.sin(dlon_rad) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad)
    
    bearing_rad = math.atan2(x, y)
    bearing_deg = math.degrees(bearing_rad)
    
    # Normalize to 0-360
    return (bearing_deg + 360) % 360


def get_compass_direction(bearing: float) -> str:
    """
    Convert a bearing to a compass direction.
    
    Args:
        bearing: Bearing in degrees (0-360)
    
    Returns:
        Compass direction string (N, NE, E, SE, S, SW, W, NW)
    """
    directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    index = round(bearing / 45) % 8
    return directions[index]


def estimate_travel_time_minutes(distance_km: float, speed_kmh: float = 40.0) -> float:
    """
    Estimate travel time based on distance and average speed.
    
    Args:
        distance_km: Distance in kilometers
        speed_kmh: Average speed in km/h (default: 40 for urban emergency response)
    
    Returns:
        Estimated travel time in minutes
    """
    if distance_km <= 0 or speed_kmh <= 0:
        return 0.0
    
    hours = distance_km / speed_kmh
    return hours * 60


def format_distance(distance_km: float) -> str:
    """
    Format distance for display.
    
    Args:
        distance_km: Distance in kilometers
    
    Returns:
        Formatted string (e.g., "2.5 km" or "500 m")
    """
    if distance_km < 1:
        meters = int(distance_km * 1000)
        return f"{meters} m"
    else:
        return f"{distance_km:.1f} km"


def generate_google_maps_url(lat: float, lon: float) -> str:
    """
    Generate a Google Maps URL for a location.
    
    Args:
        lat: Latitude
        lon: Longitude
    
    Returns:
        Google Maps URL string
    """
    return f"https://www.google.com/maps?q={lat},{lon}"


def generate_navigation_url(
    from_lat: float, 
    from_lon: float, 
    to_lat: float, 
    to_lon: float
) -> str:
    """
    Generate a Google Maps navigation URL.
    
    Args:
        from_lat: Starting latitude
        from_lon: Starting longitude
        to_lat: Destination latitude
        to_lon: Destination longitude
    
    Returns:
        Google Maps directions URL string
    """
    return f"https://www.google.com/maps/dir/{from_lat},{from_lon}/{to_lat},{to_lon}"

