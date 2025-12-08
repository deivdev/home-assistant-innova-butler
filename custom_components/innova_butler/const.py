"""Constants for Innova Butler integration."""
from homeassistant.const import Platform

DOMAIN = "innova_butler"

PLATFORMS: list[Platform] = [Platform.CLIMATE]

CONF_HOST = "host"

# Default values
DEFAULT_NAME = "Innova Butler"


