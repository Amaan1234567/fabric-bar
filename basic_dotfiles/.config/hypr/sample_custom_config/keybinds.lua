-- Sample override: Custom minimalist or alternative keybinds set
return function()
    local mainmod = "ALT"

    -- Close window
    hl.bind(string.format("%s + Q", mainmod), hl.dsp.window.close())

    -- Open terminal (using alacritty instead of kitty)
    hl.bind(string.format("%s + T", mainmod), hl.dsp.exec_cmd("alacritty"))

    -- Focus movement
    hl.bind(string.format("%s + left", mainmod), hl.dsp.focus({ direction = "left" }))
    hl.bind(string.format("%s + right", mainmod), hl.dsp.focus({ direction = "right" }))
    hl.bind(string.format("%s + up", mainmod), hl.dsp.focus({ direction = "up" }))
    hl.bind(string.format("%s + down", mainmod), hl.dsp.focus({ direction = "down" }))

    -- Following keybinds are required for the fabric-bar to work properly, do not remove them unless you know what you're doing
    hl.bind("ALT + TAB", hl.dsp.exec_cmd("fabric-cli invoke-action hypr-fabric-bar-main alt-tab-next"),
        { repeat_on_hold = true })
    hl.bind(string.format("%s + SHIFT + W", mainmod),
        hl.dsp.exec_cmd("fabric-cli invoke-action hypr-fabric-bar-main toggle-wallpaper-selector"))
    hl.bind(string.format("%s + SHIFT + T", mainmod),
        hl.dsp.exec_cmd("fabric-cli invoke-action hypr-fabric-bar-main toggle-theme-selector"))
    hl.bind(string.format("%s + V", mainmod),
        hl.dsp.exec_cmd(
            "rofi -modi clipboard:~/Scripts/cliphist-rofi-img.sh -theme drun_theme -show clipboard -show-icons"))

    print("Loaded custom keybinds override successfully!")
end
