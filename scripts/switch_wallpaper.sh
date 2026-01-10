#!/bin/bash

WALLPAPER="$1"

wallust run "$WALLPAPER" -C ~/.config/wallust/wallust.toml
x=$(seq 0 .01 1 | shuf | head -n1);
y=$(seq 0 .01 1 | shuf | head -n1);
THUMBNAIL="/tmp/wallpaper_thumb.png"
swww img -o eDP-1 --transition-type outer --transition-pos "$x","$y" --transition-step 60 --transition-duration 1.5 --transition-fps 144 "$WALLPAPER"
pywalfox update
swww img -o HDMI-A-1 --transition-type outer --transition-pos "$x","$y" --transition-step 60 --transition-duration 1.5 --transition-fps 60 "$WALLPAPER"
convert "$WALLPAPER" -resize 1280x720 "$THUMBNAIL"
asusctl aura static -c $(cat ~/rog_colors.txt)
notify-send --hint=string:image-path:"$WALLPAPER"  "Wallpaper changed" "Wallpaper changed to $(basename "$WALLPAPER")"