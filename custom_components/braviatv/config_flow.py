from __future__ import annotations

import logging
from typing import Final

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from homeassistant.components.braviatv.config_flow import (
    BraviaTVConfigFlow as BraviaTVConfigFlowBase,
    CONF_HOST
)
from homeassistant.components.braviatv.const import DOMAIN

from .coordinator import (
    BraviaTVCoordinator, 
    SourceType,
    DEFAULT_ADB_SERVICE_PORT, 
    DEFAULT_ADB_DEVICE_PORT
)

_LOGGER = logging.getLogger(__name__)
UNINSTALLED_TAIL: Final = " (已卸载)"

class BraviaTVConfigFlow(BraviaTVConfigFlowBase, domain=DOMAIN):

    @staticmethod
    @callback
    def async_get_options_flow(entry: config_entries.ConfigEntry):
        return BraviaTVOptionsFlow(entry)
    

class BraviaTVOptionsFlow(config_entries.OptionsFlow):

    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry
        _LOGGER.info(f"config data: {config_entry.data}")

    def _get_app_list(self) -> tuple(dict, list):
        coordinator: BraviaTVCoordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
        current_app_list = [
            item["title"]
            for item in coordinator.source_map.values()
            if item["type"] == SourceType.APP
        ]
        config_app_list = self.config_entry.data.get("app_list", [])
        result = {
            item: item + ("" if item in current_app_list else UNINSTALLED_TAIL)
            for item in config_app_list
        }
        for item in current_app_list:
            result.setdefault(item, item)
        return {
            d[0]: d[1]
            for d in sorted(result.items(), key=lambda d: d[1])
        }, config_app_list

    async def async_step_init(self, user_input=None):
        return await self.async_step_app()

    async def async_step_app(self, user_input=None):
        app_list, selected = self._get_app_list()
        _LOGGER.info(f"app list: {app_list}")
        _LOGGER.info(f"selected: {selected}")
        if user_input is not None:
            data = {
                **self.config_entry.data,
                **user_input
            }
            _LOGGER.debug(user_input)
            data["adb_service_host"] = data.get("adb_service_host", "").strip()
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=data
            )
            return self.async_create_entry(
                title=self.config_entry.title,
                data=data
            )
        data = self.config_entry.data
        data_schema = {
            vol.Optional("app_list", default=selected): cv.multi_select(app_list),
            vol.Optional("adb_service_host", default=data.get("adb_service_host", vol.UNDEFINED)): str,
            vol.Optional("adb_service_port", default=data.get("adb_service_port", DEFAULT_ADB_SERVICE_PORT)): int,
            vol.Optional("adb_device_port", default=data.get("adb_device_port", DEFAULT_ADB_DEVICE_PORT)): int,
        }
        return self.async_show_form(
            step_id='app',
            data_schema=vol.Schema(data_schema),
            description_placeholders={
                "tip": self.config_entry.data[CONF_HOST]
            },
            errors={},
        )