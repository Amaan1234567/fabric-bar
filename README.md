# fabric-bar
custom bar and widgets written in fabric for my fedora hyprland rice


# setup
```bash
sudo dnf install gtk3-devel cairo-devel gtk-layer-shell-devel glib2 gobject-introspection-devel python3-devel python-pip python3-gobject python3-cairo python3-loguru pkgconf cava
```
for other distro's refer to https://wiki.ffpy.org/getting-started/installation-guide/
```python
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
You can download and setup wallust or matugen to create a colors.css, or create a custom one for yourself

# Running the bar and widget 
```python
python start-shell.py
```