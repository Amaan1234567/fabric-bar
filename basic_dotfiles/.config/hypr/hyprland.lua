-- Helper function to safely load user overrides if they exist
local function load_override(module_name, default_func)
    local success, custom_module = pcall(require, "custom_config." .. module_name)
    if success then
        print("Loaded custom override: custom_config." .. module_name)
        if type(custom_module) == "function" then
            custom_module()
        end
        return true
    else
        default_func()
        return false
    end
end

-- ==========================================
-- 1. MONITORS
-- ==========================================
load_override("monitors", function()
    hl.monitor({
        output = "",
        mode = "preferred",
        position = "auto",
        scale = "1",
    })
end)

local home = os.getenv("HOME")

-- ==========================================
-- 2. ENVIRONMENT VARIABLES
-- ==========================================
hl.env("SSH_AUTH_SOCK", "$XDG_RUNTIME_DIR/keyring/ssh")
hl.env("HYPRCURSOR_SIZE", "24")
hl.env("XDG_CURRENT_DESKTOP", "Hyprland")
hl.env("XDG_SESSION_TYPE", "wayland")
hl.env("XDG_SESSION_DESKTOP", "Hyprland")
hl.env("XDG_SCREENSHOTS_DIR", "$HOME/Pictures/screenshots")
hl.env("QT_QPA_PLATFORM", "wayland")
hl.env("QT_QPA_PLATFORMTHEME", "qt6ct")
hl.env("QT_WAYLAND_DISABLE_WINDOWDECORATION", "1")
hl.env("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
hl.env("MOZ_ENABLE_WAYLAND", "1")
hl.env("GDK_SCALE", "1")
hl.env("GDK_BACKEND", "wayland")
hl.env("WLR_NO_HARDWARE_CURSORS", "1")
hl.env("ELECTRON_OZONE_PLATFORM_HINT", "auto")

load_override("env", function()

end)

-- ==========================================
-- 3. AUTOSTART HOOKS
-- ==========================================
hl.on("hyprland.start", function()
    hl.exec_cmd("systemctl --user import-environment WAYLAND_DISPLAY XDG_CURRENT_DESKTOP")
    hl.exec_cmd("dbus-update-activation-environment --systemd WAYLAND_DISPLAY XDG_CURRENT_DESKTOP")
    hl.exec_cmd("dbus-update-activation-environment --systemd --all")
    hl.exec_cmd("awww-daemon")
    hl.exec_cmd("hypridle")
    hl.exec_cmd(home .. "/fabric-bar/scripts/start.sh")
    hl.exec_cmd(home .. "/fabric-bar/scripts/wallpaper_loop.sh")
    hl.exec_cmd("wl-paste --watch cliphist store")
end)

load_override("autostart", function()
    hl.on("hyprland.start", function()
    end)
end)



-- ==========================================
-- 4. GENERAL CONFIGURATION, STYLES & ANIMATIONS
-- ==========================================
load_override("theme", function()
    hl.config({
        general = {
            gaps_in = 5,
            gaps_out = 10,
            border_size = 3,
            col = {
                active_border = { colors = { "rgba(33ccffee)" } },
                inactive_border = "rgba(595959aa)",
            },
            resize_on_border = false,
            allow_tearing = false,
            layout = "dwindle",
        },
        decoration = {
            rounding = 30,
            rounding_power = 2.5,
            active_opacity = 1.0,
            inactive_opacity = 1.,
            shadow = {
                enabled = true,
                range = 10,
                render_power = 3,
                color = 0xee1a1a1a,
            },
            blur = {
                enabled = true,
                size = 2,
                passes = 3,
                vibrancy = 0.1696,
            },
        },
        animations = { enabled = true },
        dwindle = {
            force_split = 0,
            preserve_split = true,
            smart_split = false,
            smart_resizing = true,
            special_scale_factor = 1,
            split_width_multiplier = 1.0,
            use_active_for_splits = true,
            default_split_ratio = 1.0,
            split_bias = 0,
        },
        input = {
            kb_layout = "us",
            repeat_rate = 25,
            repeat_delay = 200,
            follow_mouse = 1,
            sensitivity = 0,
            touchpad = { natural_scroll = true }
        },
        misc = {
            force_default_wallpaper = 0,
            disable_hyprland_logo = true,
            vrr = 1,
            mouse_move_enables_dpms = true,
            key_press_enables_dpms = true,
            animate_manual_resizes = true,
            animate_mouse_windowdragging = true
        },
        xwayland = { force_zero_scaling = true },
        cursor = { no_hardware_cursors = true },
        render = { new_render_scheduling = true },
        debug = { vfr = true }
    })

    hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })

    -- Curves & Animations
    hl.curve("wind", { type = "bezier", points = { { 0.05, 0.9 }, { 0.1, 1.05 } } })
    hl.curve("winIn", { type = "bezier", points = { { 0.1, 1.1 }, { 0.1, 1.1 } } })
    hl.curve("winOut", { type = "bezier", points = { { 0.3, -0.3 }, { 0, 1 } } })
    hl.curve("linear", { type = "bezier", points = { { 1, 1 }, { 1, 1 } } })

    hl.animation({ leaf = "windows", enabled = true, speed = 6, bezier = "wind", style = "slide" })
    hl.animation({ leaf = "windowsIn", enabled = true, speed = 6, bezier = "winIn", style = "popin 80%" })
    hl.animation({ leaf = "windowsOut", enabled = true, speed = 5, bezier = "winOut", style = "slide" })
    hl.animation({ leaf = "windowsMove", enabled = true, speed = 5, bezier = "wind", style = "popin" })
    hl.animation({ leaf = "border", enabled = true, speed = 1, bezier = "linear" })
    hl.animation({ leaf = "borderangle", enabled = true, speed = 30, bezier = "linear", style = "loop" })
    hl.animation({ leaf = "fade", enabled = true, speed = 10, bezier = "default" })
    hl.animation({ leaf = "workspaces", enabled = true, speed = 5, bezier = "winIn", style = "slide" })
