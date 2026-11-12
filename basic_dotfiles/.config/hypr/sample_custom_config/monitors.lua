-- Custom monitor configuration override
return function()
    hl.monitor({
        output = "eDP-1",
        mode = "1920x1080@144",
        position = "auto-right",
        scale = "1.2",
    })

    hl.monitor({
        output = "HDMI-A-1",
        mode = "1920x1080@100",
        position = "auto",
        scale = "1",
    })
end
