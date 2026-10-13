extends Control

# F1 2D Mount practice scene: renders BjjMountPracticeController's presentation model and forwards
# input to it. It never touches the simulation: no stamina, initiative, grade, position or
# behavior changes happen here, and nothing advances in _process, animation callbacks or timers.
# The only things that move time are the player's Next Window and Submit Decision commands,
# which the controller sends through BjjPositionGraphMatch. Refreshing is a pure read.
const FIGHTER_A_DEFINITION: String = "res://tests/resources/fighter_test_alpha.tres"
const FIGHTER_B_DEFINITION: String = "res://tests/resources/fighter_test_bravo.tres"
const BAND_COLORS: Dictionary = {"Fresh": Color(0.35, 0.8, 0.4), "Working": Color(0.72, 0.85, 0.35),
    "Tired": Color(0.95, 0.65, 0.25), "Exhausted": Color(0.9, 0.3, 0.3)}
const BANNER_COLORS: Dictionary = {"active": Color(0.75, 0.9, 1.0), "terminal": Color(1.0, 0.95, 0.7), "blocked": Color(1.0, 0.8, 0.6)}

var controller: BjjMountPracticeController = BjjMountPracticeController.new()

@onready var mode_option: OptionButton = %ModeOption
@onready var clock_label: Label = %ClockLabel
@onready var banner_panel: PanelContainer = %BannerPanel
@onready var banner_label: Label = %BannerLabel
@onready var axis_bar: ProgressBar = %AxisBar
@onready var axis_label: Label = %AxisLabel
@onready var band_label: Label = %BandLabel
@onready var window_label: Label = %WindowLabel
@onready var technique_header: Label = %TechniqueHeader
@onready var technique_list: ItemList = %TechniqueList
@onready var response_header: Label = %ResponseHeader
@onready var response_list: ItemList = %ResponseList
@onready var commit_option: OptionButton = %CommitOption
@onready var commit_note: Label = %CommitNote
@onready var next_button: Button = %NextWindowButton
@onready var submit_button: Button = %SubmitButton
@onready var new_match_button: Button = %NewMatchButton
@onready var message_label: Label = %MessageLabel
@onready var result_label: Label = %ResultLabel
@onready var event_log: RichTextLabel = %EventLog


func _ready() -> void:
    axis_bar.min_value = BjjMountRules.MIN_AXIS
    axis_bar.max_value = BjjMountRules.MAX_AXIS
    axis_bar.step = 0.1
    for commitment: String in BjjCommitment.ORDER:
        commit_option.add_item(commitment)
    for mode: String in BjjMountPracticeController.MODES:
        mode_option.add_item(BjjMountPracticeController.MODE_LABELS[mode])
    mode_option.item_selected.connect(_on_mode_selected)
    technique_list.item_selected.connect(_on_technique_selected)
    response_list.item_selected.connect(_on_response_selected)
    commit_option.item_selected.connect(_on_commitment_selected)
    next_button.pressed.connect(_on_next_pressed)
    submit_button.pressed.connect(_on_submit_pressed)
    new_match_button.pressed.connect(_on_new_match_pressed)
    _on_new_match_pressed()


func _unhandled_key_input(event: InputEvent) -> void:
    if event is InputEventKey and event.pressed and not event.echo:
        match (event as InputEventKey).keycode:
            KEY_N:
                _on_next_pressed()
            KEY_S:
                _on_submit_pressed()


# --- Input handlers: forward to the controller, then re-read ---------------------------------

func _on_next_pressed() -> void:
    controller.next_window()
    refresh()


func _on_submit_pressed() -> void:
    controller.submit_decision()
    refresh()


func _on_new_match_pressed() -> void:
    controller.start_new_match(load(FIGHTER_A_DEFINITION), load(FIGHTER_B_DEFINITION))
    refresh()


func _on_mode_selected(index: int) -> void:
    controller.set_practice_mode(BjjMountPracticeController.MODES[index])
    refresh()


func _on_technique_selected(index: int) -> void:
    controller.select_action(str(technique_list.get_item_metadata(index)))
    refresh()


func _on_response_selected(index: int) -> void:
    controller.select_response(str(response_list.get_item_metadata(index)))
    refresh()


func _on_commitment_selected(index: int) -> void:
    controller.select_commitment(commit_option.get_item_text(index))
    refresh()


# --- Rendering: a pure read of the controller's model ----------------------------------------

