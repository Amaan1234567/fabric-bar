"""holds the playerctl service"""

import os
from fabric import Property
from fabric.core.service import Service, Signal
from loguru import logger
from gi.repository import Playerctl  # type: ignore


class Player(Service):
    """mpris player service"""

    @Signal
    def changed(self) -> None:
        """signal to request focus"""

    def __init__(self, player: Playerctl.Player, **kwargs):
        super().__init__(**kwargs)
        self._player = player
        self._connect_player_signals_with_emits(player)
        self.temp_art_path = None

    @Property(str, "readable")
    def name(self):
        """property to get name of player"""
        return self._player.props.player_name

    def _emit_update(self, _, __):
        self.emit("changed")

    def _connect_player_signals_with_emits(self, player) -> None:
        signals = [
            "metadata",
            "loop-status",
            "seeked",
            "shuffle",
            "playback-status::playing",
            "playback-status::paused",
            "playback-status::ended",
        ]
        for signal_name in signals:
            player.connect(signal_name, self._emit_update)

    def get_metadata(self):
        """Get metadata for player (or first available player if None)"""

        try:
            metadata = self._player.props.metadata
            if not metadata:
                return None

            # Extract basic info
            # print(metadata)
            title = self._get_variant_string(metadata.lookup_value("xesam:title", None))
            artist = self._get_variant_artist(
                metadata.lookup_value("xesam:artist", None)
            )
            album = self._get_variant_string(metadata.lookup_value("xesam:album", None))
            art_url = self._get_variant_string(
                metadata.lookup_value("mpris:artUrl", None)
            )
            length = self._get_variant_int(metadata.lookup_value("mpris:length", None))
            # print(length)
            return {
                "title": title,
                "artist": artist,
                "album": album,
                "art_url": art_url,
                "length": (
                    length / 1000000 if length is not None and length > 0 else 0
                ),  # Convert to seconds
                "player_name": self._player.props.player_name,
            }
        except Exception as exception:
            logger.exception(f"Exception encountered in Playerctl: {exception} ")
            return None

    def get_position(self):
        """Get current position in seconds"""
        try:
            position = self._player.props.position
            # print("position: ",position)
            return position / 1000000 if position > 0 else 0  # Convert to seconds
        except Exception as exception:
            logger.exception(f"Exception encountered in Playerctl: {exception} ")
            return 0

    def set_position(self, position):
        """set given position(time in seconds) in player"""

        try:
            player: Playerctl.Player = self._player
            player.set_position(int(position * 1e6))
        except Exception as exception:
            logger.exception(f"Exception encountered in Playerctl: {exception} ")

    def get_status(self):
        """Get playback status"""

        try:
            status = self._player.props.playback_status
            if hasattr(status, "value_nick"):
                return status.value_nick.lower()
            else:
                return str(status).rsplit(".", maxsplit=1)[-1].lower()
        except Exception as exception:
            logger.exception(f"Exception encountered in Playerctl: {exception} ")
            return "stopped"

    def get_shuffle(self):
        """Get shuffle status"""
        try:
            return bool(self._player.props.shuffle)
        except Exception as exception:
            logger.exception(f"Exception encountered in Playerctl: {exception} ")

    def get_loop(self):
        """Get loop status"""

        try:
            loop_status = self._player.props.loop_status
            if hasattr(loop_status, "value_nick"):
                return loop_status.value_nick.lower()  # type: ignore
            else:
                return str(loop_status).rsplit(".", maxsplit=1)[-1].lower()
        except Exception as exception:
            logger.exception(f"Exception encountered in Playerctl: {exception} ")
            return "none"

    # Control methods
    def play_pause(self):
        """Toggle play/pause"""

        try:
            self._player.play_pause()
            return True
        except Exception as exception:
            logger.exception(f"Exception encountered in Playerctl: {exception} ")
            return False

    def next_track(self):
        """Next track"""

        try:
            self._player.next()
            return True
        except Exception as exception:
            logger.exception(f"Exception encountered in Playerctl: {exception} ")
            return False

    def previous_track(self):
        """Previous track"""

        try:
            self._player.previous()
            return True
        except Exception as exception:
            logger.exception(f"Exception encountered in Playerctl: {exception} ")
            return False

    def toggle_shuffle(self):
        """Toggle shuffle"""

        try:
            current = self._player.props.shuffle
            self._player.set_shuffle(not current)
            return True
        except Exception as exception:
            logger.exception(f"Exception encountered in Playerctl: {exception} ")
            return False

    def cycle_loop(self):
        """Cycle loop mode"""

        try:
            current = self._player.props.loop_status
            if current == Playerctl.LoopStatus.NONE:
                new_status = Playerctl.LoopStatus.PLAYLIST
            elif current == Playerctl.LoopStatus.PLAYLIST:
                new_status = Playerctl.LoopStatus.TRACK
            else:
                new_status = Playerctl.LoopStatus.NONE

            self._player.set_loop_status(new_status)
            return True
        except Exception as exception:
            logger.exception(f"Exception encountered in Playerctl: {exception} ")
            return False

    def _cleanup_temp(self):
        """Clean up temp files"""
        if self.temp_art_path and os.path.isfile(self.temp_art_path):
            try:
                os.remove(self.temp_art_path)
            except Exception as exception:
                logger.exception(f"Exception encountered in Playerctl: {exception} ")

            self.temp_art_path = None

    # Helper methods for variant conversion
    def _get_variant_string(self, variant):
        """Convert variant to string"""
        if variant is None:
            return ""
        try:
            return str(variant.get_string())
        except Exception as exception:
            logger.exception(f"Exception encountered in Playerctl: {exception} ")

            try:
                return str(variant.unpack())
            except TypeError as type_error:
                logger.exception(f"Exception encountered in Playerctl: {type_error} ")
                return ""

    def _get_variant_artist(self, variant):
        """Convert variant to artist string (handle arrays)"""
        if variant is None:
            return ""
        try:
            artist_data = variant.unpack()
            if isinstance(artist_data, list) and len(artist_data) > 0:
                return str(artist_data[0])
            else:
                return str(artist_data)
        except Exception as exception:
            logger.exception(f"Exception encountered in Playerctl: {exception} ")
            return self._get_variant_string(variant)

    def _get_variant_int(self, variant):
        """Convert variant to int - FIXED for uint64"""
        if variant is None:
            return 0
        try:
            # First try to unpack - this should work for any variant type
            value = variant.unpack()
            return int(value)
        except Exception as exception:
            logger.exception(f"Exception encountered in Playerctl: {exception} ")

            try:
                # Fallback: try different getter methods
                if hasattr(variant, "get_uint64"):
                    return int(variant.get_uint64())
                elif hasattr(variant, "get_int64"):
                    return int(variant.get_int64())
                # ... other types
            except TypeError as type_error:
                logger.exception(f"Exception encountered in Playerctl: {type_error} ")
                return 0


