import blocks
import os
import game_functions
import map_helper
import json
from map_helper import boardToJson
from layered_glow import layeredGlow
from time import time_ns
from clouds import Cloud
from ursina import *
from ursina.curve import *
from projector_shader import *

# setup window
app = Ursina()
window.exit_button.visible = False
window.size = window.fullscreen_size
window.position = (1, 1)
window.title = "Gravkoban"
window.fps_counter.visible = False

# init projector shader
projector_texture = load_texture("vignette", application.internal_textures_folder)
projector_texture.repeat = False
projector_shader.default_input["projector_texture"] = projector_texture
projector_shader.default_input["projector_uv_scale"] = Vec2(0.005, 0.005)

# textures
Texture.default_filtering = "mipmap"

# fonts
Text.default_font = "fonts/caveman.ttf"

# move a block
def moveBlock(board, coordinate, new, duration):

    # change entities positions
    new_position = ((new[0] - 6) * 10 + 5, new[2] * 10, (-new[1] + 5) * 10 + 5)
    board[coordinate].entity.animate("position", new_position, duration, curve = linear)
    board[coordinate].x = new[0]
    board[coordinate].y = new[1]
    if new in board:
        destroy(board[new].entity)

    # change coordinates
    board[new] = board[coordinate]
    if coordinate[2] == 0:
        board[(coordinate[0], coordinate[1]) + (0,)] = blocks.NullBlock(*coordinate[:2])
    
    # delete if its a gravity block
    if coordinate[2] > 0:
        del board[coordinate]

# setup scene
board_entity = Entity(
    model = "models/board/board",
    position = (0, -5, 0),
    scale = (60, 1, 60),
    texture = "models/board/board.jpg",
    shader = projector_shader,
)

ground_entity = Entity(
    model = "cube",
    position = (0, -6, 0),
    scale = (200, 1, 200),
    texture_scale = (20, 20),
    texture = "models/ground/ground.jpg",
    shader = projector_shader,
)

Sky(color = color.black)

# position camera
editor_camera = EditorCamera()
editor_camera.rotation = (40, 0, 0)
editor_camera.target_z = -290
editor_camera.rotation_speed = 0
editor_camera.zoom_speed = 0
editor_camera.pan_speed = (0, 0)
editor_camera.hotkeys["focus"] = "THISWILLNEVERBEPRESSED"

# game states
GAME = 5
MENU = 6
MAPPING = 7
game_state = MENU

# some consts
BLOCK_NAMES = ("wall", "direction_block", "crate")

# mapping data
selected_block = None # this will be an entity
block_last = None
last_saved = (5, 5)

# ui entities
menu_ui = {}
selection_ui = {}
game_ui = {}
mapping_ui = {}

# board
board = {}
menu_blocks = {}
game_functions.createMenuScene(board, menu_blocks)

# clouds
next_cloud = True
def setCloudTrue(): global next_cloud; next_cloud = True

