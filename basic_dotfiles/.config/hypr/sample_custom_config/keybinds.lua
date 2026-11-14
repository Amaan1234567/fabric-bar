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
    
    print("Loaded custom keybinds override successfully!")
end