func refresh() -> void:
    var view: Dictionary = controller.view()
    if not view.has_match:
        message_label.text = "No practice match."
        return
    var seconds: int = view.clock_seconds
    mode_option.select(BjjMountPracticeController.MODES.find(view.mode))
    clock_label.text = "Clock %d:%02d remaining (%d s of %d)" % [floori(seconds / 60.0), seconds % 60, seconds, view.initial_clock]
    banner_label.text = view.banner
    banner_panel.self_modulate = BANNER_COLORS[view.status_kind]
    _fill_fighter("FighterA", view.fighters[0])
    _fill_fighter("FighterB", view.fighters[1])
    axis_bar.value = view.axis
    axis_label.text = "Axis %.1f (positive = Top control)" % view.axis
    band_label.text = "Band: %s" % view.band_name
    window_label.text = _window_text(view)
    _fill_list(technique_list, view.actions)
    _fill_list(response_list, view.responses)
    technique_header.text = _technique_header(view)
    response_header.text = _response_header(view)
    _fill_commitment(view.commitment)
    next_button.disabled = not view.commands.next_window.enabled
    submit_button.disabled = not view.commands.submit.enabled
    next_button.tooltip_text = view.commands.next_window.reason
    submit_button.tooltip_text = view.commands.submit.reason
    new_match_button.disabled = not view.commands.new_match.enabled
    message_label.text = "%s  [practice match #%d]" % [view.last_message, view.match_serial]
    result_label.text = "\n".join(view.last_lines) if not view.last_lines.is_empty() else "No decision yet."
    event_log.text = "\n".join(view.events)


func _fill_fighter(prefix: String, snapshot: Dictionary) -> void:
    (get_node("%" + prefix + "Name") as Label).text = snapshot.display_name
    (get_node("%" + prefix + "Role") as Label).text = "Role: %s" % String(snapshot.role).capitalize()
    var bar: ProgressBar = get_node("%" + prefix + "StaminaBar")
    bar.max_value = snapshot.stamina_maximum
    bar.value = snapshot.stamina_current
    bar.self_modulate = BAND_COLORS.get(snapshot.exhaustion_band, Color.WHITE)
    (get_node("%" + prefix + "StaminaLabel") as Label).text = "Stamina %d / %d - %s" % [snapshot.stamina_current, snapshot.stamina_maximum, snapshot.exhaustion_band]
    (get_node("%" + prefix + "Behavior") as Label).text = "Behavior: %s" % snapshot.behavior
    (get_node("%" + prefix + "Identity") as Label).text = "%s (template %s)" % [snapshot.fighter_id, snapshot.definition_id]


func _window_text(view: Dictionary) -> String:
    var window: Dictionary = view.window
    if view.status_kind != "active":
        return "No window: the match is not active."
    if not window.open:
        return "No window open. Press Next Window."
    var text := "Window #%d: %s (%s) decides." % [window.window_id, window.owner_name, String(window.role).capitalize()]
    if window.scripted:
        text += " SCRIPTED practice behavior: the existing no-action Bottom decision (its held behavior still drives time and stamina)."
    elif window.two_sided_bottom:
        text += " Two-sided practice: you choose Bottom's technique and the Top's response, or No action (the engine's existing Bottom decision: a reset or a recovery hold)."
    return text


func _technique_header(view: Dictionary) -> String:
    var window: Dictionary = view.window
    if view.status_kind != "active" or not window.open:
        return "Techniques (open a window first)"
    if window.scripted:
        return "%s's legal techniques (informational only)" % window.owner_name
    if window.two_sided_bottom:
        return "Choose %s's technique (or No action)" % window.owner_name
    return "Choose %s's technique" % window.owner_name


func _response_header(view: Dictionary) -> String:
    if view.status_kind != "active" or not view.window.open:
        return "Opponent response (open a window first)"
    if view.window.scripted:
        return "No response choice in a scripted Bottom window"
    if view.window.two_sided_bottom:
        if view.no_action_selected:
            return "No Top response: No action was chosen"
        if view.responses.is_empty():
            return "Top's response (choose a Bottom technique first)"
        return "Top's response to the selected Bottom technique"
    return "Opponent response (choose a technique first)" if view.responses.is_empty() else "Opponent response to the selected technique"


func _fill_list(list: ItemList, rows: Array) -> void:
    list.clear()
    for row: Dictionary in rows:
        var text: String = row.name
        if not row.available:
            # The exact engine reason comes first so a narrow list can never clip it.
            text = "[unavailable: %s]  %s" % [row.reason, row.name]
        var index: int = list.add_item(text)
        list.set_item_metadata(index, row.id)
        list.set_item_tooltip(index, row.get("hint", row.id))
        list.set_item_disabled(index, not row.available)
        list.set_item_selectable(index, row.available)
        if row.selected:
            list.select(index)


func _fill_commitment(commitment: Dictionary) -> void:
    commit_option.disabled = not commitment.selectable
    commit_option.select(commitment.options.find(commitment.selected))
    commit_note.text = "Top's commitment (policy default %s)" % commitment.policy_selected if commitment.selectable \
        else "Selectable only for the Top fighter's window; Bottom's is policy-selected (%s)." % commitment.policy_selected
