"""
author: Horst JENS
email: horstjens@gmail.com
contact: see http://spielend-programmieren.at/de:kontakt
license: gpl, see http://www.gnu.org/licenses/gpl-3.0.de.html
download:

based on: http://www.roguebasin.com/index.php?title=Complete_Roguelike_Tutorial,_using_python%2Blibtcod,_part_4

field of view and exploration
also see http://www.roguebasin.com/index.php?title=Comparative_study_of_field_of_view_algorithms_for_2D_grid_based_worlds

field of view improving, removing of artifacts:
https://sites.google.com/site/jicenospam/visibilitydetermination

"""
import pygame
import random
#import inspect

import os


def make_text(text="@", font_color=(255, 0, 255), font_size=48, font_name = "mono", bold=True, grid_size=None):
    """returns pygame surface with text and x, y dimensions in pixel
       grid_size must be None or a tuple with positive integers.
       Use grid_size to scale the text to your desired dimension or None to just render it
       You still need to blit the surface.
       Example: text with one char for font_size 48 returns the dimensions 29,49
    """
    myfont = pygame.font.SysFont(font_name, font_size, bold)
    size_x, size_y = myfont.size(text)
    mytext = myfont.render(text, True, font_color)
    mytext = mytext.convert_alpha() # pygame surface, use for blitting
    if grid_size is not None:
        # TODO error handler if grid_size is not a tuple of positive integers
        mytext = pygame.transform.scale(mytext, grid_size)
        mytext = mytext.convert_alpha()  # pygame surface, use for blitting
        return mytext, (grid_size[0], grid_size[1])

    return mytext, (size_x, size_y)


