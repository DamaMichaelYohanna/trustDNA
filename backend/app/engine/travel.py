"""Impossible Travel & Geographic Velocity Engine.
Uses Haversine spherical trigonometric distance formula.
"""
import math
from typing import Tuple, Optional


def calculate_haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:
    """
    Calculate the great circle distance between two points on Earth in kilometers.
    Radius of Earth: ~6,371 km.
    """
    # Earth radius in kilometers
    r = 6371.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    distance_km = r * c
    return round(distance_km, 2)


def calculate_travel_velocity(
    distance_km: float,
    time_delta_hours: float
) -> Tuple[float, bool]:
    """
    Given distance in kilometers and elapsed time in hours,
    returns (velocity_kmh, is_impossible_travel).
    Threshold for impossible travel: > 800.0 km/h (faster than commercial passenger jet).
    """
    if time_delta_hours <= 0:
        # Concurrent / instantaneous disparate locations
        return float("inf"), distance_km > 50.0

    velocity_kmh = round(distance_km / time_delta_hours, 2)
    is_impossible = velocity_kmh > 800.0
    return velocity_kmh, is_impossible
