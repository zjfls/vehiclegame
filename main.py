from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.showbase.DirectObject import DirectObject
from panda3d.core import *
from direct.gui.OnscreenText import OnscreenText
import math

class RacingGame(ShowBase):
    def __init__(self):
        super().__init__()
        self.setBackgroundColor(0.15, 0.18, 0.22)

        # Game settings
        self.is_running = True
        self.speed = 0.0
        self.max_speed = 80.0
        self.acceleration = 40.0
        self.deceleration = 25.0
        self.turn_speed = 120.0
        self.car_heading = 0.0
        
        # Car position (for actual movement)
        self.car_pos = [0, 0, 0.6]

        # Input state
        self.keys = {
            "up": False,
            "down": False,
            "left": False,
            "right": False
        }

        # Setup game
        self.setup_lights()
        self.setup_scene()
        self.setup_car()
        self.setup_camera()
        self.setup_inputs()
        self.setup_ui()

        # Add update task
        self.taskMgr.add(self.update, "UpdateTask")

        print("Racing game initialized!")

    def setup_lights(self):
        """Setup scene lighting"""
        ambient_light = AmbientLight("ambient_light")
        ambient_light.setColor((0.4, 0.4, 0.45, 1))
        ambient_np = self.render.attachNewNode(ambient_light)
        self.render.setLight(ambient_np)

        directional_light = DirectionalLight("directional_light")
        directional_light.setColor((0.9, 0.85, 0.8, 1))
        directional_light.setDirection((0.5, -0.8, -0.3))
        directional_np = self.render.attachNewNode(directional_light)
        self.render.setLight(directional_np)

        self.render.setShaderAuto()

    def setup_scene(self):
        """Setup the racing track and ground"""
        # Ground
        cm = CardMaker("ground")
        cm.setFrame(-200, 200, -200, 200)
        self.ground = self.render.attachNewNode(cm.generate())
        self.ground.setP(-90)
        self.ground.setPos(0, 0, 0)
        self.ground.setColor(0.15, 0.18, 0.15, 1)

        # Track center line
        cm_line = CardMaker("track_line")
        cm_line.setFrame(-1.2, 1.2, -200, 200)
        self.track_line = self.render.attachNewNode(cm_line.generate())
        self.track_line.setP(-90)
        self.track_line.setPos(0, 0, 0.01)
        self.track_line.setColor(0.25, 0.25, 0.3, 1)

        # Track borders
        for x_offset in [-15, 15]:
            cm_border = CardMaker(f"border_{x_offset}")
            cm_border.setFrame(-1.5, 1.5, -200, 200)
            border = self.render.attachNewNode(cm_border.generate())
            border.setP(-90)
            border.setPos(x_offset, 0, 0.02)
            border.setColor(0.7, 0.1, 0.1, 1)

        # Track markers
        for i in range(-150, 151, 30):
            marker = self.loader.loadModel("box")
            marker.reparentTo(self.render)
            marker.setScale(1, 1, 1)
            marker.setPos(15, i, 0.5)
            marker.setColor(0.9, 0.15, 0.15, 1)

            marker2 = self.loader.loadModel("box")
            marker2.reparentTo(self.render)
            marker2.setScale(1, 1, 1)
            marker2.setPos(-15, i, 0.5)
            marker2.setColor(0.1, 0.15, 0.9, 1)

    def setup_car(self):
        """Setup a better looking racing car"""
        self.car_root = self.render.attachNewNode("car_root")
        self.car_root.setPos(self.car_pos[0], self.car_pos[1], self.car_pos[2])

        # Main body - lower chassis (wider at bottom)
        chassis = self.loader.loadModel("box")
        chassis.reparentTo(self.car_root)
        chassis.setScale(1.6, 3.2, 0.5)
        chassis.setPos(0, 0, -0.2)
        chassis.setColor(0.8, 0.1, 0.1, 1)

        # Upper body
        upper_body = self.loader.loadModel("box")
        upper_body.reparentTo(self.car_root)
        upper_body.setScale(1.4, 2.8, 0.4)
        upper_body.setPos(0, 0, 0.15)
        upper_body.setColor(0.85, 0.12, 0.12, 1)

        # Cabin/roof
        cabin = self.loader.loadModel("box")
        cabin.reparentTo(self.car_root)
        cabin.setScale(1.0, 1.4, 0.5)
        cabin.setPos(0, -0.3, 0.6)
        cabin.setColor(0.2, 0.2, 0.3, 1)

        # Hood
        hood = self.loader.loadModel("box")
        hood.reparentTo(self.car_root)
        hood.setScale(1.3, 0.8, 0.15)
        hood.setPos(0, 1.0, 0.35)
        hood.setColor(0.8, 0.1, 0.1, 1)

        # Trunk
        trunk = self.loader.loadModel("box")
        trunk.reparentTo(self.car_root)
        trunk.setScale(1.3, 0.6, 0.15)
        trunk.setPos(0, -1.1, 0.35)
        trunk.setColor(0.8, 0.1, 0.1, 1)

        # Spoiler
        spoiler_base = self.loader.loadModel("box")
        spoiler_base.reparentTo(self.car_root)
        spoiler_base.setScale(0.1, 0.3, 0.3)
        spoiler_base.setPos(0, -1.4, 0.6)
        spoiler_base.setColor(0.1, 0.1, 0.1, 1)

        spoiler_wing = self.loader.loadModel("box")
        spoiler_wing.reparentTo(self.car_root)
        spoiler_wing.setScale(1.4, 0.2, 0.1)
        spoiler_wing.setPos(0, -1.4, 0.85)
        spoiler_wing.setColor(0.1, 0.1, 0.1, 1)

        # Headlights
        headlight_left = self.loader.loadModel("box")
        headlight_left.reparentTo(self.car_root)
        headlight_left.setScale(0.25, 0.1, 0.15)
        headlight_left.setPos(-0.5, 1.6, 0.25)
        headlight_left.setColor(1, 1, 0.8, 1)

        headlight_right = self.loader.loadModel("box")
        headlight_right.reparentTo(self.car_root)
        headlight_right.setScale(0.25, 0.1, 0.15)
        headlight_right.setPos(0.5, 1.6, 0.25)
        headlight_right.setColor(1, 1, 0.8, 1)

        # Taillights
        taillight_left = self.loader.loadModel("box")
        taillight_left.reparentTo(self.car_root)
        taillight_left.setScale(0.25, 0.1, 0.15)
        taillight_left.setPos(-0.5, -1.6, 0.25)
        taillight_left.setColor(0.9, 0.1, 0.1, 1)

        taillight_right = self.loader.loadModel("box")
        taillight_right.reparentTo(self.car_root)
        taillight_right.setScale(0.25, 0.1, 0.15)
        taillight_right.setPos(0.5, -1.6, 0.25)
        taillight_right.setColor(0.9, 0.1, 0.1, 1)

        # Wheels - using cylinders would be better but box is available
        wheel_positions = [
            (-0.9, 1.3, -0.35),
            (0.9, 1.3, -0.35),
            (-0.9, -1.3, -0.35),
            (0.9, -1.3, -0.35)
        ]

        self.wheels = []
        for i, pos in enumerate(wheel_positions):
            wheel = self.loader.loadModel("box")
            wheel.reparentTo(self.car_root)
            # Make wheels look more like wheels (wider, shorter)
            if i % 2 == 0:  # Left wheels
                wheel.setScale(0.25, 0.5, 0.5)
            else:  # Right wheels
                wheel.setScale(0.25, 0.5, 0.5)
            wheel.setPos(pos[0], pos[1], pos[2])
            wheel.setColor(0.1, 0.1, 0.1, 1)
            self.wheels.append(wheel)

        # Store car parts for reference
        self.car_parts = {
            'chassis': chassis,
            'upper_body': upper_body,
            'cabin': cabin,
            'hood': hood,
            'trunk': trunk,
            'spoiler_base': spoiler_base,
            'spoiler_wing': spoiler_wing,
            'headlight_left': headlight_left,
            'headlight_right': headlight_right,
            'taillight_left': taillight_left,
            'taillight_right': taillight_right
        }

    def setup_camera(self):
        """Setup the camera to follow car"""
        self.camera_distance = 20
        self.camera_height = 12
        self.camera.setPos(0, -self.camera_distance, self.camera_height)
        self.camera.lookAt(0, 0, 1)

    def setup_inputs(self):
        """Setup keyboard input handling"""
        self.accept("w", self.set_key, ["up", True])
        self.accept("w-up", self.set_key, ["up", False])
        self.accept("s", self.set_key, ["down", True])
        self.accept("s-up", self.set_key, ["down", False])
        self.accept("a", self.set_key, ["left", True])
        self.accept("a-up", self.set_key, ["left", False])
        self.accept("d", self.set_key, ["right", True])
        self.accept("d-up", self.set_key, ["right", False])

        self.accept("arrow_up", self.set_key, ["up", True])
        self.accept("arrow_up-up", self.set_key, ["up", False])
        self.accept("arrow_down", self.set_key, ["down", True])
        self.accept("arrow_down-up", self.set_key, ["down", False])
        self.accept("arrow_left", self.set_key, ["left", True])
        self.accept("arrow_left-up", self.set_key, ["left", False])
        self.accept("arrow_right", self.set_key, ["right", True])
        self.accept("arrow_right-up", self.set_key, ["right", False])

        self.accept("escape", self.exit_game)

    def setup_ui(self):
        """Setup UI elements"""
        self.speed_text = OnscreenText(
            text="Speed: 0 km/h",
            pos=(-0.9, 0.9),
            scale=0.07,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft
        )

        self.instructions = OnscreenText(
            text="W/S - Accelerate/Brake  |  A/D - Steer  |  ESC - Exit",
            pos=(0, -0.9),
            scale=0.05,
            fg=(0.8, 0.8, 0.8, 1),
            align=TextNode.ACenter
        )

    def set_key(self, key, value):
        """Set key state"""
        self.keys[key] = value

    def update_car_transform(self):
        """Update car position and rotation"""
        self.car_root.setPos(self.car_pos[0], self.car_pos[1], self.car_pos[2])
        self.car_root.setH(self.car_heading)

    def update_camera(self):
        """Update camera position to follow car"""
        angle = math.radians(self.car_heading)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        # Camera follows behind the car
        cam_x = self.car_pos[0] - sin_a * self.camera_distance
        cam_y = self.car_pos[1] + cos_a * self.camera_distance

        self.camera.setPos(cam_x, cam_y, self.camera_height)
        self.camera.lookAt(self.car_pos[0], self.car_pos[1], 1)

    def update(self, task):
        """Main game update loop"""
        dt = globalClock.getDt()

        # Handle acceleration/deceleration
        if self.keys["up"]:
            self.speed += self.acceleration * dt
        elif self.keys["down"]:
            self.speed -= self.deceleration * dt
        else:
            # Natural deceleration
            if self.speed > 0:
                self.speed -= self.deceleration * 0.3 * dt
                if self.speed < 0:
                    self.speed = 0
            elif self.speed < 0:
                self.speed += self.deceleration * 0.3 * dt
                if self.speed > 0:
                    self.speed = 0

        # Clamp speed
        self.speed = max(-self.max_speed * 0.3, min(self.speed, self.max_speed))

        # Handle steering (only when moving)
        if abs(self.speed) > 0.5:
            turn_factor = min(abs(self.speed) / 20, 1.0)
            if self.keys["left"]:
                self.car_heading += self.turn_speed * dt * turn_factor
            if self.keys["right"]:
                self.car_heading -= self.turn_speed * dt * turn_factor

        # ACTUALLY MOVE THE CAR based on speed and heading
        if abs(self.speed) > 0:
            angle = math.radians(self.car_heading)
            # Move forward in the direction car is facing
            self.car_pos[0] += math.sin(angle) * self.speed * dt
            self.car_pos[1] += math.cos(angle) * self.speed * dt

        # Update car visual
        self.update_car_transform()

        # Update camera
        self.update_camera()

        # Update UI
        self.speed_text.setText(f"Speed: {abs(int(self.speed))} km/h")

        return Task.cont

    def exit_game(self):
        """Exit the game"""
        self.is_running = False
        self.userExit()

if __name__ == "__main__":
    game = RacingGame()
    game.run()
