#!/bin/bash
# playerctl_get.sh
# This script retrieves various metadata fields from playerctl.
# It supports commands:
#   title    - current song title.
#   artist   - current song’s artist.
#   length   - total track length (in minutes with an "m" suffix).
#   status   - playback status.
#   trackid  - track id.
#   cover    - downloads album art to /tmp/cover.jpeg and outputs its path.
#   progress - outputs the current track position and total length in mm:ss/mm:ss format.
#
# Usage: ./playerctl_get.sh <command>

# Make sure playerctl is installed.
if ! command -v playerctl >/dev/null; then
    echo "playerctl not found" >&2
    exit 1
fi

COMMAND="$1"

case "$COMMAND" in
    title)
        output=$(playerctl metadata --format "{{ title }}" 2>/dev/null | cut -c 1-20)
        ;;
    artist)
        output=$(playerctl metadata --format "{{ xesam:artist }}" 2>/dev/null | cut -c 1-40)
        ;;
    length)
        meta=$(playerctl metadata --format "{{ mpris:length }}" 2>/dev/null | xargs)
        if [[ -n "$meta" && "$meta" =~ ^[0-9]+$ ]]; then
            # Divide by 60000000 to get length in minutes.
            minutes=$(( meta / 60000000 ))
            output="${minutes}m"
        else
            output=""
        fi
        ;;
    status)
        output=$(playerctl status 2>/dev/null)
        ;;
    trackid)
        output=$(playerctl metadata --format "{{ mpris:trackid }}" 2>/dev/null)
        ;;
    cover)
        # Retrieve album art URL (for Spotify, adjust as needed).
        artUrl=$(playerctl metadata --format "{{ mpris:artUrl }}" 2>/dev/null | xargs)
        if [[ -z "$artUrl" ]]; then
            output="/home/amaan/Pictures/blank.jpeg"
        else
            tmpfile="/home/amaan/.cache/cover.jpeg"
            # Download album art; use -L to follow any redirects.
            curl -sL "$artUrl" -o "$tmpfile"
            if [[ $? -eq 0 && -s "$tmpfile" ]]; then
                magick "$tmpfile" -gravity center -extent "1:1" "$tmpfile"
                output="$tmpfile"
            fi
        fi
        ;;
    progress)
        # Retrieve current position (in seconds) and total length (in microseconds)
        pos=$(playerctl position 2>/dev/null)
        raw_length=$(playerctl metadata --format "{{ mpris:length }}" 2>/dev/null | xargs)
        # Ensure pos is a number (in seconds) and raw_length is numeric.
        if [[ -z "$pos" || -z "$raw_length" || ! "$raw_length" =~ ^[0-9]+$ ]]; then
            output=""
        else
            # Round the current position to an integer (seconds)
            cur_sec=$(printf "%.0f" "$pos")
            # Convert total length from microseconds to seconds.
            total_sec=$(( raw_length / 1000000 ))
            # Compute minutes and seconds for current position.
            cur_min=$(( cur_sec / 60 ))
            cur_sec_rem=$(( cur_sec % 60 ))
            # Compute minutes and seconds for total length.
            total_min=$(( total_sec / 60 ))
            total_sec_rem=$(( total_sec % 60 ))
            # Format the output with leading zeros.
            formatted_cur=$(printf "%02d:%02d" "$cur_min" "$cur_sec_rem")
            formatted_total=$(printf "%02d:%02d" "$total_min" "$total_sec_rem")
            # You can add a Nerd Font icon, e.g., a musical note (♪) or any preferred glyph.
            output="󰎇 ${formatted_cur}/${formatted_total}"
        fi
        ;;
    *)
        echo "Usage: $0 {title|artist|length|status|trackid|cover|progress}" >&2
        exit 1
        ;;
esac

echo "$output"
