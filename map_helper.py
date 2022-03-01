import blocks
import json
from ursina import *

def loadMap(file):

    # board coordinates and walls
    wall_coordinates = [
        *[(0, y) for y in range(11 + 1)],
        *[(11, y) for y in range(11 + 1)],
        *[(x, 0,) for x in range(11 + 1)],
        *[(x, 11) for x in range(11 + 1)],
    ]
    board = {(x, y, 0): (blocks.NullBlock(x, y) if not (x, y) in wall_coordinates else blocks.WallBlock(x, y, True)) for x in range(11 + 1) for y in range(11 + 1)}

    if not file:
        return board

    # parse map json
    with open(file, "r") as r:
        map_data = json.load(r)

    # walls
    for position in map_data["WallBlock"]:
        board[tuple(position) + (0, )] = blocks.WallBlock(*position)

    # crate blocks
    for position in map_data["CrateBlock"]:
        board[tuple(position)] = blocks.CrateBlock(*position)

    # direction blocks
    for position in map_data["DirectionBlock"]:
        board[tuple(position[:3])] = blocks.DirectionBlock(*position)

    # movement restrictions
    board["max_moves"] = map_data["max_moves"]
    board["max_moved"] = map_data["max_moved"]
    
    # start and end
    board["start"] = [tuple(map_data["start"]), blocks.PortalBlock(*map_data["start"], color.green)]
    board["end"] = [tuple(map_data["end"]), blocks.PortalBlock(*map_data["end"], color.red)]

    # data
    board["map_name"] = map_data["map_name"]

    return board

def boardToJson(board):

    map_data = {
        "WallBlock": [], "CrateBlock": [], "DirectionBlock": [],
        "max_moves": 1000, "max_moved": 1000,
        "start": (1, 1),
        "end": (10, 10),
        "map_name": "Untitled Map",
    }

    type_strings = {
        blocks.WallBlock: "WallBlock",
        blocks.CrateBlock: "CrateBlock",
        blocks.DirectionBlock: "DirectionBlock",
        blocks.CustomBlock: None,
    }

    for key, block in board.items():

        if isinstance(block, blocks.NullBlock):
            continue
        
        is_block = False
        for block_class, type_string in type_strings.items():
            if isinstance(block, block_class):
                if type_string:
                    map_data[type_string].append(block.getJsonData()) # store position
                is_block = True

        if is_block:
            continue

        if key in ("max_moves", "max_moved", "map_name"):
            map_data[key] = block

        else: # portal
            block = block[1]
            map_data[key] = (block.x, block.y)

    return json.dumps(map_data)

def selectBlock(board, block_entity):

    # replace block in board if exists
    if (block_entity.x, block_entity.y, block_entity.level) in board:
        board[(block_entity.x, block_entity.y, block_entity.level)] = blocks.NullBlock(block_entity.x, block_entity.y)

def editBlock(block, direction):

    # hacky stuff to get around having to be a yandere dev
    boundary_checks = {
        "w": [block.y > 1, -1, "y"],
        "a": [block.x > 1, -1, "x"],
        "s": [block.y < 10, 1, "y"],
        "d": [block.x < 10, 1, "x"],
        "e": [block.level < 6, 1, "level"],
        "q": [block.level > 0, -1, "level"],
    }
    checked = boundary_checks[direction]
    if checked[0]:
        setattr(
            block,
            checked[2],
            (getattr(block, checked[2]) + checked[1]) * int(not (isinstance(block, (blocks.WallBlock, blocks.PortalBlock)) and direction in ("q", "e")))
        )

    # reload block
    block.entity.position = ((block.x - 6) * 10 + 5, block.level * 10, (-block.y + 5) * 10 + 5)

def canPlaceBlock(board, block):

    block_pos = (block.x, block.y, block.level)

    # block overlaps?
    if block_pos in board and not isinstance(board[block_pos], blocks.NullBlock):
        return False

    # block floating?
    for level in range(block_pos[2]):
        if not (block.x, block.y, level) in board or isinstance(board[(block.x, block.y, level)], blocks.NullBlock):
            return False

    # block intersects with start/end?
    if ("start" in board and board["start"][0] + (0,) == (block.x, block.y, block.level)) or ("end" in board and board["end"][0] + (0,) == (block.x, block.y, block.level)):
        return False
    
    return True

def deleteSelected(board, selected_block):

    if selected_block is None:
        return None
    
    # check if was saved
    if (selected_block.x, selected_block.y, selected_block.level) in board:
        del board[(selected_block.x, selected_block.y, selected_block.level)]

    # check if is portalblock
    if isinstance(selected_block, blocks.PortalBlock) and selected_block._for in board:
        del board[selected_block._for]

    destroy(selected_block.entity)

    return None

def cancelSelected(board, selected_block, block_last):

    # if has position history then reset it
    if not block_last is None:
        selected_block.x, selected_block.y, selected_block.level = block_last

        # reload block
        selected_block.entity.position = ((selected_block.x - 6) * 10 + 5, selected_block.level * 10, (-selected_block.y + 5) * 10 + 5)

        # save block
        board[(selected_block.x, selected_block.y, selected_block.level)] = selected_block

        block_last = None

    else:
        destroy(selected_block.entity)

    return None