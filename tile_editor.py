import pygame, json, os, sys, array, time, random
from datetime import datetime

script_dir = os.path.dirname(os.path.abspath(__file__))
global ASSETS_DIR
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),"server","tile_data.json")
APPDATA_PATH = os.path.join(os.getenv('APPDATA'),"Hammerworld","tile_data.json")
BACKUP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),"server","backups")
tdata = None

def save():
    os.makedirs(BACKUP_PATH,exist_ok=True)
    path = os.path.join(BACKUP_PATH,"tile_data" + datetime.now().strftime("%H%M%S%d%m%Y") + ".json")
    os.rename(json_path, path)
    for path in [json_path,APPDATA_PATH]:
        try:
            with open(path, "w") as json_file:
                json.dump(tdata, json_file)
        except IOError as e:
            message_text = f"Fout bij opslaan in {path}: {e}"

pygame.init()
font = pygame.font.Font(None, 36)
info = pygame.display.Info()
global WIDTH, HEIGHT, TILESIZE
WIDTH, HEIGHT = info.current_w, info.current_h
TILESIZE = 32
global screen
screen = pygame.display.set_mode((WIDTH, HEIGHT))
CENTER = [WIDTH // 2, HEIGHT // 2]
pygame.display.set_caption("Hammerworld")

global clock
clock = pygame.time.Clock()
FPS = 60
current_frame = 0

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BROWN = (139, 69, 19)
RED = (255, 0, 0)
ORANGE = (255, 140, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 200, 0)
BLUE = (0, 0, 255)
CYAN =  (50,255,200)
PURPLE = (240,0,255)
GREY = (128, 128, 128)
LARSGROEN = (70,255,70)
PINK = (255,192,203)

global mapwidth, mapheight
mapwidth = mapheight = None

global tb_tilesize, tb_indent
tb_tilesize = 48
tb_indent = tb_tilesize // 4

global total_imgs, total_unanimated_imgs, imgs_per_layer
total_imgs = imgs_per_layer = None
total_unanimated_imgs = 999

def compress_list(l, compress_from : int = 5):
    return_value = []
    streak = 0
    streak_char = -1
    for i, num in enumerate(l):
        if num == streak_char:
            streak += 1
        else:
            if streak >= compress_from:
                return_value.append([streak,streak_char])
            else:
                return_value += [streak_char for _ in range(streak)]
            streak = 1
            streak_char = num
    if streak >= compress_from:
        return_value.append([streak,streak_char])
    else:
        return_value += [streak_char for _ in range(streak)]
    return return_value

def decompress_list(l):
    return_value = []
    for i, val in enumerate(l):
        if type(val) == list and len(val) != 3:
            return_value += [val[1] for _ in range(val[0])]
        else:
            return_value.append(val)
    return return_value

def update_list(l,old_amounts,new_amounts):
    return_value = []
    for i, val in enumerate(l):
        if type(val) == list: tochange = val[1]
        else: tochange = val
        if type(tochange) == list:
            return_value.append(tochange)
            continue
        for index, amount in enumerate(old_amounts):
            if tochange >= amount:
                tochange += new_amounts[index] - old_amounts[index]
                break
        if type(val) == list: return_value.append([val[0],tochange])
        else: return_value.append(tochange)
    print("updated the list")
    return return_value

def play_music(song_id):
    music_file = f"assets/area{song_id}.mp3" if isinstance(song_id, int) else f"assets/{song_id}.mp3"
    music_path = os.path.join(script_dir, music_file)
    try:
        pygame.mixer.music.load(music_path)
        pygame.mixer.music.play()
    except pygame.error as e:
        print(f"invalid music ID: {song_id}")
        play_music(random.randint(2,9))
    return f"Nu aan het spelen: area{song_id}"

def play_random_music():
    random_music_list = [
        "area0",
        "area2",
        "area3",
        "area4",
        "area5",
        "area6",
        "area7",
        "area8",
        "area9",
        "area11",
        "area13",
        "area14",
        "area15",
        #"area16",
    ]
    song = random.choice(random_music_list)
    music_file = f"assets/{song}.mp3"
    music_path = os.path.join(script_dir, music_file)
    pygame.mixer.music.load(music_path)
    pygame.mixer.music.play()
    return f"Nu aan het spelen: {song}"

def get_buttons(ikey,mleft,get_esc=False):
    esc_pressed = False
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if get_esc: esc_pressed = True
                else: sys.exit()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mleft = True
        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                mleft = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e:
                ikey = True
        if event.type == pygame.KEYUP:
            if event.key == pygame.K_e:
                ikey = False
    return (ikey,mleft,esc_pressed) if get_esc else (ikey,mleft)

def draw_button(button, text, color1, color2, centered : bool = False, increased_size : bool = False):
    if centered: button = pygame.Rect(button[0]-button[2]//2,button[1]-button[3]//2,button[2],button[3])
    if increased_size: button = pygame.Rect(button[0]-button[2]//10,button[1]-button[3]//10,round(button[2]*1.2),round(button[3]*1.2))
    pygame.draw.rect(screen,color1,button)
    global font
    start_text = font.render(text, True, color2[:3])
    start_text.set_alpha(color2[3] if len(color2) == 4 else 255)
    text_rect = start_text.get_rect(center=(button[0]+button[2]//2,button[1]+button[3]//2))
    screen.blit(start_text, text_rect)
    return button

def enter_text(msg: int, buttons : list = []):
    font = pygame.font.Font(None, 74)
    header_font = pygame.font.Font(None, 100)

    answer = ""
    input_active = True

    if buttons:
        for index, buttonname in enumerate(buttons):
            if len(buttons) % 2 == 0: 
                dif = index - len(buttons) // 2 + 0.5
                rect = pygame.Rect(WIDTH // 2 + round(275 * dif),HEIGHT // 3 * 2,200,100)
            else:
                dif = index - len(buttons) // 2
                rect = pygame.Rect(WIDTH // 2 + round(275 * dif),HEIGHT // 3 * 2,200,100)
            buttons[index] = (index + 1, rect, buttonname)

    result = False
    mouse_down = False
    selected = None

    while input_active and (not result or mouse_down):
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    sys.exit()
                if event.key not in [pygame.K_DELETE, pygame.K_TAB, pygame.K_BACKSPACE, pygame.K_RETURN]: 
                    answer += event.unicode
                if event.key in [pygame.K_DELETE, pygame.K_BACKSPACE]:
                    answer = answer[:-1]
                if event.key == pygame.K_RETURN:
                    input_active = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_down = True
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    mouse_down = False
        
        screen.fill(WHITE)
        header_surface = header_font.render(msg, True, BLACK)
        screen.blit(header_surface, (WIDTH // 2 - header_surface.get_width() // 2, HEIGHT // 4))

        text_surface = font.render(answer, True, BLACK)
        screen.blit(text_surface, (WIDTH // 2 - text_surface.get_width() // 2, HEIGHT // 2))

        for index, button, text in buttons:
            if draw_button(button,text,(170,170,170),BLACK,centered=True,increased_size=(selected==index)).collidepoint(pygame.mouse.get_pos()):
                selected = index
                if mouse_down: 
                    result = text[5:]
            elif selected == index: selected = None
        if not result:
            pygame.display.flip()
            clock.tick(FPS)

    return result or answer

def display_text(text, position, color = (0,0,0), centered : bool = False):
    global font
    text_surface = font.render(text, True, color)
    if centered:
        text_rect = text_surface.get_rect(center=position)
        screen.blit(text_surface, text_rect)
    else:
        screen.blit(text_surface, position)

def menu(caption = None, buttons = None, bgcolor = (0,255,0), esc_allowed = False):
    buttons = [button for button in buttons]
    result = None
    interact_key_pressed, mouse_down = False, False
    selected = None

    if caption: header = pygame.font.Font(None, 120).render(caption, True, BLACK)

    if buttons:
        for index, buttonname in enumerate(buttons):
            if len(buttons) % 2 == 0: 
                dif = index - len(buttons) // 2 + 0.5
                rect = pygame.Rect(WIDTH // 2 + round(275 * dif),HEIGHT // 2,200,100)
            else:
                dif = index - len(buttons) // 2
                rect = pygame.Rect(WIDTH // 2 + round(275 * dif),HEIGHT // 2,200,100)
            buttons[index] = (index + 1, rect, buttonname)
    while not result or mouse_down:
        screen.fill(bgcolor)
        if caption: screen.blit(header, ((WIDTH - header.get_width()) // 2, HEIGHT // 4))
        interact_key_pressed, mouse_down, esc_pressed = get_buttons(interact_key_pressed,mouse_down,get_esc=True)
        if esc_pressed: return None
        for index, button, text in buttons:
            if draw_button(button,text,WHITE,BLACK,centered=True,increased_size=(selected==index)).collidepoint(pygame.mouse.get_pos()):
                selected = index
                if mouse_down: result = text
            elif selected == index: selected = None
        if not result:
            pygame.display.flip()
            clock.tick(FPS)
    pygame.display.flip()
    return result

tiletex_img = pygame.image.load(os.path.join(os.path.join(os.path.dirname(__file__), "assets"), "tilemap.png"))
tiletex_width = tiletex_img.get_size()[0] // TILESIZE
tiletex_height = tiletex_img.get_size()[1] // TILESIZE

atiletex_img = pygame.image.load(os.path.join(os.path.join(os.path.dirname(__file__), "assets"), "atilemap.png"))
atiletex_height = atiletex_img.get_size()[1] // TILESIZE

stiletex_img = pygame.image.load(os.path.join(os.path.join(os.path.dirname(__file__), "assets"), "stilemap.png"))
stiletex_width = stiletex_img.get_size()[0] // TILESIZE

here_starts_animated = tiletex_width * tiletex_height
here_starts_seasonal = here_starts_animated + atiletex_height
total_imgs = here_starts_seasonal + stiletex_width

new_amounts = [here_starts_animated,here_starts_seasonal,total_imgs]

with open(json_path, 'r', encoding='utf-8') as json_file:
    try:
        tdata = json.load(json_file)
    except Exception as e:
        sys.exit()

tilemaps = tdata['tiles']
old_amounts = tdata['amounts'] if 'amounts' in tdata else new_amounts
tdata['amounts'] = new_amounts
if old_amounts != new_amounts: # update all values to accomodate for new textures
    for area in tilemaps.keys():
        tilemaps[area][1] = update_list(tilemaps[area][1],old_amounts,new_amounts)
save()

area = None

inmenu = True

tile_cache = tdata['tilecache'] if 'tilecache' in tdata else dict()
if 'history' in tile_cache: last_buttons = tile_cache['history']
else: last_buttons = []
while inmenu:
    choice = menu(
        caption = "Tile Editor voor Hammerworld",
        buttons = ["Open...","Nieuw...","Verwijder..."],
        bgcolor=BROWN
    )
    if choice == "Open...":
        area = enter_text(
            "Vul gebiedsnummer in...",
            buttons=["Area " + i for i in last_buttons]
        )
        while not (area.isdigit() and area in tilemaps.keys()): area = enter_text("Probeer opnieuw.")
        tdata['tilecache'] = tile_cache
        if area in last_buttons:
            last_buttons.remove(area)
            tdata['tilecache']['history'] = ([area] + last_buttons)
        else:
            tdata['tilecache']['history'] = ([area] + last_buttons[:4])
        saveable_interact_rects = tilemaps[area][3]
        interact_rects = []
        for rectinfo in saveable_interact_rects:
            appended = [pygame.Rect(rectinfo[0][0]*TILESIZE,rectinfo[0][1]*TILESIZE,rectinfo[0][2]*TILESIZE,rectinfo[0][3]*TILESIZE),rectinfo[1]]
            if len(rectinfo) == 3: appended.append(rectinfo[2])
            interact_rects.append(appended)
        inmenu = False
    elif choice == "Nieuw...":
        if menu(
            caption = "Tile Editor voor Hammerworld",
            buttons = ["Gebied..."], #"Tegels"],
            bgcolor=PINK
        ) == "Tegels": sys.exit()
        else:
            results = ["Vul gebiedsnummer in...","Breedte: (-)","Lengte: (|)"]
            for i in range(len(results)):
                results[i] = enter_text(results[i])
                while not (results[i].isdigit() and int(results[i]) < 999): results[i] = enter_text("Probeer opnieuw.") 
            if results[0] in tilemaps.keys(): raise ValueError("gebied bestaat al")
            area = results[0]
            tdata["tiles"][area] = [[int(results[1]),int(results[2])],[],False]
            for _ in range(int(results[1])*int(results[2])):
                tdata["tiles"][area][1].append(0)
            mapwidth, mapheight = results[1:]
            interact_rects = []
            saveable_interact_rects = []
            inmenu = False
    elif choice == "Verwijder...":
        area = enter_text("Vul gebiedsnummer in...")
        while not (area.isdigit() and area in tilemaps.keys()): area = enter_text("Probeer opnieuw.")
        del tdata['tiles'][area]
        save()

global textures
textures = []
def create_toolbox(tb_rect : pygame.Rect, season : int = 0):
    space = round(tb_tilesize * 1.25)
    global total_imgs, total_unanimated_imgs, imgs_per_layer
    imgs_per_layer = round((tb_rect[2] - tb_tilesize // 4) // space)

    height = total_imgs // imgs_per_layer + 1
    teximg = pygame.Surface((tb_rect[2], height * (tb_tilesize + tb_indent)))
    teximg.fill(BROWN)
    starting_point = tb_indent
    tileindex = 0
    global textures
    textures = []
    for y in range(height):
        for x in range(imgs_per_layer):
            if tileindex >= here_starts_seasonal:
                texture = stiletex_img.subsurface((tileindex - here_starts_seasonal) * TILESIZE, season * TILESIZE, TILESIZE, TILESIZE)
            elif tileindex >= here_starts_animated:
                texture = atiletex_img.subsurface(0, (tileindex - here_starts_animated) * TILESIZE, TILESIZE, TILESIZE)
            else:
                texture = tiletex_img.subsurface(((tileindex % tiletex_width) * TILESIZE, (tileindex // tiletex_width) * TILESIZE, TILESIZE, TILESIZE))
            teximg.blit(pygame.transform.scale(texture, (tb_tilesize, tb_tilesize)), (starting_point + x * space, starting_point + y * space))
            textures.append(texture)
            tileindex += 1
            if tileindex >= total_imgs: return teximg
    return teximg

def set_bgimg(changes : list = None):
    global bgimg, current_tilemap, map_back
    if changes: #change = (posx, posy, newindex)
        for change in changes:
            map_back[change[0]][change[1]] = change[2]
    bgimg = pygame.Surface(pixsize)
    glitch = pygame.transform.scale(pygame.image.load(os.path.join(ASSETS_DIR,'glitch.png')),(TILESIZE,TILESIZE))
    for x, col in enumerate(map_back):
        for y, val in enumerate(col):
            if type(val) == list:
                pygame.draw.rect(bgimg,tuple(val),(x * TILESIZE, y * TILESIZE, TILESIZE, TILESIZE))
                continue
            try:
                bgimg.blit(textures[val], (x * TILESIZE, y * TILESIZE))
            except:
                bgimg.blit(glitch, (x * TILESIZE, y * TILESIZE))

if area:
    global current_tilemap, bgimg
    bgimg = None

    season = 0
    
    current_tilemap = tilemaps[area]
    current_tilemap[1] = decompress_list(current_tilemap[1])

    mapwidth, mapheight = current_tilemap[0][0], current_tilemap[0][1]
    pixsize = (mapwidth * TILESIZE, mapheight * TILESIZE)

    toolbox_rect = pygame.Rect(WIDTH // 8 * 7 - 20, 0, WIDTH // 8 + 20, HEIGHT)
    tb_img = create_toolbox(toolbox_rect)

    map_back = [current_tilemap[1][i * mapheight:(i + 1) * mapheight] for i in range(mapwidth)]
    map_animated = current_tilemap[2] if current_tilemap[2] else None
    set_bgimg()
    camera_pos = [0,0] 

    message_text = play_music(area)
    message_text_timer = pygame.time.get_ticks() + 6000

    e_pressed = False
    mouse_down = mouse_just_pressed = [False, False]

    scroll_y = 0

    selected_tile = [-1,-1]

    tools = ["Pen","Rechthoek","Vervang","Kwast"]
    current_tool = 0

    layer_img = pygame.image.load(os.path.join(ASSETS_DIR, "layers.png"))
    layers = [pygame.transform.scale(layer_img.subsurface((0,0,16,16)),(32,32)),pygame.transform.scale(layer_img.subsurface((16,0,16,16)),(32,32))]
    current_layer = 0
    brush_img = pygame.transform.scale(pygame.image.load(os.path.join(ASSETS_DIR, "brush.png")),(32,32))
    brush_color = [255,0,0]
    global brush_values
    brush_values = dict()
    for x in range(32):
        for y in range(32):
            r, g, b, a = brush_img.get_at((x,y))
            if (g,b) == (0,0) and r > 0:
                if r not in brush_values: brush_values[r] = []
                brush_values[r].append((x,y))
    def change_brush_color(brush,color):
        global brush_values
        for rgbmult, poses in brush_values.items():
            colorhere = tuple([round(i * rgbmult / 255) for i in color])
            for x, y in poses:
                print(colorhere)
                brush.set_at((x,y),colorhere)
        return brush

    current_mouse = None

    changes = []
    changing = False

    using = [-1,-1]
    old_mouse_coordinate = [0,0]

    message_text = ''
    message_text_timer = 0

    save_rect = pygame.Rect(0,0,110,30)
    layer_rect = pygame.Rect(10, HEIGHT - 42, 32, 32)
    brush_rect = pygame.Rect(10, HEIGHT - 82, 32, 32)

    dark_overlay = pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
    dark_overlay.fill((0,0,0,120))

    spread = 50
    slider_down = False
    mousepressed = False

    running = True
    while running:
        screen.fill((135,206,235))
        current_time = pygame.time.get_ticks()

        mouse_pos = pygame.mouse.get_pos()
        colliding_toolbox = toolbox_rect.collidepoint(mouse_pos)

        mouse_just_pressed = [False, False]
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    sys.exit()
                elif event.key == pygame.K_r and not changing and current_layer == 0:
                    current_tool = (current_tool + 1) % len(tools)
                    message_text = f"Je gebruikt nu {tools[current_tool]}."
                    message_text_timer = current_time + 2000
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if layer_rect.collidepoint(mouse_pos):
                        current_layer = (current_layer + 1) % len(layers)
                        message_text = f"Huidige laag: {["Tegelachtergrond","Activatielaag"][current_layer]}."
                        message_text_timer = current_time + 2000
                    elif current_tool == 3 and current_layer == 0 and brush_rect.collidepoint(mouse_pos):
                        brush_color = []
                        for c in ['r','g','b']:
                            a = enter_text(f"Vul kleurwaarde {c} in:")
                            while not (a.isdigit() and int(a) >= 0 and int(a) <= 255):
                                a = enter_text(f"Vul kleurwaarde {c} in:")
                            brush_color.append(int(a))
                        brush_img = change_brush_color(brush_img,brush_color)
                    else:
                        mouse_down[0] = True
                        mouse_just_pressed[1] = True
                elif event.button == 3:
                    mouse_down[1] = True
                    mouse_just_pressed[1] = True
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    mouse_down[0] = False
                elif event.button == 3:
                    mouse_down[1] = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_e:
                    e_pressed = True
                if event.key == pygame.K_t:
                    season = (season + 1) % 4
                    message_text = f"Huidig seizoen: {['lente','zomer','herfst','winter'][season]}"
                    message_text_timer = current_time + 3000
                    tb_img = create_toolbox(toolbox_rect,season=season)
                    set_bgimg()
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_e:
                    e_pressed = False
            if event.type == pygame.MOUSEWHEEL and colliding_toolbox:
                scroll_y = max(scroll_y - event.y * 50, 0)
        
        keys = pygame.key.get_pressed()
        cam_speed = 10 if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] else 5
        if (keys[pygame.K_LEFT] or keys[pygame.K_a]):
            camera_pos[0] -= cam_speed
        if (keys[pygame.K_RIGHT] or keys[pygame.K_d]):
            camera_pos[0] += cam_speed
        if (keys[pygame.K_UP] or keys[pygame.K_w]):
            camera_pos[1] -= cam_speed
        if (keys[pygame.K_DOWN] or keys[pygame.K_s]):
            camera_pos[1] += cam_speed
        screen.blit(bgimg,(-camera_pos[0],-camera_pos[1]))

        mouse_coordinate = ((mouse_pos[0] + camera_pos[0]) // TILESIZE, (mouse_pos[1] + camera_pos[1]) // TILESIZE)
        if mouse_coordinate[0] >= mapwidth or mouse_coordinate[0] < 0 or mouse_coordinate[1] >= mapheight or mouse_coordinate[1] < 0: mouse_coordinate = None
        else: pygame.draw.rect(screen, YELLOW, (mouse_coordinate[0] * TILESIZE - camera_pos[0], mouse_coordinate[1] * TILESIZE - camera_pos[1], TILESIZE, TILESIZE), 2)

        if current_layer == 1:
            screen.blit(dark_overlay,(0,0))
        
        if True:
            tempsurface = pygame.Surface(pixsize,pygame.SRCALPHA)
            alpha = 128 if current_layer == 1 else 30
            colors = [(255,0,0,alpha),(0,255,0,alpha),(0,0,255,alpha)]
            delete = []
            for index, tup in enumerate(interact_rects):
                rect, itype = tup[:2]
                pygame.draw.rect(tempsurface,(colors[itype]),rect)
                if itype in {1,2}: display_text(str(tup[2]), (rect[0]+rect[2]//2-camera_pos[0],rect[1]+rect[3]//2-camera_pos[1]), color=WHITE, centered=True)
                if mouse_down[1] and current_layer == 1 and rect.collidepoint((mouse_pos[0] + camera_pos[0], mouse_pos[1] + camera_pos[1])): delete.append(index)
            for index in delete[::-1]:
                interact_rects.pop(index)
                saveable_interact_rects.pop(index)
            screen.blit(tempsurface,(-camera_pos[0],-camera_pos[1]))
        
        pygame.draw.rect(screen, BROWN, toolbox_rect)
        screen.blit(tb_img, (toolbox_rect[0], toolbox_rect[1] - scroll_y))

        check_mouse_outside_map = (colliding_toolbox or save_rect.collidepoint(mouse_pos) or layer_rect.collidepoint(mouse_pos))
        if (current_tool == 1 and selected_tile[0] != -1 or current_layer == 1) and not check_mouse_outside_map:
            if mouse_coordinate and not changing:
                if mouse_down[0]:
                    using = [selected_tile[0], (selected_tile[1] if selected_tile[1] != -1 else selected_tile[0])]
                    changing = True
                    old_mouse_coordinate = [mouse_coordinate[0],mouse_coordinate[1]]
            elif mouse_coordinate and changing:
                deltax = abs(old_mouse_coordinate[0] - mouse_coordinate[0]) + 1
                deltay = abs(old_mouse_coordinate[1] - mouse_coordinate[1]) + 1
                lowerx = min(old_mouse_coordinate[0], mouse_coordinate[0])
                lowery = min(old_mouse_coordinate[1], mouse_coordinate[1])
                if mouse_down[0]:
                    example_rect = pygame.Rect(lowerx * TILESIZE - camera_pos[0], lowery * TILESIZE - camera_pos[1], deltax * TILESIZE, deltay * TILESIZE)
                    pygame.draw.rect(screen, WHITE, example_rect)
                else:
                    if current_layer == 0:
                        changes = []
                        for x in range(lowerx, lowerx + deltax):
                            for y in range(lowery, lowery + deltay):
                                changes.append((x,y,(using[1] if x == lowerx or x == lowerx + deltax - 1 or y == lowery or y == lowery + deltay - 1 else using[0])))
                        set_bgimg(changes=changes)
                    elif current_layer == 1:
                        possiblities = ["muur","interactiezone"]
                        #if (deltax == 1 and mouse_coordinate[0] in {0,mapwidth-1}) or (deltay == 1 and mouse_coordinate[1] in {0,mapheight-1}): 
                        possiblities.append("naar andere area")
                        ans = menu(caption="Kies een functionaliteit:",buttons=possiblities,bgcolor=PURPLE)
                        if ans:
                            i = possiblities.index(ans)
                            if i == 1:
                                a = enter_text("Vul framesleutel in...")
                                while len(a) > 25: a = enter_text("Probeer opnieuw.") # arbitrary limit
                                interact_rects.append((
                                    pygame.Rect(lowerx * TILESIZE, lowery * TILESIZE, deltax * TILESIZE, deltay * TILESIZE),
                                    i, a
                                ))
                                saveable_interact_rects.append((
                                    [lowerx, lowery, deltax, deltay],
                                    i, a
                                ))
                            elif i == 2:
                                #notallowed = set()
                                #for tup in interact_rects:
                                #    if len(tup) == 3 and tup[1] == 2: notallowed.add(tup[2])
                                a = enter_text("Vul gebiedsnummer in...")
                                #while not (a.isdigit() and a in tilemaps.keys()) or int(a) in notallowed or a == area: a = enter_text("Probeer opnieuw.")
                                while not (a.isdigit() and int(a) < 999) or a == area: a = enter_text("Probeer opnieuw.")
                                interact_rects.append((
                                    pygame.Rect(lowerx * TILESIZE, lowery * TILESIZE, deltax * TILESIZE, deltay * TILESIZE),
                                    i, int(a)
                                ))
                                saveable_interact_rects.append((
                                    [lowerx, lowery, deltax, deltay],
                                    i, int(a)
                                ))
                            else:
                                interact_rects.append((
                                    pygame.Rect(lowerx * TILESIZE, lowery * TILESIZE, deltax * TILESIZE, deltay * TILESIZE),
                                    i
                                ))
                                saveable_interact_rects.append((
                                    [lowerx, lowery, deltax, deltay],
                                    i
                                ))
                    changing = False
        elif current_tool == 0:
            if mouse_coordinate:
                for i in range(2):
                    if mouse_down[i] and not check_mouse_outside_map and selected_tile[i] != -1:
                        newchange = (mouse_coordinate[0],mouse_coordinate[1],selected_tile[i])
                        if newchange not in changes: changes.append(newchange)
            
            if not (mouse_down[0] or mouse_down[1]) and changes:
                set_bgimg(changes=changes)
                changes = []
            elif changes:
                for posx, posy, index in changes:
                    pygame.draw.rect(screen, WHITE, (posx * TILESIZE - camera_pos[0], posy * TILESIZE - camera_pos[1], TILESIZE, TILESIZE))
        elif current_tool == 3:
            screen.blit(brush_img,brush_rect)
            if mouse_coordinate:
                for i in range(2):
                    if mouse_down[i] and not check_mouse_outside_map:
                        newchange = (mouse_coordinate[0],mouse_coordinate[1],brush_color)
                        if newchange not in changes: changes.append(newchange)
            
            if not (mouse_down[0] or mouse_down[1]) and changes:
                set_bgimg(changes=changes)
                changes = []
            elif changes:
                for posx, posy, index in changes:
                    pygame.draw.rect(screen, WHITE, (posx * TILESIZE - camera_pos[0], posy * TILESIZE - camera_pos[1], TILESIZE, TILESIZE))
            
        
        space = tb_tilesize + tb_indent

        height = total_imgs // imgs_per_layer + 1
        teximg = pygame.Surface((toolbox_rect[0], height * space))
        teximg.fill(BROWN)
        starting_point = (toolbox_rect[0] + tb_indent, tb_indent)

        tile_index = 0
        for y in range(height):
            for x in range(imgs_per_layer):
                r = pygame.Rect(starting_point[0] + x * space, starting_point[1] + y * space - scroll_y, tb_tilesize, tb_tilesize)
                if r.collidepoint(mouse_pos) and toolbox_rect.collidepoint(mouse_pos):
                    pygame.draw.rect(screen, YELLOW, r, 2)
                    if mouse_down[0]: selected_tile[0] = tile_index
                    elif mouse_just_pressed[1]:
                        #print(f"before: {selected_tile[1]}")
                        selected_tile[1] = -1 if selected_tile[1] == tile_index else tile_index
                        #print(f"after: {selected_tile[1]}")
                if tile_index == selected_tile[0]: pygame.draw.rect(screen, BLUE, r, 3)
                elif tile_index == selected_tile[1]: pygame.draw.rect(screen, RED, r, 3)
                tile_index += 1
        
        if draw_button(save_rect,"opslaan",WHITE,BLACK).collidepoint(mouse_pos) and mouse_down[0]:
            message_text = f"Het gebied is opgeslagen naar current_area = {area}."
            message_text_timer = current_time + 3000
            
            tdata['tiles'][str(area)] = [[mapwidth, mapheight], [], False, []]
            for col in map_back:
                tdata['tiles'][str(area)][1] += col
            for tup in saveable_interact_rects:
                if len(tup) == 3:
                    tdata['tiles'][str(area)][3].append([list(tup[0]),tup[1],tup[2]])
                else:
                    tdata['tiles'][str(area)][3].append([list(tup[0]),tup[1]])

            tdata['tiles'][str(area)][1] = compress_list(tdata['tiles'][str(area)][1])
            save()
            time.sleep(0.5)

        if current_time < message_text_timer:
            if isinstance(message_text,str):
                display_text(message_text, (60, HEIGHT - 40))
            elif isinstance(message_text,list):
                display_text(message_text[0], (60, HEIGHT - 40))
        else:
            if isinstance(message_text,str):
                message_text = ""
            elif isinstance(message_text,list):
                display_text(message_text[0], (10, HEIGHT - 40))
                message_text.pop(0)
                message_text_timer = current_time + 5000
                if len(message_text) == 1: message_text = message_text[0]
        
        if not pygame.mixer.music.get_busy():
            msg = play_random_music()
            if not message_text:
                message_text = msg
                message_text_timer = current_time + 5000
        
        if current_tool == 2 and current_layer == 0 and selected_tile[0] != -1:
            slider_base = HEIGHT-160
            pygame.draw.rect(screen,BLUE,(25,slider_base,20,100))

            slider_height = 16
            slider_rect = pygame.Rect(20,slider_base+spread-slider_height//2,30,slider_height)
            if selected_tile[1] == -1: spread = 100
            if mouse_down[0] and (slider_down or slider_rect.collidepoint(mouse_pos)):
                slider_down = True
                spread = max(min(100,mouse_pos[1]-slider_base),0)
            else: slider_down = False
            pygame.draw.rect(screen,RED,(25,slider_base+spread,20,100-spread))
            pygame.draw.rect(screen,GREY,slider_rect)

            if mouse_down[0]:
                if not mousepressed and mouse_coordinate and not slider_down and not check_mouse_outside_map and selected_tile[0] != -1:
                    mousepressed = True
                    thistile = map_back[mouse_coordinate[0]][mouse_coordinate[1]]
                    for x, col in enumerate(map_back):
                        for y, i in enumerate(map_back[x]):
                            if i == thistile:
                                map_back[x][y] = (selected_tile[1] if random.randint(1,100) > spread else selected_tile[0])
                    set_bgimg()
            else: mousepressed = False
        
        screen.blit(layers[current_layer],layer_rect)
        
        pygame.display.flip()
        current_frame += 1
        clock.tick(FPS)