# player
class Player:
    def __init__(self):

        # position and moving
        self.position = (5, 5)
        self.move_duration = 0.3
        self.move_cooldown = False
        self.can_move = True

        # entity
        self.entity = Entity(
            model = "cube",
            color = color.orange,
            scale = 10,
            position = ((self.position[0] - 6) * 10 + 5, 0, (-self.position[1] + 5) * 10 + 5),
        )
        layeredGlow(self.entity, combine = True, scale_expo = 1.015)

        # stats
        self.moves_taken = 0
        self.objects_moved = 0

    def removeCooldown(self):
        self.move_cooldown = False

    def setPosition(self, new_position):
        self.position = new_position
        self.entity.position = ((self.position[0] - 6) * 10 + 5, 0, (-self.position[1] + 5) * 10 + 5)

    def move(self, board, direction, pull):

        # exit if cannot move
        if not self.can_move:
            return

        start_ns = time_ns()

        global game_state

        # set move duration
        if game_state == GAME:
            self.move_duration = game_ui["duration_slider"].value
        else:
            self.move_duration = 0.3

        # check if cooldown
        if self.move_cooldown:
            return

        # get correct movements
        move_x, move_y = {
            "right": (1, 0),
            "left": (-1, 0),
            "up": (0, -1),
            "down": (0, 1),
        }[direction]

        new_position = (self.position[0] + move_x, self.position[1] + move_y)

        # recursively check if can move affected blocks
        affected_coordinates = {}
        affected_gravity = {}
        affected_position = new_position + (0,)
        while True:
            
            if affected_coordinates:

                # check if its start portal
                if game_state == GAME and board["start"][0] + (0,) == affected_position:
                    return

                # only can move map block into the start portal after map has been selected
                if game_state == MENU and (not menu_blocks["map_block"].selected) and board["start"][0] + (0,) == affected_position:
                    return

                # check if its end portal
                if board["end"][0] + (0,) == affected_position:
                    return

            # hit nothing?
            if isinstance(board[affected_position], blocks.NullBlock):
                break

            # check if its movable
            if not board[affected_position].movable:
                return

            # check if moving in correct direction
            if board[affected_position].direction != blocks.DIRECTION_ANY:
                if board[affected_position].direction != (move_x, move_y):
                    return

            # add to affected list and continue
            affected_coordinates[affected_position] = (affected_position[0] + move_x, affected_position[1] + move_y, 0)

            # check if there is a block on top
            level = 1
            while True:
                if not (affected_position[0], affected_position[1], level) in board:
                    break

                # has gravity block
                affected_gravity[(affected_position[0], affected_position[1], level)] = (affected_position[0], affected_position[1], level - 1)
                level += 1

            affected_position = (affected_position[0] + move_x, affected_position[1] + move_y, 0)

        if pull and not isinstance(board[(self.position[0] - move_x, self.position[1] - move_y, 0)], blocks.NullBlock):

            # extra check to see if pulled block is also movable
            pull_affected_position = (self.position[0] - move_x, self.position[1] - move_y, 0)

            # check if its movable
            if not board[pull_affected_position].movable:
                return

            # check if moving in correct direction
            if board[pull_affected_position].direction != blocks.DIRECTION_ANY:
                if board[pull_affected_position].direction != (move_x, move_y):
                    return
            
            # if blocks are going to fall, player cannot move, so cannot pull anything
            if affected_gravity:
                return

            affected_coordinates[pull_affected_position] = self.position + (0,)

            # check if there is a block on top
            level = 1
            while True:
                if not (pull_affected_position[0], pull_affected_position[1], level) in board:
                    break

                # has gravity block
                affected_gravity[(pull_affected_position[0], pull_affected_position[1], level)] = (pull_affected_position[0], pull_affected_position[1], level - 1)
                level += 1

            pull_affected_position = (pull_affected_position[0] + move_x, pull_affected_position[1] + move_y, 0)

        # cant move above move limit
        if game_state == GAME and len(affected_coordinates) > board["max_moved"]:
            return

        # move all affected blocks
        for coord in reversed(affected_coordinates):
            self.objects_moved += 1
            moveBlock(board, coord, affected_coordinates[coord], self.move_duration)

        # move all affected gravity blocks if was not replaced by another block moving
        for coord, target in affected_gravity.items():
            if (not target in board) or (isinstance(board[target], blocks.NullBlock)):
                self.objects_moved += 1
                moveBlock(board, coord, target, self.move_duration)

        # move
        if not tuple(new_position) + (1,) in affected_gravity:
            self.position = new_position
            self.moves_taken += 1

        # change move counter
        if game_state == GAME:
            game_ui["moves_counter"].text = f"Moves left: {board['max_moves'] - self.moves_taken}"

        # animate entity position
        self.entity.animate("position", ((self.position[0] - 6) * 10 + 5, 0, (-self.position[1] + 5) * 10 + 5), self.move_duration, curve = linear)

        # check if player reached exit
        if self.position == board["end"][0] or (game_state == GAME and self.moves_taken >= board["max_moves"]):

            # game over?
            if game_state == GAME:

                moves_exceeded = self.moves_taken >= board["max_moves"]

                # stuff that is done after transition reaches alpha 255
                def _transitionFunc():
                    global game_state
                    game_state = MENU
                    self.setPosition((5, 5))
                    game_functions.endGame(game_ui, menu_ui, self.moves_taken, self.objects_moved, moves_exceeded, board["map_name"])
                    game_functions.createMenuScene(board, menu_blocks)
                    self.can_move = True

                # transition
                self.can_move = False
                game_functions.fadeTransition(1, 1, 0, color.black, _transitionFunc)

            # check if player exited game
            elif game_state == MENU:
                self.can_move = False
                game_functions.fadeTransition(2, 2, 0, color.black, application.quit)

        # check if player starts game
        if game_state == MENU and (menu_blocks["map_block"].x, menu_blocks["map_block"].y) == board["start"][0] and menu_blocks["map_block"].selected:
            
            # stuff that is done after transition reaches alpha 255
            def _transitionFunc():
                global game_state
                game_functions.toggleMapSelections(selection_ui, True)
                game_state = GAME
                game_functions.startGame(board, menu_blocks["map_block"].selected, menu_blocks, game_ui, menu_ui)
                player.setPosition(board["start"][0])

            # transition
            game_functions.fadeTransition(1, 1, 0, color.black, _transitionFunc)

            # reset stats
            self.moves_taken = 0
            self.objects_moved = 0

        # check if player went to mapping
        if game_state == MENU and player.position == board["mapping"][0]:

            # stuff that is done after transition reaches alpha 255
            def _transitionFunc():
                global game_state
                game_functions.toggleMapSelections(selection_ui, True)
                game_state = MAPPING
                player.can_move = False
                player.entity.visible = False
                game_functions.clearMenuStuff(menu_blocks, board, menu_ui)

                # setup default board
                game_functions.createMappingScene(board, mapping_ui)

            # transition
            game_functions.fadeTransition(1, 1, 0, color.black, _transitionFunc)

        self.move_cooldown = True
        invoke(self.removeCooldown, delay = self.move_duration + 0.01)

        # performance
        end_ns = time_ns()
        # print(f"Calculations performed in {(end_ns - start_ns) / 1000000}ms.")

