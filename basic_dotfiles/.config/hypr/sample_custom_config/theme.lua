-- Sample override: Custom gaps, sharp corners, and faster animations
return function()
    hl.config({
        general = {
            gaps_in = 2,
            gaps_out = 4,
            border_size = 2,
            col = {
                active_border = { colors = { "rgba(ff5555ee)" } },
                inactive_border = "rgba(222222aa)",
            },
            layout = "dwindle",
        },
        decoration = {
            rounding = 8,
            active_opacity = 0.95,
            inactive_opacity = 0.85,
            blur = { enabled = true, size = 4, passes = 2 },
        },
        animations = { enabled = true },
        input = {
            kb_layout = "us",
            touchpad = { natural_scroll = true }
        },
    })

    -- Custom snappy bezier animations
    hl.curve("fast", { type = "bezier", points = { { 0.25, 1 }, { 0.5, 1 } } })
    hl.animation({ leaf = "windows", enabled = true, speed = 3, bezier = "fast", style = "slide" })
    hl.animation({ leaf = "workspaces", enabled = true, speed = 3, bezier = "fast", style = "slide" })
end