def write(background, text, x=50, y=150, color=(0, 0, 0),
          font_size=None, font_name="mono", bold=True, origin="topleft"):
    """blit text on a given pygame surface (given as 'background')
       the origin is the alignement of the text surface
    """
    if font_size is None:
        font_size = 24
    font = pygame.font.SysFont(font_name, font_size, bold)
    width, height = font.size(text)
    surface = font.render(text, True, color)

    if origin == "center" or origin == "centercenter":
        background.blit(surface, (x - width // 2, y - height // 2))
    elif origin == "topleft":
        background.blit(surface, (x, y))
    elif origin == "topcenter":
        background.blit(surface, (x - width // 2, y))
    elif origin == "topright":
        background.blit(surface, (x - width , y))
    elif origin == "centerleft":
        background.blit(surface, (x, y - height // 2))
    elif origin == "centerright":
        background.blit(surface, (x - width , y - height // 2))
    elif origin == "bottomleft":
        background.blit(surface, (x , y - height ))
    elif origin == "bottomcenter":
        background.blit(surface, (x - width // 2, y ))
    elif origin == "bottomright":
        background.blit(surface, (x - width, y - height))


def get_line(start, end):
    """Bresenham's Line Algorithm
       Produces a list of tuples from start and end
       source: http://www.roguebasin.com/index.php?title=Bresenham%27s_Line_Algorithm#Python
       see also: https://en.wikipedia.org/wiki/Bresenham%27s_line_algorithm

       #>>> points1 = get_line((0, 0), (3, 4))
       # >>> points2 = get_line((3, 4), (0, 0))
       #>>> assert(set(points1) == set(points2))
       #>>> print points1
       #[(0, 0), (1, 1), (1, 2), (2, 3), (3, 4)]
       #>>> print points2
       #[(3, 4), (2, 3), (1, 2), (1, 1), (0, 0)]
    """
    # Setup initial conditions
    x1, y1 = start
    x2, y2 = end
    dx = x2 - x1
    dy = y2 - y1

    # Determine how steep the line is
    is_steep = abs(dy) > abs(dx)

    # Rotate line
    if is_steep:
        x1, y1 = y1, x1
        x2, y2 = y2, x2

    # Swap start and end points if necessary and store swap state
    swapped = False
    if x1 > x2:
        x1, x2 = x2, x1
        y1, y2 = y2, y1
        swapped = True

    # Recalculate differentials
    dx = x2 - x1
    dy = y2 - y1

    # Calculate error
    error = int(dx / 2.0)
    ystep = 1 if y1 < y2 else -1

    # Iterate over bounding box generating points between start and end
    y = y1
    points = []
    for x in range(x1, x2 + 1):
        coord = (y, x) if is_steep else (x, y)
        points.append(coord)
        error -= abs(dy)
        if error < 0:
            y += ystep
            error += dx

    # Reverse the list if the coordinates were swapped
    if swapped:
        points.reverse()
    return points


class Rect():
    """a rectangle object (room) for the dungeon
       x,y is the topleft coordinate
    """
    def __init__(self, x, y, width, height):
        self.x1 = x
        self.y1 = y
        self.x2 = x + width
        self.y2 = y + height

    def center(self):
        """returns the center coordinate of a room"""
        center_x = (self.x1 + self.x2) // 2  # TODO: // instead of / ?
        center_y = (self.y1 + self.y2) // 2
        return (center_x, center_y)

    def intersect(self, other):
        """returns true if this rectangle intersects with another one"""
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and
                self.y1 <= other.y2 and self.y2 >= other.y1)



class Tile():
    """# a tile of the map and its properties
       block_movement means blocking the movement of Monster/Player, like a wall
       block_sight means blocking the field of view
    """
    def __init__(self, char, block_movement=None, block_sight=None, explored=False):
        self.char = char
        self.block_movement = block_movement
        self.block_sight = block_sight
        self.explored = explored
        # graphic_index is a random number to choose one of several graphical tiles
        self.graphic_index = random.randint(1,4)
        # --- some common tiles ---
        if char == "#":   # wall
            self.block_movement = True
            self.block_sight = True
            self.i = random.randint(1,10)
        elif char == ".": # floor
            self.block_movement = False
            self.block_sight = False
            #self.i = random.randint(1,10)


class Object():
    """this is a generic dungeon object: the player, a monster, an item, a stair..
       it's always represented by a character (for text representation).
       NOTE: a dungeon tile (wall, floor, water..) is represented by the Tile class
    """

    number = 0 # current object number. is used as a key for the Game.objects dictionary

    def __init__(self, x, y, z=0, char="?", color=None, **kwargs):
        self.number = Object.number
        Object.number += 1
        Game.objects[self.number] = self
        self.x = x
        self.y = y
        self.z = z
        self.char = char
        self.color = color
        self.hitpoints = 1 # objects with 0 or less hitpoints will be deleted
        # --- make attributes out of all named arguments. like Object(hp=33) -> self.hp = 33
        for key, arg in kwargs.items():
            setattr(self, key, arg)
        # ---- some default values ----
        if "explored" not in kwargs:
            self.explored = False
        if "stay_visible_once_explored" not in kwargs:
            self.stay_visible_once_explored = False
        # --- child classes can do stuff in the _overwrite() method  without needing their own __init__ method
        self._overwrite()

    def _overwrite(self):
        pass

    def is_member(self, name):
        """returns True if the instance is a member of the 'name' class or a child of it"""
        #if self.__class__.__name__ == name:
        #    return True
        #for c in self.__class__.__bases__:
        #    if c.__name__ == name:
        #        return True
        ## it's not a member of 'name'
        #return False
        class_names = [c.__name__ for c in self.__class__.mro()] #if c.__name__ != "object"]
        if name in class_names:
            return True
        return False

class Stair(Object):
    """a stair, going upwards < or downwards >"""
    def _overwrite(self):
        self.color = (128,0,128) # violet
        self.stay_visible_once_explored = True


class Monster(Object):
    """a (moving?) dungeon Monster, like the player, a boss, a NPC..."""

    def _overwrite(self):
        self.char = "M"
        if self.color is None:
            # yello as default color
            self.color = (255,255,0)
        #if "hitpoints_max" not in kwargs:
        #    self.hitpoints_max = self.hitpoints


    def move(self, dx, dy, dz=0):
        try:
            target = Game.dungeon[self.z+dz][self.y+dy][self.x+dx]
        except:
            raise SystemError("out of dungeon?", self.x,self.y,self.z)
        # --- check if monsters is trying to run into a wall ---
        if target.block_movement:
            self.hitpoints -= 1
            Game.log.append("ouch!") # movement is not possible
            return



        self.x += dx
        self.y += dy
        self.z += dz

class Wolf(Monster):

    def _overwrite(self):
        self.char = "W"
        self.hitpoints = 30
        self.attack = (2,6)
        self.defense = (2,6)
        self.defense = (2,4)
        self.agility = 0.4
        self.natural_weapons = ["WolfBite()"]

class Snake(Monster):

    def _overwrite(self):
        self.char="S"
        self.hitpoints = 20
        self.attack = (2,4)
        self.defense = (3,3)
        self.damage = (3,4)
        self.natural_weapons = ["SnakeBite()"]



class Player(Monster):

    def _overwrite(self):
        self.char = "@"
        self.color = (0, 0, 255)
        self.hitpoints = 100
        self.hitpoints_max = 100
        self.items = {}


class Game():

    dungeon = [] # list of list of list. 3D map representation, using text chars. z,y,x ! z=0: first level. z=1: second level etc
    fov_map = [] # field of vie map, only for current level!
    objects = {} # container for all Object instances in this dungeon
    legend = {"@":"player",
              "#":"wall tile",
              ".":"floor tile",
              ">":"stair down",
              "<":"stair up",
              "W": "wolf",
              "S": "snake"}

    tiles_x = 0
    tiles_y = 0
    torch_radius = 10
    log = [] # message log
    game_over = False
    turn = 1
    cursor_x = 0
    cursor_y = 0

    def __init__(self, tiles_x=80, tiles_y=40):
        Game.tiles_x = tiles_x  # max. width of the level in tiles
        Game.tiles_y = tiles_y  # max. height of the level in tiles, top row is 0, second row is 1 etc.
        #self.checked = set()   # like a list, but without duplicates. for fov calculation
        self.player = Player(x=1,y=1,z=0)
        Game.cursor_x = self.player.x
        Game.cursor_y = self.player.y
        #Monster(2,2,0)
        Wolf(2,2,0)
        Snake(3,3,0)
        self.log.append("Welcome to the first dungeon level (level 0)!")
        self.log.append("Use cursor keys to move around")
        self.load_level(0, "level001.txt", "data")
        self.load_level(1, "level002.txt", "data")
        self.load_level(2, "level003.txt", "data")


        self.create_empty_dungeon_level(tiles_x, tiles_y, filled=True, z=3) # dungoen is full of walls,
        # carve out some rooms and tunnels in this new dungeon level
        self.create_rooms_and_tunnels(z=3) # carve out some random rooms and tunnels
        # append empty dungeon level

    def checkfight(self, x,y,z):
        """wir gehen davon aus dass nur der player schaut (checkt) ob er in ein Monster läuft"""
        for o in Game.objects.values():
            if o == self.player:
                continue
            if o.hitpoints <= 0:
                continue
            if not o.is_member("Monster"):
                continue
            if o.x == x and o.y == y and o.z ==z:
                self.fight(self.player, o)
                return True



    def fight(self, a, b):
        self.strike(a,b)
        if b.hitpoints > 0:
            self.strike(b,a)

    def strike(self, a, b ):
        print("{} strikes at {}".format(a , b))

    def check_player(self):
        if self.player.hitpoints <= 0:
            Game.game_over = True

    def load_level(self, z, name, folder="data"):
        """load a text file and return a list of non-empty lines without newline characters"""
        lines = []
        with open(os.path.join(folder,name ), "r") as f:
            for line in f:
                if line.strip() != "":
                    lines.append(line[:-1])  # exclude newline char
        #return lines
        level = []
        for y, line in enumerate(lines):
            row = []
            for x, char in enumerate(line):
                if char=="#" or char == ".":
                    row.append(Tile(char))
                if char=="<" or char == ">":
                    row.append(Tile("."))
                    Stair(x,y,z,char)
            level.append(row)
        try:
             Game.dungeon[z] = level
        except:
            Game.dungeon.append(level)
        print("level loaded:", self.dungeon[z])



    def create_rooms_and_tunnels(self, z=0, room_max_size = 10, room_min_size = 6, max_rooms = 30):
        """carve out some random rooms and connects them by tunnels. player is placed in the first room"""
        rooms = []
        num_rooms = 0
        self.room_max_size = room_max_size
        self.room_min_size = room_min_size
        self.max_rooms = max_rooms

        for r in range(self.max_rooms):
            print("carving out room number {}...".format(r))
            # random width and height
            w = random.randint(self.room_min_size, self.room_max_size)
            h = random.randint(self.room_min_size, self.room_max_size)
            # random topleft position without going out of the boundaries of the map
            x = random.randint(0, Game.tiles_x - w - 1)
            y = random.randint(0, Game.tiles_y - h - 1)
            # "Rect" class makes rectangles easier to work with
            new_room = Rect(x, y, w, h)
            # run through the other rooms and see if they intersect with this one
            #failed = False
            for other_room in rooms:
                if new_room.intersect(other_room):
                    #failed = True
                    break
            #if not failed:
            else: # for loop got through without a break
                # this means there are no intersections, so this room is valid
                # carve out this room!
                self.create_room(new_room, z)
                # center coordinates of new room, will be useful later
                (new_x, new_y) = new_room.center()

                if num_rooms == 0:
                    # this is the first room, where the player starts at
                    # create tunnel from player position to this room
                    prev_x, prev_y = self.player.x, self.player.y
                else:
                    (prev_x, prev_y) = rooms[num_rooms - 1].center()
                self.create_tunnel(prev_x,prev_y,new_x, new_y, z)
                ### draw a coin (random number that is either 0 or 1)
                ##if random.choice([0,1]) == 1:
                ##    # first move horizontally, then vertically
                ##    self.create_h_tunnel(prev_x, new_x, prev_y, z)
                ##    self.create_v_tunnel(prev_y, new_y, new_x, z)
                ##else:
                ##    # first move vertically, then horizontally
                ##    self.create_v_tunnel(prev_y, new_y, prev_x, z)
                ##    self.create_h_tunnel(prev_x, new_x, new_y, z)
                # finally, append the new room to the list
                rooms.append(new_room)
                num_rooms += 1
        # --------- all rooms added. check stairs now -------
        # ---------- stairs up ---------------
        # check if this is level 0, add a single stair up
        if z == 0:
            # place stair up in a random room
            r = random.choice(rooms)
            Stair(r.center()[0], r.center()[1], z, char="<")
        else:
            # collect all stairs down from previous level,
            # make at same position a stair up, carve a tunnel to a random room if necessary
            stairlist = [(o.x, o.y) for o in Game.objects.values() if o.char == ">" and o.z == z - 1 and o.is_member("Stair")]
            print("creating prev stairlist:", stairlist)
            for (x, y) in stairlist:
                if Game.dungeon[z][y][x].char != ".":
                    # carve tunnel to random room center
                    r = random.choice(rooms)
                    self.create_tunnel(x,y, r.center()[0], r.center()[1],z)
                # make a stair!
                Stair(x, y, z, char="<")
        # ------------------ stairs down ----------------
        # select up to 3 random rooms and place a stair down in it's center
        num_stairs = 0
        stairs = random.randint(1,3)
        print("creating stairs down...")
        while num_stairs < stairs:
            r = random.choice(rooms)
            x,y = r.center()
            # is there already any object at this position?
            objects_here = [o for o in Game.objects.values() if o.z == z and o.x == x and o.y == y]
            if len(objects_here) > 0:
                continue
            Stair(x,y,z, char=">")
            num_stairs += 1










    def ascend(self):
        """go up one dungeon level (or leave the game if already at level 0)"""
        if self.player.z == 0:
            Game.log.append("You climb back to the surface and leave the dungeon. Good Bye!")
            print(Game.log[-1])
            Game.game_over = True
        else:
            Game.log.append("climbing up one level....")
            self.player.z -= 1

    def descend(self):
        """go down one dungeon level. create this level if necessary """
        Game.log.append("climbing down one level, deeper into the dungeon...")
        try:
            l = Game.dungeon[self.player.z +1]
        except:
            Game.log.append("please wait a bit, i must create this level...")
            self.create_empty_dungeon_level(Game.tiles_x, Game.tiles_y,
                                            z=self.player.z+1)
            self.create_rooms_and_tunnels(z=self.player.z+1)
        self.player.z += 1
        #return True

    def create_empty_dungeon_level(self, max_x, max_y, filled=True,z=0):
        """creates empty dungeon level and append it to Game.dungeon
           if "filled" is False with floor tiles ('.') and an outer wall ('#')
           otherwise all is filled with walls
        """
        # TODO: check max x,y from doors in previous level, randomize level dimension
        # TODO: create tunnel from stair to closest room, not to random room
        floor = []
        for y in range(max_y):
            line = []
            for x in range(max_x):
                if filled:
                    line.append(Tile("#")) # fill the whole dungeon level with walls
                else:
                    # outer walls only
                    line.append(Tile("#") if y == 0 or y== max_y - 1 or x == 0 or x ==max_x-1 else Tile("."))
            floor.append(line)
        try:
            Game.dungeon[z] = floor
        except:
            Game.dungeon.append(floor)
        #print(Game.dungeon)

    def create_room(self, rect, z=0):
        """needs a rect object and carves a room out of this (z) dungeon level. Each room has a wall"""
        for x in range(rect.x1 + 1, rect.x2):
            for y in range(rect.y1 + 1, rect.y2):
                # replace the tile at this position with an floor tile
                Game.dungeon[z][y][x] = Tile(".") # replace whatever tile that was there before with a floor

    def create_h_tunnel(self, x1, x2, y, z=0):
        """create an horizontal tunnel in dungeon level z (filled with floor tiles)"""
        for x in range(min(x1, x2), max(x1, x2) + 1):
            Game.dungeon[z][y][x] = Tile(".")  # replace whatever tile that was there before with a floor

    def create_v_tunnel(self, y1, y2, x, z=0):
        """create an vertical tunnel in dungeon level z (filled with floor tiles)"""
        for y in range(min(y1, y2), max(y1, y2) + 1):
            Game.dungeon[z][y][x] = Tile(".")  # replace whatever tile that was there before with a floor


    def create_tunnel(self, x1, y1, x2, y2, z=0):
        if random.choice([0, 1]) == 1:
            # first move horizontally, then vertically
            self.create_h_tunnel(x1, x2, y1, z)
            self.create_v_tunnel(y1, y2, x2, z)
        else:
            # first move vertically, then horizontally
            self.create_v_tunnel(y1, y2, x1, z)
            self.create_h_tunnel(x1, x2, y2, z)

    def make_fov_map(self):
        Game.fov_map = []
        #self.checked = set() # clear the set of checked coordinates
        px,py,pz = self.player.x, self.player.y, self.player.z
        # set all tiles to False
        for line in Game.dungeon[pz]:
            row = []
            for tile in line:
                 row.append(False)
            Game.fov_map.append(row)
        # set player's tile to visible
        Game.fov_map[py][px] = True
        # get coordinates form player to point at end of torchradius / torchsquare
        endpoints = set()
        for y in range(py - Game.torch_radius, py + Game.torch_radius + 1):
            if y == py - Game.torch_radius or y == py + Game.torch_radius:
                for x in range(px - Game.torch_radius, px + Game.torch_radius +1):
                    endpoints.add((x,y))
            else:
                endpoints.add((px - Game.torch_radius,  y))
                endpoints.add((px + Game.torch_radius, y))
        for coordinate in endpoints:
            # a line of points from the player position to the outer edge of the torchsquare
            points = get_line((px, py), (coordinate[0], coordinate[1]))
            self.calculate_fov_points(points)
        #print(Game.fov_map)
        # ---------- the fov map is now ready to use, but has some ugly artifacts ------------
        # ---------- start post-processing fov map to clean up the artifacts ---
        # -- basic idea: divide the torch-square into 4 equal sub-squares.
        # -- look of a invisible wall is behind (from the player perspective) a visible
        # -- ground floor. if yes, make this wall visible as well.
        # -- see https://sites.google.com/site/jicenospam/visibilitydetermination
        # ------ north-west of player
        for xstart, ystart, xstep, ystep, neighbors in [
                ( -Game.torch_radius, -Game.torch_radius,1,1,   [(0, 1),( 1,0), ( 1, 1)]),
                ( -Game.torch_radius,  Game.torch_radius,1,-1,  [(0,-1),( 1,0), ( 1,-1)]),
                (  Game.torch_radius,  -Game.torch_radius,-1,1, [(0,-1),(-1,0), (-1,-1)]),
                (  Game.torch_radius, Game.torch_radius, -1,-1, [(0, 1),(-1,0), (-1, 1)])]:

            for x in range(px + xstart , px, xstep):
                for y in range(py + ystart, py, ystep):
                    # not even in fov?
                    try:
                        visible = Game.fov_map[y][x]
                    except:
                        continue
                    if visible:
                        continue # next, i search invisible tiles!
                    # oh, we found an invisble tile! now let's check:
                    # is it a wall?
                    if Game.dungeon[pz][y][x].char != "#":
                        continue # next, i search walls!
                    #--ok, found an invisible wall.
                    # check south-east neighbors

                    for dx, dy in neighbors:
                        # does neigbor even exist?
                        try:
                            v = Game.fov_map[y+dy][x+dx]
                            t = Game.dungeon[pz][y+dy][x+dx]
                        except:
                            continue
                        # is neighbor a tile AND visible?
                        if t.char == "." and v == True:
                            # ok, found a visible floor tile neighbor. now let's make this wall
                            # visible as well
                            Game.fov_map[y][x] = True
                            break # other neighbors are irrelevant now




    def calculate_fov_points(self, points):
        """needs a points-list from Bresham's get_line method"""
        for point in points:
            x,y = point[0], point[1]
            # player tile always visible
            if x == self.player.x and y == self.player.y:
                Game.fov_map[y][x] = True  # make this tile visible and move to next point
                continue
            # outside of dungeon level ?
            try:
                tile = Game.dungeon[self.player.z][y][x]
            except:
                continue # outside of dungeon error
            # outside of torch radius ?
            distance = ((self.player.x - x)**2 + (self.player.y - y)**2)**0.5
            if distance > Game.torch_radius:
                continue

            Game.fov_map[y][x] = True # make this tile visible
            if tile.block_sight:
                break #  forget the rest



class Cursor():
    
    def __init__(self):
        self.create_image()
    
    def create_image(self):
        self.image = pygame.surface.Surface((Viewer.grid_size[0],
                                             Viewer.grid_size[1]))
        c = random.randint(100,200)
        pygame.draw.rect(self.image, (c,c,c), (0,0,Viewer.grid_size[0],
                         Viewer.grid_size[1]), 3)
        self.image.set_colorkey((0,0,0))
        self.image.convert_alpha()
        

class Viewer():
    width = 0   # screen x resolution in pixel
    height = 0  # screen y resolution in pixel
    panel_width = 200
    log_height = 50
    gird_size = (32,32)

    def __init__(self, game, width=640, height=400, grid_size = (32,32), fps=60, ):
        """Initialize pygame, window, background, font,...
           default arguments """
        self.game = game
        self.fps = fps
        Viewer.grid_size = grid_size # make global readable
        Viewer.width = width
        Viewer.height = height
        pygame.init()
        # player center in pixel
        self.pcx = (width - Viewer.panel_width) // 2  # set player in the middle of the screen
        self.pcy = (height - Viewer.log_height) // 2
        self.radarblipsize = 4 # pixel
        self.logscreen_fontsize = 10
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.DOUBLEBUF)
        self.clock = pygame.time.Clock()

        self.playtime = 0.0
        # ------ surfaces for radar, panel and log ----
        # all surfaces are black by default
        self.radarscreen = pygame.surface.Surface((Viewer.panel_width, Viewer.panel_width))  # same width and height as panel, sits in topright corner of screen
        self.panelscreen =   pygame.surface.Surface((Viewer.panel_width, Viewer.height-Viewer.panel_width))
        self.logscreen = pygame.surface.Surface((Viewer.width - Viewer.panel_width, Viewer.log_height))
        # radar screen center
        self.rcx = Viewer.panel_width // 2
        self.rcy = Viewer.panel_width // 2

        # ------ background images ------
        self.backgroundfilenames = []  # every .jpg or .jpeg file in the folder 'data'
        self.make_background()
        # ------ joysticks ----
        pygame.joystick.init()
        self.joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
        for j in self.joysticks:
            j.init()
        # ------ create bitmaps for player and dungeon tiles ----
        #print("fontsize dim values")
        #test = make_text("@")

        self.create_tiles()
        self.cursor = Cursor()
        self.run()

    def move_cursor(self, dx=0, dy=0):
        """moves the cursor dx, dy tiles away from the current position"""
        target_x, target_y = self.game.player.x + Game.cursor_x + dx, self.game.player.y + Game.cursor_y + dy
        # check if the target tile is inside the current level dimensions
        level_width = len(Game.dungeon[self.game.player.z][0])
        level_height = len(Game.dungeon[self.game.player.z])
        print("level dimension in tiles:", level_width, level_height, Game.cursor_x, Game.cursor_y, dx, dy)
        if target_x < 0 or target_y < 0 or target_x >= level_width or target_y >= level_height:
            return # cursor can not move outside of the current level
        # check if the target tile is outside the current game window
        x = self.pcx + (Game.cursor_x + dx) * self.gird_size[0]
        y = self.pcy + (Game.cursor_y + dy) * self.grid_size[1]
        if x < 0 or y < 0 or x > (self.width - self.panel_width) or y > (self.height - self.log_height):
            return # cursor can not move outside of the game window
        # ---- finally, move the cursor ---
        Game.cursor_x += dx
        Game.cursor_y += dy

    def make_background(self):
        """scans the subfolder 'data' for .jpg files, randomly selects
        one of those as background image. If no files are found, makes a
        white screen"""
        try:
            for root, dirs, files in os.walk("data"):
                for file in files:
                    if file[-4:].lower() == ".jpg" or file[-5:].lower() == ".jpeg":
                        self.backgroundfilenames.append(os.path.join(root,file))
            random.shuffle(self.backgroundfilenames)  # remix sort order
            self.background = pygame.image.load(self.backgroundfilenames[0])

        except:
            print("no folder 'data' or no jpg files in it")
            self.background = pygame.Surface(self.screen.get_size()).convert()
            self.background.fill((255, 255, 255))  # fill background white

        self.background = pygame.transform.scale(self.background,
                                                 (Viewer.width, Viewer.height))
        self.background.convert()

    def create_tiles(self):
        """create tiles for blitting"""
        self.darkwalls = []
        self.lightwalls = []
        self.darkfloors = []
        self.lightfloors = []
        self.darkfeats = []
        self.lightfeats = []

        walls_img = pygame.image.load(os.path.join("data", "wall.png")) # spritesheet 32x32 pixel
        floors_img = pygame.image.load(os.path.join("data", "floor.png")) # spritesheet 32x32 pixel
        walls_dark_img = walls_img.copy()
        floors_dark_img = floors_img.copy()
        feats_img = pygame.image.load(os.path.join("data", "feat.png"))
        feats_dark_img = feats_img.copy()
        # blit a darker picture over the original to darken
        darken_percent = .25
        for (original, copy) in [(walls_img, walls_dark_img),(floors_img, floors_dark_img),(feats_img, feats_dark_img)]:
            dark = pygame.surface.Surface(original.get_size()).convert_alpha()
            dark.fill((0, 0, 0, darken_percent * 255))
            copy.blit(dark, (0, 0)) # blit dark surface over original
        # get a list of floor tiles and another list of wall tiles, each with an index
        for (original, targetlist, width, height) in ((walls_img, self.lightwalls, 32, 32),
                                       (walls_dark_img, self.darkwalls, 32, 32),
                                       (floors_img, self.lightfloors, 32, 32),
                                       (floors_dark_img, self.darkfloors, 32, 32),
                                       (feats_img, self.lightfeats, 29, 32),
                                       (feats_dark_img, self.darkfeats, 29,32) ):
            size_x, size_y = original.get_size()
            #print(original, "size:", size_x, size_y)
            for y in range(0, size_y +1, height):
                for x in range(0, size_x+1, width):
                    img = pygame.surface.Surface((width, height))
                    img.blit(original, (0,0), (x, y, width, height) )
                    img.convert()
                    targetlist.append(img)

        self.wolf_tile = make_text("W", font_color=(100,100,100), grid_size=self.grid_size)[0]
        self.snake_tile = make_text("S", font_color=(0, 200,0), grid_size=self.grid_size)[0]
        self.monster_tile = make_text("M", font_color=(139,105,20), grid_size=self.grid_size)[0]
        self.player_tile = make_text("@", font_color=self.game.player.color, grid_size = self.grid_size)[0]
        self.floor_tile_dark =  make_text(".", font_color=(50,50,150), grid_size = self.grid_size)[0]
        self.floor_tile_light = make_text(".", font_color=(200, 180, 50), grid_size=self.grid_size)[0]
        ##self.floor_tile_dark = self.darkfloors[4*32+0]
        ##self.floor_tile_light = self.lightfloors[4*32+0]
        self.wall_tile_dark =   make_text("#", font_color=(0,0,100), grid_size = self.grid_size)[0]
        ##self.wall_tile_dark = self.darkwalls[3*32+0]   # 0
        self.wall_tile_light = make_text("#", font_color=(200, 180, 50), grid_size=self.grid_size)[0]
        ##self.wall_tile_light = self.lightwalls[3*32+0]  # 0
        self.unknown_tile  = make_text("?", font_color=(14,14,14),  grid_size=self.grid_size)[0]
        self.stair_up_tile = make_text("<", font_color=(128,0,128),  grid_size=self.grid_size)[0]
        ##self.stair_up_tile = self.lightfeats[5*35+2]
        self.stair_down_tile=make_text(">", font_color=(128,255,128),  grid_size=self.grid_size)[0]
        self.legend = {"@": self.player_tile,
                       ".": self.floor_tile_light,
                       "#": self.wall_tile_light,
                       ":": self.floor_tile_dark,
                       "X": self.wall_tile_dark,
                       "?": self.unknown_tile,
                       "<": self.stair_up_tile,
                       ">": self.stair_down_tile,
                       "M": self.monster_tile,
                       "W": self.wolf_tile,
                       "S": self.snake_tile}

    def tile_blit(self, surface, x_pos, y_pos):
        """correctly blits a surface at tile-position x,y, so that the player is always centered at pcx, pcy"""
        x = (x_pos-self.game.player.x) * self.grid_size[0] + self.pcx
        y = (y_pos - self.game.player.y) * self.grid_size[1] + self.pcy
        # check if the tile is inside the game screen, otherwise ignore
        if (x > (Viewer.width - Viewer.panel_width)) or (y > (Viewer.height-Viewer.log_height)):
            return
        if (x + self.grid_size[0]) < 0 or (y + self.grid_size[1]) < 0:
            return
        # blit
        self.screen.blit(surface,(x,y) )

    def draw_dungeon(self):
        z  = self.game.player.z
        px, py = self.game.player.x, self.game.player.y
        for y, line in enumerate(Game.dungeon[z]):
            for x, map_tile in enumerate(line):
                distance = ((x - px) ** 2 + (y - py) ** 2) ** 0.5
                # ---- check if tiles is outside torch radius of player ----
                # ---- or otherwise (mostly) invisible
                if distance > Game.torch_radius or Game.fov_map[y][x] == False:
                    # -- only blit (dark) if tile is explored. only draw explored Items (stairs)
                    if map_tile.explored:
                        if map_tile.char == "#":
                            c = self.wall_tile_dark
                            #print(map_tile.i)
                            #c = self.darkwalls[map_tile.i]
                        elif map_tile.char == ".":
                            c = self.floor_tile_dark
                        else:
                            raise SystemError("strange tile in map:", c)
                    else:
                        c= self.unknown_tile
                    #self.screen.blit(c, (x * self.grid_size[0], y * self.grid_size[1]))  # * self.grid_size[0], y * self.grid_size[1]))
                    #self.screen.blit(c, (x * self.grid_size[0], y * self.grid_size[1]))  # * self.grid_size[0], y * self.grid_size[1]))
                    self.tile_blit(c, x, y)
                    # ---- maybe a perma-visible objects lay here ? ---
                    olist = [o for o in Game.objects.values() if o.explored and o.stay_visible_once_explored and o.z==z and o.y==y and o.x == x]
                    for o in olist:
                        self.tile_blit(self.legend[o.char], x,y)
                    continue # next tile, please
                # ==============================================
                # ---- we are inside the torch radius ---
                # ---- AND we are visible! ----
                # explore if this tile is not yet explored
                if not map_tile.explored:
                    map_tile.explored = True
                # --- blit dungeon tile ----
                # TODO: option to skip blitting dungeon tile if Monster or object is here
                #print(self.game.player.z, map_tile.char)
                c = self.legend[map_tile.char] # light tiles
                #self.screen.blit(c, (x * self.grid_size[0], y * self.grid_size[1]))
                #self.screen.blit(c, (x * self.grid_size[0], y * self.grid_size[1]))
                self.tile_blit(c, x, y)      # first, blit the dungeon tile
                self.draw_non_monsters(x,y) # then, blit any items (stairs) on it
                self.draw_monsters(x,y)    # then, blit any monsters


    def draw_non_monsters(self, x, y):
        z = self.game.player.z
        for o in Game.objects.values():
            if o.z == z and o.y == y and o.x == x:  # only care if in the correct dungeon level
                # -- only care if NOT: Monster class instances or instances that are a child of the Monster class
                if not o.is_member("Monster"):
                    c = self.legend[o.char]
                    o.explored = True
                    #self.screen.blit(c, (m.x * self.grid_size[0], m.y * self.grid_size[1]))
                    self.tile_blit(c, o.x, o.y)

    def draw_monsters(self, x, y):
        z = self.game.player.z
        for o in Game.objects.values():
            if o.z == z and o.y == y and o.x == x: # only care if in the correct dungeon level
                # -- only care for Monster class instances or instances that are a child of the Monster class --
                if o.is_member("Monster"):
                    c = self.legend[o.char]
                    #self.screen.blit(c, (o.x * self.grid_size[0], o.y * self.grid_size[1]))
                    if o == self.game.player:
                        self.screen.blit(c, (self.pcx, self.pcy)) # blit the player always in middle of screen
                    else:
                        o.explored = True
                        self.tile_blit(c, o.x, o.y)
                    break # one monster per tile is enough

    def draw_radar(self):
        # make black square in top of panel
        self.radarscreen.fill((10,10,10)) # clear radarscreen
        delta_tiles = int(self.panel_width / 2 // self.radarblipsize)
        # make a radar blit for each explored dungeong tile
        for x in range(self.game.player.x-delta_tiles, self.game.player.x+delta_tiles+1):
            if x < 0:
                continue
            for y in range(self.game.player.y-delta_tiles, self.game.player.y+delta_tiles+1):
                if y < 0:
                    continue
                try:
                    t = Game.dungeon[self.game.player.z][y][x]
                except:
                    continue
                if t.explored:
                    if t.block_movement:
                        color = (50,50,250) # blue wall
                    else:
                        color = (150,150,150) # light grey corridor
                    dx = -(x - self.game.player.x) * self.radarblipsize
                    dy = -(y - self.game.player.y) * self.radarblipsize
                    pygame.draw.rect(self.radarscreen, color,(self.rcx-dx, self.rcy-dy, self.radarblipsize, self.radarblipsize))
                # ---if a stair is there, paint it (if explored) ---
                for o in Game.objects.values():
                    if o.z == self.game.player.z and o.y==y and o.x==x and o.is_member("Stair") and o.explored:
                        if o.char==">":
                            color = (128,255,128)
                        else:
                            color = (128,0,128)
                        pygame.draw.rect(self.radarscreen, color, (self.rcx-dx, self.rcy-dy, self.radarblipsize, self.radarblipsize))
        # make withe glowing dot at center of radarmap
        white = random.randint(200, 255)
        color = (white, white, white)
        pygame.draw.rect(self.radarscreen, color,(self.rcx , self.rcy , self.radarblipsize, self.radarblipsize))
        # blit radarscreen on screen
        self.screen.blit(self.radarscreen, (Viewer.width - Viewer.panel_width, 0))

    def draw_panel(self):
        # fill panelscreen with color
        self.panelscreen.fill((64, 128, 64))
        # write stuff in the panel
        # -y5------------
        write(self.panelscreen, text="dungeon: {}".format(self.game.player.z), x=5, y=5, color=(255, 255, 255))
        #cheering = ["go, Hero, go!",
        #            "come on, man!",
        #            "Yeah!", "That's cool!"]
        #write(self.panelscreen, text=random.choice(cheering),
        #        x=5, y=25)
        # - hitpoint bar in red, starting left
        pygame.draw.rect(self.panelscreen, (200, 0, 0),
                         (0, 35, self.game.player.hitpoints * Viewer.panel_width / self.game.player.hitpoints_max, 28))
        # -y35--------------------
        write(self.panelscreen, text="hp: {}/{}".format(
               self.game.player.hitpoints, self.game.player.hitpoints_max), x=5, y=35,
               color=(255,255,255), font_size=24)
        # -y65 ----------------------
        write(self.panelscreen, text="turn: {}".format(
               Game.turn), x=5, y=65, color=(255,255,255), font_size=24)
        # --- write cursor information into panel ---
        # - y95 ------

        tilex, tiley = self.game.player.x + Game.cursor_x, self.game.player.y + Game.cursor_y
        t = Game.dungeon[self.game.player.z][tiley][tilex]
        write(self.panelscreen, text="x: {}, y: {}".format(tilex, tiley), x=5, y=95, color=(255,255,255), font_size=16)
        # tile information
        # - y115
        write(self.panelscreen, text=Game.legend[t.char] if t.explored else "not yet explored" , x=5, y=115, color=(255,255,255), font_size=16)
        # objects on top of that tile ?
        here = []
        for o in Game.objects.values():
            #print("object:",o)
            if o.z == self.game.player.z and o.x == tilex and o.y == tiley and o.hitpoints >0:
                here.append(o)
        #print(here)
        for dy, thing in enumerate(here):
            # -y135 + 20*dy
            write(self.panelscreen, text=Game.legend[thing.char], x=5, y=135+20*dy, color=(255,255,255), font_size=16)




        # blit panelscreen
        self.screen.blit(self.panelscreen, (Viewer.width-self.panel_width, self.panel_width))

    def draw_log(self):
        # fill logscreen with color
        self.logscreen.fill((150,150,150))


        # write the log lines, from bottom (last log line) to top.
        for i in range(-1, -25, -1): # start, stop, step
            try:
                text = Game.log[i]
            except:
                continue
            textsf, (w,h) = make_text(text, font_size = self.logscreen_fontsize)
            self.logscreen.blit(textsf, (5, self.log_height + i * h))
        # ---- blit logscreen ------
        self.screen.blit(self.logscreen, (0, Viewer.height - self.log_height))

    def run(self):
        """The mainloop"""
        running = True
        pygame.mouse.set_visible(True)
        oldleft, oldmiddle, oldright = False, False, False
        self.game.make_fov_map()
        self.redraw = True
        #exittime = 0
        old_z = 999 # old z position of player
        show_range = False
        animation = 0
        
        while running:
            
            self.game.check_player()
            if Game.game_over:
                running = False
            milliseconds = self.clock.tick(self.fps)  #
            seconds = milliseconds / 1000
            # --- redraw whole screen if animation has ended ----
            if animation > self.playtime and animation < (self.playtime + seconds):
                self.redraw = True 
                
            self.playtime += seconds
            # --- check if the player has changed the dungeon level
            if old_z != self.game.player.z:
                recalculate_fov = True
            else:
                recalculate_fov = False
            old_z = self.game.player.z
            # ---------animation -------
            if animation > self.playtime:
                # --- draw laser beam -----
                c = (0,0,random.randint(10,250))
                w = random.randint(1,4)
                d = 8 # distance from corner of grid toward center for laser start points
                startpoints = [(d,d),
                         (self.grid_size[0]-d,d),
                         (d,self.grid_size[1]-d),
                         (self.grid_size[0]-d, self.grid_size[1]-d)]
                for x,y in startpoints:
                    pygame.draw.line(self.screen, c, 
                        (self.pcx+x,self.pcy+y), 
                        (self.pcx+self.grid_size[0]//2 +lasertarget[0] * self.grid_size[0],
                         self.pcy+self.grid_size[1]//2 +lasertarget[1] * self.grid_size[1]),
                         w)
                
                pygame.display.flip()
                self.screen.blit(self.background, (0, 0))
                # --- order of drawing (back to front) ---
                self.draw_dungeon()
                self.draw_radar()
                self.draw_panel()
                self.draw_log()
                continue
            #self.oldscreen = self.screen
            # -------- events ------
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                # ------- pressed and released key ------
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    # ---- move the game cursor with wasd ----
                    if event.key == pygame.K_a:
                        self.move_cursor(-1,0)
                        #Game.cursor_x -= 1
                    if event.key == pygame.K_d:
                        self.move_cursor(1,0)
                        #Game.cursor_x += 1
                    if event.key == pygame.K_w:
                        self.move_cursor(0,-1)
                        #Game.cursor_y -= 1
                    if event.key == pygame.K_s:
                        self.move_cursor(0,1)
                        #Game.cursor_y += 1
                    # ---- shoot laser beam to cursor -----
                    if event.key == pygame.K_1:
                        # laser = 1 
                        lasertarget = (Game.cursor_x, Game.cursor_y)
                        animation = self.playtime + 1
                    # ---- -simple player movement with cursor keys -------
                    if event.key == pygame.K_RIGHT:
                        Game.turn += 1
                        if not self.game.checkfight(self.game.player.x+1, self.game.player.y, self.game.player.z):

                            self.game.player.move(1, 0)
                            recalculate_fov = True
                            # TODO: weitermachen
                    if event.key == pygame.K_LEFT:
                        Game.turn += 1
                        self.game.player.move(-1, 0)
                        recalculate_fov = True
                    if event.key == pygame.K_UP:
                        Game.turn += 1
                        self.game.player.move(0, -1)
                        recalculate_fov = True
                    if event.key == pygame.K_DOWN:
                        Game.turn += 1
                        self.game.player.move(0, 1)
                        recalculate_fov = True
                    if event.key == pygame.K_SPACE:
                        # wait a turn
                        Game.turn += 1
                        self.redraw = True
                    if event.key == pygame.K_PAGEUP:
                        Game.turn += 1
                        # go up a level
                        self.game.ascend()
                    if event.key == pygame.K_PAGEDOWN:
                        Game.turn += 1
                        ready = self.game.descend()
                        #print("ready:", ready)
                    if event.key == pygame.K_r:
                        # zoom out radar
                        self.radarblipsize *= 0.5
                        self.radarblipsize = int(max(1, self.radarblipsize)) # don't become zero
                        print("radarblip:",self.radarblipsize)
                        

                        self.redraw = True
                    if event.key == pygame.K_t:
                        # zoom in radar
                        self.radarblipsize *= 2
                        self.radarblipsize = min(64, self.radarblipsize) # don't become absurd large
                        self.redraw = True
                    # --- increase torch radius ---
                    if event.key == pygame.K_PLUS:
                        Game.torch_radius += 1
                        recalculate_fov = True
                    # --- decrease torch radius ----
                    if event.key == pygame.K_MINUS:
                        Game.torch_radius -= 1
                        recalculate_fov = True


            # ============== draw screen =================
            if recalculate_fov:
                self.redraw = True
                self.game.make_fov_map()

            if self.redraw:
                Game.cursor_x, Game.cursor_y = 0, 0
                # delete everything on screen
                self.screen.blit(self.background, (0, 0))
                # --- order of drawing (back to front) ---
                self.draw_dungeon()

                self.draw_radar()
                #self.draw_panel()
                self.draw_log()
                ##for i in range(32):
                ##    print("i", i, i * 32)
                ##    self.screen.blit(self.lightfloors[i+320], (i * 32, 0))
                ##    self.screen.blit(self.darkfloors[i+320], (i * 32, 32))
                ##    self.screen.blit(self.lightwalls[i], (i * 32, 64))
                ##    self.screen.blit(self.darkwalls[i], (i * 32, 96))
            #elif Game.cursor_x != 0 or Game.cursor_y != 0:
            #    self.draw_panel()
            self.draw_panel() # always draw panel

            self.redraw = False


            # ------------ pressed keys ------
            pressed_keys = pygame.key.get_pressed()
            if pressed_keys[pygame.K_LSHIFT]:
                show_range = True
            else:
                show_range = False
            #if pressed_keys[pygame.K_SPACE]:
            #    pass

            # ------ mouse handler ------
            left, middle, right = pygame.mouse.get_pressed()
            # if oldleft and not left:
            #    self.launchRocket(pygame.mouse.get_pos())
            oldleft, oldmiddle, oldright = left, middle, right

            # ------ joystick handler -------
            for number, j in enumerate(self.joysticks):
                if number == 0:
                    x = j.get_axis(0)
                    y = j.get_axis(1)
                    buttons = j.get_numbuttons()
                    for b in range(buttons):
                        pushed = j.get_button(b)


            # write text below sprites
            fps_text = "FPS: {:5.3}".format(self.clock.get_fps())
            pygame.draw.rect(self.screen, (64, 255, 64), (Viewer.width - 110, Viewer.height - 20, 110,20))
            write(self.screen, text=fps_text, origin="bottomright", x=Viewer.width-2, y=Viewer.height-2, font_size=16, bold=True, color=(0,0,0))

            if show_range:
                pygame.draw.circle(self.screen, (200,0,0),
                                   (self.pcx, self.pcy),
                                   Game.torch_radius * self.grid_size[0],1)
            # ------ Cursor -----
            self.cursor.create_image()
            self.screen.blit(self.cursor.image,(
                  self.pcx+Game.cursor_x*self.grid_size[0],
                  self.pcy+Game.cursor_y*self.grid_size[1]))
            # -------- next frame -------------
            pygame.display.flip()
        # -----------------------------------------------------
        pygame.mouse.set_visible(True)
        pygame.quit()



if __name__ == '__main__':
    g = Game(tiles_x=80, tiles_y=40 )
    Viewer(g, width=1200, height=800, grid_size=(32,32)) #, (35,35))