def update():

    # clouds when player is moving
    global next_cloud
    if player.move_cooldown and next_cloud:
        Cloud(player.entity.position)
        next_cloud = False
        invoke(setCloudTrue, delay = 0.1 * player.move_duration / 0.3)

    for entity in scene.entities:

        # projector shader inputs
        if hasattr(entity, "shader") and entity.shader == projector_shader:

            # light at center if in selection menus
            if game_state == GAME:
                entity.set_shader_input("scale", 1)
                entity.set_shader_input("projector_uv_offset", player.entity.position.xz * projector_shader.default_input["projector_uv_scale"])
            elif game_state in (MAPPING, MENU):
                entity.set_shader_input("scale", 0.4)
                entity.set_shader_input("projector_uv_offset", Vec2(0, 0) * projector_shader.default_input["projector_uv_scale"])

        # tooltips
        if hasattr(entity, "tooltip"):
            if entity == mouse.hovered_entity:
                entity.tooltip.enabled = True
            else:
                entity.tooltip.enabled = False

    if game_state == MAPPING:

        # set block outline
        if not selected_block is None:
            mapping_ui["block_outline"].position = selected_block.entity.position
            mapping_ui["block_outline"].visible = True
        else:
            mapping_ui["block_outline"].visible = False

def input(key):
    
    global game_state, board, selected_block, block_last, last_saved

    # dev tools
    if key == "left mouse down" and held_keys["shift"]:
        print(mouse.position)

    elif key == "g" and not selected_block is None:
        print((selected_block.x, selected_block.y, selected_block.level))

    # player movement
    if game_state in (MENU, GAME):
        if key in ("w", "a", "s", "d"):
            player.move(board, {
                "w": "up",
                "a": "left",
                "s": "down",
                "d": "right",
            }[key], bool(held_keys["shift"]))

    # block movement
    elif game_state == MAPPING:
        if key in ("w", "a", "s", "d", "q", "e") and not (selected_block is None) and not any([mapping_ui["load_map_input"].active, mapping_ui["name_field"].active]):
            map_helper.editBlock(selected_block, key)

            # set color of outline
            mapping_ui["block_outline"].color = color.green if map_helper.canPlaceBlock(board, selected_block) else color.red

    if game_state == MENU:

        if key == "left mouse down":
            
            # clicked on map block?
            if mouse.hovered_entity == menu_blocks["map_block"].entity:
                if game_functions.toggleMapSelections(selection_ui) and menu_blocks["map_block"].selected: # toggled on
                    selection_ui[menu_blocks["map_block"].selected].color = color.green
                    selection_ui[menu_blocks["map_block"].selected].highlight_color = (0, 0.5, 0, 1)

            # selected a map?
            elif mouse.hovered_entity in selection_ui.values() and hasattr(mouse.hovered_entity, "map"):

                # change colors
                if menu_blocks["map_block"].selected:
                    selection_ui[menu_blocks["map_block"].selected].color = Button.color
                    selection_ui[menu_blocks["map_block"].selected].highlight_color = Button.color.tint(.2)
                selection_ui[mouse.hovered_entity.map].color = color.green
                selection_ui[mouse.hovered_entity.map].highlight_color = (0, 0.5, 0, 1)
                
                # change selection
                menu_blocks["map_block"].selected = mouse.hovered_entity.map

                # click animation
                game_functions.clickAnimation(mouse.hovered_entity, small = (0.4, 0.08), original = (0.5, 0.1))

                # notification
                game_functions.notifAt("Selected map!")

        if game_functions.map_selections_up and len(selection_ui) > 1:

            # scroll map selections up
            if key == "scroll down" and list(selection_ui.values())[1].y < 0.4:
                for selection_button in list(selection_ui.values())[1:]:
                    selection_button.y += 0.05

            # scroll map selections down
            elif key == "scroll up" and list(selection_ui.values())[-1].y > -0.4:
                for selection_button in list(selection_ui.values())[1:]:
                    selection_button.y -= 0.05

    elif game_state == MAPPING:

        if key == "left mouse down":

            # save button?
            if mouse.hovered_entity == mapping_ui["save_button"]:

                # click animation
                game_functions.clickAnimation(mapping_ui["save_button"])

                # check if map can save
                if not ("start" in board and "end" in board):

                    # warning notif
                    game_functions.notifAt("Please place start and end!", position = (0.58, -0.42), color = color.red)

                    return

                # set board max moved and max moves
                board["max_moves"] = int(mapping_ui["max_moves_input"].text) if mapping_ui["max_moves_input"].text else 1000
                board["max_moved"] = int(mapping_ui["max_moved_input"].text) if mapping_ui["max_moved_input"].text else 1000
                
                # delete old map
                old_map_name = mapping_ui["name_field"].prev
                if not old_map_name is None:
                    os.remove(f"maps/{old_map_name}.json")

                # new old text
                mapping_ui["name_field"].prev = mapping_ui["name_field"].text

                # save map name for highscore
                board["map_name"] = mapping_ui["name_field"].text

                # save new map
                json_data = map_helper.boardToJson(board)
                with open(f"maps/{mapping_ui['name_field'].text}.json", "w") as map_write:
                    map_write.write(json_data)

                # reset highscore for this map
                with open("highscores/highscores.json", "r") as read_highscores:
                    highscores = json.load(read_highscores)
                
                if mapping_ui["name_field"].text in highscores:
                    del highscores[mapping_ui["name_field"].text]

                with open("highscores/highscores.json", "w") as write_highscores:
                    json.dump(highscores, write_highscores)

                # notification
                game_functions.notifAt("Saved map!")

            elif mouse.hovered_entity == mapping_ui["clear_button"]:

                # click animation
                game_functions.clickAnimation(mapping_ui["clear_button"], 0.05, 0.07)

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
                board = map_helper.loadMap("")

                # clear selected
                if not selected_block is None:
                    destroy(selected_block.entity)
                    selected_block = None
                
                # clear stuff
                block_last = None
                last_saved = (5, 5)

                # notification
                game_functions.notifAt("Cleared map!")

            elif mouse.hovered_entity == mapping_ui["exit_button"]:

                # click animation
                game_functions.clickAnimation(mapping_ui["exit_button"])

                # stuff that is done after transition reaches alpha 255
                def _transitionFunc():
                    global game_state
                    game_state = MENU
                    player.can_move = True
                    player.entity.visible = True

                    global selected_block
                    if not selected_block is None:
                        destroy(selected_block.entity)
                    selected_block = None

                    # back to menu
                    game_functions.clearMappingScene(mapping_ui)
                    game_functions.createMenuScene(board, menu_blocks)

                # transition
                block_last = None
                last_saved = (5, 5)
                game_functions.fadeTransition(1, 1, 0, color.black, _transitionFunc)

                # notification
                game_functions.notifAt("Exitted mapping!")

            elif mouse.hovered_entity == mapping_ui["load_map_button"]:

                # click animation
                game_functions.clickAnimation(mapping_ui["load_map_button"])

                loaded_file = f"{mapping_ui['load_map_input'].text}.json"

                # check if loaded file exists
                if not loaded_file in os.listdir("maps"):
                    game_functions.notifAt("Could not find map!", (0.6, -0.42), color.red)
                    return

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

                # clear selected block
                if not selected_block is None:
                    destroy(selected_block.entity)
                    selected_block = None
                
                # clear last position
                block_last = None

                # load board
                board = game_functions.loadMap(f"maps/{loaded_file}")

                # notification
                game_functions.notifAt("Loaded map!")

            elif mouse.hovered_entity in (mapping_ui["crate"], mapping_ui["direction_block"], mapping_ui["wall"]):

                # click animation
                game_functions.clickAnimation(mouse.hovered_entity, 0.064, 0.08)
                
                # clear current selected
                if not selected_block is None:
                    map_helper.cancelSelected(board, selected_block, block_last)

                # switch to corresponding block
                selected_block = {
                    mapping_ui["crate"]: lambda: blocks.CrateBlock(*last_saved, 0),
                    mapping_ui["direction_block"]: lambda: blocks.DirectionBlock(*last_saved, 0, (0, 1)),
                    mapping_ui["wall"]: lambda: blocks.WallBlock(*last_saved),
                }[mouse.hovered_entity]()

                # set color of outline
                mapping_ui["block_outline"].color = color.green if map_helper.canPlaceBlock(board, selected_block) else color.red

                # notification
                game_functions.notifAt("Selected block!")

            elif mouse.hovered_entity == mapping_ui["confirm_button"]:

                # click animation
                game_functions.clickAnimation(mapping_ui["confirm_button"])

                # check if not even selected
                if selected_block is None:
                    return

                # check if in illegal position
                if map_helper.canPlaceBlock(board, selected_block):

                    # save block
                    if isinstance(selected_block, blocks.PortalBlock):
                        board[selected_block._for] = [(selected_block.x, selected_block.y), selected_block]
                    else:
                        board[(selected_block.x, selected_block.y, selected_block.level)] = selected_block

                    # last saved
                    last_saved = selected_block.x, selected_block.y

                    # clear block
                    selected_block = None

                    # notification
                    game_functions.notifAt("Saved block!")

                else:

                    # notification
                    game_functions.notifAt("Unable to save block!", (0.6, -0.42), color.red)

            elif mouse.hovered_entity == mapping_ui["delete_button"]:

                # click animation
                game_functions.clickAnimation(mapping_ui["delete_button"])

                # check if theres no selected block
                if selected_block is None:
                    return

                # delete
                selected_block = map_helper.deleteSelected(board, selected_block)

                # notification
                game_functions.notifAt("Deleted block!")

            elif mouse.hovered_entity == mapping_ui["cancel_button"]:

                # click animation
                game_functions.clickAnimation(mapping_ui["cancel_button"])

                # check if theres no selected block
                if selected_block is None:
                    return

                selected_block = map_helper.cancelSelected(board, selected_block, block_last)

                # notification
                game_functions.notifAt("Cancelled!")

            elif mouse.hovered_entity and mouse.hovered_entity.name == "block":

                # don't do anything if clicked selected block
                if not selected_block is None and mouse.hovered_entity == selected_block.entity:
                    return

                # cancel if selected already
                if not selected_block is None:
                    map_helper.cancelSelected(board, selected_block, block_last)

                # get the block instance
                new_block = mouse.hovered_entity.owner

                # check if it is a default block that cannot be moved
                if hasattr(new_block, "default") and new_block.default:
                    return

                # select block
                selected_block = new_block
                map_helper.selectBlock(board, new_block)

                # save position history
                block_last = (new_block.x, new_block.y, new_block.level)

                # notification
                game_functions.notifAt("Selected block!")

            elif mouse.hovered_entity == mapping_ui["start_portal"]:

                # click animation
                game_functions.clickAnimation(mapping_ui["start_portal"], 0.03, 0.035)

                # check if start portal already placed
                if "start" in board:
                    game_functions.notifAt("Start portal already placed!", position = (0.58, -0.42), color = color.red)
                    return

                # clear current selected
                if not selected_block is None:
                    map_helper.cancelSelected(board, selected_block, block_last)

                # set selected block
                selected_block = blocks.PortalBlock(*last_saved, color.green, "start")

                # set color of outline
                mapping_ui["block_outline"].color = color.green if map_helper.canPlaceBlock(board, selected_block) else color.red

                # notification
                game_functions.notifAt("Selected portal!")

            elif mouse.hovered_entity == mapping_ui["end_portal"]:

                # click animation
                game_functions.clickAnimation(mapping_ui["end_portal"], 0.03, 0.035)

                # check if end portal already placed
                if "end" in board:
                    game_functions.notifAt("End portal already placed!", position = (0.58, -0.42), color = color.red)
                    return

                # clear current selected
                if not selected_block is None:
                    map_helper.cancelSelected(board, selected_block, block_last)

                # set selected block
                selected_block = blocks.PortalBlock(*last_saved, color.red, "end")

                # set color of outline
                mapping_ui["block_outline"].color = color.green if map_helper.canPlaceBlock(board, selected_block) else color.red

                # notification
                game_functions.notifAt("Selected portal!")
        
        elif key == "right mouse down":

            # rotating direction blocks
            if hasattr(mouse.hovered_entity, "owner") and isinstance(mouse.hovered_entity.owner, blocks.DirectionBlock):

                rotated_block = mouse.hovered_entity.owner
                
                # change direction
                rotated_block.direction = {
                    (0, 1): (-1, 0),
                    (-1, 0): (0, -1),
                    (0, -1): (1, 0),
                    (1, 0): (0, 1),
                }[tuple(rotated_block.direction)]

                # rotate
                rotated_block.entity.rotation_y += 90

game_functions.fadeTransition(0, 1, 1.5, color.black, lambda: None, "Gravkoban")
player = Player()
app.run()