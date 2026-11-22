#!/usr/bin/env sh
HYPRGAMEMODE=$(hyprctl getoption animations:enabled | awk 'NR==1{print $2}')
if [ "$HYPRGAMEMODE" = "true" ] ; then
    hyprctl dispatch "function ()
    hl.config({
        general = {
            gaps_in = 0,
            gaps_out = 0,
            border_size = 0,
        },

        animations = {
            enabled = false,
        },

        decoration = {
            shadow = { enabled = false },
            blur = { enabled = false },
            rounding = 0,
        }
    })
    end
    "
    notify-send "Gamemode [ON]"
    exit
else
    notify-send "Gamemode [OFF]"
    hyprctl dispatch "hl.dsp.reload_config()"
    exit 0
fi
exit 1