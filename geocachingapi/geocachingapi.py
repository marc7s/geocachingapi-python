"""Class for managing one Geocaching API integration."""
from __future__ import annotations

import asyncio
import json
import logging
import socket
import async_timeout
import backoff

from yarl import URL
from aiohttp import ClientResponse, ClientSession, ClientError

from typing import Any, Awaitable, Callable, Dict, Optional
from .const import ENVIRONMENT_SETTINGS, CACHE_FIELDS_PARAMETER
from .exceptions import (
    GeocachingApiConnectionError,
    GeocachingApiConnectionTimeoutError,
    GeocachingApiError,
    GeocachingApiRateLimitError,
)

from .models import (
    GeocachingCoordinate,
    GeocachingStatus,
    GeocachingSettings,
    GeocachingApiEnvironment,
    GeocachingApiEnvironmentSettings,
    GeocachingTrackableJourney
)

_LOGGER = logging.getLogger(__name__)

class GeocachingApi:
    """ Main class to control the Geocaching API"""
    _close_session: bool = False
    _status: GeocachingStatus = None
    _settings: GeocachingSettings = None
    _environment_settings: GeocachingApiEnvironmentSettings = None
    def __init__(
        self,
        *,
        environment: GeocachingApiEnvironment,
        token: str,
        settings: GeocachingSettings = None,
        request_timeout: int = 8,
        session: Optional[ClientSession] = None,
        token_refresh_method: Optional[Callable[[], Awaitable[str]]] = None
       
    ) -> None:
        """Initialize connection with the Geocaching API."""
        self._environment_settings = ENVIRONMENT_SETTINGS[environment]
        self._status = GeocachingStatus()
        self._settings = settings or GeocachingSettings(False)
        self._session = session
        self.request_timeout = request_timeout
        self.token = token
        self.token_refresh_method = token_refresh_method

    @backoff.on_exception(backoff.expo, GeocachingApiConnectionError, max_tries=3, logger=_LOGGER)
    @backoff.on_exception(
        backoff.expo, GeocachingApiRateLimitError, base=60, max_tries=6, logger=_LOGGER
    )
    async def _request(self, method, uri, **kwargs) -> ClientResponse:
        """Make a request."""
        if self.token_refresh_method is not None:
            self.token = await self.token_refresh_method()
            _LOGGER.debug(f'Token refresh method called.')
        
        url = URL.build(
            scheme=self._environment_settings["api_scheme"],
            host=self._environment_settings["api_host"],
            port=self._environment_settings["api_port"],
            path=self._environment_settings["api_base_bath"],
        ) 
        url = str(url) + uri
        _LOGGER.debug(f'Executing {method} API request to {url}.')
        headers = kwargs.get("headers")

        if headers is None:
            headers = {}
        else:
            headers = dict(headers)

        headers["Authorization"] = f"Bearer {self.token}"
        _LOGGER.debug(f'With headers:')
        _LOGGER.debug(f'{str(headers)}')
        if self._session is None:
            self._session = ClientSession()
            _LOGGER.debug(f'New session created.')
            self._close_session = True

        try:
            async with async_timeout.timeout(self.request_timeout):
                response =  await self._session.request(
                    method,
                    f"{url}",
                    **kwargs,
                    headers=headers,
                )
        except asyncio.TimeoutError as exception:
            raise GeocachingApiConnectionTimeoutError(
                "Timeout occurred while connecting to the Geocaching API"
            ) from exception
        except (ClientError, socket.gaierror) as exception:
            raise GeocachingApiConnectionError(
                "Error occurred while communicating with the Geocaching API"
            ) from exception
        
        content_type = response.headers.get("Content-Type", "")
        # Error handling
        if (response.status // 100) in [4, 5]:
            contents = await response.read()
            response.close()

            if response.status == 429:
                raise GeocachingApiRateLimitError(
                    "Rate limit error has occurred with the Geocaching API"
                )

            if content_type == "application/json":
                raise GeocachingApiError(response.status, json.loads(contents.decode("utf8")))
            raise GeocachingApiError(response.status, {"message": contents.decode("utf8")})
        
        # Handle empty response
        if response.status == 204:
            _LOGGER.warning(f'Request to {url} resulted in status 204. Your dataset could be out of date.')
            return
        
        if "application/json" in content_type:
            result =  await response.json()
            _LOGGER.debug(f'Response:')
            _LOGGER.debug(f'{str(result)}')
            return result
        result =  await response.text()
        _LOGGER.debug(f'Response:')
        _LOGGER.debug(f'{str(result)}')
        return result

    async def update(self) -> GeocachingStatus:
        await self._update_user()
        if len(self._settings.tracked_trackable_codes) > 0:
            await self._update_trackables()
        if self._settings.nearby_caches_setting is not None and self._settings.nearby_caches_setting.max_count > 0:
            await self._update_nearby_caches()
        if len(self._settings.tracked_cache_codes) > 0:
            await self._update_tracked_caches()

        _LOGGER.info(f'Status updated.')
        return self._status

    async def _update_tracked_caches(self, data: Dict[str, Any] = None) -> None:
        assert self._status
        if data is None:
            cache_codes = ",".join(self._settings.tracked_cache_codes)
            data = await self._request("GET", f"/geocaches?referenceCodes={cache_codes}&fields={CACHE_FIELDS_PARAMETER}&lite=true")
        self._status.update_caches(data)
        _LOGGER.debug(f'Tracked caches updated.')

    async def _update_user(self, data: Dict[str, Any] = None) -> None:
        assert self._status
        if data is None:
            fields = ",".join([
                "username",
                "referenceCode",
                "findCount",
                "hideCount",
                "favoritePoints",
                "souvenirCount",
                "awardedFavoritePoints",
                "membershipLevelId"
            ])
            data = await self._request("GET", f"/users/me?fields={fields}")
        self._status.update_user_from_dict(data)
        _LOGGER.debug(f'User updated.')

    async def _update_trackables(self, data: Dict[str, Any] = None) -> None:
        assert self._status
        if data is None:
            fields = ",".join([
                "referenceCode",
                "name",
                "holder",
                "owner",
                "releasedDate",
                "trackingNumber",
                "kilometersTraveled",
                "milesTraveled",
                "currentGeocacheCode",
                "currentGeocacheName",
                "isMissing",
                "type"
            ])
            trackable_parameters = ",".join(self._settings.tracked_trackable_codes)
            data = await self._request("GET", f"/trackables?referenceCodes={trackable_parameters}&fields={fields}&expand=trackablelogs:1")
        self._status.update_trackables_from_dict(data)
        
        # Update trackable journeys
        if len(self._status.trackables) > 0:
            for trackable in self._status.trackables.values():
                fields = ",".join([
                    "referenceCode",
                    "geocacheName",
                    "loggedDate",
                    "coordinates",
                    "url",
                    "owner"
                ])
                max_log_count: int = 10
                
                # Only fetch logs related to movement
                # Reference: https://api.groundspeak.com/documentation#trackable-log-types
                logTypes: list[int] = ",".join([
                    "14", # Dropped Off
                    "15" # Transfer
                ])
                trackable_journey_data = await self._request("GET",f"/trackables/{trackable.reference_code}/trackablelogs?fields={fields}&logTypes={logTypes}&take={max_log_count}")

                if trackable_journey_data:
                    # Create a list of GeocachingTrackableJourney instances
                    journeys = await GeocachingTrackableJourney.from_list(trackable_journey_data)
                    
                    # Calculate distances between journeys
                    # The journeys are sorted in order, so reverse it to iterate backwards
                    j_iter = iter(reversed(journeys))
                    curr_journey: GeocachingTrackableJourney | None = next(j_iter)
                    prev_journey: GeocachingTrackableJourney | None = None
                    while True:
                        if curr_journey is None:
                            break
                        prev_journey = next(j_iter, None)
                        if prev_journey is None:
                            curr_journey.distance_km = 0
                            break
                        
                        curr_journey.distance_km = GeocachingCoordinate.get_distance_km(prev_journey.coordinates, curr_journey.coordinates)
                        curr_journey = prev_journey

                    trackable.journeys = journeys

                    # Set the trackable coordinates to that of the latest log
                    trackable.coordinates = journeys[-1].coordinates

        _LOGGER.debug(f'Trackables updated.')

    async def _update_nearby_caches(self, data: Dict[str, Any] = None) -> None:
        assert self._status
        if self._settings.nearby_caches_setting is None:
            _LOGGER.warning("Cannot update nearby caches, setting has not been configured.")
            return
        
        if data is None:
            coordinates: GeocachingCoordinate = self._settings.nearby_caches_setting.location
            radiusM: int = round(self._settings.nearby_caches_setting.radius_km * 1000)
            maxCount: int = min(max(self._settings.nearby_caches_setting.max_count, 0), 100) # Take range is 0-100 in API
            URL = f"/geocaches/search?q=location:[{coordinates.latitude},{coordinates.longitude}]+radius:{radiusM}m&fields={CACHE_FIELDS_PARAMETER}&take={maxCount}&sort=distance+&lite=true"
            # The + sign is not encoded correctly, so we encode it manually
            data = await self._request("GET", URL.replace("+", "%2B"))
        self._status.update_nearby_caches_from_dict(data)

        _LOGGER.debug(f'Nearby caches updated.')

    async def update_settings(self, settings: GeocachingSettings):
        """Update the Geocaching settings"""
        self._settings = settings
        
    async def close(self) -> None:
        """Close open client session."""
        if self._session and self._close_session:
            await self._session.close()
            _LOGGER.debug(f'Session closed.')
    
    async def __aenter__(self) -> GeocachingApi:
        """Async enter."""
        return self
    
    async def __aexit__(self, *exc_info) -> None:
        """Async exit."""
        await self.close()
        