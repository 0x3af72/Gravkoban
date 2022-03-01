import blocks
import json
import string
from map_helper import loadMap
from ursina import *
from ursina.curve import *
from ursina.prefabs.slider import ThinSlider

map_selections_up = False

class FadeTransition:
    def __init__(self, fill_duration, fade_duration, mid_duration, color, text, audio, filename):

        # entity
        self.entity = Entity(
            model  = "quad",
            parent = camera.ui,
            scale = 5,
            z = -100,
            color = color,
            alpha = 0,
        )

        # text
        self.text_entity = Text(
            text,
            origin = (0, 0),
            scale = 2,
            z = -101,
            alpha = 0,
        )

        # audio
        if audio:
            invoke(Audio, sound_file_name = filename, auto_destroy = True, delay = fill_duration - 0.2)

        # animations
        self.entity.animate("alpha", 1, fill_duration, curve = linear)
        self.entity.animate("alpha", 0, fade_duration, delay = fill_duration + mid_duration, curve = linear)
        destroy(self.entity, delay = fill_duration + fade_duration + mid_duration)

        self.text_entity.animate("alpha", 1, fill_duration, curve = linear)
        self.text_entity.animate("alpha", 0, fade_duration, delay = fill_duration + mid_duration, curve = linear)
        destroy(self.text_entity, delay = fill_duration + fade_duration + mid_duration)

class Notification:
    def __init__(self, text, position, color, duration):

        # entity
        self.text_entity = Text(
            text,
            position = position,
            color = color,
        )

        # center text
        self.text_entity.x -= self.text_entity.width / 2

        # animations
        self.text_entity.animate("alpha", 0, duration = duration, curve = linear)
        self.text_entity.animate("y", self.text_entity.y + 0.1, duration = duration, curve = out_expo)
        destroy(self.text_entity, delay = duration)

def _menuBlockAt(board, menu_blocks, entity_type, name, x, y, texture = None, **kwargs):
    menu_blocks[name] = blocks.CustomBlock(entity_type, x, y, 0, texture, **kwargs)
    board[x, y, 0] = menu_blocks[name]

def _updateText(text, menu_ui, template, audio = True, filename = "audio/count.mp3"):
    
    if text in menu_ui:
        value = int(menu_ui[text].value)
        menu_ui[text].text = template.replace("<VALUE>", str(value))

        # sound effect
        if audio and menu_ui[text].old < value:
            Audio(filename, auto_destroy = True)

        menu_ui[text].old = value

def createMenuScene(board, menu_blocks):

    # clear board and entities
    for key, block in board.items():
        if hasattr(block, "entity"):
            destroy(block.entity)
        elif key in ("max_moves", "max_moved", "map_name"):
            continue
        else: # portal
            block[1].removed = True
            destroy(block[1].entity)
    board.clear()

    # blank map
    board.update(loadMap(""))

    # menu start and end points
    board["start"] = [(10, 5), blocks.PortalBlock(10, 5, color.green)]
    board["end"] = [(1, 5), blocks.PortalBlock(1, 5, color.red)]

    # portal to go to mapping
    board["mapping"] = [(5, 1), blocks.PortalBlock(5, 1, color.yellow)]

    # map block
    _menuBlockAt(
        board, menu_blocks,
        Entity,
        "map_block",
        6, 5,
        "models/map_block/map_block.png",
        tooltip = Tooltip("Click to select a map.\n\nMove this block to the start slot to start the game.", scale = 0.5),
        selected = "",
    )

def clearMenuStuff(menu_blocks, board, menu_ui):

    # clear menu blocks
    menu_blocks.clear()

    # clear board and entities
    for block in board.values():
        if hasattr(block, "entity"):
            destroy(block.entity)
        else: # portal
            block[1].removed = True
            destroy(block[1].entity)
    board.clear()

    # clear menu ui
    for ui_entity in menu_ui.values():
        destroy(ui_entity)
    menu_ui.clear()

def startGame(board, map, menu_blocks, game_ui, menu_ui):
    
    # clear menu stuff
    clearMenuStuff(menu_blocks, board, menu_ui)

    # load map
    board.update(loadMap(f"maps/{map}.json"))

    # player speed slider
    game_ui["duration_slider"] = ThinSlider(
        min = 0,
        max = 1,
        step = 0.1,
        position = (0.49, 0.45),
        scale = 0.7,
        default = 0.3,
        text = "Player move duration: ",
    )

    # max moves counter
    game_ui["moves_counter"] = Text(
        f"Moves left: {board['max_moves']}",
        position = (-0.85, 0.45),
        scale = 0.7,
    )

