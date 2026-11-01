-- Sample override: Custom workspace and window rules
return function()
    -- Custom gaps override for specific workspaces
    hl.workspace_rule({ workspace = "1", gaps_out = 0, gaps_in = 0 })
    
    -- Force specific applications to always float
    hl.window_rule({
        match = { class = "^pavucontrol$" },
        float = true,
    })
    
    -- Custom opacity rules for transparent terminals
    hl.window_rule({
        match = { class = "^alacritty$" },
        opacity = "0.9 override",
    })
    
    print("Loaded custom rules override successfully!")
end