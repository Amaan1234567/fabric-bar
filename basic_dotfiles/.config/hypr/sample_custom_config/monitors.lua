-- Custom monitor configuration override
return function()
    hl.monitor({
        output = "HDMI-A-1",
        mode = "2560x1440@144",
        position = "0,0",
        scale = "1",
    })
end