def endGame(game_ui, menu_ui, moves_taken, objects_moved, moves_exceeded, map_name):

    # clear game ui
    for ui_entity in game_ui.values():
        destroy(ui_entity)
    game_ui.clear()

    # highscore
    with open("highscores/highscores.json", "r") as read_highscores:

        # parse to dict
        highscores = json.load(read_highscores)

    # add highscore if not inside already
    if (not map_name in highscores) or (highscores[map_name] > moves_taken):

        # save highscore
        highscores[map_name] = moves_taken

        menu_ui["highscore"] = Text(
            f"New Highscore: {moves_taken} moves taken",
            color = color.yellow,
            position = (-0.85, 0.15),
        )

        # highscore sound
        Audio("audio/bell.mp3", auto_destroy = True)

        # save file
        with open("highscores/highscores.json", "w") as write_highscores:
            json.dump(highscores, write_highscores)

    else:

        menu_ui["highscore"] = Text(
            f"Highscore: {highscores[map_name]} moves taken",
            position = (-0.85, 0.15),
        )

    # moves taken
    menu_ui["moves_taken"] = Text(
        "Moves taken: 0",
        value = 0,
        position = (-0.85, 0.07),
        color = color.red if moves_exceeded else color.white,
        old = 0,
    )
    menu_ui["moves_taken"].animate("value", moves_taken, duration = 3, curve = linear)
    for i in range(80):
        invoke(_updateText, delay = i * 0.05, text = "moves_taken", menu_ui = menu_ui, template = "Moves taken: <VALUE>")

    # objects moved
    menu_ui["objects_moved"] = Text(
        "Objects pushed: 0",
        value = 0,
        old = 0,
        position = (-0.85, -0.01),
    )
    menu_ui["objects_moved"].animate("value", objects_moved, duration = 3, curve = linear)
    for i in range(80):
        invoke(_updateText, delay = i * 0.05, text = "objects_moved", menu_ui = menu_ui, template = "Objects pushed: <VALUE>")

def toggleMapSelections(selection_ui, off = False):

    # selections
    map_selections = [os.path.splitext(file)[0] for file in os.listdir("maps")]

    global map_selections_up
    if not map_selections_up and not off: # not up, open map selections

        # clear current ui
        selection_ui.clear()

        # selection background
        selection_ui["selection_background"] = Entity(
            model = "quad",
            parent = camera.ui,
            color = (0.2, 0.2, 0.2, 0.2),
            position = (0.49, 0.5, 1),
            scale = (0.55, 3),
        )

        for index, map in enumerate(map_selections):
            selection_ui[map] = Button(
                text = map,
                position = (0.5, index * 0.1 - 0.3),
                scale = (0.5, 0.1),
                map = map,
                tooltip = Tooltip(text = f"Select {map}", scale = 0.5),
            )

    else: # up already, destroy map selections

        # destroy selection entities
        for ui_entity in selection_ui.values():
            destroy(ui_entity)
        selection_ui.clear()

    map_selections_up = not map_selections_up
    return map_selections_up

