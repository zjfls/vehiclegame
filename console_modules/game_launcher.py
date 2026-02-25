"""
Game Launcher Module - Support multiple vehicle configurations
"""
import dearpygui.dearpygui as dpg
from typing import List, Dict, Any, Optional
from .base_module import ConsoleModule, ModuleRegistry


@ModuleRegistry.register
class GameLauncherModule(ConsoleModule):
    """Game Launcher Module"""
    
    name = "game_launcher"
    display_name = "Launch Game"
    icon = "🚀"
    description = "Launch vehicle game with multiple vehicle configs"
    
    def __init__(self, console_app: Any):
        super().__init__(console_app)
        self.vehicle_configs: List[str] = []
        self.terrain_configs: List[str] = []
        self.selected_vehicle: Optional[str] = None
        self.selected_terrain: Optional[str] = None
        self.is_running: bool = False
        self.game_process_id: Optional[str] = None
        
        self.vehicle_combo = None
        self.terrain_combo = None
        self.fullscreen_check = None
        self.debug_check = None
        self.status_text = None
    
    def build_ui(self, parent: Any) -> None:
        """Build UI"""
        with dpg.group(parent=parent, horizontal=False):
            dpg.add_text("Game Launch Configuration")
            dpg.add_separator()
            
            dpg.add_text("Vehicle Config:")
            with dpg.group(horizontal=True):
                self.vehicle_combo = dpg.add_combo(
                    label="",
                    width=200,
                    callback=self._on_vehicle_selected
                )
                dpg.add_button(label="Refresh", callback=self._refresh_configs)
                dpg.add_button(label="Edit", callback=self._edit_vehicle_config)
            
            dpg.add_spacer(height=10)
            
            dpg.add_text("Terrain Config:")
            with dpg.group(horizontal=True):
                self.terrain_combo = dpg.add_combo(
                    label="",
                    width=200,
                    callback=self._on_terrain_selected
                )
                dpg.add_button(label="Refresh", callback=self._refresh_configs)
                dpg.add_button(label="Generate", callback=self._open_terrain_generator)
            
            dpg.add_spacer(height=15)
            
            dpg.add_text("Game Settings:")
            self.fullscreen_check = dpg.add_checkbox(label="Fullscreen", default_value=False)
            self.debug_check = dpg.add_checkbox(label="Debug Mode", default_value=False)
            dpg.add_checkbox(label="Shadows", default_value=True)
            
            dpg.add_spacer(height=15)
            
            with dpg.group(horizontal=True):
                dpg.add_text("Resolution:")
                resolution_combo = dpg.add_combo(
                    items=["1280x720", "1920x1080", "2560x1440", "3840x2160"],
                    default_value="1280x720",
                    width=150
                )
            
            dpg.add_spacer(height=20)
            
            dpg.add_text("Status:", color=(200, 200, 200, 255))
            self.status_text = dpg.add_text("Ready", color=(0, 255, 0, 255))
            
            dpg.add_spacer(height=15)
            
            with dpg.group(horizontal=True):
                self.start_button = dpg.add_button(
                    label="Start Game",
                    width=150,
                    height=40,
                    callback=self._start_game
                )
                dpg.add_button(
                    label="Stop Game",
                    width=150,
                    height=40,
                    callback=self._stop_game,
                    enabled=False
                )
                dpg.add_button(
                    label="View Log",
                    width=120,
                    callback=self._view_log
                )
            
            dpg.add_spacer(height=10)
            dpg.add_separator()
            dpg.add_spacer(height=10)
            
            dpg.add_text("Vehicle Preview:", color=(200, 200, 200, 255))
            self.vehicle_info_text = dpg.add_text("Please select a vehicle", color=(150, 150, 150, 255))
        
        self._refresh_configs()
    
    def _refresh_configs(self, sender=None, app_data=None) -> None:
        """Refresh config list"""
        config_mgr = self.get_config_manager()
        if not config_mgr:
            self.log("Config manager not initialized", "error")
            return
        
        self.vehicle_configs = config_mgr.list_configs("vehicles")
        if self.vehicle_combo:
            dpg.configure_item(self.vehicle_combo, items=self.vehicle_configs)
            if self.vehicle_configs and not self.selected_vehicle:
                self.selected_vehicle = self.vehicle_configs[0]
                dpg.configure_item(self.vehicle_combo, default_value=self.selected_vehicle)
                self._update_vehicle_info()
        
        self.terrain_configs = config_mgr.list_configs("terrain")
        if self.terrain_combo:
            dpg.configure_item(self.terrain_combo, items=self.terrain_configs)
            if self.terrain_configs and not self.selected_terrain:
                self.selected_terrain = self.terrain_configs[0]
                dpg.configure_item(self.terrain_combo, default_value=self.selected_terrain)
        
        self.log(f"Loaded {len(self.vehicle_configs)} vehicle configs", "info")
    
    def _on_vehicle_selected(self, sender, app_data) -> None:
        """Vehicle selection changed"""
        self.selected_vehicle = app_data
        self._update_vehicle_info()
    
    def _on_terrain_selected(self, sender, app_data) -> None:
        """Terrain selection changed"""
        self.selected_terrain = app_data
    
    def _update_vehicle_info(self) -> None:
        """Update vehicle info preview"""
        if not self.selected_vehicle:
            return
        
        config_mgr = self.get_config_manager()
        if not config_mgr:
            return
        
        try:
            config = config_mgr.load_config("vehicles", self.selected_vehicle)
            name = config.get("name", self.selected_vehicle)
            mass = config.get("vehicle_mass", "N/A")
            max_speed = config.get("physics", {}).get("max_speed", "N/A")
            
            info = f"{name} | Mass: {mass}kg | Max Speed: {max_speed}km/h"
            if self.vehicle_info_text:
                dpg.configure_item(self.vehicle_info_text, default_value=info)
        except Exception as e:
            if self.vehicle_info_text:
                dpg.configure_item(self.vehicle_info_text, default_value=f"Load failed: {e}")
    
    def _start_game(self, sender=None, app_data=None) -> None:
        """Start game"""
        if self.is_running:
            self.log("Game is already running", "warning")
            return
        
        if not self.selected_vehicle:
            self.log("Please select a vehicle config", "error")
            return
        
        import sys
        cmd_parts = [sys.executable, "main.py"]
        
        if self.selected_vehicle:
            cmd_parts.extend(["--vehicle", self.selected_vehicle])
        
        if self.selected_terrain:
            cmd_parts.extend(["--terrain", self.selected_terrain])
        
        if self.debug_check and dpg.get_value(self.debug_check):
            cmd_parts.append("--debug")
        
        command = " ".join(cmd_parts)
        self.game_process_id = "game_session"
        
        self.log(f"Starting game: {command}", "info")
        dpg.configure_item(self.status_text, default_value="Starting...", color=(255, 200, 0, 255))
        
        process_mgr = self.get_process_manager()
        if process_mgr:
            import asyncio
            
            def on_output(line: str):
                self.log(f"[Game] {line}", "info")
            
            async def start():
                result = await process_mgr.run_command(
                    self.game_process_id,
                    command,
                    callback=on_output,
                    cwd=None
                )
                
                if result.status.value == "completed":
                    self.log("Game exited", "info")
                    dpg.configure_item(self.status_text, default_value="Exited", color=(150, 150, 150, 255))
                else:
                    self.log(f"Game error: {result.stderr}", "error")
                    dpg.configure_item(self.status_text, default_value=f"Error: {result.status.value}", color=(255, 0, 0, 255))
                
                self.is_running = False
                if self.start_button:
                    dpg.configure_item(self.start_button, enabled=True)
            
            if hasattr(self.console_app, 'run_async'):
                self.console_app.run_async(start())
            else:
                import subprocess
                try:
                    self.process = subprocess.Popen(command, shell=True)
                    self.is_running = True
                    dpg.configure_item(self.start_button, enabled=False)
                    dpg.configure_item(self.status_text, default_value="Running", color=(0, 255, 0, 255))
                    self.log("Game started", "success")
                except Exception as e:
                    self.log(f"Start failed: {e}", "error")
                    dpg.configure_item(self.status_text, default_value=f"Failed: {e}", color=(255, 0, 0, 255))
    
    def _stop_game(self, sender=None, app_data=None) -> None:
        """Stop game"""
        if not self.is_running:
            self.log("Game is not running", "warning")
            return
        
        process_mgr = self.get_process_manager()
        if process_mgr and self.game_process_id:
            import asyncio
            async def stop():
                await process_mgr.kill_process(self.game_process_id)
            
            if hasattr(self.console_app, 'run_async'):
                self.console_app.run_async(stop())
        
        if hasattr(self, 'process') and self.process:
            self.process.terminate()
            self.log("Game stopped", "info")
            self.is_running = False
            dpg.configure_item(self.start_button, enabled=True)
            dpg.configure_item(self.status_text, default_value="Stopped", color=(150, 150, 150, 255))
    
    def _edit_vehicle_config(self, sender=None, app_data=None) -> None:
        """Edit vehicle config"""
        if not self.selected_vehicle:
            self.log("Please select a vehicle config first", "warning")
            return
        
        self.log(f"Edit config: {self.selected_vehicle}", "info")
    
    def _open_terrain_generator(self, sender=None, app_data=None) -> None:
        """Open terrain generator"""
        self.log("Switching to terrain generator", "info")
        if hasattr(self.console_app, 'switch_module'):
            self.console_app.switch_module("terrain_generator")
    
    def _view_log(self, sender=None, app_data=None) -> None:
        """View game log"""
        import os
        log_path = "game.log"
        if os.path.exists(log_path):
            self.log(f"Log file: {log_path}", "info")
            import subprocess
            subprocess.run(["open", log_path] if os.uname().sysname == "Darwin" else ["xdg-open", log_path])
        else:
            self.log("Log file not found", "warning")
    
    def on_show(self) -> None:
        """On module show"""
        self._refresh_configs()
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        if self.is_running and hasattr(self, 'process'):
            self.process.terminate()
