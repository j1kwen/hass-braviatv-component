from homeassistant.components.braviatv import (
    HomeAssistant,
    ConfigEntry,
    CookieJar,
    BraviaClient,
    update_listener,
    async_create_clientsession,
    async_unload_entry as async_unload_entry_base,
    CONF_HOST,
    CONF_MAC,
    DOMAIN,
    PLATFORMS
)

from .coordinator import BraviaTVCoordinator

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    host = config_entry.data[CONF_HOST]
    mac = config_entry.data[CONF_MAC]

    session = async_create_clientsession(
        hass, cookie_jar=CookieJar(unsafe=True, quote_cookie=False)
    )
    client = BraviaClient(host, mac, session=session)
    coordinator = BraviaTVCoordinator(
        hass=hass,
        client=client,
        config=config_entry.data,
    )
    config_entry.async_on_unload(config_entry.add_update_listener(update_listener))

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await async_unload_entry_base(hass, config_entry)