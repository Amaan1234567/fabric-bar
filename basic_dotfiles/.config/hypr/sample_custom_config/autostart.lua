-- Custom autostart hooks override
return function()
    hl.on("hyprland.start", function()
        hl.exec_cmd("waybar")
        hl.exec_cmd("mako")
    end)
end