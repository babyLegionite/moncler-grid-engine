# InfectionHUD.gd
# Per-player HUD: health, shield, ammo, round timer, team indicator, status
extends Control
class_name InfectionHUD

@export var player_index: int = 0

# UI elements
var health_bar: ProgressBar
var shield_bar: ProgressBar
var ammo_label: Label
var timer_label: Label
var team_label: Label
var status_label: Label
var score_label: Label

func _ready() -> void:
	setup_hud()

func setup_hud() -> void:
	# Main VBox container
	var container = VBoxContainer.new()
	container.set_anchors_preset(Control.PRESET_FULL_RECT)
	container.add_theme_constant_override("separation", 4)
	add_child(container)

	# Team and status
	team_label = Label.new()
	team_label.text = "HUMAN"
	team_label.add_theme_color_override("font_color", Color.GREEN)
	team_label.add_theme_font_size_override("font_size", 18)
	container.add_child(team_label)

	status_label = Label.new()
	status_label.text = ""
	status_label.add_theme_color_override("font_color", Color.YELLOW)
	status_label.add_theme_font_size_override("font_size", 14)
	container.add_child(status_label)

	# Score
	score_label = Label.new()
	score_label.text = "K: 0 D: 0"
	score_label.add_theme_font_size_override("font_size", 12)
	container.add_child(score_label)

	# Shield bar
	shield_bar = ProgressBar.new()
	shield_bar.max_value = 100
	shield_bar.value = 100
	shield_bar.add_theme_color_override("font_color", Color.CYAN)
	shield_bar.size_flags_horizontal = Control.SIZE_FILL
	container.add_child(shield_bar)

	# Health bar
	health_bar = ProgressBar.new()
	health_bar.max_value = 100
	health_bar.value = 100
	health_bar.add_theme_color_override("font_color", Color.RED)
	health_bar.size_flags_horizontal = Control.SIZE_FILL
	container.add_child(health_bar)

	# Ammo
	ammo_label = Label.new()
	ammo_label.text = "32 / 288"
	ammo_label.add_theme_font_size_override("font_size", 14)
	container.add_child(ammo_label)

	# Timer
	timer_label = Label.new()
	timer_label.text = "3:00"
	timer_label.add_theme_font_size_override("font_size", 16)
	container.add_child(timer_label)

func update_health(health: float, shield: float) -> void:
	health_bar.value = health
	shield_bar.value = shield

func update_ammo(current: int, reserve: int) -> void:
	ammo_label.text = "%d / %d" % [current, reserve]

func update_timer(minutes: int, seconds: int) -> void:
	timer_label.text = "%d:%02d" % [minutes, seconds]

func update_team(team: String) -> void:
	team_label.text = team.to_upper()
	if team == "infected":
		team_label.add_theme_color_override("font_color", Color.ORANGE_RED)
	else:
		team_label.add_theme_color_override("font_color", Color.GREEN)

func update_status(status: String) -> void:
	status_label.text = status

func update_score(kills: int, deaths: int) -> void:
	score_label.text = "K: %d D: %d" % [kills, deaths]

func show_last_man_standing() -> void:
	status_label.text = "LAST MAN STANDING"
	status_label.add_theme_color_override("font_color", Color.GOLD)
	status_label.add_theme_font_size_override("font_size", 20)

func show_dead() -> void:
	status_label.text = "YOU ARE DEAD"
	status_label.add_theme_color_override("font_color", Color.RED)