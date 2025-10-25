# fabric-bar
custom bar and widgets written in fabric for my fedora hyprland rice
![demo video](assets/repo_assets/demo.mp4)

# setup
```bash
sudo dnf copr enable materka/wallust
sudo dnf install gtk3-devel cairo-devel gtk-layer-shell-devel glib2 gobject-introspection-devel python3-devel python-pip python3-gobject python3-cairo python3-loguru pkgconf cava NetworkManager-libnm-devel webp-pixbuf-loader blueman blueman-applet playerctl jetbrains-mono-fonts wallust
```
for other distro's refer to https://wiki.ffpy.org/getting-started/installation-guide/
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
You can download and setup wallust or matugen to create a colors.css, or create a custom one for yourself

# Running the bar and widget 
```bash
python start_shell.py
```