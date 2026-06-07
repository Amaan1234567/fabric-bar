"""A simple data holder class that can be used to store application-wide services and data."""

from dataclasses import dataclass
from services.notification_service import NotificationService
from services.playerctlservice import SimplePlayerctlService
from services.networkservice import NetworkService


@dataclass
class Data:
    """Holds application-wide services."""

    notification_service: NotificationService
    playerctl_service: SimplePlayerctlService
    network_service: NetworkService
