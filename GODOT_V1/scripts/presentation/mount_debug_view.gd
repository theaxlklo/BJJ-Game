extends Node3D

# Visual-only greybox. Cameras and rendering do not drive BJJ game outcomes.
@onready var match_camera: Camera3D = $Camera3D
@onready var hud: Label = $CanvasLayer/MarginContainer/VBoxContainer/Hint


func _ready() -> void:
    _set_camera(1)


func _unhandled_key_input(event: InputEvent) -> void:
    if event is InputEventKey and event.pressed and not event.echo:
        var key_event: InputEventKey = event as InputEventKey
        match key_event.keycode:
            KEY_1:
                _set_camera(1)
            KEY_2:
                _set_camera(2)
            KEY_3:
                _set_camera(3)


func _set_camera(preset: int) -> void:
    match preset:
        1:
            match_camera.position = Vector3(0.0, 5.0, 8.0)
        2:
            match_camera.position = Vector3(6.0, 3.5, 4.0)
        3:
            match_camera.position = Vector3(0.0, 8.0, 0.5)
    match_camera.look_at(Vector3(0.0, 0.65, 0.0), Vector3.UP)
    hud.text = "BJJ Game GODOT_V1 | Mount 3D greybox | Camera: %d (keys 1 / 2 / 3)\nNo match engine connected yet. Run headless Mount slice tests separately." % preset