end)

-- ==========================================
-- 5. RULES & BINDINGS
-- ==========================================

local layer_names = {
    "fabric-mpris-popup", "fabric-networks-popup", "fabric-notifications",
    "volume_osd", "wallpaper-selector", "control_center", "brightness_osd",
    "logout_popup", "theme_selector", "fabric-audio-popup", "fabric-clock-popup", "fabric-alttab"
}

for _, value in ipairs(layer_names) do
    hl.layer_rule({ match = { namespace = value }, no_anim = true, blur = true, ignore_alpha = 0 })
end

hl.layer_rule({ match = { namespace = "rofi" }, blur = true, animation = "popin 95%" })
hl.layer_rule({ match = { namespace = "wallpaper-selector" }, dim_around = true })

load_override("rules", function()
    hl.workspace_rule({ workspace = "w[tv1]", gaps_out = { top = 10, right = 12, bottom = 19, left = 12 }, gaps_in = 5 })
    hl.workspace_rule({ workspace = "w[tv2-100]", gaps_out = { top = 20, right = 18, bottom = 24, left = 18 }, gaps_in = 5 })
    hl.window_rule({ match = { float = false, workspace = "w[tv1]s[false]" }, border_size = 0 })
    hl.window_rule({ match = { float = false, workspace = "w[tv1]s[false]" }, rounding = 0 })
    hl.window_rule({ match = { float = false, workspace = "f[1]s[false]" }, border_size = 0 })
    hl.window_rule({ match = { float = false, workspace = "f[1]s[false]" }, rounding = 0 })

    hl.window_rule({
        name     = "fix-xwayland-drags",
        match    = { class = "^$", title = "^$", xwayland = true, float = true, fullscreen = false, pin = false },
        no_focus = true,
    })

    hl.window_rule({
        match = { class = "*" },
        opacity = "0.8 override",
        animation = "popin 85%"
    })
end)

