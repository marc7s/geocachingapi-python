from __future__ import annotations
from enum import Enum
from typing import Any, Dict, Optional, TypedDict, List
from dataclasses import dataclass, field
from datetime import datetime
from .utils import try_get_from_dict

class GeocachingApiEnvironmentSettings(TypedDict):
    """Class to represent API environment settings"""
    api_scheme:str
    api_host:str
    api_port: int
    api_base_bath:str

class GeocachingApiEnvironment(Enum):
    """Enum to represent API environment"""
    Staging = 1,
    Production = 2,

@dataclass
class NearbyCachesSetting:
    location: GeocachingCoordinate
    radiusKm: float

class GeocachingSettings:
    """Class to hold the Geocaching Api settings"""
    cache_codes: list[str]
    trackable_codes: list[str]
    environment: GeocachingApiEnvironment
    nearby_caches_setting: NearbyCachesSetting

    def __init__(self, environment:GeocachingApiEnvironment = GeocachingApiEnvironment.Production, trackables: list[str] = [], caches: list[str] = [], nearby_caches_setting: NearbyCachesSetting = None) -> None:
        """Initialize settings"""
        self.trackable_codes = trackables
        self.nearby_caches_setting = nearby_caches_setting
        self.cache_codes = caches

    def set_caches(self, cache_codes: list[str]):
        self.cache_codes = cache_codes

    def set_trackables(self, trackable_codes: list[str]):
        self.trackable_codes = trackable_codes

    def set_nearby_caches_setting(self, setting: NearbyCachesSetting):
        self.nearby_caches_setting = setting

@dataclass
class GeocachingUser:
    """Class to hold the Geocaching user information"""
    reference_code: Optional[str] = None
    username: Optional[str] = None
    find_count: Optional[int] = None
    hide_count: Optional[int] = None
    favorite_points: Optional[int] = None
    souvenir_count: Optional[int] = None
    awarded_favorite_points: Optional[int] = None
    membership_level_id: Optional[int] = None

    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update user from the API result"""
        self.reference_code = try_get_from_dict(data, "referenceCode", self.reference_code)
        self.username = try_get_from_dict(data, "username", self.username)
        self.find_count = try_get_from_dict(data, "findCount", self.find_count)
        self.hide_count = try_get_from_dict(data, "hideCount", self.hide_count)
        self.favorite_points = try_get_from_dict(data, "favoritePoints", self.favorite_points)
        self.souvenir_count = try_get_from_dict(data, "souvenirCount", self.souvenir_count)
        self.awarded_favorite_points = try_get_from_dict(data, "awardedFavoritePoints", self.awarded_favorite_points)
        self.membership_level_id = try_get_from_dict(data, "membershipLevelId", self.membership_level_id)

@dataclass
class GeocachingCoordinate:
    """Class to hold a Geocaching coordinate"""
    latitude: Optional[str] = None
    longitude: Optional[str] = None

    def __init__(self, *, data: Dict[str, Any]) -> GeocachingCoordinate:
        """Constructor for Geocaching coordinates"""
        self.latitude = try_get_from_dict(data, "latitude", None)
        self.longitude = try_get_from_dict(data, "longitude", None)

@dataclass
class GeocachingTrackableJourney:
    """Class to hold Geocaching trackable journey information"""
    coordinates: GeocachingCoordinate = None
    logged_date: Optional[datetime] = None

    def __init__(self, *, data: Dict[str, Any]) -> GeocachingTrackableJourney:
        """Constructor for Geocaching trackable journey"""
        if "coordinates" in data:
            self.coordinates = GeocachingCoordinate(data=data["coordinates"])
        else:
            self.coordinates = None
        self.logged_date = try_get_from_dict(data, "loggedDate", self.logged_date)

    @classmethod
    def from_list(cls, data_list: List[Dict[str, Any]]) -> List[GeocachingTrackableJourney]:
        """Creates a list of GeocachingTrackableJourney instances from an array of data"""
        return [cls(data=data) for data in data_list]

@dataclass
class GeocachingTrackableLog:
    reference_code: Optional[str] = None
    owner: GeocachingUser = None
    text: Optional[str] = None
    log_type: Optional[str] = None
    logged_date: Optional[datetime] = None

    def __init__(self, *, data: Dict[str, Any]) -> GeocachingTrackableLog:
        self.reference_code = try_get_from_dict(data, 'referenceCode',self.reference_code)
        if self.owner is None:
            self.owner = GeocachingUser()
        if 'owner' in data:
            self.owner.update_from_dict(data['owner'])
        else:
            self.owner = None
        self.log_type = try_get_from_dict(data['trackableLogType'], 'name',self.log_type)
        self.logged_date = try_get_from_dict(data, 'loggedDate',self.logged_date)
        self.text = try_get_from_dict(data, 'text',self.text)


@dataclass
class GeocachingTrackable:
    """Class to hold the Geocaching trackable information"""
    reference_code: Optional[str] = None
    name: Optional[str] = None
    holder: GeocachingUser = None
    tracking_number: Optional[str] = None
    kilometers_traveled: Optional[float] = None
    miles_traveled: Optional[float] = None
    current_geocache_code: Optional[str] = None
    current_geocache_name: Optional[str] = None
    latest_journey: Optional[GeocachingTrackableJourney] = None,
    trackable_journeys: Optional[List[GeocachingTrackableJourney]] = field(default_factory=list)

    is_missing: bool = False,
    trackable_type: str = None,
    latest_log: GeocachingTrackableLog = None

    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update trackable from the API"""
        self.reference_code = try_get_from_dict(data, "referenceCode", self.reference_code)
        self.name = try_get_from_dict(data, "name", self.name)
        if data["holder"] is not None:
            if self.holder is None :
                holder = GeocachingUser()
            holder.update_from_dict(data["holder"])
        else:
            holder = None

        self.tracking_number = try_get_from_dict(data, "trackingNumber", self.tracking_number)
        self.kilometers_traveled = try_get_from_dict(data, "kilometersTraveled", self.kilometers_traveled, float)
        self.miles_traveled = try_get_from_dict(data, "milesTraveled", self.miles_traveled, float)
        self.current_geocache_code = try_get_from_dict(data, "currectGeocacheCode", self.current_geocache_code)
        self.current_geocache_name = try_get_from_dict(data, "currentGeocacheName", self.current_geocache_name)
        self.is_missing = try_get_from_dict(data, "isMissing", self.is_missing)
        self.trackable_type = try_get_from_dict(data, "type", self.trackable_type)
        if "trackableLogs" in data and len(data["trackableLogs"]) > 0:
            self.latest_log = GeocachingTrackableLog(data=data["trackableLogs"][0])

