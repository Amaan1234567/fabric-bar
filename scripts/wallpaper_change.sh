#!/bin/zsh

# Set the wallpaper directory
WALLPAPER_DIR="$HOME/Pictures/backgrounds"

# Select a random wallpaper
WALLPAPER=$(find "$WALLPAPER_DIR" -type f \( -iname '*.jpg' -o -iname '*.png' -o -iname '*.jpeg' \) | shuf -n 1)

# Check if a wallpaper was found
if [[ -n "$WALLPAPER" ]]; then
    # Set the wallpaper using awww
    wallust run "$WALLPAPER" -C ~/.config/wallust/wallust.toml
    x=$(seq 0 .01 1 | shuf | head -n1);
    y=$(seq 0 .01 1 | shuf | head -n1);
    THUMBNAIL="/tmp/wallpaper_thumb.png"
    cp $WALLPAPER ~/.cache/current_wallpaper.jpg
    awww img -o eDP-1 --transition-type outer --transition-pos "$x","$y" --transition-step 60 --transition-duration 1.25 --transition-fps 144 "$WALLPAPER"
    pywalfox update
    awww img -o HDMI-A-1 --transition-type outer --transition-pos "$x","$y" --transition-step 60 --transition-duration 1.25 --transition-fps 100 "$WALLPAPER"
    convert "$WALLPAPER" -resize 1280x720 "$THUMBNAIL"
    asusctl aura effect static -c $(cat ~/rog_colors.txt)
    pkill -USR2 hyprlock
    # Send notification with thumbnail using swaync
    #swaync-client -rs
    #notify-send "Wallpaper Changed" "New wallpaper: $(basename "$WALLPAPER")" -i "$THUMBNAIL"
    notify-send --hint=string:image-path:"$WALLPAPER"  "Wallpaper changed" "Wallpaper changed to $(basename "$WALLPAPER")"
    # Any other commands that need the wallpaper path can go here
    echo "$(date) - Changed wallpaper to: $wallpaper" >> $HOME/wallpaper_log.txt
fi
