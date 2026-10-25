from loguru import logger
from gi.repository import Playerctl, Gdk  # type: ignore
from fabric.widgets.stack import Stack
from fabric.utils.helpers import cooldown
from modules.mpris.mpris_player import MprisPlayer
from services.playerctlservice import SimplePlayerctlService, Player
from custom_widgets.HackedStackRevealer import HackedStack


class MprisPlayerStack(Stack):
    """mpris popup widget which shows more song details, progressbar and controls"""

    def __init__(self, **kwargs):
        super().__init__(
            name="mpris-stack",
            transition_type="slide-left-right",
            **kwargs
        )
        self.add_events("scroll")
        
        # CRITICAL: Enable smooth scroll events for trackpad two-finger swipes
        self.add_events(Gdk.EventMask.SMOOTH_SCROLL_MASK)

        self._service = SimplePlayerctlService()
        self.players = {}
        self._visible_child_index = 0
        self._service.manager.connect("name-appeared", self._add_player)
        self._service.manager.connect("name-vanished", self._remove_player)
        self._create_players()

        self.connect("scroll-event", self._on_scroll_handler)

    def _create_players(self):
        players: dict[str, Player] = self._service.players
        for _, player in players.items():
            mpris_player = MprisPlayer(player)
            self.add(mpris_player)
            self.players[player.name] = mpris_player
            player.connect(
                "changed",
                lambda player: self.set_visible_child(self.players[player.name]),
            )

    def _add_player(self, _, player_name: Playerctl.PlayerName):
        name = player_name.name
        new_player = MprisPlayer(self._service.players[name])
        logger.info(f"added {name} player")
        self.players[name] = new_player
        self.set_visible_child(new_player)
        self.add(new_player)

    def _remove_player(self, _, player_name: Playerctl.PlayerName):
        logger.info(f"deleted {player_name.name} player")
        if len(self.players) == 0:
            return
        widget = self.players.pop(player_name.name)
        self.remove(widget)

    @cooldown(0.2)
    def _on_scroll_handler(self, _, event):
        if len(self.children) == 0:
            return

        # Parse smooth scroll deltas for trackpad two-finger swipes
        success, dx, dy = event.get_scroll_deltas()

        if success:
            # Use horizontal movement (dx) for left/right swipes, vertical (dy) otherwise
            delta = dx if abs(dx) > abs(dy) else dy
            direction_offset = 1 if delta > 0 else -1
        else:
            # Fall back to your working mouse wheel logic
            direction_offset = -1 if event.direction in (0, 2) else 1

        self._visible_child_index = (
            self._visible_child_index + direction_offset
        ) % len(self.children)

        return self.set_visible_child(self.children[self._visible_child_index])