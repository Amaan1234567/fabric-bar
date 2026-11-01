-- Custom environment variables override
return function()
    hl.env("XDG_CURRENT_DESKTOP", "Hyprland")
    hl.env("MOZ_ENABLE_WAYLAND", "1")
end