load_override("keybinds", function()
    local mainmod = "SUPER"
    local terminal = "kitty"
    local fileManager = "nautilus"
    local menu = "rofi -show drun -theme drun_theme"
    local editor = "code"
    local browser = "google-chrome"

    hl.bind("ALT + TAB", hl.dsp.exec_cmd("fabric-cli invoke-action hypr-fabric-bar-main alt-tab-next"),
        { repeat_on_hold = true })
    hl.bind("SUPER + Q", hl.dsp.window.close())
    hl.bind(string.format("%s + DELETE", mainmod), hl.dsp.exit())
    hl.bind(string.format("%s + SHIFT + W", mainmod),
        hl.dsp.exec_cmd("fabric-cli invoke-action hypr-fabric-bar-main toggle-wallpaper-selector"))
    hl.bind(string.format("%s + SHIFT + T", mainmod),
        hl.dsp.exec_cmd("fabric-cli invoke-action hypr-fabric-bar-main toggle-theme-selector"))
    hl.bind(string.format("%s + V", mainmod),
        hl.dsp.exec_cmd(
        "rofi -modi clipboard:~/Scripts/cliphist-rofi-img.sh -theme drun_theme -show clipboard -show-icons"))
    hl.bind("SUPER  +  A", hl.dsp.exec_cmd(menu))
    hl.bind(string.format("%s + P", mainmod), hl.dsp.window.pseudo())
    hl.bind(string.format("%s + J", mainmod), hl.dsp.layout("togglesplit"))
    hl.bind(string.format("%s + W", mainmod), hl.dsp.window.float({ action = "toggle" }))
    hl.bind("ALT  +  Return", hl.dsp.window.fullscreen({ mode = "fullscreen", action = "toggle" }))
    hl.bind(string.format("%s + L", mainmod), hl.dsp.exec_cmd("hyprlock"))
    hl.bind(string.format("%s + R", mainmod), hl.dsp.exec_cmd("~/fabric-bar/scripts/reset.sh"))
    hl.bind("ALT  +  Tab", hl.dsp.group.prev())

    hl.bind("print", hl.dsp.exec_cmd("grimshot savecopy anything"))

    hl.bind("SUPER + T", hl.dsp.exec_cmd(terminal))
    hl.bind(string.format("%s + E", mainmod), hl.dsp.exec_cmd(fileManager))
    hl.bind(string.format("%s + C", mainmod), hl.dsp.exec_cmd(editor))
    hl.bind(string.format("%s + F", mainmod), hl.dsp.exec_cmd(browser))
    hl.bind(string.format("%s + left", mainmod), hl.dsp.focus({ direction = "left" }))
    hl.bind(string.format("%s + right", mainmod), hl.dsp.focus({ direction = "right" }))
    hl.bind(string.format("%s + up", mainmod), hl.dsp.focus({ direction = "up" }))
    hl.bind(string.format("%s + down", mainmod), hl.dsp.focus({ direction = "down" }))

    for i = 1, 10, 1 do
        if i == 10 then
            hl.bind(string.format("%s + %d", mainmod, 0), hl.dsp.focus({ workspace = 10 }))
        else
            hl.bind(string.format("%s + %d", mainmod, i), hl.dsp.focus({ workspace = i }))
        end
    end

    for i = 1, 10, 1 do
        if i == 10 then
            hl.bind(string.format("%s + SHIFT + %d", mainmod, 0), hl.dsp.window.move({ workspace = 10, follow = true }))
            hl.bind(string.format("%s + ALT + %d", mainmod, 0), hl.dsp.window.move({ workspace = 10, follow = false }))
        else
            hl.bind(string.format("%s + SHIFT + %d", mainmod, i), hl.dsp.window.move({ workspace = i, follow = true }))
            hl.bind(string.format("%s + ALT + %d", mainmod, i), hl.dsp.window.move({ workspace = i, follow = false }))
        end
    end

    hl.bind(string.format("%s + S", mainmod), hl.dsp.workspace.toggle_special("background"))
    hl.bind(string.format("%s + SHIFT + S", mainmod), hl.dsp.window.move({ workspace = "special:background" }))
    hl.bind(string.format("%s + mouse_down", mainmod), hl.dsp.focus({ workspace = "m + 1" }))
    hl.bind(string.format("%s + mouse_up", mainmod), hl.dsp.focus({ workspace = "m-1" }))
    hl.bind(string.format("%s + mouse:272", mainmod), hl.dsp.window.drag())
    hl.bind(string.format("%s + mouse:273", mainmod), hl.dsp.window.resize())

    hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 3%+ --limit 1.0"),
        { repeating = true })
    hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 3%- --limit 1.0"),
        { repeating = true })
    hl.bind("XF86AudioMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"))
    hl.bind("XF86AudioMicMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle"))
    hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd("brightnessctl s 5%+"), { repeating = true })
    hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd("brightnessctl s 5%-"), { repeating = true })
    hl.bind("XF86AudioNext", hl.dsp.exec_cmd("playerctl next"))
    hl.bind("XF86AudioPause", hl.dsp.exec_cmd("playerctl play-pause"))
    hl.bind("XF86AudioPlay", hl.dsp.exec_cmd("playerctl play-pause"))
    hl.bind("XF86AudioPrev", hl.dsp.exec_cmd("playerctl previous"))
end)