class SimplePlayerctlService(Service):
    """Simple, lightweight service for MPRIS players"""

    @Signal
    def changed(self) -> None:
        """signal to show state-change"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.manager: Playerctl.PlayerManager = Playerctl.PlayerManager()
        self.current_player: None | Player = None
        self._players: dict[str, Player] = {}
        # Discover existing players
        self._discover_players()

        # Connect manager signals
        self.manager.connect("name-appeared", self._on_player_appeared)
        self.manager.connect("name-vanished", self._on_player_vanished)

    @Property(dict, "read-write")
    def players(self) -> dict:
        """property to access players"""
        return self._players

    def _discover_players(self):
        """Find all available players"""
        for name in self.manager.props.player_names:  # type: ignore
            logger.info(f"player found: {name.name}")
            if name.name not in self._players:
                try:
                    player = Playerctl.Player.new_from_name(name)
                    player = Player(player)
                    self._players[name.name] = player
                    player.connect("changed", self._update_current_player)
                except Exception as exception:
                    logger.debug(f"Exception encountered in Playerctl: {exception} ")
        if len(self._players) != 0:
            first_player_name = list(self._players.keys())[0]
            logger.debug(first_player_name)
            self.current_player = self._players[first_player_name]

    def _on_player_appeared(self, _, name):
        """Handle new player"""
        logger.info(f"adding_player {name.name}")

        if name.name not in self._players:
            try:
                player = Playerctl.Player.new_from_name(name)
                player = Player(player)
                self._players[name.name] = player
                self.current_player = player
                player.connect("changed", self._update_current_player)
                self.emit("changed")
            except Exception as exception:
                logger.exception(f"Exception encountered in Playerctl: {exception} ")

    def _update_current_player(self, player: Player):
        self.current_player = player
        logger.info(f"mpris player {player.name} state changed")
        self.emit("changed")

    def _on_player_vanished(self, _, player):
        """Handle player disappearing"""
        logger.info(f"player {player.name} vanished")

        player_name = player.name
        if player_name in self._players:
            self._players.pop(player_name)
        if len(self._players) == 0:
            self.current_player = None
            self.emit("changed")
            return
        first_player_name = list(self._players.keys())[0]
        self.current_player = self._players[first_player_name]
        self.emit("changed")

    def get_players_names(self):
        """Get list of all player names"""
        return list(self._players.keys())
