# fabric-bar
custom

https://github.com/user-attachments/assets/7a3d0675-f824-4df3-b435-bc3348000d30

 bar and widgets written in fabric for my fedora hyprland rice


# setup
```bash
sudo dnf copr enable materka/wallust
sudo dnf install gtk3-devel cairo-devel gtk-layer-shell-devel glib2 gobject-introspection-devel python3-devel python-pip python3-gobject python3-cairo python3-loguru pkgconf cava NetworkManager-libnm-devel webp-pixbuf-loader blueman blueman-applet playerctl jetbrains-mono-fonts wallust
sudo dnf remove tuned-ppd && sudo dnf install power-profiles-daemon
```
for other distro's refer to https://wiki.ffpy.org/getting-started/installation-guide/
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
run the following command to get the .so file to get smooth revealer(make sure the gtk3 install command ran successfully, else this might fail)
```bash
cd custom_widgets/
gcc $(pkg-config --cflags gtk+-3.0) -fPIC -c hacktk.c -o libhacktk.o                                                                                                                            ─╯
gcc -shared -o libhacktk.so libhacktk.o $(pkg-config --libs gtk+-3.0)
```

You can download and setup wallust or matugen to create a colors.css, or create a custom one for yourself, This UI is intended to work with [mydotfiles](https://github.com/Amaan1234567/mydotfiles) so you will have a better time if you setup that first or if you dont want that setup, then atleast install the dependencies given there, cause you will need them.

# Running the bar and widget 
rename sample_colors.css to colors.css so the bar has basic colors to use, ideally this file comes from a colors generator like pywal, wallust, matugen etc.]

```bash
python start_shell.py
```
