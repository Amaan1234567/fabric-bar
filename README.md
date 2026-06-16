
<div align="center">

# fabric-bar

**Custom bar & widgets built with [Fabric](https://github.com/Fabric-Development/fabric) for a Fedora Hyprland rice**

A handcrafted desktop bar featuring workspaces, system tray, media controls,
audio visualizer, and more — all powered by Python & GTK3.

</div>

---

https://github.com/user-attachments/assets/0a049fb6-e79b-4c61-9571-09b95cb1c7d2

---

## Features

- Hyprland workspaces with smooth transitions
- System tray, clock, and battery indicators
- Media player controls via `playerctl`
- Audio visualizer powered by `cava`
- Bluetooth & network management widgets
- Dynamic color theming with `wallust`
- Smooth GTK3 revealer animations via a custom C extension

## Prerequisites

| Dependency | Purpose |
|---|---|
| Python 3.11+ | Runtime |
| GTK3, Cairo, GTK Layer Shell | UI rendering |
| GObject Introspection | Python ↔ GTK bindings |
| Cava | Audio visualizer input |
| Playerctl | Media metadata & controls |
| Wallust | Dynamic color generation |
| DDCUtil | External monitor brightness |
| Blueman | Bluetooth management |

## Installation

> **Other distros?** See the [Fabric installation guide](https://wiki.ffpy.org/getting-started/installation-guide/).

### 1. System dependencies (Fedora)

```bash
sudo dnf copr enable materka/wallust
sudo dnf install \
  gtk3-devel cairo-devel gtk-layer-shell-devel glib2 \
  gobject-introspection-devel python3-devel python-pip \
  python3-gobject python3-cairo python3-loguru pkgconf \
  cava NetworkManager-libnm-devel webp-pixbuf-loader \
  blueman blueman-applet playerctl jetbrains-mono-fonts \
  wallust ddcutil
```

Replace `tuned-ppd` with `power-profiles-daemon` (required for the power widget):

```bash
sudo dnf remove tuned-ppd && sudo dnf install power-profiles-daemon
```

### 2. Python environment

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Build the smooth revealer extension

```bash
cd custom_widgets/
gcc $(pkg-config --cflags gtk+-3.0) -fPIC -c hacktk.c -o libhacktk.o
gcc -shared -o libhacktk.so libhacktk.o $(pkg-config --libs gtk+-3.0)
```

> [!NOTE]
> Make sure the GTK3 dev packages installed correctly in step 1, otherwise this will fail.

### 4. Color theme

Generate a `colors.css` from your wallpaper using [wallust](https://github.com/dexpota/wallust) or [matugen](https://github.com/InioX/matugen):

```bash
wallust run /path/to/wallpaper.jpg
```

Or just grab the fallback to get started:

```bash
cp sample_colors.css colors.css
```

## Usage

```bash
python start_shell.py
```

## Recommended setup

This UI is designed to pair with **[mydotfiles](https://github.com/Amaan1234567/mydotfiles)**. Setting up the dotfiles first (or at least installing the shared dependencies listed there) will give you the smoothest experience.

## Project structure

```
fabric-bar/
├── start_shell.py          # Entry point
├── custom_widgets/         # Custom GTK widgets & C revealer extension
│   ├── hacktk.c
│   └── libhacktk.so
├── sample_colors.css       # Fallback color theme
└── requirements.txt
```

## Special Thanks

- **[its-darsh](https://github.com/its-darsh)** — for creating [Fabric](https://github.com/Fabric-Development/fabric) and providing invaluable snippets like `Animator`, none of this would exist without their work
- **[amansxcalibur](https://github.com/amansxcalibur)** — for code snippets, borrowed implementations, and a ton of UI inspiration
- **[rubiin](https://github.com/rubiin)** — for code snippets, borrowed implementations, and a ton of UI inspiration
- **[Axenide](https://github.com/Axenide)** — for code snippets, borrowed implementations, and a ton of UI inspiration
- **[Coffee](https://github.com/coffeeisangry)** — for hackedRevealer and more UI inspirations from [caffyne-shell](https://github.com/caffyne-org/caffyne-shell)

## Credits

- [Fabric](https://github.com/Fabric-Development/fabric) — the Python GTK framework powering this bar
- [wallust](https://github.com/dexpota/wallust) — dynamic color generation from wallpapers
- [mydotfiles](https://github.com/Amaan1234567/mydotfiles) — companion Hyprland configuration

---

<div align="center">

Made with Python, GTK3, and too many late nights.

</div>