def createMappingScene(board, mapping_ui):
    
    # default board
    board.update(loadMap(""))

    # ui backgrounds
    mapping_ui["background_left"] = Entity(
        model = "quad",
        parent = camera.ui,
        position = (-0.62, -0.5),
        scale = (0.45, 3),
        z = 2,
        color = (0.2, 0.2, 0.2, 0.4),
    )

    mapping_ui["background_right"] = Entity(
        model = "quad",
        parent = camera.ui,
        position = (0.62, -0.5),
        scale = (0.45, 3),
        z = 2,
        color = (0.2, 0.2, 0.2, 0.4),
    )

    # inputfield for map name
    mapping_ui["name_field"] = InputField(
        "Untitled Map",
        position = (-0.62, 0.45),
        character_limit = 23,
        limit_content_to = string.ascii_letters + string.digits + "!,().[]}{ ",
        prev = None,
    )
    mapping_ui["name_field"].scale *= (0.85, 1, 1)

    # save button
    mapping_ui["save_button"] = Entity(
        model = "quad",
        texture = "images/save_button.png",
        parent = camera.ui,
        position = (-0.78, 0.38),
        scale = 0.06,
        collider = "box",
    )

    # exit button
    mapping_ui["exit_button"] = Entity(
        model = "quad",
        texture = "images/exit_button.png",
        parent = camera.ui,
        position = (-0.70, 0.38),
        scale = 0.06,
        collider = "box",
    )

    # clear button
    mapping_ui["clear_button"] = Entity(
        model = "quad",
        texture = "images/clear_map.png",
        parent = camera.ui,
        position = (-0.62, 0.38),
        scale = 0.07,
        collider = "box",
        color = color.white,
    )

    # text for loading map
    mapping_ui["load_map_text"] = Text(
        "Load map",
        position = (0.41, 0.47),
        scale = 1,
    )

    # inputfield for loading map
    mapping_ui["load_map_input"] = InputField(
        "",
        position = (0.62, 0.40),
        character_limit = 23,
    )
    mapping_ui["load_map_input"].scale *= (0.85, 1, 1)

    # load map button
    mapping_ui["load_map_button"] = Entity(
        model = "quad",
        texture = "images/load_map.png",
        parent = camera.ui,
        position = (0.44, 0.32),
        scale = 0.06,
        collider = "box",
    )

    # select buttons
    mapping_ui["crate"] = Entity(
        model = "quad",
        texture = "models/crate/crate.jpg",
        parent = camera.ui,
        position = (-0.78, 0),
        scale = 0.08,
        collider = "box",
    )

    mapping_ui["direction_block"] = Entity(
        model = "quad",
        texture = "models/direction_block/thumbnail.jpg",
        parent = camera.ui,
        position = (-0.68, 0),
        scale = 0.08,
        collider = "box",
    )

    mapping_ui["wall"] = Entity(
        model = "quad",
        texture = "models/wall/wall.png",
        parent = camera.ui,
        position = (-0.58, 0),
        scale = 0.08,
        collider = "box",
    )

    # block actions header
    mapping_ui["actions_header"] = Text(
        "Actions",
        position = (0.42, 0.08),
        scale = 1,
    )

    # confirm button
    mapping_ui["confirm_button"] = Entity(
        model = "quad",
        texture = "images/confirm.png",
        parent = camera.ui,
        position = (0.44, 0),
        scale = 0.06,
        collider = "box",
    )

    # cancel button
    mapping_ui["cancel_button"] = Entity(
        model = "quad",
        texture = "images/cancel.png",
        parent = camera.ui,
        position = (0.52, 0),
        scale = 0.06,
        collider = "box",
    )

    # delete button
    mapping_ui["delete_button"] = Entity(
        model = "quad",
        texture = "images/delete.png",
        parent = camera.ui,
        position = (0.6, 0),
        scale = 0.06,
        collider = "box",
    )
    
    # block outline entity (idk why this is in mapping ui)
    mapping_ui["block_outline"] = Entity(
        model = "models/block_outline/block_outline",
        color = color.green,
        scale = 0.13,
        visible = False,
    )

    # portal buttons
    mapping_ui["start_portal"] = Entity(
        model = "models/portal/portal",
        parent = camera.ui,
        color = color.green,
        scale = 0.035,
        position = (-0.78, -0.1),
        rotation_x = 90,
        collider = "box",
    )

    mapping_ui["end_portal"] = Entity(
        model = "models/portal/portal",
        parent = camera.ui,
        color = color.red,
        scale = 0.035,
        position = (-0.68, -0.1),
        rotation_x = 90,
        collider = "box",
    )

    # max moves input and text
    mapping_ui["max_moves_text"] = Text(
        "Max moves taken",
        position = (-0.83, 0.32),
        scale = 0.7,
    )

    mapping_ui["max_moves_input"] = InputField(
        "1000",
        position = (-0.62, 0.26),
        character_limit = 23,
        prev = None,
        limit_content_to = "0123456789",
    )
    mapping_ui["max_moves_input"].scale *= (0.85, 1, 1)

    # max moved input and text
    mapping_ui["max_moved_text"] = Text(
        "Max moved blocks per move",
        position = (-0.83, 0.18),
        scale = 0.7,
    )

    mapping_ui["max_moved_input"] = InputField(
        "1000",
        position = (-0.62, 0.12),
        character_limit = 23,
        prev = None,
        limit_content_to = "0123456789",
    )
    mapping_ui["max_moved_input"].scale *= (0.85, 1, 1)

def clearMappingScene(mapping_ui):
    
    # clear mapping ui
    for ui_entity in mapping_ui.values():
        destroy(ui_entity)
    mapping_ui.clear()

def fadeTransition(fill_duration, fade_duration, mid_duration, color, func, text = "", audio = True, filename = "audio/woosh.mp3"):
    FadeTransition(fill_duration, fade_duration, mid_duration, color, text, audio, filename)
    invoke(func, delay = fill_duration)

def notifAt(text, position = (0.6, -0.42), color = color.white, duration = 2, audio = True, filename = "audio/notification.mp3"):
    Notification(text, position, color, duration)

    if audio:
        Audio(filename, auto_destroy = True)

def clickAnimation(button, small = 0.045, original = 0.06, audio = False, filename = "audio/pop.mp3"):
    button.scale = small
    invoke(lambda: setattr(button, "scale", original), delay = 0.1)

    if audio: # i dont think we want the pop sound effect...
        Audio(filename, auto_destroy = True, volume = 0.2)