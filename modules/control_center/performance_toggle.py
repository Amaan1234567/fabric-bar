import fabric
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
import subprocess
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib


class PerformanceToggle(Box):
    def __init__(self):
        super().__init__(
            name="performance-toggle-container",
            orientation="vertical",
            spacing=8,
        )
        
        # Header
        self.header_box = Box(
            name="performance-header-box",
            orientation="horizontal",
            spacing=8,
        )
        
        self.performance_icon = Label(
            name="performance-icon",
            label="",  # Nerd Font CPU/performance icon
        )
        
        self.performance_label = Label(
            name="performance-label",
            label="Performance Mode",
        )
        
        self.status_label = Label(
            name="performance-status-label",
            label="",
        )
        
        self.header_box.children = [
            self.performance_icon,
            self.performance_label,
            self.status_label,
        ]
        
        # Performance mode buttons with Nerd Font icons
        self.modes_box = Box(
            name="performance-modes-box",
            orientation="horizontal",
            spacing=4,
        )
        
        self.powersave_button = Button(
            name="performance-powersave-button",
            label=" Power Save",  # Battery icon
            on_clicked=lambda btn: self.set_performance_mode("powersave"),
        )
        
        self.balanced_button = Button(
            name="performance-balanced-button", 
            label=" Balanced",  # Balance/scale icon
            on_clicked=lambda btn: self.set_performance_mode("balanced"),
        )
        
        self.performance_button = Button(
            name="performance-performance-button",
            label="󱐋 Performance",  # Lightning/performance icon
            on_clicked=lambda btn: self.set_performance_mode("performance"),
        )
        
        self.modes_box.children = [
            self.powersave_button,
            self.balanced_button,
            self.performance_button,
        ]
        
        # System info with Nerd Font icons
        self.info_box = Box(
            name="performance-info-box",
            orientation="horizontal",
            spacing=12,
        )
        
        self.cpu_label = Label(
            name="performance-cpu-label",
            label=" CPU: --",  # CPU icon
        )
        
        self.temp_label = Label(
            name="performance-temp-label",
            label=" Temp: --°C",  # Thermometer icon
        )
        
        self.freq_label = Label(
            name="performance-freq-label",
            label="󱑆 Freq: -- GHz",  # Frequency/wave icon
        )
        
        self.info_box.children = [
            self.cpu_label,
            self.temp_label,
            self.freq_label,
        ]
        
        self.children = [
            self.header_box,
            self.modes_box,
            self.info_box,
        ]
        
        # Initialize
        self.update_status()
        GLib.timeout_add_seconds(2, self.update_system_info)
    
    def get_current_governor(self):
        """Get current CPU frequency governor"""
        try:
            result = subprocess.run(
                ["cat", "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            return "unknown"
        except:
            return "unknown"
    
    def set_performance_mode(self, mode):
        """Set CPU performance mode"""
        governor_map = {
            "powersave": "powersave",
            "balanced": "ondemand", 
            "performance": "performance"
        }
        
        governor = governor_map.get(mode, "ondemand")
        
        try:
            # Try using cpufreq-set
            subprocess.run(["sudo", "cpufreq-set", "-g", governor], check=False)
        except:
            try:
                # Try direct sysfs write
                for cpu in range(8):  # Assume max 8 cores
                    path = f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_governor"
                    try:
                        subprocess.run(["sudo", "sh", "-c", f"echo {governor} > {path}"], check=False)
                    except:
                        break
            except:
                pass
        
        self.update_status()
        self.update_performance_icon()
    
    def update_performance_icon(self):
        """Update performance icon based on current mode"""
        current_governor = self.get_current_governor()
        
        # Update main icon based on performance mode
        if current_governor == "powersave":
            self.performance_icon.label = ""  # Battery save icon
            self.performance_icon.get_style_context().add_class("powersave-mode")
            self.performance_icon.get_style_context().remove_class("balanced-mode")
            self.performance_icon.get_style_context().remove_class("performance-mode")
        elif current_governor in ["ondemand", "conservative"]:
            self.performance_icon.label = ""  # Balanced icon
            self.performance_icon.get_style_context().add_class("balanced-mode")
            self.performance_icon.get_style_context().remove_class("powersave-mode")
            self.performance_icon.get_style_context().remove_class("performance-mode")
        elif current_governor == "performance":
            self.performance_icon.label = "󱐋"  # Performance/lightning icon
            self.performance_icon.get_style_context().add_class("performance-mode")
            self.performance_icon.get_style_context().remove_class("powersave-mode")
            self.performance_icon.get_style_context().remove_class("balanced-mode")
        else:
            self.performance_icon.label = ""  # Default CPU icon
    
    def get_cpu_usage(self):
        """Get current CPU usage percentage"""
        try:
            result = subprocess.run(
                ["sh", "-c", "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | sed 's/%us,//'"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
            return 0.0
        except:
            return 0.0
    
    def get_cpu_temp(self):
        """Get CPU temperature"""
        try:
            # Try different temperature sources
            temp_files = [
                "/sys/class/thermal/thermal_zone0/temp",
                "/sys/class/hwmon/hwmon0/temp1_input",
                "/sys/class/hwmon/hwmon1/temp1_input",
            ]
            
            for temp_file in temp_files:
                try:
                    result = subprocess.run(
                        ["cat", temp_file],
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode == 0:
                        temp = int(result.stdout.strip()) / 1000  # Convert from millidegrees
                        return temp
                except:
                    continue
            
            return 0
        except:
            return 0
    
    def get_cpu_freq(self):
        """Get current CPU frequency"""
        try:
            result = subprocess.run(
                ["cat", "/proc/cpuinfo"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'cpu MHz' in line:
                        freq = float(line.split(':')[1].strip()) / 1000  # Convert to GHz
                        return round(freq, 2)
            return 0.0
        except:
            return 0.0
    
    def update_status(self):
        """Update performance mode status"""
        current_governor = self.get_current_governor()
        
        # Reset button styles
        for button in [self.powersave_button, self.balanced_button, self.performance_button]:
            button.get_style_context().remove_class("active")
        
        # Set active button and status
        if current_governor == "powersave":
            self.powersave_button.get_style_context().add_class("active")
            self.status_label.label = "Power Saving"
        elif current_governor in ["ondemand", "conservative"]:
            self.balanced_button.get_style_context().add_class("active")
            self.status_label.label = "Balanced"
        elif current_governor == "performance":
            self.performance_button.get_style_context().add_class("active")
            self.status_label.label = "High Performance"
        else:
            self.status_label.label = f"Mode: {current_governor}"
    
    def update_system_info(self):
        """Update CPU usage, temperature, and frequency"""
        cpu_usage = self.get_cpu_usage()
        cpu_temp = self.get_cpu_temp()
        cpu_freq = self.get_cpu_freq()
        
        self.cpu_label.label = f" CPU: {cpu_usage:.1f}%"
        self.temp_label.label = f" Temp: {cpu_temp:.0f}°C"
        self.freq_label.label = f"󱑆 Freq: {cpu_freq:.1f} GHz"
        
        # Update performance icon
        self.update_performance_icon()
        
        return True
