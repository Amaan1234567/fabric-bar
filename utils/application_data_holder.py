from dataclasses import dataclass
from modules.control_center.control_center import ControlCenter
from services.notification_service import NotificationService
from services.playerctlservice import SimplePlayerctlService
from services.networkservice import NetworkService


@dataclass
class Data:
    """Holds application-wide services."""

    notification_service: NotificationService
    playerctl_service: SimplePlayerctlService
    network_service: NetworkService
    control_center: ControlCenter
