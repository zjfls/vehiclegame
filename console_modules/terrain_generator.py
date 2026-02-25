"""
Terrain Generator Module - Visual interface for generate_terrain.py
"""
import dearpygui.dearpygui as dpg
from typing import Optional, List, Any
from .base_module import ConsoleModule, ModuleRegistry


@ModuleRegistry.register
class TerrainGeneratorModule(ConsoleModule):
    """Terrain Generator Module"""
    
    name = "terrain_generator"
    display_name = "Terrain Generator"
    icon = "🛠️"
    description = "Generate procedural terrain heightmaps"
    
    def __init__(self, console_app: Any):
        super().__init__(console_app)
        self.is_generating = False
        
        self.width = 1024
        self.height = 1024
        self.seed = 12345
        self.noise_scale = 0.05
        self.octaves = 5
        self.persistence = 0.5
        self.lacunarity = 2.0
        self.height_scale = 20.0
        
        self.use_track = False
        self.track_csv = "scripts/track_example.csv"
        self.corridor_width = 120
        self.edge_falloff = 50
        
        self.output_name = ""
        
        self.status_text = None
        self.progress_bar = None
        self.generate_button = None
        self.log_messages: List[str] = []
    
    def build_ui(self, parent: Any) -> None:
        """Build UI"""
        with dpg.group(parent=parent, horizontal=False):
            dpg.add_text("Terrain Parameters")
            dpg.add_separator()
            
            dpg.add_text("Basic Parameters:")
            with dpg.group(horizontal=True):
                dpg.add_input_int(label="Width (px)", default_value=1024, width=120,
                                 callback=lambda s, a: setattr(self, 'width', a))
                dpg.add_input_int(label="Height (px)", default_value=1024, width=120,
                                 callback=lambda s, a: setattr(self, 'height', a))
                dpg.add_input_int(label="Seed", default_value=12345, width=120,
                                 callback=lambda s, a: setattr(self, 'seed', a))
            
            dpg.add_spacer(height=10)
            
            dpg.add_text("Noise Parameters:")
            with dpg.group(horizontal=True):
                dpg.add_input_float(label="Noise Scale", default_value=0.05, width=120,
                                   callback=lambda s, a: setattr(self, 'noise_scale', a))
                dpg.add_input_int(label="Octaves", default_value=5, min_value=1, max_value=10, width=120,
                                 callback=lambda s, a: setattr(self, 'octaves', a))
                dpg.add_input_float(label="Persistence", default_value=0.5, min_value=0.1, max_value=1.0, width=120,
                                   callback=lambda s, a: setattr(self, 'persistence', a))
                dpg.add_input_float(label="Lacunarity", default_value=2.0, width=120,
                                   callback=lambda s, a: setattr(self, 'lacunarity', a))
            
            dpg.add_spacer(height=10)
            
            dpg.add_text("Height Parameters:")
            with dpg.group(horizontal=True):
                dpg.add_input_float(label="Height Scale", default_value=20.0, width=120,
                                   callback=lambda s, a: setattr(self, 'height_scale', a))
            
            dpg.add_spacer(height=15)
            
            dpg.add_text("Track Corridor (Optional):")
            self.use_track_check = dpg.add_checkbox(
                label="Enable Track Flattening",
                default_value=False,
                callback=lambda s, a: setattr(self, 'use_track', a)
            )
            
            def on_track_toggle(sender, app_data):
                dpg.configure_item(self.track_options_group, enabled=app_data)
                self.use_track = app_data
            
            dpg.configure_item(self.use_track_check, callback=on_track_toggle)
            
            with dpg.group(enabled=False) as self.track_options_group:
                with dpg.group(horizontal=True):
                    self.track_csv_input = dpg.add_input_text(
                        label="CSV File",
                        default_value="scripts/track_example.csv",
                        width=300,
                        callback=lambda s, a: setattr(self, 'track_csv', a)
                    )
                    dpg.add_button(label="Browse", callback=self._browse_track_file)
                
                with dpg.group(horizontal=True):
                    dpg.add_input_int(label="Corridor Width (px)", default_value=120, width=120,
                                     callback=lambda s, a: setattr(self, 'corridor_width', a))
                    dpg.add_input_int(label="Edge Falloff (px)", default_value=50, width=120,
                                     callback=lambda s, a: setattr(self, 'edge_falloff', a))
            
            dpg.add_spacer(height=15)
            
            dpg.add_text("Output Filename:")
            with dpg.group(horizontal=True):
                self.output_name_input = dpg.add_input_text(
                    label="",
                    default_value="generated_terrain",
                    width=250,
                    callback=lambda s, a: setattr(self, 'output_name', a)
                )
                dpg.add_text("(without extension)", color=(150, 150, 150, 255))
            
            dpg.add_spacer(height=20)
            
            dpg.add_text("Status:", color=(200, 200, 200, 255))
            self.status_text = dpg.add_text("Ready", color=(0, 255, 0, 255))
            
            self.progress_bar = dpg.add_progress_bar(default_value=0.0, width=-1)
            dpg.configure_item(self.progress_bar, show=False)
            
            dpg.add_spacer(height=15)
            
            with dpg.group(horizontal=True):
                self.generate_button = dpg.add_button(
                    label="Generate Terrain",
                    width=150,
                    height=40,
                    callback=self._generate_terrain
                )
                dpg.add_button(
                    label="Open Output Dir",
                    width=150,
                    callback=self._open_output_dir
                )
                dpg.add_button(
                    label="View Docs",
                    width=120,
                    callback=self._view_docs
                )
            
            dpg.add_spacer(height=15)
            dpg.add_separator()
            dpg.add_spacer(height=10)
            
            dpg.add_text("Generation Log:", color=(200, 200, 200, 255))
            with dpg.child_window(height=150, border=True, autosize_x=False):
                self.log_window = dpg.add_text("", wrap=600)
    
    def _browse_track_file(self, sender=None, app_data=None) -> None:
        """Browse track CSV file"""
        self.log("File picker not implemented, please enter path manually", "info")
    
    def _generate_terrain(self, sender=None, app_data=None) -> None:
        """Generate terrain"""
        if self.is_generating:
            self.log("Terrain generation in progress", "warning")
            return
        
        if not self.output_name:
            self.log("Please enter output filename", "error")
            return
        
        self.is_generating = True
        dpg.configure_item(self.generate_button, enabled=False)
        dpg.configure_item(self.progress_bar, show=True)
        dpg.configure_item(self.status_text, default_value="Generating...", color=(255, 200, 0, 255))
        
        cmd_parts = [
            "python", "scripts/generate_terrain.py",
            f"--width={self.width}",
            f"--height={self.height}",
            f"--seed={self.seed}",
            f"--name={self.output_name}",
            f"--noise-scale={self.noise_scale}",
            f"--octaves={self.octaves}",
            f"--persistence={self.persistence}",
            f"--lacunarity={self.lacunarity}",
            f"--height-scale={self.height_scale}",
        ]
        
        if self.use_track:
            cmd_parts.extend([
                f"--track-csv={self.track_csv}",
                f"--corridor-width-px={self.corridor_width}",
                f"--edge-falloff-px={self.edge_falloff}",
            ])
        
        command = " ".join(cmd_parts)
        self.log(f"Command: {command}", "info")
        
        process_mgr = self.get_process_manager()
        if process_mgr:
            import asyncio
            
            def on_output(line: str):
                self.log(line, "info")
                if "DONE" in line or "Complete" in line:
                    dpg.configure_item(self.progress_bar, default_value=1.0)
            
            async def run():
                result = await process_mgr.run_command(
                    "terrain_gen",
                    command,
                    callback=on_output,
                    timeout=300.0
                )
                
                if result.status.value == "completed":
                    dpg.configure_item(self.status_text, default_value="Success!", color=(0, 255, 0, 255))
                    self.log("Terrain generation complete!", "success")
                else:
                    dpg.configure_item(self.status_text, default_value=f"Failed: {result.status.value}", color=(255, 0, 0, 255))
                    self.log(f"Generation failed: {result.stderr}", "error")
                
                dpg.configure_item(self.progress_bar, show=False)
                dpg.configure_item(self.generate_button, enabled=True)
                self.is_generating = False
            
            if hasattr(self.console_app, 'run_async'):
                self.console_app.run_async(run())
            else:
                import subprocess
                try:
                    self.log("Starting generation...", "info")
                    proc = subprocess.Popen(
                        command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True
                    )
                    
                    for line in proc.stdout:
                        self.log(line.strip(), "info")
                    
                    proc.wait()
                    if proc.returncode == 0:
                        dpg.configure_item(self.status_text, default_value="Success!", color=(0, 255, 0, 255))
                        self.log("Terrain generation complete!", "success")
                    else:
                        dpg.configure_item(self.status_text, default_value="Failed", color=(255, 0, 0, 255))
                        self.log("Generation failed", "error")
                except Exception as e:
                    self.log(f"Generation failed: {e}", "error")
                    dpg.configure_item(self.status_text, default_value=f"Error: {e}", color=(255, 0, 0, 255))
                finally:
                    dpg.configure_item(self.generate_button, enabled=True)
                    dpg.configure_item(self.progress_bar, show=False)
                    self.is_generating = False
        else:
            self.log("Process manager not initialized", "error")
            self.is_generating = False
            dpg.configure_item(self.generate_button, enabled=True)
    
    def _open_output_dir(self, sender=None, app_data=None) -> None:
        """Open output directory"""
        import subprocess
        output_dir = "res/terrain"
        import os
        if os.path.exists(output_dir):
            subprocess.run(["open", output_dir] if os.uname().sysname == "Darwin" else ["xdg-open", output_dir])
            self.log(f"Opened directory: {output_dir}", "info")
        else:
            self.log(f"Directory not found: {output_dir}", "warning")
    
    def _view_docs(self, sender=None, app_data=None) -> None:
        """View documentation"""
        self.log("See README.md for terrain generation docs", "info")
    
    def log(self, message: str, level: str = "info") -> None:
        """Log message to UI"""
        self.log_messages.append(f"[{level.upper()}] {message}")
        if len(self.log_messages) > 50:
            self.log_messages = self.log_messages[-50:]
        
        if hasattr(self, 'log_window'):
            dpg.configure_item(self.log_window, default_value="\n".join(self.log_messages))
        
        super().log(message, level)
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        if self.is_generating:
            process_mgr = self.get_process_manager()
            if process_mgr:
                import asyncio
                async def cancel():
                    await process_mgr.kill_process("terrain_gen")
                if hasattr(self.console_app, 'run_async'):
                    self.console_app.run_async(cancel())
