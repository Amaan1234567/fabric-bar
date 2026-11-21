"""A simple data holder class that can be used to store application-wide services and data."""

from dataclasses import dataclass

from services.network_service import NetworkService
from services.notification_service import NotificationService
from services.playerctl_service import SimplePlayerctlService


@dataclass
class Data:
    """Holds application-wide services."""

    notification_service: NotificationService
    playerctl_service: SimplePlayerctlService
    network_service: NetworkService
