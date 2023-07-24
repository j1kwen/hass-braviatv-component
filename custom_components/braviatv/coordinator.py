"""Update coordinator for Bravia TV integration."""
from __future__ import annotations

import logging
import traceback
import re
from types import MappingProxyType
from typing import Any, Final

from pybravia import BraviaClient

from homeassistant.components.media_player import MediaType
from homeassistant.core import HomeAssistant

from homeassistant.components.braviatv.coordinator import (
    SourceType,
    BraviaTVCoordinator as BraviaTVCoordinatorBase,
    catch_braviatv_errors,
    SCAN_INTERVAL as SCAN_INTERVAL_ORIG,
)

_LOGGER = logging.getLogger(__name__)
try:
    import adbutils
except:
    _LOGGER.error("adbutils not found.")

DEFAULT_ADB_SERVICE_PORT: Final = 5037
DEFAULT_ADB_DEVICE_PORT: Final = 5555
DEFAULT_APP_NAME: Final = "Smart TV"
SCAN_INTERVAL = SCAN_INTERVAL_ORIG 

class BraviaTVCoordinator(BraviaTVCoordinatorBase):
    """Representation of a Bravia TV Coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: BraviaClient,
        config: MappingProxyType[str, Any],
    ) -> None:
        """Initialize Bravia TV Client."""
        super().__init__(hass, client, config)
        self.app_list = config.get("app_list", [])
        self.adb_service_host = config.get("adb_service_host")
        self.adb_service_port = config.get("adb_service_port", DEFAULT_ADB_SERVICE_PORT)
        self.adb_device_port = config.get("adb_device_port", DEFAULT_ADB_DEVICE_PORT)
        self.adb_serial = f"{self.client.host}:{self.adb_device_port}"
        self.adb = None

    async def _get_current_top_window(self) -> str:
        if not self.adb_service_host:
            _LOGGER.info("adb service has not been configurated.")
            return DEFAULT_APP_NAME
        try:
            if self.adb is None:
                _LOGGER.info(f"create an adb client {self.adb_service_host}:{self.adb_service_port}")
                self.adb = adbutils.AdbClient(host=self.adb_service_host, port=self.adb_service_port)
            device = None 
            for item in self.adb.device_list():
                if item.serial == self.adb_serial:
                    device = item
                    break
            if not device:
                if not (ret := self.adb.connect(self.adb_serial)).startswith("connected to "):
                    _LOGGER.error(ret)
                    self.adb.disconnect(self.adb_serial)
                    return DEFAULT_APP_NAME
                device = self.adb.device(self.adb_serial)
            dump_msg = device.shell("dumpsys window | grep mTopFullscreenOpaqueWindowState")
            top_package = re.search(r"=Window\{(\w+\s+){2}(.*?)/", dump_msg).group(2)
            _LOGGER.info(f"Current top window package: {top_package}")
            for uri, item in self.source_map.items():
                if uri.find(top_package) > -1:
                    _LOGGER.info("Current APP: " + (title := item['title']))
                    return title
            _LOGGER.info(f"package {top_package} not found")
        except (ConnectionRefusedError, OSError, RuntimeError) as e:
            _LOGGER.error(f"{self.adb_service_host}:{self.adb_service_port} {e}")
        except Exception as e:
            _LOGGER.error(traceback.format_exc())
        return DEFAULT_APP_NAME

    async def async_update_sources(self) -> None:
        """Update all sources."""
        await super().async_update_sources()
        self.source_list.extend(sorted(self.app_list))

    async def async_update_playing(self) -> None:
        """Update current playing information."""
        await super().async_update_playing()
        if self.media_content_type == MediaType.APP:
            _LOGGER.info(f"Current playing source is APP, trying get the package info from adb...")
            self.media_title = await self._get_current_top_window()
            self.source = self.media_title

    @catch_braviatv_errors
    async def async_select_source(self, source: str) -> None:
        """Set the input source."""
        try:
            await self.async_source_find(source, SourceType.INPUT)
        except ValueError:
            _LOGGER.info(f"{source} is not INPUT type, try APP type.")
            await self.async_source_find(source, SourceType.APP)