@dataclass
class GeocachingCache:
    reference_code: Optional[str] = None
    name: Optional[str] = None
    coordinates: GeocachingCoordinate = None
    favoritePoints: Optional[int] = None
    findCount: Optional[int] = None
    hiddenDate: Optional[datetime.date] = None
    location: Optional[str] = None

    def update_from_dict(self, data: Dict[str, Any]) -> None:
        self.reference_code = try_get_from_dict(data, "referenceCode", self.reference_code)
        self.name = try_get_from_dict(data, "name", self.name)
        self.favoritePoints = try_get_from_dict(data, "favoritePoints", self.favoritePoints, int)
        self.findCount = try_get_from_dict(data, "findCount", self.findCount, int)
        self.hiddenDate = try_get_from_dict(data, "placedDate", self.hiddenDate, lambda d: datetime.date(datetime.fromisoformat(d)))
        
        # Parse the location
        # Returns the location as "State, Country" if either could be parsed
        location_obj: Dict[Any] = try_get_from_dict(data, "location", {})
        location_state: str = try_get_from_dict(location_obj, "state", "Unknown")
        location_country: str = try_get_from_dict(location_obj, "country", "Unknown")
        self.location = None if set([location_state, location_country]) == {"Unknown"} else f"{location_state}, {location_country}"
        
        if "postedCoordinates" in data:
            self.coordinates = GeocachingCoordinate(data=data["postedCoordinates"])
        else:
            self.coordinates = None

class GeocachingStatus:
    """Class to hold all account status information"""
    user: GeocachingUser = None
    trackables: Dict[str, GeocachingTrackable] = None
    nearby_caches: list[GeocachingCache] = []
    tracked_caches: list[GeocachingCache] = []

    def __init__(self):
        """Initialize GeocachingStatus"""
        self.user = GeocachingUser()
        self.trackables = {}
        self.nearby_caches = []
        self.tracked_caches = []

    def update_user_from_dict(self, data: Dict[str, Any]) -> None:
        """Update user from the API result"""
        self.user.update_from_dict(data)

    def update_caches(self, data: Any) -> None:
        """Update caches from the API result"""
        if not any(data):
           pass
        caches: list[GeocachingCache] = []
        for cacheData in data:
            cache = GeocachingCache()
            cache.update_from_dict(cacheData)
            caches.append(cache)
        self.tracked_caches = caches

    def update_trackables_from_dict(self, data: Any) -> None:
        """Update trackables from the API result"""
        if not any(data):
            pass
        for trackable in data:
            reference_code = trackable["referenceCode"]
            if not reference_code in self.trackables.keys():
                self.trackables[reference_code] = GeocachingTrackable()
            self.trackables[reference_code].update_from_dict(trackable)
    
    def update_nearby_caches_from_dict(self, data: Any) -> None:
        """Update nearby caches from the API result"""
        if not any(data):
            pass

        nearby_caches: list[GeocachingCache] = []
        for cacheData in data:
            cache = GeocachingCache()
            cache.update_from_dict(cacheData)
            nearby_caches.append(cache)
        
        self.nearby_caches = nearby_caches
            