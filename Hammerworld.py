import random, time
import pygame, cv2
import sys, os, json, shutil
import math, array, struct
import socket, pickle
import threading, subprocess
from PIL import Image

pygame.init()

#Checklist:
#1: De timed quest werkt, maar de beloning moet nog aangepast worden aan de waarde van het voorwerp (nu standaard 1000 euro).
#2: Er worden nog geen crops gevraagd voor de timed quest.
#3: Farmen synchroniseren.
#4: Met Ben praten voor timed quests of andere activiteiten start een nieuwe dag.
#5: Singleplayer gaat mis wanneer er al iemand in de interne server zit.
#6: Geluidseffecten?
#7: Zeldzamere vissen ook echt zeldzamer maken. #zvhier
#8: Items en statistieken samenbundelen.
#9: Easter egg met name=Tommy terugbrengen.
#10: Zelf servers toevoegen in het spel?
#11: Als je pauzeert in het journalmenu verdwijnt dat menu niet.

if hasattr(sys, '_MEIPASS'):
    BASE_PATH = ASSETS_PATH = sys._MEIPASS
    EXE_PATH = os.path.dirname(sys.executable)
else:
    BASE_PATH = EXE_PATH = os.path.dirname(os.path.abspath(__file__))
    ASSETS_PATH = os.path.join(BASE_PATH,"assets")
JSON_PATH = os.path.join(os.getenv('APPDATA'),"Hammerworld")
os.makedirs(JSON_PATH, exist_ok=True)

singleplayer = False
server_process = None
def terminate_game():
    if singleplayer and server_process:
        server_process.terminate()
        server_process.wait()
    sys.exit()

# fish list
with open(os.path.join(BASE_PATH, "fish_data.json"), "r") as file:
    data = json.load(file)
    fish_list = [] # zvhier
    for fish in data["common"]:
        fish["day"] = 5
        fish_list.append(fish)
    for fish in data["rare"]:
        fish["day"] = 12
        fish_list.append(fish)

# crops list
with open(os.path.join(BASE_PATH, "crops_data.json"), "r") as file:
    crops_list = json.load(file)

# translations
with open(os.path.join(BASE_PATH, "item_translations.json"), "r") as file:
    item_translations = json.load(file)

day_str = None

def play_video(video_file : str, music_file : str):
    video_path = os.path.join(ASSETS_PATH, video_file)
    music_path = os.path.join(ASSETS_PATH, music_file)

    video_size = [WIDTH,HEIGHT]

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        terminate_game()

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_duration = 1.0 / fps
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    pygame.mixer.music.load(music_path)
    pygame.mixer.music.play()

    running = True
    last_time = time.perf_counter()
    frame_idx = 0

    while running:
        now = time.perf_counter()
        elapsed = now - last_time

        if elapsed < frame_duration:
            time.sleep(frame_duration - elapsed)
            continue

        last_time = now

        ret, frame = cap.read()
        if not ret or frame_idx >= total_frames:
            break

        frame = cv2.flip(frame, 1)
        frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_surface = pygame.surfarray.make_surface(frame)

        screen.blit(frame_surface, ((WIDTH-video_size[0])//2, (HEIGHT-video_size[1])//2))
        pygame.display.flip()

        frame_idx += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

    cap.release()
    pygame.mixer.music.stop()
    play_music(0)

def play_music(song_id,pname:str=None):
    music_file = os.path.join(ASSETS_PATH, f"area{song_id}.mp3") if isinstance(song_id, int) else os.path.join(ASSETS_PATH, song_id)
    try:
        pygame.mixer.music.load(music_file)
        pygame.mixer.music.play(-1)
    except pygame.error as e:
        print("Denk aan de muziek!")
        pygame.mixer.music.load(os.path.join(ASSETS_PATH, f"area{11 if pname != "Tommy" else 17}.mp3"))
        pygame.mixer.music.play(-1)

def load_img_from_assets(name : str):
    global ASSETS_PATH
    try:
        return pygame.image.load(os.path.join(ASSETS_PATH, name))
    except:
        return pygame.image.load(os.path.join(ASSETS_PATH, "Glitch.png"))

ctime = pygame.time.get_ticks()
new_tick = pygame.time.get_ticks()
last_tick_time = pygame.time.get_ticks()
elapsed_real_time = (new_tick - last_tick_time) / 1000.0

global music_slider_down, music_volume
music_slider_down = False
music_volume = 100

if elapsed_real_time >= 1:
    game_time_minutes += int(elapsed_real_time)
    last_tick_time = new_tick
font = pygame.font.Font(None, 36)

global WHITE, BLACK, BROWN, RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE, GREY
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

info = pygame.display.Info()
global WIDTH, HEIGHT
WIDTH, HEIGHT = min(info.current_w,1920), min(info.current_h,1080)
global screen
screen = pygame.display.set_mode((WIDTH, HEIGHT))
CENTER = [WIDTH // 2, HEIGHT // 2]
pygame.display.set_caption("Hammerworld")

global clock
clock = pygame.time.Clock()
FPS = 60

global travel_cost
travel_cost = 50

global minimum_gus
minimum_gus = 5000

global chicken_price_increase
chicken_price_increase = 400

tree_size = 48
cactus_size = round(WIDTH * 0.026)

global border_open
border_open = True
changed_sdata = {}

def enter_text(msg: int, can_exit : bool = False):
    font = pygame.font.Font(None, 74)
    header_font = pygame.font.Font(None, 100)

    answer = ""
    input_active = True

    while input_active:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key not in [pygame.K_DELETE, pygame.K_TAB, pygame.K_BACKSPACE, pygame.K_RETURN]: 
                    answer += event.unicode
                if event.key in [pygame.K_DELETE, pygame.K_BACKSPACE]:
                    answer = answer[:-1]
                if event.key == pygame.K_RETURN:
                    input_active = False
        
        screen.fill(WHITE)
        header_surface = header_font.render(msg, True, BLACK)
        screen.blit(header_surface, (WIDTH // 2 - header_surface.get_width() // 2, HEIGHT // 4))

        text_surface = font.render(answer, True, BLACK)
        screen.blit(text_surface, (WIDTH // 2 - text_surface.get_width() // 2, HEIGHT // 2))

        pygame.display.flip()
        clock.tick(FPS)

    return answer

def load_gif_frames(path, max_frames=30, size = (WIDTH, HEIGHT)):
    pil_img = Image.open(path)
    frames = []
    frame_count = 0
    try:
        while True:
            if frame_count >= max_frames:
                break
            frame = pil_img.convert("RGBA")
            py_img = pygame.image.fromstring(frame.tobytes(), frame.size, frame.mode)
            py_img = pygame.transform.scale(py_img, size) 
            frames.append(py_img)
            pil_img.seek(pil_img.tell() + 1)
            frame_count += 1
    except EOFError:
        pass
    return frames

def overworld():
    global current_area, player_pos, accumulated_money, server_data
    current_area = 9
    server_data = {}

    global player_pos
    player_pos = (3,5)
    global controls_modifier
    controls_modifier = 1
    global accumulated_money, treechanges, rockchanges
    accumulated_money = 200
    treechanges = []
    rockchanges = []
    global events
    events = []

    #time == 1: 06:01
    #time == 60: 07:00
    ben_schedule = {
        690: (3,7),
        720: (49,7),
        900: (3,7),
        930: (2,2)
    }
    tilesize = 48
    npc_size = 32
    dev = (tilesize-npc_size) // 2
    for key, item in ben_schedule.items():
        x, y = item
        ben_schedule[key] = (x*tilesize+dev,y*tilesize+dev)


    def display_text(text, position, color = (0,0,0), area : int = 0, orientation : str = 'left', custom_font = None):
        global font
        font_here = custom_font or font
        if area in {15}: color = (255,255,255)
        text_surface = font_here.render(text, True, color)
        if orientation == 'center':
            text_rect = text_surface.get_rect(center=position)
            screen.blit(text_surface, text_rect)
        elif orientation == 'right':
            text_width = text_surface.get_rect()[2]
            screen.blit(text_surface,(position[0]-text_width,position[1]))
        else:
            screen.blit(text_surface, position)

    def display_text_pro(text, position, color, customFont = None):
        global font
        displayFont = customFont if customFont else font
        start_text = displayFont.render(text, True, color[:3])
        start_text.set_alpha(color[3] if len(color) == 4 else 255)
        text_rect = start_text.get_rect(center=position)
        screen.blit(start_text, text_rect)

    # Singleplayer world selection UI (nested so it's inside overworld scope)
    def singleplayer_menu():
        mouse_down = False
        interact_key_down = False

        w, h, dist = 300, 100, 50
        ind = [50, HEIGHT//2 - 50]

        world_dir = os.path.join(os.getenv("APPDATA"), "Hammerworld")
        worlds = [w for w in os.listdir(world_dir) if os.path.isdir(os.path.join(world_dir, w))]

        back_button = pygame.Rect(WIDTH - 150, HEIGHT - 80, 120, 50)

        selected = None
        delete_confirm = None

        while True:
            screen.fill(BROWN)
            mousePos = pygame.mouse.get_pos()

            events = pygame.event.get()

            # --- Event handling ---
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mouse_down = True
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    mouse_down = False
                if event.type == pygame.KEYDOWN:
                    if event.key == controls[4]:
                        interact_key_down = True
                if event.type == pygame.KEYUP:
                    if event.key == controls[4]:
                        interact_key_down = False

            # Titel
            display_text(["Select a world:", "Selecteer een wereld:"][taal],
                        (WIDTH // 2 - 200, 80))

            shown = 0
            for i, world in enumerate(worlds):
                interactrect = pygame.Rect(ind[0] + (w + dist) * shown, ind[1], w, h)
                hovering = interactrect.collidepoint(mousePos)

                if hovering:
                    interactrect = pygame.Rect(interactrect.x - 10, interactrect.y - 10,
                                            interactrect.w + 20, interactrect.h + 20)

                pygame.draw.rect(screen, WHITE, interactrect)
                display_text(world, (interactrect.x + 15, interactrect.y + 15))

                delete_rect = pygame.Rect(interactrect.x, interactrect.y + 60, 120, 40)
                pygame.draw.rect(screen, RED, delete_rect)
                display_text(["Delete", "Verwijderen"][taal],(delete_rect.x, delete_rect.y), color=WHITE)

                if mouse_down:
                    if delete_rect.collidepoint(mousePos) and not delete_confirm:
                        delete_confirm = world
                    elif hovering and not delete_confirm:
                        return world

                shown += 1

            # New world
            new_rect = pygame.Rect(ind[0] + (w + dist) * shown, ind[1], w, h)
            if new_rect.collidepoint(mousePos):
                new_rect = pygame.Rect(new_rect.x - 10, new_rect.y - 10,
                                    new_rect.w + 20, new_rect.h + 20)

            pygame.draw.rect(screen, GREEN, new_rect)
            display_text(["New world", "Nieuwe wereld"][taal],
                        (new_rect.x + 15, new_rect.y + 15))

            if mouse_down and new_rect.collidepoint(mousePos) and not delete_confirm:
                name = enter_text(["World name:", "Wereldnaam:"][taal])
                if name:
                    os.makedirs(os.path.join(world_dir, name), exist_ok=True)
                    return name

            # Back button
            if draw_button(back_button, ["Back","Terug"][taal], WHITE, BLACK).collidepoint(mousePos) and mouse_down:
                return (0,0)

            if delete_confirm:
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((0,0,0,150))
                screen.blit(overlay, (0,0))

                rect = pygame.Rect(WIDTH//2 - 250, HEIGHT//2 - 80, 500, 160)
                pygame.draw.rect(screen, WHITE, rect)

                display_text(
                    [f"Delete world '{delete_confirm}'?", f"Verwijder wereld '{delete_confirm}'?"][taal],
                    (WIDTH//2, HEIGHT//2 - 20), color=BLACK, orientation='center'
                )

                yes = pygame.Rect(WIDTH//2 - 140, HEIGHT//2 + 20, 120, 50)
                no  = pygame.Rect(WIDTH//2 + 20,  HEIGHT//2 + 20, 120, 50)

                draw_button(yes, ["Yes","Ja"][taal], GREEN, WHITE)
                draw_button(no, ["No","Nee"][taal], RED, WHITE)

                for ev in events:
                    if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                        m = pygame.mouse.get_pos()
                        if yes.collidepoint(m):
                            shutil.rmtree(os.path.join(world_dir, delete_confirm))
                            worlds.remove(delete_confirm)
                            delete_confirm = None
                        if no.collidepoint(m): delete_confirm = None

                pygame.display.flip()
                clock.tick(FPS)
                continue

            pygame.display.flip()
            clock.tick(60)

    def fade_out(spd : int = 5):
        global npc_text
        npc_text = ""
        fade_surface = pygame.Surface((WIDTH, HEIGHT))
        fade_surface.fill(BLACK)
        for alpha in range(0, 255, spd):
            fade_surface.set_alpha(alpha)
            screen.blit(fade_surface, (0, 0))
            pygame.display.flip()
            pygame.time.delay(30)
        global should_draw_frame
        should_draw_frame = False

    def get_buttons(ikey,mleft,get_esc=False):
        esc_pressed = False
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mleft = True
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    mleft = False
            if event.type == pygame.KEYDOWN:
                if event.key == controls[4] and not pause_menu_open:
                    ikey = True
            if event.type == pygame.KEYUP:
                if event.key == controls[4]:
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

    def choose_server():
        def update_server_status(server):
            try:
                status = query_server_status(server['ip'], server['port'])
                server['online'] = status['online']
                if status['online']:
                    server['playercount'] = status['player_count']
                    server['maxplayers'] = status['max_players']
            except Exception as e:
                server['online'] = False
                print(e)
            finally:
                server['querying'] = False
        
        servers = [
            {'name':'NPS 1','ip':"business-things.gl.at.ply.gg",'port':39153,'showoffline':True},
            {'name':'NPS 2','ip':"las-colleagues.gl.at.ply.gg",'port':5367,'showoffline':True},
        ]
        default_info = {'online':False,'playercount':0,'maxplayers':0,'querying':False,'last_query':0}
        for i in range(len(servers)):
            servers[i] = {**servers[i],**default_info}

        ip = ''
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
        except:
            ip = "127.0.0.1"
        
        font = pygame.font.Font(None, 74)
        header_font = pygame.font.Font(None, 100)

        answer = ""

        w,h,dist = 300,100,50
        ind = [50,HEIGHT//2-50]

        mouse_down = False
        interact_key_down = False

        current_frame = 0
        playing_flappy = False
        flappy_score = 0
        flappy_printing_score = False
        flappy_y = 0
        flappy_yvel = 0
        flappy_key_pressed = False
        flappy_pipes = []
        flappy_pipe_cooldown = 0
        flappy_top_pos = (0,0.8*HEIGHT-50)

        rval = None

        back_button = pygame.Rect(WIDTH - 100, HEIGHT - 50, 90, 40)
        while True:
            current_frame += 1

            screen.fill(BROWN)
            global mousePos
            mousePos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        mouse_down = True
                if event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        mouse_down = False
                if event.type == pygame.KEYDOWN:
                    if event.key == controls[4] and not pause_menu_open:
                        interact_key_down = True
                if event.type == pygame.KEYUP:
                    if event.key == controls[4]:
                        interact_key_down = False
            
            shown = 0            
            for i, server in enumerate(servers):
                interactrect = pygame.Rect(ind[0]+(w+dist)*shown,ind[1],w,h)
                interacting = interactrect.collidepoint(mousePos[0],mousePos[1])
                if interacting: interactrect = pygame.Rect(ind[0]+(w+dist)*shown-10,ind[1]-10,w+20,h+20)
                if not server['querying'] and time.time() - server['last_query'] > 5:
                    server['querying'] = True
                    server['last_query'] = time.time()
                    threading.Thread(target=update_server_status, args=(server,), daemon=True).start()
                if servers[i]['online'] or 'showoffline' in servers[i]:
                    pygame.draw.rect(screen,WHITE if servers[i]['online'] and servers[i]['playercount'] < servers[i]['maxplayers'] else GREY,interactrect)
                    display_text(server['name'],(interactrect[0]+10,interactrect[1]+10))

                    if servers[i]['online']:
                        if servers[i]['playercount'] < servers[i]['maxplayers']:
                            display_text(f"ONLINE - {servers[i]['playercount']}/{servers[i]['maxplayers']}",(interactrect[0]+10,interactrect[1]+50),color=GREEN)
                            if mouse_down and interacting: rval = (server['ip'], server['port'])
                        else: display_text(f"{["FULL","VOL"][taal]} - {servers[i]['playercount']}/{servers[i]['maxplayers']}",(interactrect[0]+10,interactrect[1]+50),color=YELLOW)
                    else: display_text("OFFLINE",(interactrect[0]+10,interactrect[1]+50),color=RED)
                    shown += 1
            
            if draw_button(back_button,["Back","Terug"][taal],WHITE,BLACK).collidepoint(mousePos) and mouse_down:
                return (0,0)
            
            header_surface = header_font.render(["Select a server:","Kies een server:"][taal], True, BLACK)
            screen.blit(header_surface, (WIDTH // 2 - header_surface.get_width() // 2, HEIGHT // 4))

            info_font = pygame.font.Font(None, 50) 
            info_text = ["The 'Nederlandse Publieke Servers' are places where fans over the entire world can play together!","De 'Nederlandse Publieke Servers' zijn plekken waar fans van over de hele wereld samen kunnen spelen!"][taal]
            info_surface = info_font.render(info_text, True, BLACK)
            screen.blit(info_surface, (WIDTH // 2 - info_surface.get_width() // 2, HEIGHT - info_surface.get_height() - 100))

            text_surface = font.render(answer, True, BLACK)
            screen.blit(text_surface, (WIDTH // 2 - text_surface.get_width() // 2, HEIGHT // 2))

            if current_frame > 500 and not playing_flappy:
                interact_box_flap = pygame.Rect(WIDTH // 40, HEIGHT * (1.17 - 0.1 * min(100,current_frame-500) ** 0.2), 420, 50)
                pygame.draw.rect(screen,WHITE,interact_box_flap)
                display_text(f"Score: {flappy_score}" if flappy_printing_score else ["Play a game while you wait?","Een spel spelen terwijl je wacht?"][taal],(interact_box_flap[0]+15,interact_box_flap[1]+15))
                if flappy_printing_score: flappy_printing_score -= 1
                if mouse_down and interact_box_flap.collidepoint(mousePos[0],mousePos[1]):
                    playing_flappy = True
                    flappy_score = 0
                    flappy_y = HEIGHT // 10 * 9
                    flappy_yvel = 0
                    flappy_pipes = []
                    flappy_pipe_cooldown = 0
            if playing_flappy:
                stop_game = False
                active = not (flappy_y == HEIGHT // 10 * 9 and flappy_yvel == 0 and not flappy_pipes)
                flappy_rect = pygame.Rect(20,round(flappy_y),10,10)
                pygame.draw.rect(screen,YELLOW,flappy_rect)
                if interact_key_down:
                    if not flappy_key_pressed:
                        flappy_key_pressed = True
                        flappy_yvel = -2
                else: flappy_key_pressed = False
                if active:
                    flappy_y += flappy_yvel
                    if flappy_y <= flappy_top_pos[1] + 50:
                        flappy_y = flappy_top_pos[1] + 50
                        flappy_yvel = max(0.1,flappy_yvel)
                    flappy_yvel += 0.1
                if flappy_y + 10 > HEIGHT: stop_game = True
                if flappy_pipes:
                    flappy_top_surf = pygame.Surface((WIDTH,50),flags=pygame.SRCALPHA)
                    pygame.draw.rect(flappy_top_surf,(50,50,50,max(0,min(75,75-(flappy_y-flappy_top_pos[1]-50)*3))),(0,0,WIDTH,50))
                    screen.blit(flappy_top_surf,flappy_top_pos)

                    pipe_width = 20
                    deleted_pipes = []
                    for i, pipe in enumerate(flappy_pipes):
                        pipe[0] -= 1
                        pipepart1 = pygame.Rect(pipe[0], 0.8 * HEIGHT, pipe_width, pipe[1] / 500 * HEIGHT)
                        pipepart2 = pygame.Rect((pipe[0], 0.8 * HEIGHT + (pipe[1] + 20) / 500 * HEIGHT, pipe_width, (100 - pipe[1]) / 500 * HEIGHT))
                        pygame.draw.rect(screen,GREEN,pipepart1)
                        pygame.draw.rect(screen,GREEN,pipepart2)
                        if pipepart1.colliderect(flappy_rect) or pipepart2.colliderect(flappy_rect): stop_game = True
                        if pipe[0] < 0:
                            deleted_pipes.append(i)
                            flappy_score += 1
                    if deleted_pipes:
                        for index in deleted_pipes: flappy_pipes.pop(index)
                flappy_pipe_cooldown -= 1
                if flappy_pipe_cooldown < 0 and active:
                    flappy_pipe_cooldown = 110
                    flappy_pipes.append([300,random.randint(10,70)]) 
                if stop_game:
                    playing_flappy = False
                    flappy_printing_score = 200
                    print(f"Score: {flappy_score}")


            pygame.display.flip()
            if rval: return rval
            clock.tick(60)

    def connect_to_server(server_ip="127.0.0.1", server_port=5555):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((server_ip, server_port))
        client.sendall(b"JOIN")
        new_data = recv_pickle(client)
        init_data = dict()
        for key, item in new_data.items():
            init_data[key] = item
        if not init_data:
            raise ConnectionError("No data received from server.")
        return client, init_data
    
    def query_server_status(server_ip="127.0.0.1", server_port=5555):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((server_ip, server_port))
            s.sendall(b"STATUS")
            data = s.recv(2048)
            s.close()
            return pickle.loads(data)
        except Exception as e:
            return {'online': False, 'error': str(e)}
    
    def send_pickle(sock, obj):
        data = pickle.dumps(obj)
        length = struct.pack("!I", len(data))
        sock.sendall(length + data)

    def recv_all(sock, length):
        data = b''
        while len(data) < length:
            packet = sock.recv(min(4096, length - len(data)))
            if not packet:
                raise EOFError("The server does not like you, please try to befriend it first")
            data += packet
        return data

    def recv_pickle(sock):
        length_bytes = recv_all(sock, 4)
        length = struct.unpack("!I", length_bytes)[0]
        data = recv_all(sock, length)
        return pickle.loads(data)
    
    def network_thread():
        global server_data, accumulated_money, treechanges, rockchanges, events, island
        while True:
            try:
                data_to_send = {'position':player_pos,'area':current_area,'events':[]}
                if accumulated_money:
                    data_to_send['money_change'] = accumulated_money
                    accumulated_money = 0
                if events:
                    data_to_send['events'] = [e for e in events]
                    events = []
                if treechanges:
                    data_to_send['trees'] = [t for t in treechanges]
                    treechanges = []
                if current_area in {13,14,15}:
                    data_to_send['area'] = (current_area,island.pos[0],island.pos[1])
                if rockchanges:
                    data_to_send['rocks'] = rockchanges
                    rockchanges = []
                global changed_sdata
                if changed_sdata:
                    data_to_send['change'] = changed_sdata
                    changed_sdata = dict()
                send_pickle(client_socket, data_to_send)
                new_server_data = recv_pickle(client_socket)

                for key, item in new_server_data.items():
                    server_data[key] = item
                if 'border' in new_server_data.keys():
                    global border_open
                    border_open = new_server_data['border']
                if 'trees' in server_data and False:
                    trees = server_data['trees']
                    for i in trees.keys():
                        trees[i] = (trees[i][0]*tree_size,trees[i][1]*tree_size)
                if 'rocks' in server_data.keys():
                    for change in server_data['rocks']:
                        island.areainfo[change[0][1]][change[0][0]][change[1][0]][change[1][1]] = change[2]
                    del server_data['rocks']
            except Exception as e:
                print(e)
                server_data = {}
            time.sleep(0.1)

    global settings
    if os.path.isfile(os.path.join(JSON_PATH,"settings.json")): 
        with open(os.path.join(JSON_PATH, "settings.json"), 'r', encoding='utf-8') as json_file:
            settings = json.load(json_file)
    else: settings = dict()
    
    global taal, music_volume, controls
    if settings:
        taal = settings['language']
        music_volume = settings['mvolume'] if 'mvolume' in settings else 100
        controls = settings['controls'] if 'controls' in settings else [
            pygame.K_w,
            pygame.K_s,
            pygame.K_d,
            pygame.K_a,
            pygame.K_e,
            pygame.K_j,
            pygame.K_c,
        ]
        pygame.mixer.music.set_volume(music_volume/100)
    else:
        taal = None
        controls = [
            pygame.K_w,
            pygame.K_s,
            pygame.K_d,
            pygame.K_a,
            pygame.K_e,
            pygame.K_j,
            pygame.K_c,
        ]
        while type(taal) != int:
            taal = enter_text("Fill in your preferred language: (English/Nederlands)") if WIDTH >= 1920 else enter_text("English/Nederlands")
            if taal.upper() == 'ENGLISH': taal = 0
            elif taal.upper() == 'NEDERLANDS': taal = 1
        try:
            with open(os.path.join(JSON_PATH, "settings.json"), "w") as json_file:
                json.dump({"language":taal,"mvolume":music_volume,"controls":controls}, json_file, indent=4)
        except IOError as e:
            print(f"Error writing to file: {e}")
    
    VARETORAH = [
        ["To know that there is a God","Serve only Him","Recognizing His oneness","Love Him","Fear Him","Sanctify His name","Follow His ways","Hold on to Him","To swear by His name as permitted","Studying the VARETORAH","Teaching VARETORAH","Consider the words of the VARETORAH","Writing a Sefer VARETORAH","Wearing tefillin on the arm","Wearing tefillin on the head","Placing a mezuzah","Wearing tzitzit","Pray to God","The priests must bless the people","Using ritual immersion","Keeping Shabbat holy","Resting on Shabbat","Removing chametz before Passover","Eating matzah on Passover","Blowing a shofar on Rosh Hashanah","Counting the Omer","Humble your soul on Yom Kippur","Do not work on public holidays","Celebrating holidays with sacrifices","Living in a sukkah","Take the four types","On the first day of Passover a holy assembly","On the seventh day of Passover a holy convocation","On Shavuot holy convocation","On Rosh Hashana holy convocation","On Yom Kippur holy convocation","On the first day of Sukkot holy assembly","On Shemini Atzeret holy assembly","Bringing the Passover sacrifice","Bringing a Passover Sheni offering if necessary","Eating the Passover offering according to rules","Bringing firstfruits","Giving the priests the teruma","Giving the ma'aser rishon","The ma'aser sheni eat in Jerusalem","Giving the ma'aser ani","Bringing Bikkurim","To rest the harvest of the land in the Sabbath year","Proclaim the year of jubilee","Freeing slavery in the 7th year","Apply the Jubilee rules","Treating non-Jewish slaves correctly","Build altars as directed","Building a temple","Maintain a fire on the altar","Remove ash","Taking ashes outside the camp","Light the menorah","Place showbread","Offering incense","Anoint the kohein gadol","Wearing sacred clothing","Let the priests do their service","Making the priests eat holy gifts","Bringing the daily tamid offering (morning,","Bringing the daily tamid offering (afternoon,","Making Musaf sacrifices on Shabbat","Musaf sacrifices on Rosh Chodesh","Musaf sacrifices on Passover","Musaf sacrifices on Shavuot","Musaf sacrifices on Rosh Hashana","Musaf sacrifices on Yom Kippur","Musaf sacrifice on Sukkot","Musaf sacrifice on Shemini Atzeret","Performing the Yom Kippur service of the kohein gadol","Carry out offering procedures according to rules","Offering sin offerings when required","Making guilt offerings when required","Offering peace offerings","Bring peace offerings","Dispose of bird victims correctly","Making grain offerings correctly","Offering libations correctly","Offering firstborn animals as a sacrifice","Eating holy things according to rules","Eat the second tithe in Jerusalem","Keep the perpetual lamp burning","Follow cleaning procedures","Cleanse unclean persons by water","Performing red cow ritual","Save red cow ashes","Conducting research on tsara'at","Isolate the with tsara'at","Bringing purification offerings at tsara'at","Cleansing of houses with tsara'at","Cleansing of clothes with tsara'at","Maintaining a mikveh","Learn and apply cleanliness laws","Apply niddah cleansing","Zav cleaning","Zava cleaning","Cleaning after birth","The rule of sprinkling on days 3 and 7","Separate unclean persons from the sanctuary","To handle sacred matters in purity","Kohanim must maintain purity","Perform a circumcision","Eating sacred food in the right place","Saying a priestly blessing","Assigning kohanim to temple service","Let Kohanim blow trumpets","Teaching Purity Laws","Clean objects","Carry out slaughter according to halacha","Slaughtering animals by schechita","Not killing animals in gruesome ways (positive technique of schechita,","Remove hidden grease properly","Drain blood","Carrying out commandments of Nazir","Keeping vows","Keeping Eden","To give the land rest during the Sabbath year","Permissible use of fruits of the Shabbat year","Return Jubilee land","Settling houses in walled cities","Redeeming sacred things according to rules","Giving priestly taxes","Allowing the poor to share in the harvest: pe'ah","Letting arms share: leket","Letting arms share: shichecha","Letting arms share: peret and olelot","Loan to the poor","Supporting the poor","Avoiding hostage taking—returning property by day","Returning widow's property","Loving the stranger","Loving one's neighbor","Honoring parents","Parents fear","Respecting the wise","Respecting the old","Honoring the priest","Helping pack animals","Returning lost property","Bird's Nest—send mother away","Install a fence on the roof","Saving people in danger","Encouraging the people in war","Remember Amalek","Fight against Amalek","Appoint the king","To honor the king","Have the king write a VARETORAH scroll","Establishing justice","Appoint judges","Calling witnesses","Conducting legal cases according to halacha","Kill by Beit Din when required","Apply flogging when required","Exile to cities of refuge","Establishing refuge cities","Securing borders","Compensation for damage","Compensation for physical damage","Compensation for theft","Compensation for defamation","To force a seducer to marry or pay","Force the rapist to marry (if the victim wants it,","Penance for slander","Bury people","Apply mourning laws","Do not desecrate kohen gadol","Do not desecrate Kohein by corpse unless family","Burn unclean meat","Avoiding dangerous things","Treat weeds in vineyard according to rules","Applying Vows of Inheritance","Enter into marriage","Provide divorce document","Performing Levirate Marriage","Perform chalitza","Follow Sota procedure","Treating guilty unfaithful wife","Making the menstruating woman clean","Cleansing the unclean woman","Treating a priest's widow according to the rules","Treating the married fornicator according to halacha","Carrying out trial of unsolved murder (egla arufa,","Regulating vengeance of blood avenger","Treating home theft","Buried convicts before sunset","Supporting impoverished people","Ransom hostage","Follow Musser procedures","Compensate for animal damage","Compensate for fire damage","Property of a foreigner in light protection status","Honor priest's property","Avoiding rules regarding bribery (positive: fair justice,","To regard unclean animals as unclean","Unclean fish as unclean","Unclean birds as unclean","Classify locusts as clean or unclean","Sacrifice animals by correct methods","Removing Korban chelev during sacrifice","Sacrifice sharing right food","Mitzvah to offer sacrifices for transgressions","Sacrifice for involuntary sin","Sacrifice for sin of will","Pay estimated fines","Eating holy things at the right time","Eating holy things in the right place","Do not sacrifice animals before the 8th day (positive: wait,","Do not sacrifice an animal with a defect (positive: suitable molars,","Eating sacrifice in purity","Offer food in time","Caution about temple rules","Remove ashes from altar","Cleansing by priests","Giving gifts to the kohen","Give the Levite the tithe","Levite must give tithe of tithe","Sprinkling cleaning","Beit Din must take strict action on idiot duty","Priests must oversee sanctuary","Determining the price of sacred things","Receiving a priestly harvest","Giving the first clipping of sheep to the priest","Blessing the people through priests","Education of law and ritual","Applying laws of war","Marrying a prisoner's wife according to the rules","Treat mother of loot according to rules","Prevent rebellion against judge (positive: obey,","Observe king's rules","Observing rules about priests","Consult the elderly","Cut down idol tree","Cleansing the land from idolatry","Punish criminals","Dealing with unresolved debt","Returning lost inheritance","Obey prophet","Testing true prophet","Vow to make voluntary sacrifices","Leaving work at sundown on Yom Kippur","Stopping work on public holidays","Holding holy meetings","Not recognizing other gods","Do not make idols","Don't worship idols","Do not make sacrifices to idols","No smoke offerings to idols","No libations to idols","No bowing to idols","Do not create idolatry objects","Do not show idolatry","Do not possess idols","No temptation to idolatry","Do not deceive a congregation into idolatry","Do not practice occultism","No fortune telling","No magicians","Do not consult mediums","Do not consult spirit charmers","Do not curse in the name of idols","Do not make graves for idols","Do not decorate idols","No ring or ornament for idols","No misplaced honor to idols","Do not eat sacrifices made to idols","Not profiting from idol objects","Don't act like you're an idol","Do not profane the Name of God","Do not swear falsely by His name","Do not destroy the name of God","Do not destroy sacred objects","Do not make sacrifices outside the Temple","Let no unclean person enter the sanctuary","Kohen may not enter the sanctuary in uncleanness","Kohen may not eat unclean offerings","Ordinary Israelite are not allowed to eat kohanim food items","No inappropriate consumption of holy things","Not eating improper offerings","Do not eat sacred things outside of location","Do not eat holy things out of season","Do not eat inappropriate priestly offerings","Do not sacrifice an animal with a defect","Do not cause deficiency in sacrificial animals","Do not offer any sacrifice that has been killed outside the temple","Do not eat offerings that have become unclean","Do not eat sacrifices that have been improperly slaughtered","Do not touch unclean meat (negative part,","Don't eat blood","No Chelev food","Do not cook meat with milk","Do not eat meat with milk","Don't benefit from meat with milk","Do not leave carcass remains behind","No sacrificial food on 3rd day","Do not eat chametz on Passover","Do not keep chametz on Passover","No mixing of chametz in property on Passover","Do not eat a new crop before Omer","Do not roast a new crop before Omer","Do not eat a new crop of grains before Omer","Do not remove a leprosy building before kohen has declared it","No tanda'ah (negative part of cleanliness,","Do not skip a ceremony when cleansing","Do not spoil holy oil","Do not make incense such as sacred incense","No strange fire in Tabernacle","No profane work on Shabbat","Do not desecrate Shabbat","No work on the 1st day of Passover","No work on the 7th day of Passover","No work on Shavuot","No work on Rosh Hashana","No work on Yom Kippur","No work on the 1st day of Sukkot","No work on Shemini Atzeret","No food on Yom Kippur","Do not eat chametz mixed with sacrifice","No sacrifice of payment through prostitution","No sacrifice of money by dog","Don't eat insects","Don't eat reptiles","Don't eat rotten food","Do not eat an organ from a living animal","Do not eat animals that have died inappropriately","Do not eat animals that have been torn to pieces","Do not eat parts forbidden to priestly sex","No drinking of wine by priest during service","Do not serve a priest in want","Do not serve a priest with temporary infirmity","Ordinary Israelite may not perform priestly duties","No stranger may eat priestly food","No uncircumcised person may eat Passover","No non-Jewish slave eating Passover","Do not eat an unclean Passover offering","Do not break a bone of the Passover sacrifice","Do not bring Passover meat outside the home","No chametz together with Passover sacrifice","Do not leave any leftover Passover offering","Don't forget what Amalek did","Don't take revenge","Don't harbor hatred","Don't gossip","No slander","Don't ignore danger","No jealousy","No desire","No theft","No kidnapping","No fraud","No weight cheating","Do not charge interest from Jews","No pressure on debtor","No withholding of wages","No swearing about the deaf","Do not deceive the blind","No injustice in justice","No partiality","Don't accept bribes","No distortion of the rights of strangers or orphans","No condemning the innocent","Do not acquit the guilty","No more than 39 strokes","No hindrance during execution","No organs from executed leftovers","No dead hang around longer than day","Do not cross-pollinate animals","Do not plant mixed fields","Do not mix wool and linen clothing (shaatnez,","Don't take revenge with words","Don't take revenge with actions","Avoiding Fake Harvest in Vineyard","Do not plant fields together","No woman wear men's clothes","No man wear women's clothes","Do not take a bird mother without sending her away (negative part,","Do not let an animal plow with cattle and donkey at the same time","No blocking of pack animals","No interference with working animals","No abuse of those in need","No pagan mourning practices","No bald spot on the head during mourning","No cuts in body","No tattoo","No prostitution of a daughter","Do not commit atrocities","No incest with mother","No incest with father's wife","No incest with sister","No incest with half sister","No incest with granddaughter","No incest with aunt","No incest with paternal aunt","No incest with aunt on mother's side","No incest with paternal uncle's wife","No incest with wife of uncle's mother's side","No incest with mother-in-law","No incest with son's wife","No incest with grandchild's wife","No incest with sister-in-law (except yibboom,","No incest with aunt through marriage","No sexual intercourse with a menstruating woman","No adultery with a married woman","No male homosexual contact","No bestiality by man","No bestiality by woman","No incest with stepdaughter","No incest with daughter-in-law","No intercourse with forbidden women","No intercourse with niece through forbidden line","No incest with woman's sister during her lifetime","No intercourse with animals","No intercourse with male prostitution","No intercourse with a prostitute","No intercourse outside of marriage according to halacha","No rape","No seduction of minors","No intercourse with priest's daughter who has been desecrated","No intercourse with desecrating persons","No intercourse with owned animals","Do not unjustly prevent divorce","No hypocritical but misleading commitments","Not an unfair purchase","Don't avoid debt","No abuse of land distribution","No bribery in the judiciary","No false testimony","No slander against relatives","No murder","No suicide","No revenge killings","No guilty blood shed","No insult to judge","No rebellion against Sanhedrin","No rebellion against prophet","Not a bad prophecy","Don't listen to false prophets","Do not arouse disgust against prophet","No fear of passing on prophecy","No hateful war","No destruction of fruit trees during war","No fleeing from enemy in panic","No wasting of sacred resources","No running away from pack animals aid","No mixing of sacred and profane labor","Do not mutilate animal sacrifices","Do not sacrifice temporarily defective animals","Do not sacrifice an animal that is too young","Do not slaughter an animal and young on the same day","Don't eat blood","Don't drink blood","Do not eat sacred offerings outside of time","Do not enter an unclean temple","Do not receive unwanted foreign offerings as gifts","Don't break a vow","Don't break oaths","No deception in vows","No slaves escape","No alcohol abuse by priests","No rude behavior towards parents","No bad treatment of foreigners","No ill-treating widow","No mistreating orphans","No withholding of poor people's rights","No ignoring nudity of those in need","No abuse of debtor","No withholding of tools necessary for living","No cheating in trade","No wrong weights","No wrong sizes","No kidnapping","No withholding of other people's property","No theft due to burglary","No theft of sacred property","No witchcraft","No fortune telling","No magical predictions","No drawing magic","No spirit exorcism","No necromancy","Do not move boundary stones","Don't steal animals","No theft of goods","No deception in agriculture","No deception in business","No cruelty to animals","Don't let animals suffer","Do not take a bird mother without sending her away (negative part,","No misuse of goods","Don't seek money through deception","Do not tolerate questionable practices","No incest between husband and in-laws","No adultery","No incest by man with mother","No incest by man with sister","No incest by man with aunt","No incest by man with daughter","No incest by man with granddaughter","No incest by man with mother-in-law","No incest by man with stepdaughter","No incest by man with brother's wife (except levirate,","No incest by man with paternal aunt","No incest by man with maternal aunt","No incest by man with half sister","No incest by man with wife of paternal uncle","No incest by man with wife of maternal uncle","No incest by man with daughter-in-law","No incest by man with son's wife","No incest by man with grandson's wife","No incest by man with cousins, nieces, in-laws","No ritual fornication at temple","Let no unclean person enter the sanctuary","No kohen gadol with widow","No priest with a divorced wife","No priest with a fornicating wife","No priest with a profane wife","No kohen gadol with widow","No kohen in mourning unjustly","Do not eat unclean holy food","No gifts from kohanim eat unjustly","Do not use first fruit incorrectly","Do not eat sacrifices after time","Do not eat offerings that are unclean","Do not eat sacrifices that are slaughtered incorrectly","No off-site food offerings","No sacrificing yearling animals outside the rules","Do not sacrifice animals with defects","Do not buy animals for sacrifices with defects","Do not designate an animal as a sacrifice that is unsuitable","Do not exchange an animal that is sacred for profane","Do not desecrate an animal that is sacred","Do not damage sacred objects","Don't pollute a shrine","Do not extinguish fire on altar","Don't just put fire on an altar","No sacrificial food that has been bought out","No sacrificial food outside the sanctuary","No spoilage of holy oil","Don't burn any strange fire","Do not remove gold or silver from sanctuary","Do not sacrifice any animal that had intercourse with humans","Do not sacrifice an animal with a defect","Do not sacrifice any animal that was refused","Do not sacrifice an injured animal","Do not sacrifice an animal that has a bone deficiency","Do not sacrifice an animal born with defect","Do not sacrifice an animal that is blind","Do not sacrifice an animal with mange","Do not sacrifice an animal with crust","Do not sacrifice an animal that has an absent limb","Do not sacrifice an animal with a broken limb","Do not sacrifice an animal that has been crushed","Do not sacrifice an animal with its genitals cut","No pressed animal sacrifice","Do not sacrifice any carved animal","Do not sacrifice mixed animals","Do not sacrifice an animal for birth","Don't change a sacrifice","No exchanging money for shrine inappropriate","Do not sell the first born animal","Do not use a first born animal","Don't ruin a firstborn","No substitutions for sacrifices","Don't sell offerings","No sacrificial consuming profane","Consume no part of sacrifice inappropriately","Do not drop any parts of the offering","Do not burn parts of an offering unjustly","No fat disappear","Do not burn parts of the offering in the wrong place","Do not sacrifice inappropriate animals","Do not sacrifice animals purchased on the Sabbath","Do not offer unholy temple sacrifices","No extra work on Shabbat","Do not desecrate the Sabbath","Not to profane a day of sanctification","Do not desecrate a holy place","Do not desecrate sacred food","Do not spoil holy water","Do not violate red cow ritual","Do not mix ashes with unclean things","Don't skip a cleaning process","Do not allow priests to work in uncleanness","Do not give holy food to the unclean","Don't falsify rituals","Do not adopt profane customs","Do not imitate pagan practices","No body cuts","No tattoos","No mourning practices of pagans","No sayings from pagan practices","Do not use amulets as magic","Don't drink blood","Do not eat meat with milk","Do not eat fruit from the first three years (orla,","No use of uncircumcised tree","No withholding of poor people's rights","No oppressing the poor","Do not oppress a stranger","Do not oppress a widow","Do not oppress an orphan","No curse on judge","No curse on leader","No curse on God","No disrespect to sanctuary","No disrespect to VARETORAH teacher","No deviation from commandments","No addition or subtraction of commandments"],
        ["Te weten dat er een God bestaat","Alleen Hem dienen","Zijn eenheid erkennen","Hem liefhebben","Hem vrezen","Zijn naam heiligen","Zijn wegen volgen","Aan Hem vasthouden","Bij Zijn naam zweren zoals toegestaan","De VARETORAH bestuderen","VARETORAH onderwijzen","De woorden van de VARETORAH overwegen","Een Sefer VARETORAH schrijven","Tefillin op de arm dragen","Tefillin op het hoofd dragen","Mezoeza plaatsen","Tzitzit dragen","Tot God bidden","De priesters moeten het volk zegenen","Rituele onderdompeling gebruiken","Sjabbat heiligen","Op Sjabbat rusten","Chametz verwijderen vóór Pesach","Matzah eten op Pesach","Shofar blazen op Rosj Hasjana","De Omer tellen","Je ziel verootmoedigen op Jom Kippoer","Op feestdagen niet werken","Feestdagen vieren met offers","In een soeka wonen","De vier soorten nemen","Op de eerste dag Pesach een heilige samenkomst","Op de zevende dag Pesach een heilige samenkomst","Op Shavuot heilige samenkomst","Op Rosh Hashana heilige samenkomst","Op Yom Kippur heilige samenkomst","Op de eerste dag Sukkot heilige samenkomst","Op Shemini Atzeret heilige samenkomst","Het Pesach-offer brengen","Pesach-sjéni-offer brengen indien nodig","Pesach-offer eten volgens regels","Eerstelingen brengen","De priesters de teruma geven","De ma’aser rishon geven","De ma’aser sjeni eten in Jeruzalem","De ma’aser ani geven","Bikkurim brengen","De oogst van het land doen rusten in het sjabbatjaar","Het jubeljaar verkondigen","Slavernij in het 7e jaar vrijlaten","De jubeljaarregels toepassen","Niet-Joodse slaven correct behandelen","Altaren opbouwen zoals voorgeschreven","Tempel bouwen","Vuur op het altaar onderhouden","As verwijderen","As buiten het kamp brengen","De menorah aansteken","Toonbrood plaatsen","Wierook offeren","De kohein gadol zalven","Heilige kleding dragen","De priesters hun dienst laten doen","De priesters heilige gaven laten eten","Het dagelijkse tamid-offer brengen (ochtend,","Het dagelijkse tamid-offer brengen (middag,","Musaf-offers brengen op sjabbat","Musaf-offers op Rosh Chodesh","Musaf-offers op Pesach","Musaf-offers op Shavuot","Musaf-offers op Rosh Hashana","Musaf-offers op Yom Kippur","Musaf-offer op Sukkot","Musaf-offer op Shemini Atzeret","De Yom Kippur dienst van de kohein gadol uitvoeren","Offerprocedures volgens regels uitvoeren","Zondeoffers brengen wanneer verplicht","Schuldoffers brengen wanneer verplicht","Vredeoffers brengen","Dankoffers brengen","Vogelslachtoffers correct brengen","Graanoffers correct brengen","Plengoffers correct brengen","Eerstgeboren dieren als offer brengen","Heilige dingen volgens regels eten","Tweede tiende in Jeruzalem eten","Eeuwigdurende lamp brandend houden","Reinigingsprocedures volgen","Onreine personen reinigen door water","Rode koe ritueel verrichten","As van rode koe bewaren","Onderzoek op tsara’at uitvoeren","De met tsara’at isoleren","Reinigingsoffers bij tsara’at brengen","Reiniging van huizen met tsara’at","Reiniging van kleding met tsara’at","Een mikve in stand houden","Reinheidswetten leren en toepassen","Niddah reiniging toepassen","Zav reiniging","Zava reiniging","Reiniging na geboorte","De regel van sprinkeling op dag 3 en 7","Onreine personen scheiden van het heiligdom","Heilige zaken in reinheid behandelen","Kohanim moeten reinheid onderhouden","Een besnijdenis uitvoeren","Heilig voedsel op de juiste plek eten","Priesterlijke zegen uitspreken","Kohanim in tempeldienst indelen","Kohanim trompetten laten blazen","Onderwijzen van reinheidswetten","Voorwerpen reinigen","Slachting volgens halacha uitvoeren","Dieren door schechita slachten","Dieren niet op gruwelijke manieren doden (positieve techniek van schechita,","Verborgen vet op de juiste manier verwijderen","Bloed afvoeren","Geboden van nazir uitvoeren","Geloften nakomen","Eden nakomen","Het land rust geven in sjabbatjaar","Vruchten van sjabbatjaar toegestaan gebruiken","Jubilee-land teruggeven","Verrekenen van huizen in ommuurde steden","Geheiligde dingen inwisselen volgens regels","Priesterlijke belasting geven","Armen laten delen in oogst: pe\'ah","Armen laten delen: leket","Armen laten delen: shichecha","Armen laten delen: peret en olelot","Uitlening aan de arme","De arme ondersteunen","Gijzelneming vermijden—teruggeven van pand bij dag","Pand van weduwe teruggeven","De vreemdeling liefhebben","De naaste liefhebben","Ouders eren","Ouders vrezen","De wijze eerbiedigen","De oude eerbiedigen","De priester eren","Lastdier helpen","Teruggeven van gevonden voorwerpen","Vogelnest—moeder wegsturen","Hek op dak aanbrengen","Mensen redden die in gevaar zijn","Het volk aanmoedigen in oorlog","Amalek herinneren","Tegen Amalek strijden","De koning aanstellen","De koning eer bewijzen","De koning een VARETORAHrol laten schrijven","Rechtspraak instellen","Rechters aanstellen","Getuigen oproepen","Rechtszaken volgens halacha voeren","Doden door Beit Din wanneer verplicht","Geseling toepassen wanneer verplicht","Verbanning naar vluchtsteden","Vluchtsteden inrichten","Grenzen veiligstellen","Vergoeding voor schade","Vergoeding voor lichamelijke schade","Vergoeding voor diefstal","Vergoeding voor smaad","Een verleider verplichten te trouwen of te betalen","De verkrachter verplichten te trouwen (indien het slachtoffer dat wil,","Boetedoening bij laster","Mensen begraven","Rouwwetten toepassen","Kohen gadol niet ontheiligen","Kohein niet door lijk ontheiligen tenzij familie","Onrein vlees verbranden","Gevaarlijke dingen vermijden","Onkruid in wijngaard volgens regels behandelen","Geloften van erfenissen toepassen","Huwelijk sluiten","Scheidingsdocument geven","Leviraatshuwelijk uitvoeren","Chalitza uitvoeren","Sota-procedure volgen","Schuldige ontrouwe vrouw behandelen","De menstruerende vrouw rein maken","De onreine vrouw reinigen","De weduwe van priester volgens regels behandelen","De getrouwde ontuchtige vrouw behandelen volgens halacha","Proces van onopgeloste moord uitvoeren (egla arufa,","Wraak van bloedwreker reguleren","Diefstal in huizen behandelen","Veroordeelden begraven vóór zonsondergang","Verpauperde mensen ondersteunen","Gijzelaar loskopen","Musser-procedures volgen","Dierlijke schade compenseren","Schade door vuur compenseren","Bezittingen van vreemdeling in licht beschermingsstatus","Eigendom van priester naleven","Regels bij omkoping vermijden (positief: eerlijk rechtspreken,","Onreine dieren als onrein in acht nemen","Onreine vissen als onrein","Onreine vogels als onrein","Sprinkhanen als rein of onrein classificeren","Dieren door correcte methodes offeren","Korban chelev verwijderen bij offer","Offer delen correct eten","Mitswa om offers te brengen bij overtredingen","Offer voor onvrijwillige zonde","Offer voor willenszonde","Geraamde boetes betalen","Heilige zaken op juiste tijd eten","Heilige zaken op juiste plaats eten","Dieren niet offeren voor 8e dag (positief: wachten,","Dier met gebrek niet offeren (positief: geschikte kiezen,","Offer in reinheid eten","Offer in tijd eten","Voorzichtigheid bij tempelregels","As van altaar verwijderen","Reiniging door priesters","Gaven aan de kohen geven","De Leviet de tiende geven","Leviet moet tiende van tiende geven","Reiniging door sprinkeling","Beit Din moet streng bij idiool-dienst optreden","Priesters moeten toezicht houden op heiligdom","Prijs van heilige dingen bepalen","Priesterlijke oogst ontvangen","Eerste knippen van schapen aan priester geven","Het volk zegenen door priesters","Onderwijs van recht en ritueel","Wetten van oorlog toepassen","Gevangene-vrouw volgens regels huwen","Moeder van buit volgens regels behandelen","Rebellie tegen rechter voorkomen (positief: gehoorzamen,","Regels voor koning naleven","Regels over priesters naleven","Ouderen raadplegen","Afgodsboom omhakken","Het land reinigen van afgoderij","Misdadigers bestraffen","Onopgeloste schuld afhandelen","Verloren nalatenschap teruggeven","Profeet gehoorzamen","Ware profeet testen","Gelofte vrijwillige offers brengen","Ophouden met werk tegen zonsondergang op Yom Kippur","Werk stoppen op feestdagen","Heilige samenkomsten houden","Geen andere goden erkennen","Geen afgodsbeelden maken","Geen afgoden aanbidden","Geen offers voor afgoden brengen","Geen rookoffers aan afgoden","Geen plengoffers aan afgoden","Geen buigen voor afgoden","Geen afgoderij objecten maken","Geen afgodenliefde tonen","Geen afgoden in bezit houden","Geen verleiding tot afgoderij","Geen gemeente tot afgoderij misleiden","Geen occultisme beoefenen","Geen waarzeggerij","Geen tovenaars","Geen mediums raadplegen","Geen geestenbezweerders raadplegen","Niet vloeken in naam van afgoden","Geen graven voor afgoden maken","Geen afgodsbeelden versieren","Geen ring of ornament voor afgoden","Geen misplaatste eer aan afgoden","Niet eten van offers aan afgoden","Niet profiteren van afgodsobjecten","Niet doen alsof jij een afgod bent","De Naam van God niet profaneren","Niet bij Zijn naam vals zweren","Niet de naam van God vernietigen","Geen heilige objecten vernietigen","Geen offers buiten Tempel brengen","Geen onreine het heiligdom laten betreden","Kohen mag niet het heiligdom betreden in onreinheid","Kohen mag niet onrein eten van offers","Gewone Israëliet mag geen kohanim-eetstukken eten","Geen ongepaste consumptie van heilige dingen","Niet eten van ongepaste offers","Heilige dingen niet buiten locatie eten","Heilige dingen niet buiten tijd eten","Geen ongepaste priesterlijke gaven eten","Geen dier met gebrek offeren","Geen gebrek veroorzaken bij offerdieren","Geen offer dat buiten de tempel is gedood offeren","Geen offers eten die onrein geworden zijn","Geen offers eten die onjuist geslacht zijn","Geen onrein vlees aanraken (negatief deel,","Geen bloed eten","Geen chelev eten","Geen vlees met melk koken","Geen vlees met melk eten","Geen vlees met melk profiteren","Geen karbaansresten laten liggen","Geen offer eten op 3e dag","Geen chametz eten op Pesach","Geen chametz behouden op Pesach","Geen menging van chametz in eigendom op Pesach","Geen nieuwe oogst eten vóór Omer","Geen nieuwe oogst roosteren vóór Omer","Geen nieuwe oogst korrels eten vóór Omer","Geen lepragebouw verwijderen voordat kohen het verklaard heeft","Geen tanda’ah (negatief deel reinheid,","Geen ceremonie overslaan bij reiniging","Geen bederf van heilige olie maken","Geen wierook maken zoals heilige wierook","Geen vreemd vuur in Tabernakel","Geen profaan werk op Sjabbat","Sjabbat niet ontwijden","Geen werk op de 1e dag Pesach","Geen werk op de 7e dag Pesach","Geen werk op Shavuot","Geen werk op Rosh Hashana","Geen werk op Yom Kippur","Geen werk op 1e dag Sukkot","Geen werk op Shemini Atzeret","Geen eten op Yom Kippur","Niet eten van chametz gemengd met offer","Geen offer van betaling door prostitutie","Geen offer van geld door hond","Geen insecten eten","Geen reptielen eten","Geen verrotting eten","Geen orgaan van levend dier eten","Geen dieren eten die op ongepaste wijze gestorven zijn","Geen dieren eten die verscheurd zijn","Geen delen eten die verboden zijn aan priesterlijk geslacht","Geen wijn drinken door priester tijdens dienst","Priester niet met gebrek dienen","Priester niet met tijdelijk gebrek dienen","Gewone Israëliet mag geen priestertaak doen","Geen vreemdeling mag eten van priesterlijk voedsel","Geen onbesnedene mag Pesach eten","Geen niet-Joodse slaaf Pesach eten","Geen onreine Pesach-offer eten","Geen bot van Pesach-offer breken","Geen vlees van Pesach-offer buiten huis brengen","Geen chametz samen met Pesach-offer","Geen overgebleven Pesach-offer laten liggen","Niet vergeten wat Amalek deed","Geen wraak nemen","Niet haat koesteren","Niet roddelen","Geen laster","Geen gevaar negeren","Geen jaloezie","Geen begeerte","Geen diefstal","Geen ontvoering","Geen fraude","Geen gewichtsbedrog","Geen rente van Joden vragen","Geen druk op schuldenaar","Geen achterhouden van loon","Geen vloek over doven","Blinden niet misleiden","Geen onrecht in rechtspraak","Geen partijdigheid","Geen omkoperij aannemen","Geen verdraaien van recht van vreemdeling of wees","Geen onschuldig veroordelen","Geen schuldige vrijspreken","Niet meer dan 39 slagen","Geen hinder bij executie","Geen organen van geëxecuteerde overlaten","Geen dode hangen langer dan dag","Geen dieren kruisbestuiven","Geen mengvelden planten","Geen kleding van wol en linnen mengen (sjaatnez,","Geen wraak nemen met woorden","Geen wraak nemen met daden","Nepoogst in wijngaard vermijden","Geen velden samen planten","Geen vrouw dragen mannenkleding","Geen man dragen vrouwenkleding","Geen vogelmoeder nemen zonder wegsturen (negatief deel,","Geen dier met rund en ezel tegelijk laten ploegen","Geen blokkeren van lastdieren","Geen hinderen van werkdieren","Geen misbruik van hulpbehoevenden","Geen heidense rouwpraktijken","Geen kale plek op hoofd bij rouw","Geen insnijdingen in lichaam","Geen tatoeage","Geen prostitutie van een dochter","Geen gruwelen plegen","Geen incest met moeder","Geen incest met vaders vrouw","Geen incest met zuster","Geen incest met halfzuster","Geen incest met kleindochter","Geen incest met tante","Geen incest met tante vaderszijde","Geen incest met tante moederszijde","Geen incest met vrouw van oom vaderszijde","Geen incest met vrouw van oom moederszijde","Geen incest met schoonmoeder","Geen incest met vrouw van zoon","Geen incest met vrouw van kleinkind","Geen incest met schoonzus (behalve yibboem,","Geen incest met tante door huwelijk","Geen seksuele omgang met menstruerende vrouw","Geen overspel met getrouwde vrouw","Geen mannelijk homoseksueel contact","Geen bestialiteit door man","Geen bestialiteit door vrouw","Geen incest met stiefdochter","Geen incest met schoondochter","Geen gemeenschap met verboden vrouwen","Geen gemeenschap met nicht door verboden lijn","Geen incest met zus van vrouw tijdens haar leven","Geen gemeenschap met dieren","Geen gemeenschap met mannelijke prostitutie","Geen gemeenschap met prostituee","Geen gemeenschap buiten huwelijk volgens halacha","Geen verkrachting","Geen verleiden van minderjarige","Geen gemeenschap met dochter van priester die ontheiligd is","Geen gemeenschap met ontheiligende personen","Geen gemeenschap met dieren in bezit","Scheiding niet onterecht tegenhouden","Geen huichelachtige maar misleidende verbintenissen","Geen oneerlijke koop","Geen schulden ontduiken","Geen misbruik van landverdeling","Geen omkoping in rechtspraak","Geen vals getuigenis","Geen laster tegen verwanten","Geen moord","Geen zelfmoord","Geen wraakmoorden","Geen schuldig bloed vergieten","Geen belediging van rechter","Geen rebellie tegen Sanhedrin","Geen rebellie tegen profeet","Geen verkeerde profetie","Geen luisteren naar valse profeet","Geen afkeer oproepen tegen profeet","Geen vrees om profetie door te geven","Geen haatdragende oorlog","Geen vernietiging van vruchtbomen tijdens oorlog","Geen vluchten voor vijand in paniek","Geen verspillen van heilige middelen","Geen weglopen van lastdieren hulp","Geen vermenging van heilige en profane arbeid","Geen dierenofferkomen verminken","Geen tijdelijk gebrekkige dieren offeren","Geen te jong dier offeren","Geen dier en jong op zelfde dag slachten","Geen bloed eten","Geen bloed drinken","Geen heilige offers buiten tijd eten","Geen onreine tempel betreden","Geen ongewenste buitenlandse offers cadeau ontvangen","Geen gelofte breken","Geen eden breken","Geen misleiding in geloften","Geen slaven ontvluchten","Geen alcohol misbruik door priesters","Geen ruw gedrag tegen ouders","Geen slechte behandeling van vreemdelingen","Geen slecht behandelen van weduwe","Geen slecht behandelen van wees","Geen achterhouden van recht van arme","Geen naakt van hulpbehoevende negeren","Geen mishandeling van schuldenaar","Geen achterhouden van gereedschap dat nodig is voor leven","Geen valsheid in handel","Geen verkeerde gewichten","Geen verkeerde maten","Geen ontvoering","Geen achterhouden van eigendom ander","Geen diefstal door inbraak","Geen ontvreemden van heilig eigendom","Geen hekserij","Geen waarzeggerij","Geen magische voorspellingen","Geen tekenmagie","Geen geestenbezwering","Geen necromantie","Geen grensstenen verplaatsen","Geen dieren stelen","Geen ontvreemden van goederen","Geen misleiding in landbouw","Geen misleiding in zaken","Geen wreedheid tegen dieren","Geen dieren laten lijden","Geen vogelmoeder nemen zonder wegsturen (negatief deel,","Geen misbruik van goederen","Geen geld zoeken via bedrog","Geen twijfelachtige praktijken tolereren","Geen incest tussen man en schoonfamilie","Geen overspel","Geen incest door man met moeder","Geen incest door man met zus","Geen incest door man met tante","Geen incest door man met dochter","Geen incest door man met kleindochter","Geen incest door man met schoonmoeder","Geen incest door man met stiefdochter","Geen incest door man met vrouw van broer (behalve leviraat,","Geen incest door man met tante vaderszijde","Geen incest door man met tante moederszijde","Geen incest door man met halfzus","Geen incest door man met vrouw van oom vaderszijde","Geen incest door man met vrouw van oom moederszijde","Geen incest door man met schoondochter","Geen incest door man met vrouw van zoon","Geen incest door man met vrouw van kleinzoon","Geen incest door man met neef, nicht, schoonfamilie","Geen rituele ontucht bij tempel","Geen onreine in heiligdom laten","Geen kohen gadol met weduwe","Geen priester met gescheiden vrouw","Geen priester met ontuchtige vrouw","Geen priester met profane vrouw","Geen kohen gadol met weduwe","Geen kohen in rouw onterecht","Geen heilig voedsel onrein eten","Geen gaven van kohanim onterecht eten","Geen eerste fruit onterecht gebruiken","Geen offers eten na tijd","Geen offers eten die onrein zijn","Geen offers eten die verkeerd worden geslacht","Geen offers eten buiten locatie","Geen eenjarige dieren offeren buiten regels","Geen dieren offeren met gebrek","Geen dieren kopen voor offers met tekortkoming","Geen dier betitelen als offer dat ongeschikt is","Geen dier ruilen dat heilig is voor profaan","Geen dier ontheiligen dat heilig is","Geen heilige voorwerpen beschadigen","Geen heiligdom vervuilen","Geen vuur op altaar doven","Geen gewoon vuur op altaar leggen","Geen offer eten dat uitgekocht is","Geen offer eten buiten heiligdom","Geen bederf van heilige olie","Geen vreemd vuur branden","Geen goud of zilver verwijderen uit heiligdom","Geen dier dat met mens gemeenschap had offeren","Geen dier met gebrek offeren","Geen dier dat geweigerd werd offeren","Geen dier dat verwond is offeren","Geen dier dat botgebrek heeft offeren","Geen dier dat geboren met gebrek is offeren","Geen dier dat blind is offeren","Geen dier met schurft offeren","Geen dier met korst offeren","Geen dier dat afwezig ledemaat heeft offeren","Geen dier dat gebroken ledemaat heeft offeren","Geen dier dat geplet is offeren","Geen dier met gesneden geslachtsdelen offeren","Geen dier geperst offeren","Geen dier gesneden offeren","Geen gemengd dier offeren","Geen dier voor geboorte offeren","Geen offer veranderen","Geen geld wisselen voor heiligdom ongepast","Geen eerste geboren dier verkopen","Geen eerste geboren dier gebruiken","Geen eerstgeborene ruïneren","Geen offers vervangen","Geen offers verkopen","Geen offers consumeren profaan","Geen deel van offer consumeren ongepast","Geen delen van offer laten vallen","Geen delen van offer onterecht verbranden","Geen vet verdwijnen","Geen delen van offer op verkeerde plaats branden","Geen ongepaste dieren offeren","Geen dieren die op sabbat gekocht zijn offeren","Geen onheilige tempeloffers brengen","Geen extra werk op sjabbat","Geen sjabbat ontwijden","Geen dag van heiliging ontwijden","Geen heilige plaats ontwijden","Geen heilig voedsel ontwijden","Geen heiligwater bederven","Geen ritueel van rode koe schenden","Geen as mengen met onreine dingen","Geen reinigingsproces overslaan","Geen priesters in onreinheid laten werken","Geen heilig voedsel geven aan onreinen","Geen rituelen vervalsen","Geen profane gebruiken overnemen","Geen heidense praktijken nabootsen","Geen lichaamssneden","Geen tatoeages","Geen rouwpraktijken van heidenen","Geen spreuken uit heidense praktijken","Geen amuletten gebruiken als magie","Geen bloed drinken","Geen vlees met melk eten","Geen fruit van eerste drie jaar eten (orla,","Geen gebruik van ongecircumcideerde boom","Geen achterhouden van armenrechten","Geen arme onderdrukken","Geen vreemdeling onderdrukken","Geen weduwe onderdrukken","Geen wees onderdrukken","Geen vloek over rechter","Geen vloek over leider","Geen vloek over God","Geen minachting voor heiligdom","Geen minachting voor VARETORAHleraar","Geen afwijking van geboden","Geen toevoegen of afdoen van geboden"]
    ][taal]
        
    start_time = pygame.time.get_ticks()
    ctime = start_time
    imgsize = 100
    devimg = [pygame.transform.scale(pygame.image.load(os.path.join(ASSETS_PATH, image)), (imgsize, imgsize)) for image in ["Dev1.png", "Dev2.png"]]
    devnames = ["Dimitri Varetidis", "Marsu1038"]
    duration = 100 if settings.get('fastopen',False) else 3000
    text_size = (100, 20)
    between = 10

    while ctime < start_time + duration * len(devimg):
        ctime = pygame.time.get_ticks()
        elapsed_time = ctime - start_time
        screen.fill(WHITE)
        
        devindex = elapsed_time // duration
        if devindex < len(devimg):
            display_text(["Developed by:","Gemaakt door:"][taal], (WIDTH // 2 - text_size[0] // 2 - imgsize // 2 - between // 2, HEIGHT // 2 - text_size[1] - 10))
            display_text(devnames[devindex], (WIDTH // 2 - text_size[0] // 2 - imgsize // 2 - between // 2, HEIGHT // 2 + 10))
            screen.blit(devimg[devindex], (WIDTH // 2 + text_size[0] + between, (HEIGHT + text_size[1] - imgsize) // 2))

        pygame.display.flip()
        clock.tick(FPS)

    play_music(current_area)

    def main_menu():
        result = None
        interact_key_down, mouse_down = False, False
        selected = None

        header = pygame.font.Font(None, 120).render("Hammerworld", True, BLACK)

        settings_icon = pygame.transform.scale(pygame.image.load(os.path.join(ASSETS_PATH,"settings_icon.png")),(64,64))
        settings_rect = pygame.Rect(20,HEIGHT-84,64,64)
        settings_menu_open = False

        dark_overlay = pygame.Surface((WIDTH, HEIGHT),flags=pygame.SRCALPHA)
        pygame.draw.rect(dark_overlay,(50,50,50,100),(0,0,WIDTH,HEIGHT))
        reset_rect = pygame.Rect(WIDTH // 2, HEIGHT // 2,300,100)
        reset_dialog = ["Reset data?"] + [f"Press {i} more times" for i in [3,2,1,"0.5","0.25"]]
        reset_index = 0

        while not result:
            esc_pressed = False

            screen.fill(GREEN)
            screen.blit(header, ((WIDTH - header.get_width()) // 2, HEIGHT // 4))
            buttons = [
                (1,pygame.Rect(WIDTH // 2 - 150,HEIGHT // 2,200,100),"Multiplayer"),
                (2,pygame.Rect(WIDTH // 2 + 150,HEIGHT // 2,200,100),"Singleplayer"),
            ]

            screen.blit(settings_icon,settings_rect)
            if settings_menu_open:
                interact_key_down, mouse_down, esc_pressed = get_buttons(interact_key_down,False,get_esc=True)
                if esc_pressed: settings_menu_open = False
            else:
                interact_key_down, mouse_down = get_buttons(interact_key_down,mouse_down)
                screen.blit(settings_icon,settings_rect)
                if mouse_down and settings_rect.collidepoint(pygame.mouse.get_pos()):
                    settings_menu_open = True
            if mouse_down and settings_rect.collidepoint(pygame.mouse.get_pos()):
                settings_menu_open = True


            for index, button, text in buttons:
                if draw_button(button,text,WHITE,BLACK,centered=True,increased_size=(selected==index)).collidepoint(pygame.mouse.get_pos()) and not settings_menu_open:
                    selected = index
                    if mouse_down: result = text.lower()
                elif selected == index and not settings_menu_open: selected = None
            
            if settings_menu_open:
                screen.blit(dark_overlay,(0,0))
                if draw_button(reset_rect,reset_dialog[reset_index],RED,WHITE,centered=True,increased_size=(selected==3)).collidepoint(pygame.mouse.get_pos()):
                    selected = 3
                    if mouse_down:
                        reset_index += 1
                        if reset_index == len(reset_dialog):
                            target_dir = os.path.join(os.getenv("APPDATA"), "Hammerworld")
                            print(target_dir)
                            if os.path.isdir(target_dir):
                                shutil.rmtree(target_dir)
                                sys.exit()
                else:
                    if selected == 3: selected = None
                    if mouse_down: reset_index = 0
            
            if not result:
                pygame.display.flip()
                clock.tick(FPS)
        if result == 'singleplayer':
            world = singleplayer_menu()

            if world in [None, (0,0)]:
                return None

            return ("singleplayer", world)
        
        pygame.display.flip()
        return result
    def find_free_port(start=5555, end=6000):
        for port in range(start, end):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind(('127.0.0.1', port))
                    return port
            except OSError:
                continue
        raise RuntimeError("Geen vrije poort gevonden in het opgegeven bereik.")
    ip = None
    global world
    world = None
    while ip is None:
        result = main_menu()
        if result is None:
            terminate_game()

        if isinstance(result, tuple) and result[0] == "singleplayer":
            world = result[1]

            def is_port_in_use(port):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    return s.connect_ex(('localhost', port)) == 0

            server_path = os.path.join(EXE_PATH, "server.exe")
            if not os.path.isfile(server_path):
                print("Fout: server.exe niet gevonden!")
                terminate_game()

            port = 5555
            if is_port_in_use(port):
                port = find_free_port()
                print(f"Poort 5555 bezet, gebruik {port} voor singleplayer.")

            global singleplayer, server_process
            singleplayer = True
            server_process = subprocess.Popen([server_path, str(port)])

            # Server laten opstarten
            for _ in range(10):
                time.sleep(0.5)
                if is_port_in_use(port):
                    break
            else:
                print("Server startte niet op tijd.")
                terminate_game()

            ip = "127.0.0.1"

        elif result == 'multiplayer':
            ip, port = choose_server()
            if not ip or not port:
                ip = None  
    
    #JTOQM YCQSSMXL
    print(["Connecting...","Verbinden..."][taal])
    print(query_server_status(ip, port))

    # Verbinden met de server
    client_socket, pre_initial_data = connect_to_server(ip, port)

    # Voeg automatisch de '+' (nieuw character) toe
    pre_initial_data['chars'].append(('+', False))

    # Kies automatisch het laatste character → altijd '+'
    selected = len(pre_initial_data['chars']) - 1

    print(f"Selected: {selected}")
    send_pickle(client_socket, selected)

    # Ontvang de initial data van het nieuwe character
    initial_data = recv_pickle(client_socket)

    global data
    data = initial_data['chardata']

    flist = []
    global name, journal, border_open
    border_open = True
    if data:
        try:
            name = data["name"]
        except KeyError:
            raise KeyError("Save data missing, outdated or corrupted: please reset your save data.")
    else:
        name = enter_text(["Enter your name:","Vul je naam in:"][taal])

    if name == 'Dimitri': current_area = 9
    elif name == 'Marsu': current_area = 9

    threading.Thread(target=network_thread, daemon=True).start()
    time.sleep(0.5)
    while not server_data: 
        time.sleep(1)

    tilemap_img = pygame.image.load(os.path.join(ASSETS_PATH, "Tilemap.png")).convert_alpha()
    atilemap_img = pygame.image.load(os.path.join(ASSETS_PATH, "aTilemap.png")).convert_alpha()
    stilemap_img = pygame.image.load(os.path.join(ASSETS_PATH, "sTilemap.png")).convert_alpha()
    #FOIWI YCQSSMXL

    class Tilemap:
        tilesize = 48
        tiletexsize = 32
        tilemap_width = tilemap_img.get_size()[0] // tiletexsize
        tilemap_height = tilemap_img.get_size()[1] // tiletexsize

        maxscreensize = (1920,1080)

        animation_info = {
        #   tile : (frames, frame_time)
            0 : (2, 1),
            1 : (2, 1),
        }
        def __init__(self, mapinfo, should_extend=False):
            self.width, self.height = mapinfo[0][0], mapinfo[0][1]
            self.pixsize = (self.width * self.tilesize, self.height * self.tilesize)

            self.standard_offset = [0,0]
            if should_extend:
                if self.pixsize[0] < self.maxscreensize[0]:
                    self.tilesize = round(self.tilesize * (self.maxscreensize[0] / self.pixsize[0]) + 0.5)
                    self.pixsize = (self.width * self.tilesize, self.height * self.tilesize)
                if self.pixsize[1] < self.maxscreensize[1]:
                    self.tilesize = round(self.tilesize * (self.maxscreensize[1] / self.pixsize[1]) + 0.5)
                    self.pixsize = (self.width * self.tilesize, self.height * self.tilesize)
                if self.tilesize != 32 and current_area == 0:
                    global tree_size
                    tree_size = self.tilesize
            else:
                if self.pixsize[0] < WIDTH:
                    self.standard_offset[0] = (WIDTH-self.pixsize[0])//2
                if self.pixsize[1] < HEIGHT:
                    self.standard_offset[1] = (HEIGHT-self.pixsize[1])//2
            def rebuild_2d_map_1(map_bytes, sizex, sizey):
                flat_array = array.array("B")  
                flat_array.frombytes(map_bytes)
                twod_map = [flat_array[i * sizex:(i + 1) * sizex] for i in range(sizey)]
                for y, row in enumerate(twod_map):
                    newrow = []
                    x = 0
                    while x < len(row):
                        if row[x] == 255:
                            newrow.append(tuple(row[x+1:x+4]))
                            x += 4
                        else:
                            newrow.append(row[x])
                            x += 1
                    twod_map[y] = newrow
            def rebuild_2d_map_2(map_bytes, sizex, sizey):
                flat_array = array.array("B")
                flat_array.frombytes(map_bytes)

                result = []
                index = 0

                for _ in range(sizey):
                    row = []
                    while len(row) < sizex:
                        val = flat_array[index]

                        if val == 255:
                            r = flat_array[index + 1]
                            g = flat_array[index + 2]
                            b = flat_array[index + 3]
                            row.append((r, g, b))
                            index += 4
                        else:
                            row.append(val)
                            index += 1

                    result.append(row)

                return result
                            

            self.map_back = rebuild_2d_map_2(mapinfo[1],self.height,self.width)
            self.map_animated = rebuild_2d_map_2(mapinfo[2],self.height,self.width) if mapinfo[2] else None

            self.collisionrects = []
            self.interactrects = []
            self.transportrects = dict()

            for rectinfo in mapinfo[3]:
                if rectinfo[0] == "fish": interact_range = self.tilesize // 5
                else: interact_range = 0
                if rectinfo[1] == 0: self.collisionrects.append(pygame.Rect(rectinfo[0][0] * self.tilesize,rectinfo[0][1] * self.tilesize,rectinfo[0][2] * self.tilesize,rectinfo[0][3] * self.tilesize))
                elif rectinfo[1] == 2:
                    if rectinfo[2] not in self.transportrects: self.transportrects[rectinfo[2]] = []
                    self.transportrects[rectinfo[2]].append(pygame.Rect(rectinfo[0][0] * self.tilesize,rectinfo[0][1] * self.tilesize,rectinfo[0][2] * self.tilesize,rectinfo[0][3] * self.tilesize))
                elif rectinfo[1] == 1:
                    self.interactrects.append((pygame.Rect(rectinfo[0][0] * self.tilesize - interact_range, rectinfo[0][1] * self.tilesize - interact_range, (rectinfo[0][2]+1) * self.tilesize, (rectinfo[0][3]+1) * self.tilesize),rectinfo[2]))
            
            self.bgimg = pygame.Surface(self.pixsize,flags=pygame.SRCALPHA)
            self.bgimg.fill(BROWN)
            start_animated = self.tilemap_width * self.tilemap_height
            start_seasonal = start_animated + atilemap_img.get_size()[1] // 32
            self.animated_layers = dict()
            self.season_layers = []
            for i in range(4):
                self.season_layers.append(pygame.Surface(self.pixsize,flags=pygame.SRCALPHA))
                self.season_layers[i].fill((0,0,0,0))
            for x, col in enumerate(self.map_back):
                for y, integer in enumerate(col):
                    if type(integer) == tuple and len(integer) == 3:
                        pygame.draw.rect(self.bgimg,integer,(x * self.tilesize, y * self.tilesize, self.tilesize, self.tilesize))
                        continue
                    try:
                        if integer >= start_seasonal:
                            integer -= start_seasonal
                            for i, surface in enumerate(self.season_layers):
                                tex = pygame.transform.scale(stilemap_img.subsurface(integer*self.tiletexsize,i*self.tiletexsize,self.tiletexsize,self.tiletexsize), (self.tilesize,self.tilesize))
                                surface.blit(tex,(x * self.tilesize, y * self.tilesize))
                        elif integer >= start_animated:
                            integer -= start_animated
                            if integer not in self.animated_layers:
                                if integer not in self.animation_info: raise ValueError(f"Don't forget to set the settings of animated tile {integer}")
                                self.animated_layers[integer] = [0,0,[pygame.Surface(self.pixsize, flags=pygame.SRCALPHA) for _ in range(self.animation_info[integer][0])]]
                            for i, surface in enumerate(self.animated_layers[integer][2]):
                                tex = pygame.transform.scale(atilemap_img.subsurface(i*self.tiletexsize,integer*self.tiletexsize,self.tiletexsize,self.tiletexsize), (self.tilesize,self.tilesize))
                                surface.blit(tex,(x * self.tilesize, y * self.tilesize))
                        else:
                            tex = pygame.transform.scale(tilemap_img.subsurface(pygame.Rect((integer % self.tilemap_width) * self.tiletexsize, (integer // self.tilemap_width) * self.tiletexsize, self.tiletexsize, self.tiletexsize)), (self.tilesize, self.tilesize))
                            self.bgimg.blit(tex, (x * self.tilesize, y * self.tilesize))
                    except ValueError as e:
                        print(e)
                        tex = pygame.transform.scale(pygame.image.load(os.path.join(ASSETS_PATH,"Glitch.png")), (self.tilesize, self.tilesize))
                        self.bgimg.blit(tex, (x * self.tilesize, y * self.tilesize))
            
        def tick_animations(self, dt : float = 1/60):
            for index in self.animated_layers:
                anim_info = self.animated_layers[index]
                anim_info[0] += dt
                if anim_info[0] >= self.animation_info[index][1]:
                    anim_info[0] = 0
                    anim_info[1] = (anim_info[1] + 1) % self.animation_info[index][0]

    if initial_data:
        player_id = initial_data['player_id']
        global money
        money = initial_data['money']
        server_data['day_data'] = initial_data['day_data']
        global day
        day = initial_data['day_data']['day']
        global trees
        trees = dict()
        global deleted_trees
        deleted_trees = []
        global tilemaps
        tilemaps = {tilemap_data[0]: Tilemap(tilemap_data[1:]) for tilemap_data in initial_data['tiles']}

        tile_areas = set(tilemaps.keys())
        scrolling_areas = {15} | tile_areas
    else:
        raise ConnectionRefusedError("connection with server refused")

    wave_offset = 0  
    #Variables
    global stamina, max_stamina, stamina_regen_rate
    stamina = 100
    max_stamina = 100
    stamina_regen_rate = 0.1
    global journal_open
    journal_open = False
    global met_kanye1
    met_kanye1 = False
    global met_kanye2
    met_kanye2 = False
    global fixed_geluidsoverlast1
    fixed_geluidsoverlast1 = False
    global fixed_geluidsoverlast2
    fixed_geluidsoverlast2 = False
    global ferryquest
    ferryquest = 0
    global electioncounter
    electioncounter = 0
    global election_day
    election_day = 0
    global electionresult
    electionresult = 2
    global helped_bouncer
    helped_bouncer = False
    global apartment_has_carpet
    apartment_has_carpet = False
    global has_goedje
    has_goedje = False
    global told_about_moonfish
    told_about_moonfish = False
    global journal_tasks
    journal_tasks = []
    last_frame_time : float = 1/60
    frame_counter = 0
    global romancepoints
    romancepoints = 0
    global married
    married = False
    global has_gift
    has_gift = False
    global gift_available
    gift_available = False
    global given_gift
    given_gift = False
    has_torch = True
    global has_quest
    has_quest = False
    global quest_available
    quest_available = False
    global given_quest
    given_quest = False
    global perfection
    perfection = False
    global election_started
    election_started = False
    global no_stamina_system
    no_stamina_system = False
    global has_keys
    has_keys = [False for _ in range(7)]
    global talked_about_elections
    talked_about_elections = [False for _ in range(5)]
    global finished_list
    finished_list = [False for _ in range(5)]
    global endgame
    endgame = [False,False,False]
    global ben_mayor1
    ben_mayor1 = False
    global michael_mayor1
    michael_mayor1 = False
    global ben_mayor2
    ben_mayor2 = False
    global michael_mayor2
    michael_mayor2 = False
    global has_card
    has_card = False
    global has_bait
    has_bait = False
    global snackbar_counter
    snackbar_counter = 0
    global played_video
    played_video = False
    global next_day
    next_day = day + 1
    global claimed_tree_money
    claimed_tree_money = False
    if day == 1: 
        global gus_available
        gus_available = False
        global has_rod
        has_rod = False
        global card_available
        card_available = False
        global robot_purchased
        robot_purchased = False
        global shovel_purchased
        shovel_purchased = False
    elif day > 1:
        gus_available = (has_card and money >= minimum_gus)
        has_rod = (day > 5)
        card_available = (day == 25)
        has_card = (day > 25)
        robot_purchased = (day >= 25)
        shovel_purchased = (day >= 50)
    
    button_textures = { # result will be "key": pygame.Image
        "settings": ("Settings_icon.png", 64, 64),
    }
    for key, (file, sizex, sizey) in button_textures.items():
        button_textures[key] = pygame.transform.scale(pygame.image.load(os.path.join(ASSETS_PATH, file)),(sizex,sizey))
    
    forest_area_overlay = None#pygame.transform.scale(load_img_from_assets("Treetops.png"),tilemaps[current_area].pixsize)

    coffee_active = False

    class Effects:
        images = {
            "energetic" : "Coffee.png",
        }
        for i, img in images.items():
            try:
                base_img = pygame.image.load(os.path.join(ASSETS_PATH,img))
            except:
                base_img = pygame.image.load(os.path.join(ASSETS_PATH,"Glitch.png"))
            images[i] = pygame.transform.scale(base_img,(32,32))
        duration_order = ['minutes','hours','days']
        def __init__(self):
            self.effects = []
        def add_effect(self, id : str, dur : int, durtype : str = 'days'):
            if durtype not in self.duration_order: raise ValueError("wrong duration type, please choose from the ones listed at self.duration_order")
            for i, (id2, dur2, durtype2) in enumerate(self.effects):
                if id == id2:
                    if self.duration_order.index(durtype) > self.duration_order.index(durtype2):
                        self.effects[i][1] = dur
                        self.effects[i][2] = durtype
                    elif durtype == durtype2:
                        self.effects[i][1] = max(dur,dur2)
                    return True
            self.effects.append([id, dur, durtype])
        def draw(self, start_pos, between : int = 16):
            imgsize = 32
            for i, (id, dur, durtype) in enumerate(self.effects):
                img = self.images[id]
                screen.blit(img, (start_pos[0]+i*(imgsize+between), start_pos[1]))
        def tick_days(self, daysamount : int = 1):
            toremove = []
            for i, (id, dur, durtype) in enumerate(self.effects):
                if durtype == 'days':
                    self.effects[i][1] -= daysamount
                    if self.effects[i][1] <= 0: toremove.append(i)
            for i in toremove[::-1]:
                self.effects.pop(i)
        def check_for_effect(self, name):
            return (name in [i[0] for i in self.effects])
    effects = Effects()

    global mail_content
    mail_content = ""
    global michael_on_cooldown
    michael_on_cooldown = False
    in_selling_range = False
    mouse_down = False
    global leah_on_cooldown
    leah_on_cooldown = False
    global fish_caught
    fish_caught = 0
    eggs = {
        0:[],
        2:[],
        9:[],
        11:[],
    }
    flags = False
    ben_speed = 1
    earl_pos = [WIDTH // 2, HEIGHT - 100]
    tix_pos = [CENTER[0], HEIGHT // 4]
    max_pos = [WIDTH * 1440 / 1920, HEIGHT * 810 / 1080]
    global npc_text
    npc_text = ""
    global npc_text_timer
    npc_text_timer = 0
    global game_time_minutes
    game_time_minutes = 360
    global robot
    robot = {
        'cost': 2500,
        'speed': 120, # px/sec
        'cooldown': 0.5,
        'cutting_speed': 2.0,
        'task': 'IDLE',
        'time_left': 0,
        'target': None,
        'pos': [0,0],
        'should_draw': True,
    }
                
    shovel_cost = 2500
    global chicken_amount
    chicken_amount = 0  
    global cow_amount
    cow_amount = 0
    player_size = 40
    
    global cacti
    cacti = []
    trees = {}
    treechanges = []
    rockchanges = []
    cactus_img = pygame.transform.scale(pygame.image.load(os.path.join(ASSETS_PATH, "Cactus.png")), (player_size, player_size)) 

    global sea_pos, sea_size
    sea_pos = [0, round(HEIGHT*0.8)]
    sea_size = [(round(WIDTH*0.2)), (round(HEIGHT*0.2))]

    global talked_to_tix
    talked_to_tix = False

    visited = []
    visit_animation = 0
    outside_areas = {0,2,3,4,5,6,8,11,12,13}
    own_weather_areas = {13}
    struct 
    class Area():
        tilesize = 48
        playersize = 32
        def __init__(self,name="???",bg=(173, 216, 230),enter_pos=None,leave_pos=None):
            self.name = name
            self.background = bg
            indent = (self.tilesize-self.playersize)//2
            self.enter_pos = [
                enter_pos[0]*self.tilesize+indent,
                enter_pos[1]*self.tilesize+indent
            ] if enter_pos else None
            self.leave_pos = [
                leave_pos[0]*self.tilesize+indent,
                leave_pos[1]*self.tilesize+indent
            ] if leave_pos else None
    all_area_info = {
        # posities beginnen op (0,0)
         0: Area(name="Hanztown"),
         1: Area(name="Tixheadquarters",enter_pos=(4,3),leave_pos=(20,16)),
         2: Area(name="Snowfall"),
         3: Area(name="Maxdesert"),
         4: Area(name="Frogswamp"),
         5: Area(name="Tixcity"),
         6: Area(name="Gus's Dock"),
         7: Area(name="Leah's Apartment",bg=LARSGROEN),
         8: Area(name="Grasslands"),
         9: Area(name="Lumber Cottage",enter_pos=(3,5),leave_pos=(13,16)),
        10: Area(name="Kanye's House",bg=LARSGROEN),
        11: Area(name="Camden County"),
        12: Area(name="End of Gus's Dock"),
        13: Area(name="Turmeric Island"),
        14: Area(name="Turmeric Cave"),
        16: Area(name="Tommywood"),
        17: Area(name="Studio X"),
        18: Area(name="Prairie Passage"),
        19: Area(bg=LARSGROEN,enter_pos=(3,5),leave_pos=(3,5)),
        20: Area(bg=LARSGROEN,enter_pos=(3,5),leave_pos=(13,5)),
        21: Area(bg=LARSGROEN,enter_pos=(3,5),leave_pos=(3,16)),
        22: Area(name="Snackbar & More",bg=LARSGROEN,leave_pos=(10,44)),
    }
    player_pos = all_area_info[current_area].enter_pos or [WIDTH//2,HEIGHT//2]

    def is_prop_on_surface(propPos : list, propSize : int, surfacePos : list, surfaceSize : list, dist : int = 0):
        prop_right = propPos[0] + propSize
        prop_bottom = propPos[1] + propSize
        surface_right = surfacePos[0] + surfaceSize[0]
        surface_bottom = surfacePos[1] + surfaceSize[1]
        return (
            prop_right >= surfacePos[0] - dist and
            propPos[0] <= surface_right + dist and
            prop_bottom >= surfacePos[1] - dist and
            propPos[1] <= surface_bottom + dist
        )
    def convert_rect_to_interactrect(rect : pygame.Rect, zone : int = 10):
        return pygame.Rect(rect[0] - zone, rect[1] - zone, rect[2] + 2*zone, rect[3] + 2*zone)
    
    def generate_trees(amount: int):

        for _ in range(amount):
            valid_position = False

            while not valid_position:
                tree_x = random.randint(0, WIDTH - tree_size)
                tree_y = random.randint(0, HEIGHT - tree_size)

                if is_prop_on_surface([tree_x, tree_y], tree_size, sea_pos, sea_size): continue  

                road_width = 40
                screen_center_x = WIDTH // 2
                screen_center_y = HEIGHT // 2

                on_horizontal_road = screen_center_y - road_width // 2 <= tree_y <= screen_center_y + road_width // 2
                on_vertical_road = screen_center_x - road_width // 2 <= tree_x <= screen_center_x + road_width // 2

                if not (on_horizontal_road or on_vertical_road):  
                    valid_position = True 

            trees.append((tree_x,tree_y))
            global treechanges
            treechanges.append((tree_x,tree_y)) 
    
    def generate_cacti(amount : int):
        for _ in range(amount):
            cactus_x = random.randint(48, 576 - cactus_size)
            cactus_y = random.randint(48, 576 - cactus_size)
            if not is_prop_on_surface([cactus_x,cactus_y], tree_size, sea_pos, sea_size): 
                cacti.append({"x": cactus_x, "y": cactus_y})
 
    flags_color = [RED, GREEN, BLUE, YELLOW]

    flags = []
    flag_width = 20
    flag_height = 15
    spacing = 10
    x = 0
    y = 20

    while x < tilemaps[0].pixsize[0]:
        flag_color = random.choice(flags_color)
        flags.append((x, y + random.randint(-5,5), flag_color))
        x += flag_width + spacing

    def draw_flags():
        if current_area == 0:
            for flag in flags:
                x, y, flag_color = flag
                x -= camera_pos[0]
                y -= camera_pos[1]
                pygame.draw.polygon(
                    screen, flag_color,
                    [(x, y), (x + flag_width // 2, y + flag_height), (x + flag_width, y)]
                )

    def draw_jelly(area):
        freq, amp = 0.01, 30
        jelly_img = pygame.transform.scale(load_img_from_assets("Jelly.png"),(player_size//2, player_size//2))
        intensity = 30
        for x, y, offset in jelly[area]:
            newy = y + int(math.sin(frame_counter * freq + offset) * amp)
            screen.blit(jelly_img,(x, newy))
            light_rects.append(pygame.Rect(x-intensity,newy-intensity,2*intensity+player_size//2,2*intensity+player_size//2))

    def draw_waves(wave_offset, freq : float = 0.1, amp : int = 10, color : tuple = (80,130,250)):
        for y in range(0, HEIGHT, 20):
            wave_x_offset = int(math.sin(y * freq + wave_offset) * amp)
            pygame.draw.line(screen, color, (0, y + wave_x_offset), (WIDTH, y + wave_x_offset), 2)

        return wave_offset + 0.1

    global current_time
    current_time = pygame.time.get_ticks()
    day_time = 0

    raindrops = [{"x": random.randint(0, tilemaps[0].pixsize[0]), "y": random.randint(-tilemaps[0].pixsize[1], 0)} for _ in range(500)]
    rain_speed = 5
    mistrays = [{"y": random.randint(0, HEIGHT), "x": random.randint(-WIDTH-250, -250)} for _ in range(80)]
    mist_speed = 1

    stuck_in_area = False

    global current_minigame
    current_minigame = None
    global fishing_timer
    fishing_timer = 0
    fishing_max_time = 3000
    font = pygame.font.Font(None, 36)
    interact_key_down = False

    class Farmland:
        crop = 'empty'
        size = [90,90]
        pixelSize = 10
        cropPos = [[10,20],[50,20],[30,70],[70,70]]
        def __init__(self, X : int, Y : int, isLocked : bool = True, language : int = 0, custom = False): # custom should be a list [cropID,startDay,endDay]
            self.x = X
            self.y = Y
            if custom:
                self.cropID = custom[0]
                self.crop = crops_list[self.cropID]
                self.name = self.crop["name"][0]
                self.dName = self.crop["name"][language]
                self.locked = False
                self.startingDay = custom[1]
                self.dayReady = self.startingDay + self.crop["dur"]
                #self.x = custom[3][0]
                #self.y = custom[3][1]
            else:
                self.cropID = -1
                self.crop = {"name":'nothing'}
                self.name = 'nothing'
                self.locked = isLocked
                self.startingDay, self.dayReady = 0, 0
            self.language = language
        def unlock(self):
            if self.locked:
                self.locked = False
                time.sleep(0.5)
        def playerInRange(self, player): # player(x,y,width,height)
            return (self.x + self.size[0] > player[0] and player[0] + player[2] > self.x and self.y + self.size[1] > player[1] and player[1] + player[3] > self.y)
        def plant(self, day : int, cropOverride = None):
            if self.crop != {"name":"nothing"} or self.locked: return False
            if cropOverride:
                self.crop = cropOverride
            else:
                self.cropID = random.randint(0,len(crops_list)-1)
                self.crop = crops_list[self.cropID]
                self.name = self.crop["name"][0]
                self.dName = self.crop["name"][self.language]
            self.dayReady = day + self.crop["dur"]
            self.startingDay = day
            return True
        def harvest(self, day : int):
            if self.crop == {"name": "nothing"} or day < self.dayReady or self.locked: return False
            else:
                #moneyGained = max(round(self.crop["val"] - self.crop["val"] * (day - self.dayReady) * 0.2), 0)
                if day - self.dayReady:
                    if day - self.dayReady > 2: moneyGained = 0
                    else: moneyGained = round(self.crop["val"] * 0.8)
                else: moneyGained = self.crop["val"]
                special = 0
                if day - self.dayReady < 2:
                    newText = [f"You harvested a {self.dName}. It's worth €{moneyGained}!",f"Je oogstte een {self.dName}. Deze is €{moneyGained} waard!"][self.language]
                    special += 1
                elif moneyGained == 0:
                    newText = [f"This {self.dName} is unfortunately rotten. Remember to harvest on time!", f"Deze {self.dName} is helaas verrot. Graag de volgende keer op tijd oogsten!"][self.language]
                else:
                    newText = [f"You harvested a {self.dName}. It's worth €{moneyGained}.",f"Je oogstte een {self.dName}. Deze is €{moneyGained} waard."][self.language]
                textTimer = 3500
                self.crop = {"name":'nothing'}
                cropname = self.name
                cropdname = self.dName
                self.dName = 'nothing'
                return {'success':True if moneyGained else False,'cropname':cropname,'dispName':cropdname,'special':special,'money+':moneyGained,'newT':newText,'textT':textTimer} #results
        def draw(self, scrn, day : int):
            if self.locked: return
            pygame.draw.rect(scrn, (129, 59, 9), (self.x, self.y, self.size[0], self.size[1]))
            if self.crop == {"name": "nothing"}: return
            day = min([day,self.dayReady])
            if day - self.startingDay == 0:
                for cPos in self.cropPos:
                    pygame.draw.rect(scrn, tuple(self.crop["seedColor"]), (self.x + cPos[0], self.y + cPos[1], self.pixelSize, self.pixelSize))
            elif self.crop["reverse"] == False:
                plant = []
                for c in range(0,len(self.crop["length"])):
                    for x in range(0,self.crop["length"][c]):
                        plant.append([self.crop["colors"][c],self.crop["width"][c]])
                for cPos in self.cropPos:
                    offset = 0
                    for c in range(0,len(plant)):
                        if c+0.5 <= (day-self.startingDay)/self.crop["dur"]*sum(self.crop["length"]) or c == 0:
                            pygame.draw.rect(scrn, plant[c][0], (self.x + cPos[0] - (plant[c][1]-1)/2*self.pixelSize, self.y + cPos[1] + offset, round(self.pixelSize * plant[c][1]), self.pixelSize))
                            offset -= self.pixelSize
            else:
                plant = []
                pl = []
                for c in range(0,len(self.crop["length"])):
                    for x in range(0,self.crop["length"][len(self.crop["length"])-1-c]):
                        pl.append([tuple(self.crop["colors"][len(self.crop["length"])-1-c]),self.crop["width"][len(self.crop["length"])-1-c]])
                for c in range(0,len(pl)):
                    if c+0.5 <= (day-self.startingDay)/self.crop["dur"]*sum(self.crop["length"]) or len(plant) == 0: plant.append(pl[c])
                plant.reverse()
                for cPos in self.cropPos:
                    offset = 0
                    for c in range(0,len(plant)):
                            pygame.draw.rect(scrn, plant[c][0], (self.x + cPos[0] - (plant[c][1]-1)/2*self.pixelSize, self.y + cPos[1] + offset, round(self.pixelSize * plant[c][1]), self.pixelSize))
                            offset -= self.pixelSize
        def getSaveData(self):
            if self.cropID != -1:
                return [self.cropID, self.startingDay]
            else: return False

    class FishingGame: 
        barWidth = 25
        barHeight = 300
        scoreBarWidth = 10
        fishHeight = barWidth - 10
        fishPos = 100
        rodVel = 0
        rodPos = 90
        fishingScore = 30
        fishTarget = 0
        fishVel = 0.0
        fishTDist = 0
        counter = 0
        mod = 0
        shiny = False
        TREASURE_REQ = 35
        abilities = { # [relative cooldown, ability name]
            'floater': [5,'up',3],
            'sinker': [5,'down',3],
        }
        ability = None
        def __init__(self, day : int = 999, language : int = 0, area : int = 0, luk : int = 0, bar : int = 80):
            self.rodHeight = bar
            if day == 17: self.fishType = fish_list[5]
            else:
                self.fishType = random.choice(fish_list)
                while self.fishType["day"] > day or ("area" in self.fishType and self.fishType["area"] != area): self.fishType = random.choice(fish_list)
            if self.fishType["type"] in ["sine","mixed"]: self.sine = [0.0, 0.09, 0.17, 0.26, 0.34, 0.42, 0.5, 0.57, 0.64, 0.71, 0.77, 0.82, 0.87, 0.91, 0.94, 0.97, 0.98, 1.0, 1.0, 1.0, 0.98, 0.97, 0.94, 0.91, 0.87, 0.82, 0.77, 0.71, 0.64, 0.57, 0.5, 0.42, 0.34, 0.26, 0.17, 0.09, 0.0, -0.09, -0.17, -0.26, -0.34, -0.42, -0.5, -0.57, -0.64, -0.71, -0.77, -0.82, -0.87, -0.91, -0.94, -0.97, -0.98, -1.0, -1.0, -1.0, -0.98, -0.97, -0.94, -0.91, -0.87, -0.82, -0.77, -0.71, -0.64, -0.57, -0.5, -0.42, -0.34, -0.26, -0.17]
            if random.randint(1,128) == 1:
                self.shiny = True
                self.fishType["val"] *= 3
            self.treasure = (random.randint(1,100)/(luk+5.01) <= 2)
            if self.treasure:
                self.treasurePos = random.randint(10,self.barHeight-10-self.fishHeight)
                self.treasureScore = 0
                self.treasureCooldown = 1
            self.treasureCaught = False

            self.difficulty = self.fishType["dif"]
            self.fishName = self.fishType["name"]
            self.type = self.fishType["type"]
            if self.type in self.abilities.keys(): self.abilityCooldown = self.get_ability_cooldown(self.abilities[self.type][0],dif=self.difficulty)

        def get_ability_cooldown(self, standardCooldown, dif = 1, relRange = 0, accuracy : int = 3): # relRange is the relative range in percents
            if not isinstance(relRange,int) or relRange > 99 or relRange < 0: raise ValueError("relRange must be non-negative and lower than 100%")
            relRange /= 100
            target = standardCooldown * (1.5/(dif**0.3)) * 10**accuracy
            return random.randint(round(target * (1 - relRange)), round(target * (1 + relRange))) / 10**accuracy
        
        def tick(self, keyPressed, playerPos, scrn, dt : float = 1/60):
            global npc_text, npc_text_timer

            barPos = [playerPos[0] + 30, playerPos[1] - self.barHeight + 10]
            if self.fishingScore < 100 and round(self.fishingScore) > 0:
                score = round(self.fishingScore) # score to be shown
                pygame.draw.rect(scrn, (30, 30, 30), (barPos[0], barPos[1], self.barWidth, self.barHeight))
                pygame.draw.rect(scrn, (100, 100, 100), (barPos[0] + self.barWidth, barPos[1], self.scoreBarWidth, self.barHeight))
                pygame.draw.rect(
                    scrn,
                    (255, int(255 * (score - 1) / 49), 0) if score <= 50 else (int(255 * (100 - score) / 50), 255, 0),
                    (barPos[0] + self.barWidth, barPos[1] + self.barHeight - score*round(self.barHeight/100),
                    self.scoreBarWidth,
                    score*round(self.barHeight/100))
                )
                if keyPressed: self.rodVel -= .09 # up or down?
                else: self.rodVel += .09

                if self.rodPos <= 0 or self.rodPos >= self.barHeight - self.rodHeight: # bounce
                    self.rodVel = -0.5 * self.rodVel
                    self.rodPos += self.rodVel
                if self.rodPos <= 0: self.rodPos += 1
                if self.rodPos >= self.barHeight - self.rodHeight: self.rodPos -= 1
                self.rodPos += self.rodVel
                if self.type == "psychic" and random.randint(0,1200) < self.difficulty**0.4: self.rodVel = -self.rodVel if random.randint(1,3)==1 else 0
                pygame.draw.rect(scrn, (200, 200, 0), (barPos[0], barPos[1] + self.rodPos, self.barWidth, self.rodHeight))
                
                # draw fish
                if not (self.type == "ghost" and self.counter != 0): pygame.draw.rect(scrn, (40, 255, 10) if self.shiny else (0, 200, 0), (barPos[0] + 5, barPos[1] + self.fishPos, self.barWidth - 2*5, self.fishHeight)) 
                if self.type == "quantum":
                    pygame.draw.rect(scrn, (0, 70, 0), (barPos[0] + 5, barPos[1] + self.barHeight - self.fishPos - self.fishHeight, self.barWidth - 2*5, self.fishHeight))
                    if random.randint(0,2000) < self.difficulty**0.4:
                        self.fishPos = self.barHeight - self.fishPos - self.fishHeight
                        self.fishVel = -self.fishVel

                if self.fishPos > self.rodPos and self.fishPos + self.fishHeight <= self.rodPos + self.rodHeight: self.fishingScore += .3 # fish in range
                else: self.fishingScore -= .2

                if self.type in ["dart","mixed"]:
                    if self.fishTarget == 0 and random.randint(1,round(400/(1+0.4*(self.type=='mixed')))) <= self.difficulty: self.fishTarget = random.randint(10,self.barHeight-10-self.fishHeight)
                    if self.fishTarget:
                        self.fishVel = 0.05*((self.difficulty-0.25)**0.3)*(abs(abs(self.fishPos-self.fishTarget)-self.fishTDist) + 1.1*self.fishTDist)
                        if self.fishTarget < self.fishPos: self.fishPos -= self.fishVel
                        else: self.fishPos += self.fishVel
                        if abs(self.fishTarget - self.fishPos) < 5: self.fishTarget = 0
                    elif self.type == "mixed":
                        self.fishVel += 0.0045*random.randint(-self.difficulty*10,self.difficulty*10)
                        self.fishPos += self.fishVel
                elif self.type in ["smooth","floater","sine","sinker","ghost","quantum","psychic"]:
                    self.fishVel += 0.006*random.randint(-self.difficulty*(10+3*(self.ability=='up')-3*(self.ability=='down')),self.difficulty*(10+3*(self.ability=='down')-3*(self.ability=='up')))
                    self.fishPos += self.fishVel
                if self.type == "sine":
                    self.fishPos -= self.mod
                    self.counter += 1
                    if self.counter >= len(self.sine): self.counter = 0
                    self.mod = (self.difficulty+4)**0.65*self.sine[round(self.counter)]
                    self.fishPos += self.mod
                if self.type == "ghost":
                    if random.randint(1,300) == 1 and self.counter == 0:
                        self.counter = 1
                    if self.counter != 0:
                        self.counter += 1
                    if self.counter > 60:
                        self.counter = 0
                if self.fishPos < 5:
                    self.fishPos = 5
                    self.fishVel = 0.05
                if self.fishPos > self.barHeight - self.fishHeight - 5:
                    self.fishPos = self.barHeight - self.fishHeight - 5
                    self.fishVel = -0.05
                
                if self.type in self.abilities.keys():
                    self.abilityCooldown -= dt
                    if self.abilityCooldown < 0:
                        if self.ability:
                            self.ability = None
                            self.abilityCooldown = self.get_ability_cooldown(self.abilities[self.type][0],dif=self.difficulty,relRange=20)
                        else:
                            self.ability = self.abilities[self.type][1]
                            self.abilityCooldown = self.get_ability_cooldown(self.abilities[self.type][2],dif=self.difficulty,relRange=20)

                if self.treasure:
                    if self.treasureCooldown > 0:
                        self.treasureCooldown -= dt
                    else:
                        if self.treasurePos > self.rodPos and self.treasurePos + self.fishHeight <= self.rodPos + self.rodHeight:
                            self.treasureScore += 0.3
                            color = (255,120,120)
                            if self.treasureScore >= self.TREASURE_REQ:
                                self.treasure = False
                                self.treasureCaught = True
                        else:
                            self.treasureScore -= 0.17
                            if self.treasureScore < 0: self.treasureScore = 0
                            color = (255,20,20)
                        if self.treasureScore > 0:
                            pygame.draw.rect(scrn, (0,0,0), (barPos[0] + 5 - (self.barWidth - 2*5), barPos[1] + self.treasurePos - 10, 3*self.barWidth - 6*5, self.fishHeight // 2)) # 5 is the indent of the square (or rect)
                            pygame.draw.rect(scrn, (0,255,0), (barPos[0] + 5 - (self.barWidth - 2*5), barPos[1] + self.treasurePos - 10, round((3*self.barWidth - 6*5) * (self.treasureScore / self.TREASURE_REQ)), self.fishHeight // 2)) # 5 is the indent of the square (or rect)
                        pygame.draw.rect(scrn, color, (barPos[0] + 5, barPos[1] + self.treasurePos, self.barWidth - 2*5, self.fishHeight))

            elif self.fishingScore > 100: # win
                global fish_caught
                fishDName = itemlist[self.fishName][0]

                moneyGained = self.fishType["val"] * (3 if self.shiny else 1) + (50 if self.treasureCaught else 0)

                fish_caught += 1
                legendary = bool('legendary' in itemlist[self.fishName][1])
                rarityLvl = (int(self.shiny) + int(legendary))

                if not inventory.pickup(self.fishName,rarity=rarityLvl,value=moneyGained,dispName=fishDName): print('inventory full!')
                if self.treasureCaught:
                    if not inventory.pickup('searelic',value=50): print('inventory full!')

                npctext.set_message(([
                    f"I have caught {'the legendary' if legendary else 'a'} {fishDName} of level {self.difficulty} and Michael will give me {'as much as ' if self.shiny else ''}€{moneyGained} for it!{' He needs to recover for a moment now.' if legendary else ''}",
                    f"Ik heb {'de legendarische' if legendary else 'een'} {fishDName} van niveau {self.difficulty} gevangen en Michael zal me er {'maar liefst ' if self.shiny else ''}€{moneyGained} voor geven!{' Hij moet nu even bijkomen.' if legendary else ''}"
                ][taal],{'thinking':True}),player_pos,can_skip=False)
                return "done"
            else: # fail
                fishDName = itemlist[self.fishName][0]

                npctext.set_message(([
                        f"I didn't catch the {fishDName} of level {self.difficulty}...",
                        f"Ik heb de {fishDName} van niveau {self.difficulty} niet gevangen..."
                    ][taal],{'thinking':True}),player_pos,can_skip=False)
                return "done"

    def draw_clock(GameTime : int):
        hour = (GameTime // 60) % 24
        minute = GameTime % 60
        display_text(f"{hour:02d}:{minute:02d}", (WIDTH - 20, 50), area=current_area,orientation='right')
    def draw_stamina():
        stamina_bar_width = 200
        bar_x = 20
        bar_y = 60
        stamina_ratio = stamina / max_stamina
        pygame.draw.rect(screen, BLACK, (bar_x - 2, bar_y - 2, stamina_bar_width + 4, 24))
        pygame.draw.rect(screen, GREY, (bar_x, bar_y, stamina_bar_width, 20))
        pygame.draw.rect(screen, GREEN, (bar_x, bar_y, stamina_bar_width * stamina_ratio, 20))
    
    class SInteract:
        width = player_size
        height = player_size
        defaultMessages = []
        def __init__(self, name : str, npcTextures : list, loc : int, pos = (0,0), centered : bool = True, defaultMessages : list = [], customSize : list = None):
            if len(pos) != 2: raise ValueError

            self.name = name
            if customSize: self.width, self.height = customSize
            self.defaultMessages = defaultMessages if isinstance(defaultMessages, list) else [defaultMessages]

            self.pos = [round(pos[0]),round(pos[1])]
            if centered: self.pos = [self.pos[0] - self.width // 2, self.pos[1] - self.height // 2]
            self.rect = pygame.Rect(self.pos[0],self.pos[1],self.width,self.height)
            self.location = loc

            self.npcTex = []
            for tex in npcTextures:
                try:
                    img = pygame.image.load(os.path.join(ASSETS_PATH, tex))
                except:
                    print(f"warning: please include {tex} in the assets folder")
                    img = pygame.image.load(os.path.join(ASSETS_PATH, "Glitch.png"))
                self.npcTex.append(pygame.transform.scale(img, (self.width, self.height)))
        def draw(self, area : int = -1, texture : int = 0):
            if isinstance(self.location,list): check = (area in self.location)
            else: check = (area == self.location)
            if check or area == -1:
                if area in tile_areas:
                    screen.blit(self.npcTex[texture], (self.pos[0] - camera_pos[0], self.pos[1] - camera_pos[1]))
                else:
                    screen.blit(self.npcTex[texture], (self.pos[0], self.pos[1]))
        def get_message(self):
            return self.name + ": " + (random.choice(self.defaultMessages) if self.defaultMessages else "...")
        def is_interacting(self, objPos = [], objSize : list = [], area : int = 0):
            if objSize: objRect = pygame.Rect(objPos[0],objPos[1],objSize[0],objSize[1])
            else: objRect = pygame.Rect(objPos[0],objPos[1],player_size,player_size)
        def is_interacting_rect(self, objRect, area : int = 0):
            if isinstance(self.location,list): check = (area in self.location)
            else: check = (area == self.location)
            return (objRect.colliderect(self.rect) and check)

    class Npc(SInteract):
        shouldDeleteMessage = False
        spokento = False
        messageOverride = None
        def __init__(self, name : str, npcTextures : list, loc : int, pos : list = [0,0], centered : bool = True, defaultMessages : list = [], customSize : list = None, schedule=None, speed=1):
            if type(pos) != list:
                try: pos = list(pos)
                except: raise ValueError(f"invalid position type for class Npc() (is {type(pos)}, should be <class 'list'>)")
            self.schedule = schedule
            self.speed = speed
            self.target = tuple(pos)
            super().__init__(name, npcTextures, loc, pos, centered, defaultMessages, customSize)
        def get_message(self):
            return self.name + ": " + (self.messageOverride or (random.choice(self.defaultMessages) if self.defaultMessages else "..."))
        def tick_overnight(self):
            if self.shouldDeleteMessage: self.messageOverride = None
        def draw(self,area:int=-1,texture : int = 0):
            if isinstance(self.location,list): check = (area in self.location)
            else: check = (area == self.location)
            if check or area == -1:
                if area in tile_areas:
                    screen.blit(self.npcTex[texture], (self.pos[0] - camera_pos[0], self.pos[1] - camera_pos[1]))
                else:
                    screen.blit(self.npcTex[texture], self.pos)
        def update_target(self, game_time):
            if self.schedule is None: return
            times = sorted(self.schedule.keys())
            for t in reversed(times):
                if game_time >= t:
                    self.target = self.schedule[t]
                    break

        def move(self):
            if self.schedule is None: return
            tx, ty = self.target
            dx = tx - self.pos[0]
            dy = ty - self.pos[1]
            dist = math.hypot(dx, dy)

            if dist > 1:
                self.pos[0] += self.speed * dx / dist
                self.pos[1] += self.speed * dy / dist
    
    class QuestlineNpc(Npc):
        cooldown = 0
        def __init__(self, name : str, npcTextures : list, loc, questline : list, pos : tuple = (0,0), centered : bool = True):
            self.questline = []
            for i, val in enumerate(questline):
                newval = []
                if isinstance(val, tuple):
                    newval = ((["name","tag","wait","reward","key"].index(val[0]), *[value for value in val[1:]]))
                else: raise ValueError("Invalid: tuples required for Questline")
                self.questline.append(tuple(newval))
            self.counter = 0
            self.wait = 0
            self.completed = False
            super().__init__(name, npcTextures, loc, pos=pos, centered=centered)
        def check_quest(self, npcText = ''):
            global key_items, npc_text_timer
            messageappend = ''
            if not self.completed:
                typeindex = self.questline[self.counter][0]
                otheritems = self.questline[self.counter][2:]
                if typeindex in {0,1}:
                    tag = otheritems[0]
                    if len(otheritems) > 1:
                        delete = otheritems[1]
                    else: delete = False
                    check = (inventory.get_nth_named(tag) if typeindex == 0 else inventory.get_nth_tagged_in_itemlist(tag))
                    if ((isinstance(otheritems[-1],int) and keys[otheritems[-1]]) or not isinstance(otheritems[-1],int)) and (inventory.get_nth_named(tag,delete=delete) if typeindex == 0 else inventory.get_nth_tagged_in_itemlist(tag,delete=delete)):
                        self.counter += 1
                        npcText = ''
                        if self.counter < len(self.questline) and self.questline[self.counter][0] == 2: self.cooldown = self.questline[self.counter][2]
                    elif isinstance(otheritems[-1],int) and check:
                        messageappend = f" ({["Press","Druk op"][taal]} {[48,49,50,51,52,53].index(otheritems[-1])})"
                elif typeindex == 3:
                    value = self.questline[self.counter][2]
                    if isinstance(value,int):
                        global accumulated_money
                        accumulated_money += value
                    elif isinstance(value,str):
                        key_items.add(value)
                    self.counter += 1
                elif typeindex == 4:
                    required_item = self.questline[self.counter][2]
                    if required_item in key_items:
                        self.counter += 1
                        if self.counter < len(self.questline) and self.questline[self.counter][0] == 2: self.cooldown = self.questline[self.counter][2]

                if self.counter >= len(self.questline):
                    self.completed = True
                    message = self.questline[self.counter-1][1]
                else:
                    message = self.questline[self.counter][1]
                if not (len(npcText) > len(self.name) and npcText.startswith(self.name)):
                    npcText = self.name + ": " + message + messageappend
                    npc_text_timer = current_time + 5000
            elif not (len(npcText) > len(self.name) and npcText.startswith(self.name)):
                npcText = self.get_message()
                npc_text_timer = current_time + 5000
            return npcText
        def check_quest_overnight(self):
            typeindex = self.questline[self.counter][0] if self.counter < len(self.questline) else -1
            if typeindex == 2:
                self.cooldown -= 1
                if self.cooldown < 1:
                    self.counter += 1
                    if self.questline[self.counter][0] == 2: self.cooldown = self.questline[self.counter][2]

    class Island:
        def __init__(self, serverdata, ocean_indent : int = 10):
            def decompress_cell(cell_bytes, size):
                w, h = size
                a = array.array("b")
                a.frombytes(cell_bytes)
                return [a[i * w:(i + 1) * w] for i in range(h)]

            def rebuild_areainfo(base_map, compressed_cells):
                height = len(base_map)
                width = len(base_map[0]) if height else 0
                full_map = [[base_map[y][x] for x in range(width)] for y in range(height)]

                types = dict()
                for (y, x), compressed in compressed_cells.items():
                    full_map[y][x] = decompress_cell(compressed["data"], compressed["size"])
                    types[(y,x)] = compressed["type"]

                return full_map, types
            
            self.sizex, self.sizey = serverdata['x'], serverdata['y']
            def rebuild_2d_map(map_bytes, sizex, sizey):
                flat_array = array.array("B") 
                flat_array.frombytes(map_bytes)
                return [flat_array[i * sizex:(i + 1) * sizex] for i in range(sizey)]

            self.map = rebuild_2d_map(serverdata['map'], self.sizex, self.sizey)
            self.areainfo, self.types = rebuild_areainfo(
                base_map=self.map,
                compressed_cells=serverdata['areas']
            )
            
            self.spawn = [self.sizex // 2, 0]
            self.pos = [self.spawn[0],self.spawn[1]]
            self.current_area = 0
            
            self.ocean_indent = ocean_indent
            self.ocean = self.load_ocean(self.pos)
        def load_ocean(self, pos : list):
            ocean = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            if pos[0] == 0:
                pygame.draw.rect(ocean,BLUE,(0,0,self.ocean_indent,HEIGHT))
            if pos[0] == self.sizex - 1:
                pygame.draw.rect(ocean,BLUE,(WIDTH - self.ocean_indent,0,self.ocean_indent,HEIGHT))
            if pos[1] == 0:
                pygame.draw.rect(ocean,BLUE,(0,0,WIDTH,self.ocean_indent))
            if pos[1] == self.sizey - 1:
                pygame.draw.rect(ocean,BLUE,(0,HEIGHT - self.ocean_indent,WIDTH,self.ocean_indent))
            return ocean
        def addxy(self,l1,l2):
            return [l1[0]+l2[0],l1[1]+l2[1]]
        def move(self, direction):
            direction = [[1,0],[-1,0],[0,1],[0,-1]][direction]
            newpos = self.addxy(self.pos, direction)
            if newpos[0] >= 0 and newpos[0] < self.sizex and newpos[1] >= 0 and newpos[1] < self.sizey:
                self.pos = [newpos[0],newpos[1]]
                self.current_area = self.map[self.pos[1]][self.pos[0]]
                self.ocean = self.load_ocean(self.pos)
            else: print(f"out of bounds! {newpos}")
    
    global island
    island = None

    class Particle:
        x = 0
        y = 0
        size = [0,0]
        vel = [0,0]
        def __init__(self, size : list, colorID : tuple, areasize : tuple = (WIDTH,HEIGHT)):
            self.areasize = areasize
            self.size = size
            self.colorID = colorID
            self.randomize()
        def isInaccessible(self, inaccessibles : list = []):
            if self.x < 0 or self.x > self.areasize[0] - self.size[0] or self.y < 0 or self.y > self.areasize[1] - self.size[1]: return True
            for surface in inaccessibles:
                if self.x + self.size[0] > surface[0] and surface[0] + surface[2] > self.x and self.y + self.size[1] > surface[1] and surface[1] + surface[3] > self.y: return True
            return False
        def move(self, inaccessibles : list = [], spd : int = 1):
            self.vel = [self.vel[0] + random.randint(-spd,spd)/100, self.vel[1] + random.randint(-spd,spd)/100]
            self.x += self.vel[0]
            if self.isInaccessible(inaccessibles):
                self.x -= 2*self.vel[0]
                self.vel[0] = -self.vel[0]
            self.y += self.vel[1]
            if self.isInaccessible(inaccessibles):
                self.y -= 2*self.vel[1]
                self.vel[1] = -self.vel[1]
            if self.isInaccessible(inaccessibles): self.randomize(inaccessibles)
        def randomize(self, inaccessibles : list = []):
            searching = True
            while searching:
                self.x = random.randint(0,self.areasize[0]-self.size[0])
                self.y = random.randint(0,self.areasize[1]-self.size[1])
                if not self.isInaccessible(inaccessibles): searching = False
            self.vel = [0,0]
        def draw(self, color):
            if isinstance(color,list): color = color[self.colorID]
            if old_area in tile_areas: pygame.draw.rect(screen, color, (self.x - camera_pos[0], self.y - camera_pos[1], self.size[0], self.size[1]))
            else: pygame.draw.rect(screen, color, (self.x, self.y, self.size[0], self.size[1]))

    class SnowParticles:
        size = [0,0]
        poses = []
        def __init__(self, amount, xmax, ymax, size : int, color : tuple = (255,255,255), xmin = 0, ymin = 0, respawnindent : int = 100, maxoff : int = 30):
            self.poses = [[random.randint(xmin,xmax),random.randint(ymin-respawnindent,ymax+respawnindent),maxoff * random.choice([-1,1]),0] for _ in range(amount)] 
            self.maxoff = maxoff
            self.ymax = ymax + respawnindent
            self.ymin = ymin - respawnindent
            self.size = size
            self.color = color
        def tick(self, dT = 1/60, speed = 20):
            for i, pos in enumerate(self.poses):
                if random.randint(1,100) == 1: continue
                acc = -pos[2] * 1
                pos[3] += acc * dT
                pos[2] += pos[3] * dT
                pos[1] += speed / (abs(pos[3] or 0.01)**0.25) * dT
                if pos[1] > self.ymax: pos[1] = self.ymin
        def randomize(self, inaccessibles : list = []):
            searching = True
            while searching:
                self.x = random.randint(0,WIDTH-self.size[0])
                self.y = random.randint(0,HEIGHT-self.size[1])
                if not self.isInaccessible(inaccessibles): searching = False
            self.vel = [0,0]
        def tick_and_draw(self, colorOverride = None):
            self.tick(dT = 1/60)
            color = colorOverride or self.color
            for i, pos in enumerate(self.poses):
                pygame.draw.rect(screen, color, (pos[0] + pos[3], pos[1], self.size, self.size))

    class Egg:
        def __init__(self, pos):
            self.pos = pos
            self.size = player_size // 2
            self.image = pygame.image.load(os.path.join(ASSETS_PATH, "Egg.png"))
            self.image = pygame.transform.scale(self.image, (self.size, self.size))

        def draw(self):
            if old_area in tile_areas: screen.blit(self.image, (self.pos[0] - camera_pos[0], self.pos[1] - camera_pos[1]))
            else: screen.blit(self.image, self.pos)

    class Wildlife:
        water = {
            2: [pygame.Rect(sea_pos[0],sea_pos[1],sea_size[0],sea_size[1])],
            11: [],
        }
        for area in [0]:
            water[area] = []
            for rect, label in tilemaps[area].interactrects:
                if label == "fish": # this means the spot is water, as water is fishable ;)
                    water[area].append(rect)
        splooshTex = pygame.transform.scale(pygame.image.load(os.path.join(ASSETS_PATH, "Watersplash.png")), (player_size,player_size))
        fellInWater = False
        maxRespawnTimer = 5.0
        respawnTimer = 0

        jumpsLeft = random.randint(1,10)
        jumpCooldown = 1
        jumpDeltaTargetX = 0
        jumpDeltaX = 0
        jumpDeltaY = 0
        jumpSteps = 0
        jumpVY = 0
        frightened = False

        area_sizes = {2:(WIDTH, HEIGHT)}
        for area in [0]:
            area_sizes[area] = tilemaps[area].pixsize
        def __init__(self, location : list, size : int, tex : str, checkWater : bool = True, custom_pos : tuple = None, canPickUp : bool = False, area_size : tuple = None):
            if area_size: self.area_size = area_size
            self.pos = custom_pos or [random.randint(0,self.area_sizes[2][0]), random.randint(0,self.area_sizes[2][1])]
            self.location = location
            self.size = size
            if self.size != player_size:
                self.splooshTex = pygame.transform.scale(self.splooshTex, (self.size, self.size))
            self.checkWater = checkWater
            self.canPickUp = canPickUp
            tex_path = os.path.join(ASSETS_PATH, tex)
            if tex.endswith(".gif"):
                self.npcTexFrames = load_gif_frames(tex_path, size=(size,size))
                self.current_frame = 0
                self.frame_timer = 0
                self.frame_delay = 100
            else:
                img = pygame.image.load(tex_path)
                self.npcTex = pygame.transform.scale(img, (self.size, self.size))

            self.vel = self.randDir(100)

            if tex.startswith("chicken"):
                self.egg_timer = random.randint(600, 1200)

        def checkOnWater(self, indent, area = 0):
            ownRect = pygame.Rect(self.pos[0]+indent,self.pos[1]+indent,max(self.size-indent*2,1),max(self.size-indent*2,1))
            if area in self.water:
                return any(ownRect.colliderect(rect) for rect in self.water[area])            
        def outOfBounds(self, tolerance : int = 0):
            if self.pos[0] < -tolerance: self.pos[0] = self.area_size[0] + tolerance - 10 - self.size
            if self.pos[1] < -tolerance: self.pos[1] = self.area_size[1] + tolerance - 10 - self.size
            if self.pos[0] + self.size > self.area_size[0] + tolerance: self.pos[0] = -tolerance + 10
            if self.pos[1] + self.size > self.area_size[1] + tolerance: self.pos[1] = -tolerance + 10
        def checkOutOfBounds(self, tolerance : int, area : int = 0):
            if (
                self.pos[0] < -tolerance or
                self.pos[1] < -tolerance or
                self.pos[0] + self.size > self.area_size[0] + tolerance or
                self.pos[1] + self.size > self.area_size[1] + tolerance): return True
            return False
        
        def getRunawayVec(self, dPos : list, speed : float):
            vecLength = (dPos[0]**2 + dPos[1]**2)**0.5
            return [dPos[0]/vecLength*speed,dPos[1]/vecLength*speed]
        def getPos(self):
            return [self.pos[0] + self.jumpDeltaX, self.pos[1] + self.jumpDeltaY]
        def randDir(self,accuracy):
            a, b = 0,0
            while a == 0 or b == 0: a, b = random.randint(-accuracy,accuracy), random.randint(-accuracy,accuracy)
            c = (a*a+b*b) ** 0.5
            return [a/c,b/c]
            
        def tick(self, playerPos : list, dT : float = 1/60, area : int = None):
            if self.fellInWater:
                self.respawnTimer += dT
                if self.respawnTimer > self.maxRespawnTimer:
                    self.pos = [random.randint(self.area_size[0] // 2 - 200, self.area_size[0] // 2 + 200),random.randint(self.area_size[1] // 2 - 200, self.area_size[1] // 2 + 200)]
                    self.jumpDeltaX, self.jumpDeltaY = 0,0
                    self.jumpSteps = 0
                    self.fellInWater = False
                    self.respawnTimer = 0
            else:
                self.outOfBounds(0)

                if hasattr(self, "egg_timer") and not self.frightened:
                    self.egg_timer -= 1
                    if self.egg_timer <= 0:
                        if not self.checkOutOfBounds(-48) and (not self.checkWater or not self.checkOnWater(-10, area = area)): eggs[area].append(Egg([int(self.pos[0]), int(self.pos[1])]))
                        self.egg_timer = random.randint(600, 1200)
                
                if (self.checkWater and self.checkOnWater(30, area = area)):
                    self.fellInWater = True

                if self.vel != [0,0]:
                    if self.jumpCooldown <= 0:
                        if self.jumpSteps <= 0:
                            self.jumpSteps = 50
                            self.pos = [self.pos[0] + self.jumpDeltaX, self.pos[1] + self.jumpDeltaY]
                            self.jumpDeltaTargetX = self.vel[0]*1000
                            self.jumpDeltaX,self.jumpDeltaY = 0,0
                            self.jumpVY = self.vel[1]*1-2.5
                            self.jumpsLeft -= 1
                            
                            deltaPos = [self.pos[0]-playerPos[0],self.pos[1]-playerPos[1]]
                            if abs(deltaPos[0]) < 150 and abs(deltaPos[1]) < 150:
                                self.vel = self.getRunawayVec(deltaPos,3)
                                self.jumpsLeft = min(self.jumpsLeft+1,3)
                                self.frightened = True
                            
                            self.jumpCooldown = 0.1 if self.frightened else 1

                        else:
                            self.jumpSteps -= 1
                            self.jumpVY += 0.1
                            self.jumpDeltaX += self.vel[0]
                            self.jumpDeltaY += self.jumpVY
                        if self.jumpsLeft <= 0: 
                            self.vel = [0,0]
                            self.jumpCooldown = random.randint(10,30)
                    else: self.jumpCooldown -= dT
                else:
                    self.jumpCooldown -= 1
                    if self.jumpCooldown <= 1:
                        self.frightened = False
                        self.vel = self.randDir(100)
                        self.jumpsLeft = random.randint(1,5)
                        self.jumpCooldown = 1
                    
        def draw(self, area : int = -1, dT : float = 1/60, camera_pos : list = [0,0]):
            if (area in self.location or area == -1) and self.respawnTimer < self.maxRespawnTimer / 25:
                pos = [int(round(self.pos[0] + self.jumpDeltaX)),int(round(self.pos[1] + self.jumpDeltaY))]
                if hasattr(self, 'npcTexFrames'):
                    self.frame_timer += 1000 * dT
                    if self.frame_timer >= self.frame_delay:
                        self.current_frame = (self.current_frame + 1) % len(self.npcTexFrames)
                        self.frame_timer = 0
                    tex = self.npcTexFrames[self.current_frame]
                    tex = pygame.transform.flip(tex, True, False) if self.vel[0] < 0 else tex
                else:
                    tex = pygame.transform.flip(self.npcTex, True, False) if self.vel[0] < 0 else self.npcTex
                screen.blit(tex if not self.fellInWater else self.splooshTex, (pos[0] - camera_pos[0], pos[1] - camera_pos[1]))    
        def get_save_data(self):
            pass
    
    class ShopScreen:
        buttons = []
        buttonfont = pygame.font.Font(None, 24)
        sold_str = ["SOLD","VERKOCHT"][taal]
        locked_str = ["LOCKED","DICHT"][taal]
        def __init__(self, items : list = [], starting_state = 0, item_size : int = 64, autotranslate : bool = True):
            self.keys = []
            self.names = []
            self.prices = []
            self.imgs = []
            for name, file, price in items:
                self.keys.append(name)
                self.names.append(itemlist[name][0] if autotranslate else name)
                self.prices.append(price)
                try:
                    self.imgs.append(pygame.transform.scale(pygame.image.load(os.path.join(ASSETS_PATH,file)),(item_size,item_size)))
                except:
                    self.imgs.append(pygame.transform.scale(pygame.image.load(os.path.join(ASSETS_PATH,"Glitch.png")),(item_size,item_size)))
            self.states = [starting_state for _ in range(len(items))]

            self.item_size = item_size
            self.tick()
        def tick(self):
            self.window = pygame.Surface((WIDTH,HEIGHT),flags=pygame.SRCALPHA)
            self.window.fill((0,0,0,128))
            indent = HEIGHT // 10
            shoprect = pygame.Rect(indent,indent,WIDTH-2*indent,HEIGHT-2*indent)
            border = 10
            buttonborder = 5
            pygame.draw.rect(self.window,BLACK,(shoprect[0]-border,shoprect[1]-border,shoprect[2]+2*border,shoprect[3]+2*border),width=border)
            pygame.draw.rect(self.window,(179, 100, 45),shoprect)
            textcolor = BLACK
            for i, name in enumerate(self.names):
                x = indent + 20
                between = 40
                y = indent + (between+self.item_size)*i + 20
                border = 10
                pygame.draw.rect(self.window,BLACK,(x-border,y-border,self.item_size+2*border,self.item_size+2*border),width=border)
                self.window.blit(self.imgs[i],(x,y))

                global font
                text_surface = font.render(name, True, textcolor)
                textx = x+between//2+self.item_size+border
                self.window.blit(text_surface, (textx,y-border))

                if self.states[i] == 1:
                    buttoncolor = RED
                    buttontext = self.sold_str
                elif self.states[i] == 2:
                    buttoncolor = GREY
                    buttontext = self.locked_str
                else:
                    buttoncolor = GREEN
                    buttontext = f"€{self.prices[i]}"

                newbutton = pygame.Rect(textx,y+self.item_size//2,self.item_size*2,self.item_size//2)
                pygame.draw.rect(self.window,BLACK,newbutton,width=buttonborder)
                pygame.draw.rect(self.window,buttoncolor,(newbutton[0]+buttonborder,newbutton[1]+buttonborder,newbutton[2]-2*buttonborder,newbutton[3]-2*buttonborder))

                middle = (newbutton[0]+newbutton[2]//2,newbutton[1]+newbutton[3]//2)
                text_surface = self.buttonfont.render(buttontext, True, BLACK)
                text_rect = text_surface.get_rect(center=middle)
                self.window.blit(text_surface, text_rect)
                self.buttons.append(newbutton)
                
        def draw(self,mouse_pos,mouse_down):
            screen.blit(self.window,(0,0))
            if mouse_down:
                for i, name in enumerate(self.keys):
                    if not self.states[i] and self.buttons[i].collidepoint(mouse_pos): return name, self.prices[i]
        
        def restock_all(self):
            self.states = [0 for i in range(len(self.states))]
    
    class Bullet():
        def __init__(self, pos, vel, location, radius : int = 5):
            self.pos = pos
            self.vel = vel
            self.location = location
            self.radius = radius
            self.tolerance = 5 * self.radius
        def tick(self, dT : float = 1/60):
            self.pos = [self.pos[0] + self.vel[0] * dT, self.pos[1] + self.vel[1] * dT]

            if (
                self.pos[0] < -self.tolerance or
                self.pos[1] < -self.tolerance or
                self.pos[0] > WIDTH + self.tolerance or
                self.pos[1] > HEIGHT + self.tolerance): return True
        def draw(self, area : int = -1):
            if area == self.location or area == -1:
                pygame.draw.circle(screen, (200,0,0), self.pos, self.radius)

    class Monster():
        def __init__(self, startPos : list, location : list, texture : str, speed : int = 10, dist : int = 250):
            self.pos = startPos
            self.location = location
            self.size = player_size
            self.speed = speed
            self.dist = dist
            img = pygame.image.load(os.path.join(ASSETS_PATH, texture))
            self.texture = (pygame.transform.scale(img, (self.size, self.size)))
            self.vel = [0,0]
        def addV2Scaled(self, baseVector, addedVector, scale):
            return [baseVector[0] + addedVector[0] * scale, baseVector[1] + addedVector[1] * scale]
        def is_inside_target(self, playerPos, size):
            return (abs(playerPos[0] - self.pos[0]) < size and abs(playerPos[1] - self.pos[1]) < size)
        def tick(self, targetPos : list, area : int = 0, dT : float = 1/60):
            dPos = [targetPos[0] - self.pos[0], targetPos[1] - self.pos[1]]
            vecLength = (dPos[0]**2 + dPos[1]**2)**0.5
            dir = [dPos[0]/vecLength*self.speed,dPos[1]/vecLength*self.speed]
            scale = vecLength - self.dist
            scale = scale**0.5 * dT if scale > 0 else abs(scale)**0.5 * -dT
            oldVel = self.vel
            self.vel = self.addV2Scaled(self.vel, dir, scale)
            if abs(self.vel[0]-oldVel[0]) < 1 or abs(self.vel[1]-oldVel[1]) < 1:
                self.pos = self.addV2Scaled(self.pos, dir, dT * 0.1)
            friction = 1.1 if self.is_inside_target(targetPos,50) else 0.99
            self.vel = [self.vel[0] * friction, self.vel[1] * friction]
            self.pos = self.addV2Scaled(self.pos, self.vel, scale)

            bullets.append(Bullet([self.pos[0] + self.size // 2, self.pos[1] + self.size // 2], [dir[0] * 30, dir[1] * 30], area))

        def draw(self, area : int = -1):
            if area in self.location or area == -1:
                pos = [int(round(self.pos[0])),int(round(self.pos[1]))]
                tex = pygame.transform.flip(self.texture, True, False) if self.vel[0] < 0 else self.texture
                screen.blit(tex, pos)
    
    class LightningBolt:
        color = YELLOW
        livespan = 0.6
        timeAlive = 0
        def __init__(self,areasize):
            self.pos = [random.randint(0,areasize[0]),random.randint(0,areasize[1])]
            self.length = random.randint(25,50)
        def tick_and_draw(self, dT : float = 1/60):
            self.timeAlive += dT
            pygame.draw.rect(screen, self.color, (self.pos[0],self.pos[1],10,self.length))
            if self.timeAlive >= self.livespan / 6:
                pygame.draw.rect(screen, self.color, (self.pos[0]+10,self.pos[1]+self.length-10,15,10))
                if self.timeAlive >= self.livespan / 3:
                    pygame.draw.rect(screen, self.color, (self.pos[0]+15,self.pos[1]+self.length,10,self.length-10))
                    if self.timeAlive >= self.livespan: return True

    if data:
        try:
            romancepoints = data["romancepoints"]
            ben_mayor1 = data["ben1"]
            michael_mayor1 = data["michael1"]
            ben_mayor2 = data["ben2"]
            michael_mayor2 = data["michael2"]
            given_gift = data["givengift"]
            met_kanye1 = data["kanye1"]
            met_kanye2 = data["kanye2"]
            fixed_geluidsoverlast1 = data["geluid1"]
            fixed_geluidsoverlast2 = data["geluid2"]
            ferryquest = data["ferry"]
            electioncounter = data["e_counter"]
            election_day = data["e_day"]
            electionresult = data["e_result"]
            helped_bouncer = data["helpedbouncer"]
            given_quest = data["givenquest"]
            married = data["married"]
            apartment_has_carpet = data["carpet"]
            has_goedje = data["goedje"]
            told_about_moonfish = data["moonfish"]
            has_rod = data["rod"]
            robot_purchased = data["robot"]
            shovel_purchased = data["shovel"]
            fish_caught = data["fish"]
            fList = data["farms"]
            talked_to_tix = data["tix4"]
            has_keys = data["key"]
            talked_about_elections = data["tae"]
            finished_list = data["list"]
            perfection = data["perfection"]
            election_started = data["e_started"]
            no_stamina_system = data["no_stamina_system"]
            endgame = data["endgame"]
            visited = data["visited"]
            has_card = data["card"]
            chicken_amount = data["chickenamount"]
            cow_amount = data["cowamount"]
            snackbar_counter = data["snack"]
            startup_data = {
                "cacti":data["cacti"],
            }
            gus_available = data["gus"]
        except KeyError:
            raise KeyError ("Save data missing, outdated or corrupted: please reset your save data to {} and try again.")
    
    class Timedquest:
        item_names = {
            'easy_fish':item_translations['fish']['easy'],
            'egg':item_translations['egg'],
        }

        def __init__(self, language : int, duration : int = 2, save_data : list = False):
            self.language = language
            if save_data:
                self.isWoman, self.targetNpc, self.tag, self.targetItemKey, self.targetItem, self.message, self.questActive, self.duration, self.startingDay = save_data
            else:
                self.language = language
                self.isWoman, self.targetNpc = random.choice([(False,random.choice(['Ben','Michael'])),(True,random.choice(['Leah']))])
                self.tag = random.choice(['easy_fish','egg'])
                self.targetItemKey = random.choice(list(self.item_names[self.tag].keys()))
                self.targetItem = self.item_names[self.tag][self.targetItemKey][self.language]
                self.messages = {
                    'easy_fish':[
                        [f"{self.targetNpc} wants a {self.targetItem} for under {'her' if self.isWoman else 'his'} pillow.",f"{self.targetNpc} wil een {self.targetItem} voor onder {'haar' if self.isWoman else 'zijn'} kussen."][self.language],
                    ],
                    'egg':[
                        [f"{self.targetNpc} wants to eat an {self.targetItem} during {'her' if self.isWoman else 'his'} breakfast.",f"{self.targetNpc} wil een {self.targetItem} eten tijdens het ontbijt."][self.language],
                    ],
                }
                self.message = random.choice(self.messages[self.tag])
                self.questActive = False
                self.duration = duration
                self.startingDay = 0 
        def get_message(self, day : int = None):
            if day:
                label = ["Days left", "Dagen over"][taal]
                return self.message + f" - {label}: {self.startingDay + self.duration - day}"
            else: return self.message
        def activate(self, day : int):
            self.questActive = True
            self.startingDay = day
        def checkExpired(self, day : int):
            return (self.questActive and day >= self.startingDay + self.duration)
        def get_save_data(self):
            return [self.isWoman,self.targetNpc,self.tag,self.targetItemKey,self.targetItem,self.message,self.questActive,self.duration,self.startingDay]
    
    def get_items(item_dict : dict, current_tags = []):
            items = {}
            for index in item_dict.keys():
                content = item_dict[index]
                if isinstance(content, dict):
                    items = items | get_items(content, current_tags = current_tags + [index])
                elif isinstance(content, list):
                    items[index] = [content[taal]] + [current_tags]
            return items

    global itemlist
    itemlist = get_items(item_translations)
    del get_items
    print(itemlist)
    
    class Journal:
        tasks = []
        statuses = []
        statusStrs = [
            ['UNDONE','DONE','CLAIM'],
            ['NIET GEDAAN','GEDAAN','CLAIM']
        ][taal] 
        register = {
            'gift_leah' : ["Give Leah a gift.","Geef Leah een geschenk."][taal],
            'go_fish' : ["Go fishing.","Ga vissen."][taal],
            'find_max' : ["Find Max.","Vind Max."][taal],
            'find_card' : lambda: [f"Find a clubcard ({int(day / 25 * 100)}%)", f"Vind een clubkaart ({int(day / 25 * 100)}%)"][taal],
            'find_tixcity' : ["Find Tixcity.","Vind Tixcity."][taal],
            'find_mstore' : ["Go to Michael's store.","Ga naar de winkel van Michael."][taal],
            'found_swamp' : ["Find the swamp.","Zoek het moeras."][taal],
            'max' : ["Go to the desert.","Ga naar de woestijn."][taal],
            'find_house' : ["Find your new home in Tixcity.","Vind je nieuwe huis in Tixcity."][taal],
            'romance' : lambda: [f"Romantic progression: {int(romancepoints / 25 * 100)}%", f"Romantiek progressie: {int(romancepoints / 25 * 100)}%"][taal],
            'helped_bouncer' : ["Give Bouncer something cute.","Geef Bouncer iets schattigs."][taal],
            'gus1' : ["Talk to Gus.","Praat met Gus."][taal],
            'gus2' : ["Go south.","Ga naar het zuiden."][taal],
            'quest' : ["Give Gus a fish from his dock.","Geef Gus een vis van zijn kade."][taal],
            'key1' : ["Go to Ben.","Ga naar Ben."][taal],
            'key2' : ["Go to Michael.","Ga naar Michael."][taal],
            'key3' : ["Go to Leah.","Ga naar Leah."][taal],
            'key4' : ["Go to Max.","Ga naar Max."][taal],
            'key5' : ["From the desert, head north.","Ga vanaf de woestijn richting het noorden."][taal],
            'key6' : ["Find the old man.","Vind de oude man."][taal],
            'key7' : ["Find Max.","Vind Max."][taal],
            'key8' : ["Find the building.","Vind het gebouw."][taal],
            'kanye' : ["From Hanztown, walk west.","Loop vanaf Hanztown naar het westen en regel de toestemming."][taal],
            'geluid1' : ["Talk to Max's eastern neighbours.", "Praat met de oosterburen van Max."][taal],
            'geluid2' : ["Talk to Max.","Praat met Max."][taal],
            'find_michael' : ["Michael has moved...again. Find him.","Michael is verhuisd... opnieuw. Vind hem."][taal],
            'list1' : ["Give Kanye money for charity.","Geef geld aan Kanye voor goede doelen."][taal],
            'list2' : ["Say sorry to Michael on behalf of Earl.","Zeg namens Earl sorry tegen Michael."][taal],
            'list3' : ["Ask Gus if he has any trash.","Vraag aan Gus of hij afval heeft."][taal],
            'list4' : ["Take the trash to Earl.","Breng het afval naar Earl."][taal],
            'altar' : ["Give the altar something crimson.","Geef het altaar iets bloedroods."][taal],
            'endgame1' : ["Go to Ben.","Ga naar Ben."][taal],
            'endgame2' : ["Find the sender of the mail.","Vind de afzender van de mail."][taal],
            'election1' : ["Go to Michael about more information.","Ga naar Michael voor meer informatie."][taal],
            'election2' : ["Go to Camden County.","Ga naar Camden County."][taal],
        }
            
        def __init__(self, language : int, save_data : list = []):
            self.lang = language
            if save_data:
                self.tasks = save_data[0]
                self.statuses = save_data[1]
                self.create_timed_quest(save_data=save_data[2])
            else: self.timedquest = None
        def append(self, task : str, status : int = 0):
            if task not in self.tasks:
                self.tasks.append(task)
                self.statuses.append(status)
        def mark_done(self, task : str, customStatus : int = 1):
            if task in self.tasks:
                index = self.tasks.index(task)
                self.statuses[index] = customStatus
        def remove(self, task : str):
            if task in self.tasks:
                index = self.tasks.index(task)
                self.tasks.pop(index)
                self.statuses.pop(index)
        def remove_done(self):
            for i, r in enumerate(self.statuses):
                if r == 1:
                    self.tasks.pop(i)
                    self.statuses.pop(i)
        def get_tasks(self, day : int = None):
            r = []
            for t in self.tasks:
                if t in self.register:
                    val = self.register[t]
                    r.append(val() if callable(val) else val)
                else: r.append(t)
            if self.timedquest and self.timedquest.questActive: r.append(self.timedquest.get_message(day))
            return r
        def get_statuses(self):
            return self.statuses + ([3 if self.timedquest else 1] if self.timedquest and self.timedquest.questActive else [])
        def create_timed_quest(self, save_data = False):
            self.timedquest = Timedquest(self.lang, save_data=save_data)
        def get_timed_quest_info(self):
            instance = self.timedquest
            if instance and instance.questActive:
                return {
                    'npc' : instance.targetNpc,
                    'item_name' : instance.targetItemKey,
                    'disp_name' : instance.targetItem,
                }
        def get_save_data(self):
            return [
                self.tasks,
                self.statuses,
                self.timedquest.get_save_data() if self.timedquest else False
            ]
    
    class Inventory:
        class Item:
            def __init__(self, type : str, name : str, rarity : int = 0, count : int = 1, maxStack : int = 1, dispName : str = None, value : int = 0):
                self.type = type
                self.name = name
                self.rarity = rarity
                self.count = count
                self.maxStack = maxStack
                self.dispName = dispName if dispName else name
                self.value = value

            def can_stack_with(self, otherItem):
                return (
                    self.name == otherItem.name and
                    self.type == otherItem.type and
                    self.rarity == otherItem.rarity
                )
            def try_to_stack(self, otherItem):
                self.count += otherItem.count
                if self.count > self.maxStack:
                    rest = self.count - self.maxStack
                    self.count = self.maxStack
                    return rest
        types = {
            'fish' : {'sellable':True,'maxStack':3,'questable':True},
            'treasure' : {'sellable':True,'maxStack':16},
            'crop' : {'sellable':True,'maxStack':5},
            'egg' : {'sellable':True,'maxStack':16},
            'gift' : {'giftable':True},
            'wood' : {'sellable':True,'maxStack':64,'ferry':True},
            'ore' : {'sellable':True,'maxStack':16},
        }
        texList = {
            'fish':GREEN,
            'treasure':RED,
            'crop':LARSGROEN,
            'egg':'Egg.png',
            'gift':'Squirrel.png',
            'wood':'Tree.png',
            'ore':'Diamond_ore.png',
        }
        for i in texList.keys():
            if isinstance(texList[i],str):
                texList[i] = pygame.transform.scale(pygame.image.load(os.path.join(ASSETS_PATH, texList[i])), (20,20))
        
        size = 12
        items = [None for _ in range(12)]
        def __init__(self, lang, saveData : list = []):
            self.language = lang
            if saveData: self.items = [(self.Item(data[0],data[1],data[2],data[3],data[4],data[5],data[6])) if data else None for data in saveData]

            self.star_surfaces = [pygame.Surface((10, 10), pygame.SRCALPHA) for i in range(2)]
            colors = [WHITE,YELLOW]
            for i, s in enumerate(self.star_surfaces):
                pygame.draw.line(self.star_surfaces[i], colors[i], (0, 5), (10, 5), 2)
                pygame.draw.line(self.star_surfaces[i], colors[i], (5, 0), (5, 10), 2)

        def pickup(self, name : str, rarity : int = 0, count : int = 1, value : int = 0, dispName : str = None, type : str = None):
            if not type:
                for t in self.types.keys():
                    if t in itemlist[name][1]:
                        type = t
                        break
                if not type: raise ValueError("specified item does not have a type")
            if not dispName: dispName = itemlist[name][0]
            tags = self.types[type]
            maxStack = tags['maxStack'] if 'maxStack' in tags else 1
            addedItem = self.Item(type,name,rarity=rarity,count=count,maxStack=maxStack,dispName=dispName,value=value)
            for i, item in enumerate(self.items):
                if not item:
                    self.items[i] = self.Item(type,name,rarity=rarity,count=count,maxStack=maxStack,dispName=dispName,value=value)
                    item = self.items[i]
                    if count <= maxStack: return True
                    else:
                        item.count = maxStack
                        count -= maxStack
                elif item.can_stack_with(addedItem):
                    rest = item.try_to_stack(addedItem)
                    if rest: count = rest
                    else: return True
        def sell(self, index, all : bool = False):
            item = self.items[index]
            if item and 'sellable' in self.types[item.type] and item.count > 0:
                if all:
                    moneyGained = item.value * item.count
                    item.count = 0
                else:
                    moneyGained = item.value
                    item.count -= 1
                if item.count == 0: self.items[index] = None
                return moneyGained
            return 0
        def get_nth_appropriate_item(self, tag : str, delete : bool = False, all : bool = False, n : int = 1, amount : int = 1, check_func = None):
            found = 0
            enough = False if amount > 1 else True
            for i, item in enumerate(self.items):
                if item and check_func(item):
                    found += 1
                    if found >= n:
                        r = self.Item(item.type,item.name,item.rarity,item.count,item.maxStack,item.dispName)
                        if delete:
                            if all: self.items[i] = None
                            elif item.count >= amount:
                                item.count -= amount
                                enough = True
                                if item.count == 0: self.items[i] = None
                        if enough: return r
            return False
        def get_nth_tagged_in_itemlist(self, tag : str, delete : bool = False, all : bool = False, n : int = 1, amount : int = 1):
            return self.get_nth_appropriate_item(tag,delete,all,n,amount, check_func = lambda item: item.name in itemlist and tag in itemlist[item.name][1])
        def get_nth_tagged(self, tag : str, delete : bool = False, all : bool = False, n : int = 1, amount : int = 1):
            return self.get_nth_appropriate_item(tag,delete,all,n,amount, check_func = lambda item: tag in self.types[item.type])
        def get_nth_named(self, tag : str, delete : bool = False, all : bool = False, n : int = 1, amount : int = 1):
            return self.get_nth_appropriate_item(tag,delete,all,n,amount, check_func = lambda item: tag == item.name)
        def draw(self, mousePos, mouseDown : bool, dist : int = 20, size : int = 40, borderSize : int = 4, borderColor = GREY, orientation : str = 'right'):
            moneyGained = 0
            if orientation in ['left','right']:
                startingPoint = WIDTH - self.size * (size + dist) if orientation == 'right' else 0
                for i, item in enumerate(self.items):
                    pygame.draw.rect(screen,borderColor,(startingPoint + 10 + i * (size + dist), HEIGHT - 10 - size, size, size), width=borderSize)
                    if item:
                        type = self.types[item.type]
                        indent = 10
                        itemRect = pygame.Rect(startingPoint + 10 + i * (size + dist) + indent, HEIGHT - 10 - size + indent, size - 2*indent, size-2*indent)
                        c = self.texList[item.type] if item.type in self.texList.keys() else GREY
                        if isinstance(c,tuple):
                            pygame.draw.rect(screen,c,itemRect)
                        else: screen.blit(c,(itemRect[0],itemRect[1]))
                        if item.count > 1:
                            display_text(str(item.count),(startingPoint + i * (size + dist) + size, HEIGHT - 25), area = current_area)
                        elif item.count < 0: self.items[i] = None
                        if item.rarity:
                            places = [
                                (round(startingPoint + 10 + i * (size + dist) + 0.15 * size), round(HEIGHT - 10 - 0.65 * size)),
                                (round(startingPoint + 10 + i * (size + dist) + 0.35 * size), round(HEIGHT - 10 - 0.41 * size)),
                                (round(startingPoint + 10 + i * (size + dist) + 0.56 * size), round(HEIGHT - 10 - 0.79 * size)),
                            ]
                            for p in places: screen.blit(self.star_surfaces[item.rarity-1], p)
                        if itemRect.collidepoint(mousePos):
                            if mouseDown: moneyGained += self.sell(i,all=False)
                            text = item.dispName[0].upper() + item.dispName[1:]
                            if 'sellable' in type: text += f" | €{item.value}" if self.language else f" | €{item.value}"
                            display_text(text,(mousePos[0] - len(text) * 7, mousePos[1] - 40), area = current_area)
            return moneyGained
        def get_save_data(self):
            r = []
            for i, item in enumerate(self.items):
                if item: r.append([item.type,item.name,item.rarity,item.count,item.maxStack,item.dispName,item.value])
                else: r.append(False)
            return r
    
    class Worldmap:
        map = [
            [-1, -1,  -1, -1, -1, -1],
            [-1, -1,  5, -1,  4, -1],
            [11,  2,  0, 18,  3, 16],
            [-1, -1,  6, -1, -1, -1],
            [-1, -1, 12, -1, -1, -1],
        ]
        requirements = {
            2 : False,
            3 : False,
            5 : False,
            6 : False,
            8 : False,
            11 : False,
            16 : False,
            22 : False,
        }
        size = [len(map),len(map[0])]
        def __init__(self, save_data : dict = {}):
            self.current_pos = self.get_area_pos(0)
            if save_data: self.requirements = {key : save_data[key] for key in save_data.keys()} 
        def addxy(self,l1,l2):
            return [l1[0]+l2[0],l1[1]+l2[1]]
        def get_area_pos(self, area : int):
            for i, row in enumerate(self.map):
                if area in row: return [i,row.index(area)]
        def goto_dir(self, dir : int, area : int):
            dir = [[0,1],[0,-1],[1,0],[-1,0]][dir]
            newpos = self.addxy(self.current_pos, dir)
            for i in range(2):
                if newpos[i] >= self.size[i] or newpos[i] < 0:
                    print('out of bounds')
                    return area
            newarea = self.map[newpos[0]][newpos[1]]
            if newarea != -1 and (newarea not in self.requirements or self.requirements[newarea]):
                self.current_pos = self.get_area_pos(newarea)
                return newarea
            return area
        def area_allowed(self, area : int):
            if area == -1: return False
            for row in self.map:
                if area in row: return True
        def get_save_data(self):
            return self.requirements
    
    global camera_pos
    camera_pos = [0,0]

    class NpcText:
        screensize = (WIDTH,HEIGHT)
        messages = []
        buttons = None
        label = None
        frame = None
        obj_size = None
        obj_rect = None
        obj_pos = None
        textbox_appear_time = 40 # of zoiets
        textbox_tex = load_img_from_assets("Textbox.png").convert_alpha()
        this_textbox_tex = None
        textbox_font = font
        letter_slowness = 3
        is_talking = False
        fastforward = False
        thinking = False # do something with it
        maxcooldown = 10
        cooldown = 0
        last_campos = None
        def __init__(self):
            pass
        def decompile_first_message(self):
            message = self.messages[0]
            if type(message) == tuple:
                string, rest = message
                for key, val in rest.items():
                    if key == 'pos': self.obj_pos = val
                    elif key == 'obj_size': self.obj_size = val
                    elif key == 'spd': self.letter_slowness = val
                    elif key == 'thinking': self.thinking = val
                self.messages[0] = string
            else: self.letter_slowness = 3
        def recalc_obj(self,obj_size=None,collide_range=30):
            obj_size = obj_size or self.obj_size or 40
            print(self.last_campos)
            self.obj_rect = pygame.Rect(
                self.obj_pos[0]-collide_range-self.last_campos[0], self.obj_pos[1]+collide_range-self.last_campos[1],
                obj_size+2*collide_range, obj_size+2*collide_range
            )
            self.obj_size = None
        def set_message(self,messages:list,obj_pos,buttons:list=None,add_cam_pos=True,can_skip=True):
            if (self.messages or self.cooldown) and can_skip: return
            if type(messages) != list: messages = [messages]
            for i, message in enumerate(messages):
                if len(message) != 2: message = (message,{})
                if 'pos' not in message[1]: message[1]['pos'] = obj_pos
            if not self.messages:
                self.messages = messages
                self.decompile_first_message()
                self.frame = -self.textbox_appear_time
            else: self.messages += messages
            global camera_pos
            self.last_campos = camera_pos if add_cam_pos and camera_pos else (0,0)
            if not self.is_talking:
                self.recalc_obj()
                self.is_talking = True
        def display_message(self,ikey_pressed):
            if self.messages == [] or self.cooldown > 0:
                if self.cooldown > 0: self.cooldown -= 1
                return False
            self.frame += 2 if self.fastforward else 1
            textsize = self.textbox_font.size(self.messages[0])
            indent = (40,20)
            mintextboxsize = 50
            if self.frame < 0: textbox_size = (
                round((max(textsize[0]+indent[0],mintextboxsize)) * (1 + self.frame / self.textbox_appear_time)),
                round((textsize[1]+indent[1]) * (1 + self.frame / self.textbox_appear_time)),
            )
            else: textbox_size = (max(textsize[0]+indent[0],mintextboxsize),textsize[1]+indent[1])
            this_textbox_tex = pygame.transform.scale(self.textbox_tex,textbox_size)
            screen_edge_indent = 20
            textbox_pos = [
                min(max(self.obj_rect[0]+self.obj_rect[2]//2-this_textbox_tex.get_width()//2, screen_edge_indent),self.screensize[0]-screen_edge_indent-this_textbox_tex.get_width()),
                self.obj_rect[1]-this_textbox_tex.get_height()//2-self.obj_rect[2]
            ]
            if textbox_pos[1] < screen_edge_indent: textbox_pos[1] = self.obj_rect[0]+self.obj_rect[2]
            if self.frame >= 0:
                text_surface = self.textbox_font.render(self.messages[0][:self.frame//self.letter_slowness], True, (0,0,0))
                this_textbox_tex.blit(text_surface,(indent[0]//2,indent[1]//2))
            screen.blit(this_textbox_tex, textbox_pos)
            if ikey_pressed:
                if self.frame >= self.letter_slowness * len(self.messages[0]):
                    self.fastforward = False
                    self.frame = 0
                    self.messages.pop(0)
                    if len(self.messages) == 0:
                        self.messages = []
                        self.cooldown = self.maxcooldown
                        self.is_talking = False
                    else:
                        self.decompile_first_message()
                        self.recalc_obj()
                else: self.fastforward = True
    npctext = NpcText()

    global key_items
    if data:
        journal = Journal(taal, data["journal"])
        inventory = Inventory(taal, data["inventory"])
        worldmap = Worldmap({int(k): v for k, v in data["map"].items()})
    else:
        journal = Journal(taal)
        inventory = Inventory(taal)
        worldmap = Worldmap()
    key_items = set()

    farms = []
    counter = 0
    for x in range(100,WIDTH-100,150):
        for y in range(100,HEIGHT-100,150):
            if data and counter < len(flist): farms.append(Farmland(x,y,language=taal,custom=fList[counter]))
            else: farms.append(Farmland(x,y,language=taal))
            counter += 1
    
    #MOKETDML
    DIALOOG_BEN1 = [ 
        ["We are colleagues, not friends.", "Is the wood gone yet?", "I don't have time to talk..."],
        ["We zijn collega's, geen vrienden.", "Is het hout al weg?", "Ik heb geen tijd om te praten..."]
    ][taal]
    DIALOOG_BEN2 = [
        [f"Hello {name}! Nice weather, don't you think?", "The village is starting to flourish!", "I used to be a cattle farmer.", "Did you know that people are more likely to tell secrets to good fishermen...?", "Have you been to Tixcity yet? Follow the road north."],
        [f"Hallo {name}! Mooi weertje, vind je ook niet?", "Het dorp begint steeds meer te bloeien!", "Vroeger was ik veehouder.", "Wist je dat mensen vaker geheimen zullen vertellen aan goede vissers...?", "Ben je al in Tixcity geweest? Volg de weg naar het noorden."]
    ][taal]
    DIALOOG_BEN3 = DIALOOG_BEN2 + [
        [f"There's my good friend {name}!", "Hey buddy! How are you?"],
        [f"Daar is mijn goede vriend {name}!", "Hey makker! Hoe gaat het?"]
    ][taal]
    DIALOOG_LEAH1 = [
        ["The shop is closed, but you can always stop by for a chat."],
        ["De winkel is gesloten, maar je mag altijd een praatje maken."]
    ][taal]
    DIALOOG_LEAH2 = [
        ["Hello, how are you? I see you have done a lot for our community."],
        ["Hallo, hoe gaat het? Ik zie dat je al erg veel hebt gedaan voor onze gemeenschap."]
    ][taal]
    DIALOOG_LEAH3 = DIALOOG_LEAH2 + [
        ["You are really nice!"],
        ["Jij bent echt aardig!"]
    ][taal]
    DIALOOG_MAX = [
        "Jy het nog nooit 'n dwerg gesien nie, het jy?", "Eendag sal jy my moet vertel van die diere wat jy 'hoender' noem."
    ]
    #DIALOOG_MICHAEL1 = [
        #["Before you moved here, an old man did your job! I'm glad he's finally retired, but I do miss him.", "Business is good, so I'm not selling anything new right now.", "My full name is Michael John Reiziger, cool huh?"],
        #["Voordat jij hier kwam wonen, deed een oude man jouw taak! Ik ben blij dat hij eindelijk met pensioen is, maar ik mis hem wel.", "De zaken gaan goed, daarom verkoop ik nu even niks nieuws.", "Mijn volledige naam is Michael John Reiziger, cool toch?"]
    #][taal]
    #DIALOOG_MICHAEL2 = [
        #["How do you like your new devices?", "I am part of YKS Megacorp, a large company."],
        #["Hoe bevallen je nieuwe apparaten?", "Ik ben onderdeel van YKS Megacorp, een groot bedrijf."],
    #][taal]
    #DIALOOG_MICHAEL3 = [
        #["I'm glad the Secret Service sent me to this place... you didn't hear that."],
        #["Ik ben blij dat de geheime dienst mij naar deze plek heeft gestuurd... dat hoorde je niet."]
    #][taal]

    #Ontwikkel npc's
    ben = Npc("Ben", ["Ben.png"], [0,19], [100,100], schedule=ben_schedule, speed=1)
    michael = Npc("Michael", ["Michael1.png","Michael2.png"], [0,2,11,20])
    tix = Npc("Tix", ["Tix.png"], [0,1,4], pos=tix_pos)
    african_flag = Npc("african_flag", ["African_flag.png"], 3, pos=(240,192))
    bouncer = Npc("Bouncer", ["Bouncer.png"], [0,5,6,10])
    ladder = Npc("Ladder", ["Ladder.png"], 5)
    gus = Npc("Gus",["Gus.png"], 1, pos=(148,532))
    leah = Npc("Leah", ["Leah1.png","leah2.png"], [0,21], pos = (100,100))
    ed = Npc("Ed", ["Ed.png"], 8, pos=(100,100))
    mailbox = Npc("Mail", ["Mailbox1.png","Mailbox2.png"], [0,21], pos= (820,820))
    max_npc = Npc("Max", ["Max1.png","Max2.png"], [2,3], pos=(720,240))
    joy = Npc("Joy", ["Joy.png"], 11, pos=(100,100))
    randy = Npc("Randy", ["Randy.png"], 11, pos=max_pos)
    carpet = Npc("carpet", ["Carpet.png"], 7, pos=CENTER)
    altar = Npc("altar", ["Altar.png"], 14, pos=CENTER)
    kanye = Npc("Kanye", ["Kanye.png"], 11, pos=CENTER)
    earl = Npc("Earl", ["Earl.png"], 11, pos=earl_pos)
    tommycash = Npc("Tommy", ["Tommy.png"], 16, pos=tix_pos)
    metakunst = Npc("Meta-Kunstenaar", ["Metakunst.png"], 17, pos=tix_pos)
    fman = Npc("The Ferryman", ["Fman.png"], [12,13], pos=(336, 960))
    mia = Npc("Mia", ["Mia.png"], 14, pos=(WIDTH // 2, (HEIGHT + player_size) // 2 + 60))
    mscoffi = Npc("Ms. Coffi", ["Mscoffi.png"], 21, pos=tix_pos)

    npcs = [ben, michael, tix, african_flag, bouncer, gus, leah, ed, mailbox, max_npc, joy, randy, carpet, altar, kanye, earl, tommycash, metakunst, fman, mia, mscoffi]

    shops = {
        'michael': ShopScreen([('robot','Robot.png',robot['cost']),('shovel','Shovel.png',shovel_cost)],starting_state=2),
        'coffee': ShopScreen([('coffee','Coffee.png',50)]),
    }
    #random_person = QuestlineNpc("???", CENTER, ["bouncer.png"], 0, [
        #("name",["I need wood.", "Ik heb hout nodig."][taal],"wood",True,pygame.K_1),
        #("reward",["Thanks.", "Bedankt."][taal],100),
        #("wait",["Give me a moment...", "Geef me even een momentje..."][taal],1),
        #("tag",["I need fish", "Ik heb vis nodig."][taal],"fish",True,pygame.K_1),
        #("reward",["Thank you.", "Bedankt."][taal])
    #])
    simple_npcs = [
        SInteract("Max", ["Max1.png"], 3, pos=(100,100), defaultMessages="Max: Almal hier word Max genoem!"),
        SInteract("Max", ["Max1.png"], 3, pos=CENTER, defaultMessages="Max: Jy lyk besonders!"),
        SInteract("Max", ["Max1.png"], 3, pos=tix_pos, defaultMessages="Max: Ek is mal oor my kultuur!"),
        SInteract("Max", ["Max1.png"], 3, pos=earl_pos, defaultMessages="Max: Ek is koud."),
    ]

    if data: altar.spokento = data["altar"]

    wildlife = []
    monsters = []
    bullets = []
    bolts = []
    
    for _ in range(10):
        wildlife.append(Wildlife([0], player_size, "Squirrel.png", canPickUp=True, area_size=(tilemaps[0].pixsize if 0 in tilemaps else (WIDTH,HEIGHT))))
    for _ in range(chicken_amount):
        wildlife.append(Wildlife([0,2,9,11], random.randint(32,64), "Chicken.gif",area_size=(tilemaps[0].pixsize if 0 in tilemaps else (WIDTH,HEIGHT))))
    for _ in range(cow_amount):
        wildlife.append(Wildlife([0,2,9,11], player_size, "Cow.png",area_size=(tilemaps[0].pixsize if 0 in tilemaps else (WIDTH,HEIGHT))))
    particles = []
    bog_islands = []
    start_area_size = tilemaps[current_area].pixsize if current_area in tilemaps.keys() else (WIDTH,HEIGHT)
    for i in range(100):
        particles.append(Particle([16,16], (1 if i > 88 else 0), areasize=start_area_size))
        bog_islands.append(Particle([64,48],BROWN))
        bog_islands.append(Particle([48,64],BROWN))
    
    snow_particles = SnowParticles(100, WIDTH, HEIGHT, size = 10)

    #Mails
    global mail
    mail = {
        -1 : ["If you give a squirrel to someone of the opposite sex in Hanztown, it is a marriage proposal. Greetings, YKS Dating.","Als je iemand van het tegenovergestelde geslacht in Hanztown een eekhoorn geeft, dan is dat een huwelijksaanzoek. Groetjes, YKS Daten."][taal],
        -2 : ["I would like to talk to you. Greetings, Gustavo.","Ik wil graag met je praten. Groetjes, Gustavo."][taal],
        -3 : "Leah het vir jou 'n nuwe huis in Tixcity gekoop. Ek is jou verhuurder. Groete, Max.",
        -4 : ["You can now make your home beautiful with me. Greetings, Gus.","Je kan nu je huis mooi maken bij mij. Groetjes, Gus."][taal],
        -5 : ["Experts are predicting a jelly upsurge today at the dock. Don't miss out!","Experts voorspellen een grote hoeveelheid kwallen vandaag bij de kade. Mis het niet!"][taal],
        -6 : ["Gus is a criminal... go to Ben.","Gus is een crimineel... ga naar Ben."][taal],
        -7 : ["You will now participate in the elections of Camden County.","Je zal nu deelnemen aan de verkiezingen van Camden County."][taal],
        -8 : ["You won the elections.","Je hebt de verkiezingen gewonnen."][taal],
        -9 : ["You lost the elections.","Je hebt de verkiezingen verloren."][taal],
        -10 : ["Go to the snack bar today to vote.","Kom vandaag naar de snackbar om te stemmen."][taal],
         6 : ["Tixcity is now open.","Tixcity is nu geopend."][taal],
         8 : ["A robot is now available! Greetings, Michael.","Een robot is vanaf nu beschikbaar! Groetjes, Michael."][taal],
         9 : ["There's a festival tomorrow! Greetings, Michael.","Morgen is er een festival! Groetjes, Michael."][taal],
        11 : ["According to experts, fog appears every 12 days. Greetings, YKS Weather.","Er verschijnt volgens experts iedere 12 dagen mist. Groetjes, YKS Weer."][taal],
        12 : ["I have developed and released dangerous fish species. I am sure Michael will pay a lot for it. Greetings, Tix.","Ik heb gevaarlijke vissoorten ontwikkeld en vrijgelaten. Michael zal er vast veel voor betalen. Groetjes, Tix."][taal],
        13 : ["The Supershovel is now available! Greetings, Michael.","De Superschep is vanaf nu beschikbaar! Groetjes, Michael."][taal],
        18 : "Volg die paadjie oos... groete, Max.", 
        19 : [["The Legend has appeared...","There's a festival again tomorrow! Greetings, Michael."],["De Legende is nu beschikbaar...","Morgen is er weer een festival! Groetjes, Michael."]][taal],
        28 : ["Tomorrow there will be elections between Ben and Michael. Greetings, YKS Democracy.","Morgen zijn er verkiezingen tussen Ben en Michael. Groetjes, YKS Democratie."][taal],
        35 : ["Fun fact: The Supershovel can also be used as a hoe. Greetings, YKS Weather.","Leuk weetje: De Superschep kun je ook gebruiken als schoffel. Groetjes, YKS Weer."][taal],
        40 : "Kom na die woestyn... groete, Max",
        50 : "My ore gaan dood hier, kom gou!",
        59 : ["There will be a concert tomorrow morning.","Er is morgenochtend een concert."][taal]
    }

    global daily_mods, jelly
    daily_mods = []
    jelly = []

    def is_in_range(playerPos, npcPos):
        return (abs(playerPos[0] - npcPos[0]) < 50 and abs(playerPos[1] - npcPos[1]) < 50)
    
    def is_interacting(playerPos : list, npc : Npc, area : int, keyPressed : bool = True):
        if isinstance(npc.location,list): check = (area in npc.location)
        else: check = (area == npc.location)
        return (is_in_range(playerPos, npc.pos) and keyPressed and check)

    def new_day(saveData = []):
        events.append('newday')
        global current_minigame
        current_minigame = None
        global npc_text, npc_text_timer, accumulated_money, current_time, michael_on_cooldown, leah_on_cooldown, romancepoints, given_gift, game_time_minutes, day, gus_available, journal, last_tree_day, election_day

        global election_day, election_started, electioncounter, ben_mayor1, ben_mayor2, michael_mayor1, michael_mayor2
        if election_day == 1: election_day += 1
        if election_started and electioncounter < 2: 
            electioncounter += 1
            if electioncounter == 1: journal.append('election2')
        
        while not ('day_data' in server_data.keys() and server_data['day_data']['day'] == day): clock.tick(FPS)
        
        global daily_mods
        daily_mods = server_data['day_data']['mods']
        if 'jelly' in daily_mods:
            global jelly
            jelly = {
                6 : [(random.randint(0,WIDTH),random.randint(0,HEIGHT),random.randint(1,100)) for _ in range(5)],
                12 : [(random.randint(0,WIDTH),random.randint(0,HEIGHT),random.randint(1,100)) for _ in range(50)]
            }
        global day_str
        day_str = [
            ['Mon','Ma'],
            ['Tue','Di'],
            ['Wed','Wo'],
            ['Thu','Do'],
            ['Fri','Vr'],
            ['Sat','Za'],
            ['Sun','Zo'],
        ][(day-1)%7][taal] + '. ' + str((day-1)%28+1)

        global deleted_trees
        deleted_trees = []
        global trees
        trees = server_data['day_data']['trees']
        for i in trees.keys():
            trees[i] = (trees[i][0]*tree_size,trees[i][1]*tree_size)
        michael_on_cooldown = False
        leah_on_cooldown = False
        fman.spokento = False

        #random_person.check_quest_overnight()

        global has_bait
        has_bait = False

        if day >= 8: shops['michael'].states[0] = (1 if robot_purchased else 0)
        if day >= 13: shops['michael'].states[1] = (1 if shovel_purchased else 0)
        shops['michael'].tick()
        if (finished_list[1] and not finished_list[2]) or (has_keys[1] and not michael_on_cooldown) or day in {1,5,10,20,28,29,30} or (electioncounter == 1 and not talked_about_elections[1]) or (perfection and not election_started): robot["should_draw"] = False

        shops['coffee'].restock_all()

        effects.tick_days()
        
        global money, has_card
        if has_card and money >= minimum_gus:
            gus_available = True
            worldmap.requirements[6] = True
        if helped_bouncer and border_open and electioncounter == 3: worldmap.requirements[11] = True

        if day >= 50: worldmap.requirements[16] = True
        if has_card: worldmap.requirements[1] = True
        if day >= 18: worldmap.requirements[3] = True
        if day >= 6: worldmap.requirements[5] = True
        if shovel_purchased: worldmap.requirements[2] = True

        if electioncounter >= 2:
            election_day = 1
        
        journal.remove_done()
        if not saveData and day > 5 and day not in {10,20,30} and not journal.timedquest and not random.randint(0,9):
            journal.create_timed_quest()
        if journal.timedquest and journal.timedquest.checkExpired(day):
            journal.timedquest = None

        ben.messageOverride = ""
        if day in {10,20}: ben.messageOverride = ["Ben: Tix is a very good player. You try to beat him!","Ben: Tix is een erg goede speler. Probeer jij hem maar te verslaan!"][taal]
        elif day > 25 and shovel_purchased and 2 not in visited: ben.messageOverride = ["Ben: There's a cold wind coming from the west...","Ben: Er komt koude wind uit het westen..."][taal]
        if ben.messageOverride: ben_message = ben.messageOverride
        global claimed_tree_money
        claimed_tree_money = False

        cacti_generated = 0 if saveData or len(cacti) > 30 else 10
        if helped_bouncer:
            michael.location = 11
            michael.pos = CENTER
            if 11 not in visited: michael.messageOverride = ["Snowfall was too cold for me. I already found a job here in the bar.","Snowfall was te koud voor mij. Ik heb hier al een baantje gevonden in de bar."][taal]
        elif 2 in visited:
            michael.location = 2
            michael.pos = CENTER
        else:
            michael.location = 20
            michael.pos = (100,100)
        if married and not day % 4:
            leah.location = 7
            leah.pos = max_pos
        else:
            leah.location = 21
            leah.pos = (100,100)
        if day == 59:
            bouncer.location = [0]
            bouncer.pos = (500,500)
        if married and has_card:
            bouncer.location = 6
            bouncer.pos = (240,480)
        else:
            bouncer.location = [5,10]
            bouncer.pos = tix_pos

        global island
        if 'island' in server_data['day_data']:
            island = Island(server_data['day_data']['island'])
        else:
            island = None

        money_gained = 0 if saveData else 20
        if game_time_minutes >= 1440:
            accumulated_money += money_gained // 2
        else:
            accumulated_money += money_gained
        game_time_minutes = 360
        
        global last_tick_time, new_tick
        new_tick = pygame.time.get_ticks()
        last_tick_time = new_tick
        
        if saveData and day != 1:
            generate_cacti(saveData["cacti"])
        elif cacti_generated != 0:
            generate_cacti(10)  

        global mail_content, gift_available
        mail_content = []
        def check_and_delete_mail(index):
            global mail_content, mail
            if index in mail.keys():
                mail_content.append("Mail: " + mail[index])
                del mail[index]
        
        if 'jelly' in daily_mods:
            mail_content.append("Mail: " + mail[-5])
        if journal.timedquest and not journal.timedquest.questActive:
            mail_content.append([f"Mail: {journal.timedquest.message}",'timedquest'])
        if romancepoints >= 25 and not married:
            check_and_delete_mail(-1)
            if not given_gift:
                gift_available = True
                journal.append('gift_leah')
                journal.remove('romance')
        if gus_available and married and not given_quest: 
            check_and_delete_mail(-2)
            if 6 not in visited:
                journal.append('gus1')
        if married and day >= 6 and 7 not in visited: 
            check_and_delete_mail(-3)
            journal.append('find_house')
        if given_quest and not apartment_has_carpet:
            check_and_delete_mail(-4)
        if day in mail.keys():
            if isinstance(mail[day],list): mail_content += ["Mail: " + m for m in mail[day]]
            else: mail_content.append("Mail: " + mail[day])
        if worldmap.requirements[8] and not perfection:
            check_and_delete_mail(-6)
            journal.append('endgame1')
        if perfection and electioncounter < 1:
            check_and_delete_mail(-7)
            journal.append('election1')
        if electioncounter == 2 and electionresult >= 3:
            check_and_delete_mail(-8)
            electioncounter = 3
        if electioncounter == 2 and electionresult < 3:
            check_and_delete_mail(-9)
        if election_day == 2: 
            check_and_delete_mail(-10)
            ben_mayor1 = False
            michael_mayor1 = False

        global oParticles, oBG
        sDay = (day-1)%(28*4)
        if sDay < 28:
            oParticles = [LARSGROEN,YELLOW]
            oBG = (60, 210, 60)
        elif sDay < 28*2: 
            oParticles = [LARSGROEN,PURPLE]
            oBG = (130,220,40)
        elif sDay < 28*3:
            oParticles = [BROWN,BROWN]
            oBG = (255,150,0)
        elif sDay < 28*4: 
            oParticles = [WHITE,WHITE]
            oBG = (80,180,80)
        else:
            oParticles = [LARSGROEN,YELLOW]
            oBG = (60, 210, 60)
    
        fList = []
        for f in farms:
            fList.append(f.getSaveData())
        global snackbar_counter
        data = {
            "name": name,
            "romancepoints": romancepoints,
            "ben1": ben_mayor1,
            "michael1": michael_mayor1,
            "ben2": ben_mayor2,
            "michael2": michael_mayor2,
            "givengift": given_gift,
            "kanye1": met_kanye1,
            "kanye2": met_kanye2,
            "geluid1": fixed_geluidsoverlast1,
            "geluid2": fixed_geluidsoverlast2,
            "altar": altar.spokento,
            "ferry": ferryquest,
            "e_counter": electioncounter,
            "e_day": election_day,
            "e_result": electionresult,
            "helpedbouncer": helped_bouncer,
            "givenquest": given_quest,
            "key": has_keys,
            "tae": talked_about_elections,
            "list": finished_list,
            "perfection": perfection,
            "e_started": election_started,
            "no_stamina_system": no_stamina_system,
            "endgame": endgame,
            "married": married,
            "carpet": apartment_has_carpet,
            "goedje": has_goedje,
            "moonfish": told_about_moonfish,
            "rod": has_rod,
            "robot": robot_purchased,
            "shovel": shovel_purchased,
            "fish": fish_caught,
            "tix4": talked_to_tix,
            "visited": visited,
            "card": has_card,
            "chickenamount": chicken_amount,
            "cowamount": cow_amount,
            "snack": snackbar_counter,
            "cacti": len(cacti),
            "gus": gus_available,
            "journal": journal.get_save_data(),
            "inventory": inventory.get_save_data(),
            "map": worldmap.get_save_data(),
            "farms": fList
        }
        events.append(['save',data])
        if snackbar_counter and snackbar_counter < 3: snackbar_counter += 1
        """
        BASE_PATH = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(BASE_PATH, "data.json")
        try:
            with open(json_path, "w") as json_file:
                json.dump(data, json_file, indent=4)
        except IOError as e:
            print(f"Error writing to file: {e}")
        """
        
    def chop_tree(player_pos, tree_pos, tree_size):
        px, py = player_pos
        tx, ty = tree_pos
        enlarged_tree_size = tree_size + 1.5  
        return abs(px - tx) < enlarged_tree_size and abs(py - ty) < enlarged_tree_size
    def chop_cactus(player_pos, cactus_pos, cactus_size):
        px, py = player_pos
        cx, cy = cactus_pos["x"], cactus_pos["y"]
        enlarged_cactus_size = cactus_size + 1.5  
        return abs(px - cx) < enlarged_cactus_size and abs(py - cy) < enlarged_cactus_size
    
    def fishing_game():
        global trees, npc_text, npc_text_timer, fishing_timer, card_available, has_card, fish, has_quest, quest_available, current_area
        
        if npctext.is_talking: return False

        if day == 25 and not has_card and card_available:
            npctext.set_message((["I fished out a club card of something.","Ik heb een clubkaart van iets opgevist."][taal],{'thinking':True}),player_pos,can_skip=False)
            journal.mark_done('go_fish')
            journal.mark_done('find_card')
            has_card = True
            card_available = False
        else:
            if random.randint(0,63):
                global current_minigame, has_bait
                current_minigame = FishingGame(day,language=taal,area=current_area,bar=(100 if has_bait else 80))
                has_bait = False
                if quest_available and current_area == 6: 
                    has_quest = True
                    quest_available = False
            else:
                global accumulated_money
                accumulated_money += 15
                npctext.set_message((["I fished up some algae. Michael, out of pity, gave me €15 for it.","Ik heb algen opgevist. Michael gaf me er, uit medelijden, €15 voor."][taal],{'thinking':True}),player_pos,can_skip=False)
        time.sleep(3)

    def show_start_screen():
        global screen, BLACK, WHITE
        screen.fill(BLACK)

        messages = [
            ["Press 'E' to interact, 'J' for logbook, 'C' to chat, arrows to walk,",
            "press '1/2(/3)' to choose, and 'Esc' to quit!"],
            ["Druk op 'E' voor interactie, 'J' voor logboek, 'C' om te chatten, pijltjes om te lopen,",
            "gebruik '1/2(/3)' bij keuzes en 'Esc' om af te sluiten!"]
        ][taal]

        font_size = 36
        spacing = 40
        start_y = HEIGHT // 2 - spacing

        for i, line in enumerate(messages):
            rendered = font.render(line, True, WHITE)
            rect = rendered.get_rect(center=(WIDTH // 2, start_y + i * spacing))
            screen.blit(rendered, rect)

        pygame.display.flip()
        pygame.time.wait(6000)
    def show_largecredits():
        global screen, BLACK, WHITE
        screen.fill(BLACK)
        
        texts = [
            ["Based on the idea of: Dimitri Varetidis.", "Created by: Dimitri Varetidis & Marsu1038.", "Team leader: Dimitri Varetidis (2024-2026) & Marsu1038 (2026-).", "Multiplayer: Marsu1038.", "Translations: Dimitri Varetidis.", "Thank you for playing! :)"],
            ["Naar idee van: Dimitri Varetidis.", "Gemaakt door: Dimitri Varetidis & Marsu1038.", "Teamleider: Dimitri Varetidis (2024-2026) & Marsu1038 (2026-).", "Multiplayer: Marsu1038.", "Vertalingen: Dimitri Varetidis.", "Bedankt voor het spelen! :)"]
        ][taal]

        start_y = HEIGHT // 2 - (len(texts) * 30) // 2 

        for i, line in enumerate(texts):
            text_surface = font.render(line, True, WHITE)
            text_rect = text_surface.get_rect(center=(WIDTH // 2, start_y + i * 40))  
            screen.blit(text_surface, text_rect)

        pygame.display.flip()
        pygame.time.wait(6000)
    def show_backstory(dialogue, wait_time=10000):
        if type(dialogue) == str: dialogue = [dialogue]
        global screen, BLACK, WHITE
        screen.fill(BLACK)

        start_y = HEIGHT // 2 - (len(dialogue) * 30) // 2 
        for i, line in enumerate(dialogue):
            text_surface = font.render(line, True, WHITE)
            text_rect = text_surface.get_rect(center=(WIDTH // 2, start_y + i * 40))  
            screen.blit(text_surface, text_rect)

        pygame.display.flip()
        pygame.time.wait(wait_time)

    if name != "Marsu":
        show_start_screen()
        if day == 1: show_backstory([
            [
                "You are an apprentice to a physician at a renowned university.",
                "The pressure of study, discipline, and duty becomes unbearable.",
                "One night, you leave the city and travel by cart and river toward the remote settlement of Hanztown.",
                "There, you find honest work as a lumberjack, far from scholars, sermons, and expectations."
            ],
            [
                "Je bent leerling van een geneesheer aan een gerenommeerde universiteit.",
                "De druk van studie, discipline en plicht wordt ondraaglijk.",
                "Op een nacht verlaat je de stad en reis je per kar en rivier richting de afgelegen nederzetting Hanztown.",
                "Daar vind je eerlijk werk als houthakker, ver weg van geleerden, preken en verwachtingen."
            ]
        ][taal])
        
    if data: new_day(saveData=startup_data)
    else: new_day()

    in_cutscene = False
    area_size = (WIDTH, HEIGHT)

    running = True
    global should_draw_frame
    should_draw_frame = True

    in_shop = False
    pause_menu_open = False
    keybinds_open = False
    selected_keybind = -1
    not_waiting_for_key = True

    tp_cooldown = 0

    npctext.set_message([("Muhahahaha",{'spd':7}),"Ik ben de gemene tekstbox","Nou doei"],player_pos)
    
    while running:
        current_time = pygame.time.get_ticks()
        should_draw_frame = True
        old_area = current_area

        interacted_npcs = []
        camera_pos = []

        for npc in npcs:
            npc.update_target(game_time_minutes)
            npc.move()
        
        screen.fill(all_area_info[current_area].background)
        #if current_area in inside_areas: screen.fill(BLACK)
        #else: screen.fill((173, 216, 230))
        light_rects = []

        interacted_strings = set()

        if 'player_speed' in server_data:
            player_speed = server_data['player_speed'] * 60
        else:
            player_speed = 300
            
        chat_message = ""
        chat_display_time = 0
        
        keys = pygame.key.get_pressed()
        interact_key_just_pressed = False
        
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if not not_waiting_for_key: not_waiting_for_key = event.key
                if event.key == pygame.K_ESCAPE and not in_shop:
                    if keybinds_open: keybinds_open = False
                    else: pause_menu_open = not pause_menu_open
                if event.key == controls[4] and not pause_menu_open:
                    interact_key_down = True
                    interact_key_just_pressed = True
                if event.key == controls[5] and not pause_menu_open:
                    journal_open = not journal_open
                if event.key == pygame.K_p and electioncounter == 3:
                    open_law_editor()
                if event.key == controls[6] and not pause_menu_open:
                    chat_message = enter_text(["Say something:","Zeg iets:"][taal],can_exit=True)
                    if chat_message:
                        if chat_message.startswith('/'):
                            command = chat_message[1:].split()
                            command = [(int(c) if c.isdigit() else c) for c in command]
                            if command[0] == 'give' and len(command) in {2,3}:
                                if command[1] in itemlist.keys():
                                    inventory.pickup(name = command[1], dispName = None, count = command[2] if len(command) == 3 else 1)
                            elif command[0] == 'money' and len(command) == 2 and isinstance(command[1], int):
                                accumulated_money += command[1]
                            elif command[0] == 'access' and len(command) == 2 and isinstance(command[1], int):
                                if command[1] in worldmap.requirements:
                                    worldmap.requirements[command[1]] = True
                                else: print("'access' is not a valid command for this area.")
                            elif command[0] == 'remove' and len(command) == 2 and isinstance(command[1], str):
                                if command[1] == 'chickens': chicken_amount = 0
                                else: print("You can't remove this entity or it doesn't exist.")
                            elif command[0] == 'tp' and len(command) == 2 and isinstance(command[1], int):
                                if command[1] >= 0:
                                    current_area = command[1]
                                    tp_cooldown = 30
                                    if current_area not in scrolling_areas: camera_pos = []
                                    play_music(current_area)
                                else:
                                    print("invalid area")
                            elif command[0] == 'card':
                                has_card = True
                            elif command[0] == 'tix':
                                npc_text = ["Tix: I am here if you need me.","Tix: Ik ben hier als je me nodig hebt."][taal]
                                npc_text_timer = current_time + 5000
                            else:
                                print("command not recognized")
                        else:
                            events.append(["chat", chat_message])
            if event.type == pygame.KEYUP:
                if event.key == controls[4]:
                    interact_key_down = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_down = True
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    mouse_down = False
        
        if pause_menu_open: interact_key_down = False

        old_player_pos = [player_pos[0],player_pos[1]]
        player_screen_pos = []
        player_moved = False

        total_mod = controls_modifier * min(last_frame_time,0.05)
        if effects.check_for_effect('energetic'): total_mod *= 1.2

        if not in_cutscene and not pause_menu_open: 
            player_pos = list(player_pos)
            if (keys[pygame.K_LEFT] or keys[controls[3]]):
                player_pos[0] -= round(player_speed * total_mod)
                player_img = "Player1.png"
            if (keys[pygame.K_RIGHT] or keys[controls[2]]):
                player_pos[0] += round(player_speed * total_mod)
                player_img = "Player1.png"
            if (keys[pygame.K_UP] or keys[controls[0]]):
                player_pos[1] -= round(player_speed * total_mod)
                player_img = "Chicken.gif"
            if (keys[pygame.K_DOWN] or keys[controls[1]]):
                player_pos[1] += round(player_speed * total_mod)
                player_img = "Chicken.gif"
            player_moved = (old_player_pos != player_pos)
            if player_moved and random.randint(1,round(20 / last_frame_time)) == 1 and not has_bait:
                has_bait = True
                if has_rod and name != 'Dimitri': 
                    npctext.set_message((["I found a piece of bait! It'll decrease fishing difficulty if I use it today.","Ik heb een stuk aas gevonden! Die zal vandaag het vissen gemakkelijker maken."][taal],{'thinking':True}),player_pos,can_skip=False)

        if current_area in eggs.keys():
            for egg in eggs[current_area][:]:
                egg_rect = pygame.Rect(egg.pos[0], egg.pos[1], egg.size, egg.size)
                player_rect = pygame.Rect(player_pos[0], player_pos[1], player_size, player_size)
                if player_rect.colliderect(egg_rect) and interact_key_down:
                    rarity = random.choices([0,1,2], weights=[75,20,5])[0]
                    reward = [30,40,50][rarity]
                    if not inventory.pickup('egg',rarity,value=reward,dispName=['egg','ei'][taal]): pass
                    npctext.set_message((["I found an egg!", "Ik heb een ei gevonden!" ][taal],{'thinking':True}),player_pos,can_skip=False)
                    eggs[current_area].remove(egg)
        
        if current_area in tile_areas:
            area_size = tilemaps[current_area].pixsize
            camera_pos = (max(min(player_pos[0] + (player_size - WIDTH) // 2, area_size[0] - WIDTH), 0), max(min(player_pos[1] + (player_size - HEIGHT) // 2, area_size[1] - HEIGHT), 0))

            camera_pos = (camera_pos[0]-tilemaps[current_area].standard_offset[0],camera_pos[1]-tilemaps[current_area].standard_offset[1])
            player_screen_pos = [player_pos[0] - camera_pos[0],player_pos[1] - camera_pos[1]]
            camera_offset = [-camera_pos[0],-camera_pos[1]]
            screen.blit(tilemaps[current_area].bgimg, camera_offset)
            screen.blit(tilemaps[current_area].season_layers[((day-1) // 28) % 4], camera_offset)

            tilemaps[current_area].tick_animations()
            for index in tilemaps[current_area].animated_layers.keys():
                current_frame, frames = tilemaps[current_area].animated_layers[index][1:]
                screen.blit(frames[current_frame], camera_offset)

        if old_area == 1: #Tixheadquarters
            if not endgame[1] or endgame[2]: tix.draw(current_area)
            if not perfection: gus.draw(current_area)

            def gokautomaat(bet):
                global accumulated_money

                font = pygame.font.Font(None, 36)

                symbols = ["K", "P", "M1", "R", "N", "M2", "D", "S"]
                symbol_colors = [RED, YELLOW, WHITE, BLUE, GREEN, GREEN, BLUE, PURPLE]

                multipliers = {
                    "P": 5,
                    "M1": 30,
                    "R": 80,
                    "N": 120,
                    "M2": 200,
                    "K": 500,
                    "D": 1000,
                    "S": 2500
                }

                slots = ["", "", ""]
                result_message = ""

                def spin_slots():
                    return [random.choice(symbols) for _ in range(3)]

                def calculate_winnings(spins):
                    if len(set(spins)) == 1:
                        return bet * multipliers[spins[0]]
                    if len(set(spins)) == 2:
                        return bet * 3
                    else:
                        return -bet

                def draw_text(text, color, x, y):
                    text_surface = font.render(text, True, color)
                    screen.blit(text_surface, (x, y))

                running = True
                while running:
                    money = server_data['total_money'] + accumulated_money
                    for event in pygame.event.get():
                        if event.type == pygame.KEYDOWN:
                            keys = pygame.key.get_pressed()
                            if keys[pygame.K_ESCAPE]:
                                return
                            if keys[controls[4]]:
                                if money >= bet:
                                    slots = spin_slots()
                                    winnings = calculate_winnings(slots)
                                    accumulated_money += winnings
                                    if winnings > 0: result_message = [f"You have won €{winnings}!",f"Je hebt €{winnings} gewonnen!"][taal]
                                    else: result_message = ["Lost!","Verloren!"][taal]
                                else: result_message = ["You do not have enough money...","Je hebt niet genoeg geld..."][taal]

                    screen.fill(BLACK)

                    draw_text(f"Geld: {money}", WHITE, 20, 20)
                    draw_text(f"Inzet: {bet}", WHITE, 20, 60)

                    for i, slot in enumerate(slots):
                        color = symbol_colors[symbols.index(slot)] if slot in symbols else WHITE
                        draw_text(slot, color, WIDTH // 2 - 100 + i * 100, HEIGHT // 2)

                    draw_text(result_message, WHITE, 20, HEIGHT - 60)

                    pygame.display.flip()

                return
            def finalboss():
                class ShootingGame():
                    layout = [
                        [1,1,1,1,1,1,1,2,2,2,1,1,1,1,1,1,1],
                        [1,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,1],
                        [1,3,0,0,0,0,0,0,0,0,0,0,0,0,0,3,1],
                        [1,3,0,0,0,0,0,0,0,0,0,0,0,0,0,3,1],
                        [1,3,0,0,0,0,0,0,0,0,0,0,0,0,0,3,1],
                        [1,3,0,0,0,0,0,0,0,0,0,0,0,0,0,3,1],
                        [1,3,0,0,0,0,0,0,0,0,0,0,0,0,0,3,1],
                        [2,3,0,0,0,0,0,0,0,0,0,0,0,0,0,3,2],
                        [2,3,0,0,0,0,0,0,0,0,0,0,0,0,0,3,2],
                        [2,3,0,0,0,0,0,0,0,0,0,0,0,0,0,3,2],
                        [1,3,0,0,0,0,0,0,0,0,0,0,0,0,0,3,1],
                        [1,3,0,0,0,0,0,0,0,0,0,0,0,0,0,3,1],
                        [1,3,0,0,0,0,0,0,0,0,0,0,0,0,0,3,1],
                        [1,3,0,0,0,0,0,0,0,0,0,0,0,0,0,3,1],
                        [1,3,0,0,0,0,0,0,0,0,0,0,0,0,0,3,1],
                        [1,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,1],
                        [1,1,1,1,1,1,1,2,2,2,1,1,1,1,1,1,1],
                    ]
                    dialogues = [
                        [
                        "Jij: Je bent gierig.",
                        "Gus: Nee, mijn geld gaat naar mijn werknemers.",
                        "Jij: Wie dan?",
                        "Gus: Mijn geweer!"
                        ],
                        [
                        "Gus: Je bent sterker dan je eruitziet.",
                        "Gus: Maar je hebt mijn ware kracht nog niet gezien.",
                        "Jij: Maar ik heb een geheim wapen... jij kan niet op tegen Mirjam Bikker!",
                        ],
                        [
                        "Gus: Ik zit een beetje in de penarie...",
                        "Jij: Haha, was Bikker te veel voor je?",
                        "Gus: ...",
                        ]
                    ]
                    GusVel = [0,0]
                    GusMaxLives = 60
                    GusLives = GusMaxLives
                    playerLives = 5
                    playerDamaged = 0
                    orbs = []
                    GusCooldown = 500
                    GusCooldownWeapon = 200
                    GusSpdMultiplier = 0.9
                    playerCooldown = 0
                    inCutscene = True
                    dialogueActive = False
                    currentDialogueList = 0
                    playerInv = 0
                    shieldLives = 10
                    def __init__(self, w_size, player_size : int):
                        self.windowSize = w_size
                        self.playerPos = [round(w_size[0]/2-0.5*player_size),w_size[1]]
                        self.playerSize = player_size
                        self.GusPos = [round(w_size[0]/2-0.5*player_size),-player_size]
                        self.tileSize = round(min(w_size)/17-0.49)
                        self.startTile = [round((w_size[0]-w_size[1])/2),0]
                        self.bossimg = pygame.transform.scale(pygame.image.load(os.path.join(ASSETS_PATH,"Gus.png")),(self.playerSize,self.playerSize)).convert_alpha()
                        self.bosshitimg = self.color_copy(self.bossimg,WHITE)
                        self.playerimg = pygame.transform.scale(pygame.image.load(os.path.join(ASSETS_PATH,"Player1.png")),(self.playerSize,self.playerSize)).convert_alpha()
                        self.playerhitimg = self.color_copy(self.playerimg,RED)
                    def color_copy(self,surface,color):
                        w, h = surface.get_size()
                        surf = pygame.Surface((w,h), pygame.SRCALPHA)
                        for x in range(w):
                            for y in range(h):
                                r, g, b, a = surface.get_at((x, y))
                                if a > 0: surf.set_at((x, y), (color[0], color[1], color[2], a))
                        return surf
                    def isCollidingMidpoint(self, orb : list, characterPos : list, characterSize : int, radius : int = 0):
                        return (orb[0] + radius > characterPos[0] and orb[0] - radius < characterPos[0] + characterSize and orb[1] + radius > characterPos[1] and orb[1] - radius < characterPos[1] + characterSize)
                    def keep(self,charPos,charSpd):
                            if charPos[0] < self.startTile[0] + self.tileSize: charPos[0] += charSpd
                            elif charPos[0] > self.startTile[0] + (len(self.layout[0])-1)*self.tileSize - self.playerSize: charPos[0] -= charSpd
                            if charPos[1] < self.startTile[1] + self.tileSize: charPos[1] += charSpd
                            elif charPos[1] > self.startTile[1] + (len(self.layout[1])-1)*self.tileSize - self.playerSize: charPos[1] -= charSpd
                            return charPos
                    def tick(self, scrn, playerVel, shootDir, iKeyPressed : bool, spd : int = 5, shootSpd : int = 12, dt : float = 1/60):
                        for x in range(0,len(self.layout[0])):
                            for y in range(0,len(self.layout)):
                                color = [(255,255,100),(139, 69, 19),(159, 89, 39),(230,230,0)][self.layout[y][x]]
                                pygame.draw.rect(scrn,color,(self.startTile[0]+x*self.tileSize,self.startTile[1]+y*self.tileSize,self.tileSize,self.tileSize))

                        if self.inCutscene:
                            if self.currentDialogueList == 0:
                                if self.GusPos[1] < round(self.windowSize[1]/7):
                                    self.GusPos[1] += 1
                                    self.maxDialogue = 0
                                    self.currentDialogue = 0
                                elif self.playerPos[1] > self.windowSize[1] - round(self.windowSize[1]/10) - self.playerSize: self.playerPos[1] -= 2
                                else:
                                    self.dialogueActive = True
                                    if self.currentDialogue >= len(self.dialogues[self.currentDialogueList][self.maxDialogue]):
                                        if iKeyPressed:
                                            self.currentDialogue = 0
                                            self.maxDialogue += 1
                                            if self.maxDialogue >= len(self.dialogues[self.currentDialogueList]):
                                                time.sleep(2)
                                                play_music("boss2.mp3")
                                                self.inCutscene = False
                                                self.dialogueActive = False
                                                self.maxDialogue = 0
                                    else: self.currentDialogue += 1
                            else:
                                c = 0
                                if self.GusPos[0] < round(self.windowSize[0]/2) - spd: self.GusPos[0] += round(spd*self.GusSpdMultiplier)
                                elif self.GusPos[0] > round(self.windowSize[0]/2) + spd: self.GusPos[0] -= round(spd*self.GusSpdMultiplier)
                                else: c += 1
                                if self.GusPos[1] < round(self.windowSize[1]/7) - spd: self.GusPos[1] += round(spd*self.GusSpdMultiplier)
                                elif self.GusPos[1] > round(self.windowSize[1]/7) + spd: self.GusPos[1] -= round(spd*self.GusSpdMultiplier)
                                else: c += 1
                                if self.playerPos[0] < round(self.windowSize[0]/2) - spd: self.playerPos[0] += spd
                                elif self.playerPos[0] > round(self.windowSize[0]/2) + spd: self.playerPos[0] -= spd
                                else: c += 1
                                if self.playerPos[1] < round(self.windowSize[1]*0.7) - spd: self.playerPos[1] += spd
                                elif self.playerPos[1] > round(self.windowSize[1]*0.7) + spd: self.playerPos[1] -= spd
                                else: c += 1
                                if c == 4:
                                    self.dialogueActive = True
                                    if self.currentDialogue >= len(self.dialogues[self.currentDialogueList][self.maxDialogue]):
                                        if iKeyPressed:
                                            self.currentDialogue = 0
                                            self.maxDialogue += 1
                                            if self.maxDialogue >= len(self.dialogues[self.currentDialogueList]):
                                                time.sleep(2)
                                                self.inCutscene = False
                                                self.dialogueActive = False
                                                self.maxDialogue = 0
                                    else: self.currentDialogue += 1

                            screen.blit(self.playerimg,self.playerPos)
                            screen.blit(self.bossimg,self.GusPos)

                            if self.dialogueActive:
                                surface = font.render(self.dialogues[self.currentDialogueList][self.maxDialogue][:self.currentDialogue], True, (255,0,0))
                                screen.blit(surface, (10, 10))
                        
                        else:
                            if random.randint(1,25) == 1: self.GusVel = [random.choice([-spd,0,spd]),random.choice([-spd,0,spd])]
                            oldGusPos = self.GusPos
                            counter = 0
                            self.GusPos[0] += self.GusVel[0]
                            self.GusPos[1] += self.GusVel[1]
                            self.playerPos[0] += playerVel[0]*spd
                            self.playerPos[1] += playerVel[1]*spd
                            if shootDir != [0,0] and self.playerCooldown < 0:
                                self.playerCooldown = 10
                                playerCenter = [self.playerPos[0]+round(self.playerSize/2),self.playerPos[1]+round(self.playerSize/2)]
                                shootDir = [round(shootDir[0]*shootSpd),round(shootDir[1]*shootSpd)]
                                self.orbs += [playerCenter+[shootDir[0],shootDir[1],'player']]
                            else: self.playerCooldown -= 1

                            self.GusPos = self.keep(self.GusPos,spd)
                            self.playerPos = self.keep(self.playerPos,spd)
                            
                            if oldGusPos == self.GusPos:
                                counter += 1
                                if counter > 5:
                                    self.GusVel = [random.choice([-spd,0,spd]),random.choice([-spd,0,spd])]
                                    counter = 0
                            
                            GusCenter = [self.GusPos[0]+round(self.playerSize/2),self.GusPos[1]+round(self.playerSize/2)] 
                            
                            if random.randint(1,20) == 1 and self.GusCooldown <= 0:
                                if random.randint(1,3) == 1: self.orbs += [GusCenter+[6,6,'Gus'],GusCenter+[-6,6,'Gus'],GusCenter+[-6,-6,'Gus'],GusCenter+[6,-6,'Gus']]
                                else: self.orbs += [GusCenter+[8,0,'Gus'],GusCenter+[0,8,'Gus'],GusCenter+[-8,0,'Gus'],GusCenter+[0,-8,'Gus']]
                                self.GusCooldown = 60

                            self.GusCooldown -= 1
                            if self.GusLives <= 0:
                                global endgame
                                endgame[2] = True
                                return 'won'
                            elif self.playerLives <= 0:
                                npctext.set_message(["Gus: I am unstoppable!","Gus: Ik ben onverslaanbaar!"][taal],gus.pos)
                                return 'lost'
                            
                            weaponReloadValue = False
                            if self.GusLives < self.GusMaxLives / 3:
                                if self.currentDialogueList == 1:
                                    self.inCutscene = True
                                    self.currentDialogueList = 2
                                    self.orbs = []
                                    self.GusCooldown = 300
                                    self.GusCooldownWeapon = 200
                                    self.GusSpdMultiplier = 2
                                    time.sleep(1)
                                else:
                                    weaponReloadValue = 40
                            elif self.GusLives < self.GusMaxLives / 1.5:
                                if self.currentDialogueList == 0:
                                    self.inCutscene = True
                                    self.currentDialogueList = 1
                                    self.orbs = []
                                    self.GusCooldown = 300
                                    self.GusCooldownWeapon = 200
                                    self.GusSpdMultiplier = 1.5
                                    time.sleep(1)
                                else:
                                    weaponReloadValue = 50
                            
                            if weaponReloadValue:
                                if self.GusCooldownWeapon < 0:
                                    deltaPos = [self.playerPos[0]-self.GusPos[0],self.playerPos[1]-self.GusPos[1]]
                                    for i in range(len(deltaPos)):
                                        if deltaPos[i] > 96: deltaPos[i] = shootSpd
                                        elif deltaPos[i] < -96: deltaPos[i] = -shootSpd
                                        else: deltaPos[i] = 0
                                    if 0 not in deltaPos:
                                        deltaPos[0] /= 1.44
                                        deltaPos[1] /= 1.44
                                    self.orbs += [GusCenter+[deltaPos[0],deltaPos[1],'Gus'],GusCenter+[-deltaPos[0],-deltaPos[1],'Gus']]
                                    self.GusCooldownWeapon = weaponReloadValue
                                else: self.GusCooldownWeapon -= 1

                            playerdir = (self.playerPos[0] - self.GusPos[0],self.playerPos[1] - self.GusPos[1])
                            playerdirlen = (playerdir[0]**2+playerdir[1]**2)**0.5
                            playerdir = [playerdir[0]/playerdirlen,playerdir[1]/playerdirlen]
                            shield_pos = (GusCenter[0] + round(playerdir[0]*45), GusCenter[1] + round(playerdir[1]*45))
                            csize = 40

                            orb = 0
                            todelete = []
                            shieldhit = False
                            gus_hit = False
                            for i, orb in enumerate(self.orbs):
                                getsdeleted = False
                                if self.currentDialogueList == 2 and orb[4] == 'player' and self.shieldLives > 0 and ((orb[0]-shield_pos[0])**2 + (orb[1]-shield_pos[1])**2)**0.5 < csize:
                                    getsdeleted = True
                                    self.shieldLives -= 1
                                    shieldhit = True
                                if self.isCollidingMidpoint(orb,self.playerPos,self.playerSize,6) and orb[4] == 'Gus' and self.playerInv <= 0:
                                    getsdeleted = True
                                    self.playerDamaged = 128
                                    self.playerLives -= 1
                                    self.playerInv = 10
                                elif self.isCollidingMidpoint(orb,self.GusPos,self.playerSize,6) and orb[4] == 'player':
                                    getsdeleted = True
                                    gus_hit = True
                                    self.GusLives -= 1
                                orb[0] += round(orb[2])
                                orb[1] += round(orb[3])
                                pygame.draw.circle(scrn,((255,0,0) if orb[4] == 'Gus' else (0,255,0)),(orb[0],orb[1]),10)
                                if getsdeleted or orb[0] < -50 or orb[0] > self.windowSize[0] + 50 or orb[1] < -50 or orb[1] > self.windowSize[1] + 50:
                                    todelete.append(i)
                            for index in todelete[::-1]:
                                self.orbs.pop(index)
                            
                            if self.currentDialogueList == 2:
                                if shieldhit: alpha = 255
                                elif self.shieldLives > 0: alpha = 150
                                else: alpha = 50
                                circle = pygame.Surface((csize,csize),pygame.SRCALPHA)
                                pygame.draw.circle(circle,(255,255,255,alpha),(csize//2,csize//2),csize//2)
                                screen.blit(circle,(shield_pos[0]-csize//2,shield_pos[1]-csize//2))

                            if self.playerDamaged > 0:
                                red_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                                pygame.draw.rect(red_surface,(160,10,10,round(self.playerDamaged)),(0,0,WIDTH,HEIGHT))
                                scrn.blit(red_surface,(0,0))
                                self.playerDamaged -= 0.5
                                self.playerInv -= 1
                            
                            screen.blit(self.playerimg,self.playerPos)
                            screen.blit((self.bosshitimg if gus_hit else self.bossimg),self.GusPos)
                            
                            bossbarlen = WIDTH // 3
                            healthbarlen = round(bossbarlen*self.GusLives/self.GusMaxLives)
                            bossbarx = (WIDTH - bossbarlen) // 2
                            bossbary = HEIGHT // 10
                            pygame.draw.line(screen,BLACK,(bossbarx,bossbary),(bossbarx+bossbarlen,bossbary),width=20)
                            pygame.draw.line(screen,(WHITE if gus_hit else RED),(bossbarx,bossbary),(bossbarx+healthbarlen,bossbary),width=20)

                time.sleep(2)

                game = ShootingGame([WIDTH,HEIGHT],48)
                running = True
                last_frame_time = 1/60
                while running:
                    screen.fill((0,0,0))
                    player_dir = [0,0]
                    shoot_dir = [0,0]
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            running = False
                    keys = pygame.key.get_pressed()
                    if keys[pygame.K_ESCAPE]:
                            running = False
                    if keys[controls[2]]: player_dir[0] += 1
                    if keys[controls[3]]: player_dir[0] -= 1
                    if keys[controls[1]]: player_dir[1] += 1
                    if keys[controls[0]]: player_dir[1] -= 1
                    if keys[pygame.K_RIGHT]: shoot_dir[0] += 1
                    if keys[pygame.K_LEFT]: shoot_dir[0] -= 1
                    if keys[pygame.K_DOWN]: shoot_dir[1] += 1
                    if keys[pygame.K_UP]: shoot_dir[1] -= 1
                    if keys[controls[4]]: interaction_key_pressed = True
                    else: interaction_key_pressed = False
                    if shoot_dir[0] and shoot_dir[1]:
                        shoot_dir[0] /= 1.44
                        shoot_dir[1] /= 1.44
                    results = game.tick(screen,player_dir,shoot_dir,interaction_key_pressed, dt=last_frame_time)
                    if results: running = False

                    pygame.display.flip()
                    last_frame_time = clock.tick(FPS) / 1000
                play_music(current_area)
            
            if is_interacting(player_pos, tix, current_area, interact_key_down) and (not endgame[1] or endgame[2]): 
                interacted_npcs.append('tix')
                if endgame[0]:
                    npctext.set_message(["Tix: I was the sender, because Gus never gave his illegal money away to charity... *Falls into a trap.*","Tix: Ik ben de afzender, omdat Gus nooit zijn illegale geld aan goede doelen gaf... *Valt in een val.*"][taal],tix.pos)
                    endgame[1] = True
                    journal.remove('endgame2')
                elif not endgame[0]:
                    npc_text = ["Tix: Welcome to my casino. Choose your bet (10/100/1000)","Tix: Welkom in mijn casino. Kies je inzet (10/100/1000)"][taal]
                    npc_text_timer = current_time + 5000
                    if keys[pygame.K_1]:
                        gokautomaat(10)
                    if keys[pygame.K_2]:
                        gokautomaat(100)
                    if keys[pygame.K_3]:
                        gokautomaat(1000)

            if is_interacting(player_pos, gus, current_area, interact_key_down) and not perfection: 
                interacted_npcs.append('gus')
                if endgame[1] and not endgame[2]: 
                    finalboss()
                elif endgame[2] and not perfection:
                    play_video('christenunie.mp4','christenunie.mp3')
                    show_largecredits()
                    show_backstory(f"{name}...?",wait_time=2000)
                    show_backstory([
                        ["When you hear this: This is your doctor.", "You've been in a coma for months.", "You were a medical student: top of your class.", "But it all became too much for you.", "One day you came home from school, took the elevator to the roof, and you... jumped.", "I'm going to unplug your life support now.", "You will return to your coma world forever.", "You will finally be happy now...",],
                        ["Als je dit hoort: Dit is je dokter.", "Je ligt al maandenlang in coma.", "Je was een student geneeskunde: de beste van de klas.", "Maar het werd je teveel.", "Op een dag kwam je terug van school, nam je de lift naar het dak en je... sprong. ", "Ik haal nu de stekker uit je beademing.", "Je zal nu voor altijd teruggaan naar je comawereld.", "Je zal nu eindelijk gelukkig zijn...",]
                    ][taal],wait_time=20000)
                    endgame = [False for _ in range(len(has_keys))]
                    perfection = True
                elif finished_list[2] and not finished_list[3]:
                    npc_text = ["Gus: Bring this trash away.","Gus: Breng dit afval weg."][taal]
                    npc_text_timer = current_time + 5000
                    michael_on_cooldown = True
                    journal.remove('list3')
                    journal.append('list4')
                    finished_list[3] = True
                elif gus_available and married and not perfection:
                    if not 6 in visited:
                        npc_text = ["Gus: Have you been to my dock? Go south.","Gus: Ben je al op mijn kade geweest? Ga naar het zuiden."][taal]
                        npc_text_timer = current_time + 5000
                        journal.remove('gus1')
                        journal.append('gus2')
                    elif 6 in visited:
                        if given_quest:
                            npc_text = ["Gus: You bought a carpet for your apartment!","Gus: Je hebt een tapijt gekocht voor je appartement!"][taal]
                            if apartment_has_carpet: 
                                npc_text = ["Gus: Thank you, I'm definitely going to enjoy this.","Gus: Dankje, hier ga ik zeker van genieten."][taal]
                                npc_text_timer = current_time + 5000
                            elif (money >= 500 and not apartment_has_carpet and keys[pygame.K_1]):
                                accumulated_money -= 500
                                apartment_has_carpet = True
                            else: npc_text = ["Gus: (1: Buy a carpet)","Gus: (1: Koop een tapijt)"][taal]
                            npc_text_timer = current_time + 5000
                        elif not has_quest:
                            quest_available = True
                            npc_text = ["Gus: Catch a fish on my dock.","Gus: Vang een vis op mijn kade."][taal]
                            npc_text_timer = current_time + 5000
                            if not given_quest: 
                                journal.append('quest')
                        elif has_quest:
                            quest = inventory.get_nth_tagged('questable',delete=True)
                            if quest:
                                npc_text = ["Gus: Thank you, I'm definitely going to enjoy this.","Gus: Dankje, hier ga ik zeker van genieten."][taal]
                                npc_text_timer = current_time + 5000
                                has_quest = False
                                given_quest = True
                                journal.mark_done('quest')
                elif not michael_on_cooldown:
                    npc_text = ["Gus: My name is Gustavo, but you can call me Gus. I am the owner of YKS Megacorp.","Gus: Mijn naam is Gustavo, maar noem me gerust Gus. Ik ben de eigenaar van YKS Megacorp."][taal]
                    npc_text_timer = current_time + 5000
        elif old_area == 2: #Snowfall
            screen.fill((200, 220, 255)) 
            pygame.draw.rect(screen, (180, 200, 220), (0, HEIGHT // 2 - 50, WIDTH, 100)) 
            
            if not helped_bouncer and ((robot_purchased and not robot["should_draw"]) or not robot_purchased) and day not in [10,20,30]: michael.draw(current_area, 1)
            if helped_bouncer and 11 not in visited: journal.append('find_michael')
            if has_keys[6]: max_npc.draw(current_area, 1)

            if is_interacting(player_pos, max_npc, current_area, interact_key_down) and has_keys[6]:
                npc_text = [
                    "Max: Die sleutel is te gevaarlik! Daarom het ek as Max onderdak gegaan om hom te vind. Gee dit nou vir hom!",
                    ["*Gives key.*","*Geeft sleutel.*"][taal],
                    "Max: As beloning maak ek nou die deur van die sleutel oop. Vergeet dit alles."
                ]
                npc_text_timer = current_time + 7500
                journal.remove('key7')
                journal.append('key8')
                has_keys = [False for _ in range(len(has_keys))]
                worldmap.requirements[22] = True
                
            if is_interacting(player_pos, michael, current_area) and not helped_bouncer:
                in_selling_range = True
                if has_keys[1]:
                    npc_text = ["Michael: This was the key to his chicken coop. Leah knows a lot about animals, just ask her.","Michael: Dit was de sleutel van zijn kippenhok. Leah weet veel van dieren, vraag het maar aan haar."][taal]
                    npc_text_timer = current_time + 5000
                    journal.remove('key2')
                    journal.append('key3')
                    has_keys[2] = True
                elif interact_key_down:
                    interacted_npcs.append('michael')
                    if day in [28,29]:
                        npc_text = ["Michael: Vote for me and you can travel to Maxdesert for free forever!","Michael: Stem voor mij en je mag voor altijd gratis naar Maxdesert reizen!"][taal]
                        npc_text_timer = current_time + 5000
                            
            else: in_selling_range = False

            worldmap.requirements[11] = border_open and electioncounter==3
        elif old_area == 3: #Maxdesert
            player_pos = CENTER
            if not has_keys[6]: max_npc.draw(current_area, 0)
            african_flag.draw(current_area)
            if is_interacting(player_pos, max_npc, current_area, interact_key_down) and has_keys[3]:
                npc_text = "Max: Ek het soms 'n ou man noord sien gaan."
                npc_text_timer = current_time + 10000
                journal.remove('key4')
                journal.append('key5')
                has_keys[4] = True
            elif is_interacting(player_pos, max_npc, current_area, interact_key_down) and (has_keys[5] or has_keys[6]):
                npc_text = "Max: Jy het my... as jy my kan vang!"
                npc_text_timer = current_time + 10000
                journal.remove('key6')
                journal.append('key7')
                has_keys[5] = False
                has_keys[6] = True
            elif day == 40:
                journal.mark_done('max')
            elif is_interacting(player_pos, max_npc, current_area, interact_key_down):
                interacted_npcs.append('max')
                if not cacti:
                    accumulated_money += random.choice([750,930,1120,1500])
                    generate_cacti(10)
                elif day == 18:
                    npc_text = "Max: Welkom in my woestyn. Verwyder die kaktusse met hoeties en ek gee vir jou geld."
                    npc_text_timer = current_time + 10000
                elif 16 not in visited and not fixed_geluidsoverlast1 and not fixed_geluidsoverlast2:
                    npc_text = "Max: Ek word gepla deur die musiek in die ooste, maak dit reg!"
                    npc_text_timer = current_time + 10000
                    journal.append('geluid1')
                elif fixed_geluidsoverlast1 and not fixed_geluidsoverlast2: 
                    npc_text = "Max: Dit hou my stil!"
                    npc_text_timer = current_time + 10000
                    fixed_geluidsoverlast2 = True
                    journal.remove('geluid2')
                elif fish_caught < 5:
                    if day % 2:
                        npc_text = "Max: " + DIALOOG_MAX[0]
                        npc_text_timer = current_time + 10000
                    if not day % 2:
                        npc_text = "Max: " + DIALOOG_MAX[1]
                        npc_text_timer = current_time + 10000
                elif fish_caught >= 5 and not talked_to_tix:
                    npc_text = "Max: Ek het 'n geheim vir jou: Gaan nort..."
                    npc_text_timer = current_time + 10000
                    journal.append('found_swamp')
                elif fish_caught >= 5 and talked_to_tix:
                    if day % 2:
                        npc_text = "Max: " + DIALOOG_MAX[0]
                        npc_text_timer = current_time + 10000
                    if not day % 2:
                        npc_text = "Max: " + DIALOOG_MAX[1]
                        npc_text_timer = current_time + 10000
            for cactus in cacti[:]:
                if interact_key_down and shovel_purchased and stamina >= 15 and chop_cactus(player_pos, cactus, cactus_size):
                    cacti.remove(cactus)
                    if not no_stamina_system: stamina -= 15
                    chance = random.random()
                    if chance < 0.07:
                        npc_text = "Max: Jy het 'n palmfossiel gevind. Groot vonds!"
                        npc_text_timer = current_time + 10000
                        if not inventory.pickup('pfossil',value=100): print('inventory full!')
                    elif chance < 0.13:  
                        npc_text = "Max: Jy het 'n goue oorblyfsel gevind. Groot vonds!"
                        npc_text_timer = current_time + 10000
                        if not inventory.pickup('gremains',value=250): print('inventory full!')
                    elif chance < 0.16:  
                        npc_text = "Max: Jy het 'n goue masker gevind. Groot vonds!"
                        npc_text_timer = current_time + 10000
                        if not inventory.pickup('gmask',value=500): print('inventory full!')

            for cactus in cacti:
                screen.blit(cactus_img, (cactus['x'] - camera_pos[0], cactus['y'] - camera_pos[1]))
        
        elif old_area == 4: #Tixswamp
            screen.fill((0,130,50))
            for item in bog_islands:
                item.draw(BROWN)
            for f in farms:
                if f.playerInRange(player_pos + [player_size,player_size]) and interact_key_down and shovel_purchased:
                    if f.locked: f.unlock()
                    else:
                        results = f.harvest(day)
                        if results:
                            if results['success']:
                                if not inventory.pickup(results['cropname'],rarity=results['special'],value=results['money+'],dispName=results['dispName'],type='crop'): print('inventory full!')
                            npc_text = results['newT']
                            npc_text_timer = current_time + results['textT']
                        else: f.plant(day)
                f.draw(screen,day)

            tix.draw(current_area)
            if is_interacting(player_pos, tix, current_area, interact_key_down) and npc_text == '':
                interacted_npcs.append('tix')
                if has_keys[4]:
                    npctext.set_message(["Tix: This ends now. The man is long gone. Your search is useless.","Tix: Dit eindigt nu. De man is allang vertrokken. Je speurtocht heeft geen nut."][taal],tix.pos)
                    journal.remove('key5')
                    journal.append('key6')
                    has_keys[3] = False
                    has_keys[5] = True
                elif talked_to_tix:
                    npctext.set_message(["Tix: The soil here is fertile... plants would grow easily on it.","Tix: De grond is hier vruchtbaar... planten zouden er gemakkelijk op groeien."][taal],tix.pos)
                else:
                    npctext.set_message(["Tix: You found my secret swamp... congratulations. Here's your reward.","Tix: Je hebt mijn geheime moeras gevonden... gefeliciteerd. Hier is je beloning."][taal],tix.pos)
                    accumulated_money += 50000
                    talked_to_tix = True
        
        elif old_area == 5: #Tixcity
            screen.fill((30, 30, 30))  
            
            pygame.draw.rect(screen, (50, 50, 50), (WIDTH//2 - 50, 0, 100, HEIGHT))  
            
            for i in range(5):
                pygame.draw.rect(screen, (100, 100, 100), (WIDTH//2 - 200, i * 150 + 50, 100, 120)) 
                pygame.draw.rect(screen, (100, 100, 100), (WIDTH//2 + 100, i * 150 + 50, 100, 120))  
            
            for i in range(5):
                pygame.draw.rect(screen, (255, 255, 0), (WIDTH//2 - 180, i * 150 + 70, 20, 20))
                pygame.draw.rect(screen, (255, 0, 0), (WIDTH//2 - 160, i * 150 + 90, 20, 20))
                pygame.draw.rect(screen, (0, 255, 255), (WIDTH//2 + 120, i * 150 + 70, 20, 20))
                pygame.draw.rect(screen, (255, 255, 0), (WIDTH//2 + 140, i * 150 + 90, 20, 20))
            
            middle_house_rect = pygame.Rect(WIDTH//2 - 200, 2 * 150 + 50, 100, 120)

            if player_pos[0] + player_size > middle_house_rect.left and player_pos[0] < middle_house_rect.right and \
            player_pos[1] + player_size > middle_house_rect.top and player_pos[1] < middle_house_rect.bottom and \
            interact_key_down and married:
                fade_out()
                current_area = 7
                journal.mark_done('find_house') 
                player_pos = [WIDTH // 2, HEIGHT - player_size - 100]
            
            right_middle_house_rect = pygame.Rect(WIDTH//2 + 100, 2 * 150 + 50, 100, 120)

            if player_pos[0] + player_size > right_middle_house_rect.left and player_pos[0] < right_middle_house_rect.right and \
            player_pos[1] + player_size > right_middle_house_rect.top and player_pos[1] < right_middle_house_rect.bottom and \
            interact_key_down:
                fade_out()
                current_area = 10
                player_pos = [WIDTH // 2, HEIGHT - player_size - 100]
            
            if is_interacting(player_pos, bouncer, current_area, interact_key_down) and not has_card:
                interacted_npcs.append('bouncer')
                if fish_caught < 5:
                    npctext.set_message(["Bouncer: Come back when you have a club card.", "Bouncer: Kom terug wanneer je een clubkaart hebt."][taal],bouncer.pos)
                if fish_caught >= 5:
                    npctext.set_message(["Bouncer: Sorry, access denied. If you have any complaints, go from the desert north and talk to the boss.", "Bouncer: Sorry, toegang geweigerd. Als je klachten hebt, ga dan in de woestijn naar het noorden en praat met de baas."][taal],bouncer.pos) 
                journal.append('find_card')
            if is_interacting(player_pos, ladder, current_area, interact_key_down) and has_card:
                current_area = 1
                player_pos = (0,0)
            ladder.pos = tix_pos
            if not has_card: bouncer.draw(current_area)
            if has_card: ladder.draw(current_area)

        elif old_area == 6: #Gus's Dock
            #screen.fill((50, 100, 200))
            #wave_offset = draw_waves(wave_offset)

            if interact_key_just_pressed and has_rod and current_minigame == None and (not married or helped_bouncer): fishing_game()
            
            bouncer.draw(current_area)
            if is_interacting(player_pos, bouncer, current_area, interact_key_down):
                interacted_npcs.append('bouncer')
                journal.remove('gus2')
                if not has_gift and not helped_bouncer:
                    npctext.set_message(["Bouncer: You're not allowed to fish here until you give me something cute.", "Bouncer: Je mag hier niet vissen totdat je mij iets schattigs geeft."][taal],bouncer.pos)
                    gift_available = True
                    journal.append('helped_bouncer')
                if has_gift and not helped_bouncer:
                    gift = inventory.get_nth_tagged('giftable',delete=True)
                    if gift:
                        npctext.set_message(["Bouncer: Yeah, I do... oh, it's meant to be a pet. Thanks anyway!","Bouncer: Ja, ik wil... oh, het is bedoeld als huisdier. Nog steeds bedankt!"][taal],bouncer.pos)
                        has_gift = False
                        helped_bouncer = True
                        if border_open and electioncounter == 3: worldmap.requirements[11] = True
                        michael.location = 11
                        journal.mark_done('helped_bouncer')

            if 'jelly' in daily_mods: draw_jelly(current_area)
            
            """bridge_width = 100
            bridge_x_start = (WIDTH - bridge_width) // 2
            pygame.draw.rect(screen, (139, 69, 19), (bridge_x_start, 0, bridge_width, HEIGHT))

            player_pos[0] = max(bridge_x_start, min(player_pos[0], bridge_x_start + bridge_width - player_size))

            if has_card and married and not helped_bouncer: bouncer.draw(current_area)"""
        
        elif old_area == 7: #Leah's Apartment
            screen.fill((230, 230, 250))
            if not day % 4:
                leah.draw(current_area, 1) 
                if is_interacting(player_pos, leah, current_area, interact_key_down):
                    interacted_npcs.append('leah')
                    if ben.messageOverride.endswith("...") and 2 not in visited: 
                        npctext.set_message(["Sweetie, have you heard about that icy wind from the west? You should go have a look there.","Schatje, heb je al gehoord over die ijzige westenwind? Je moet daar eens kijken."][taal],leah.pos)
                        npc_text_timer = current_time + 5000
            if apartment_has_carpet:
                carpet.draw(current_area)
                if is_interacting(player_pos, carpet, current_area, interact_key_down) and not has_keys[0] and not worldmap.requirements[8]:
                    npctext.set_message((["I found a key. I should bring it to Ben.","Ik heb een sleutel gevonden. Ben kan er vast iets mee."][taal],{'thinking':True}),player_pos)
                    npc_text_timer = current_time + 5000
                    journal.append('key1')
                    has_keys[0] = True
            if player_pos[1] > HEIGHT - player_size - 10: 
                fade_out()
                player_pos = [WIDTH // 2, HEIGHT // 2]
                current_area = 5
  
        elif old_area == 10: #Kanye's Apartment
            screen.fill((230, 230, 250))
            if helped_bouncer: bouncer.draw(current_area)

            if is_interacting(player_pos, bouncer, current_area, interact_key_down) and helped_bouncer and not met_kanye1:
                npctext.set_message(["Bouncer: I want to change my name, but I need permission from Kanye West.","Bouncer: Ik wil mijn naam wijzigen, alleen ik heb toestemming nodig van Kanye West."][taal],bouncer.pos) 
                journal.append('kanye')
            if is_interacting(player_pos, bouncer, current_area, interact_key_down) and helped_bouncer and met_kanye1:
                npctext.set_message(["Kanye North: I feel a lot cooler now.","Kanye North: Ik voel me nu een stuk cooler."][taal],bouncer.pos) 
                journal.remove('kanye')
                met_kanye2 = True

            if player_pos[1] > HEIGHT - player_size - 10: 
                fade_out()
                player_pos = [WIDTH // 2, HEIGHT // 2]
                current_area = 5

        elif old_area == 11: #Camden County
            screen.fill((190, 170, 140)) 
            if electioncounter == 1: journal.remove('election2')

            pygame.draw.rect(screen, (120, 120, 120), (0, HEIGHT - 100, WIDTH, 100)) 

            crab_shack_rect = pygame.Rect(100, 150, 200, 150)
            pygame.draw.rect(screen, (160, 60, 40), crab_shack_rect)  
            screen.blit(font.render("Crab Shack", True, (255, 255, 0)), (130, 180))

            motel_rect = pygame.Rect(400, 100, 250, 180)
            pygame.draw.rect(screen, (90, 90, 150), motel_rect)
            screen.blit(font.render("Camden Motel", True, (255, 255, 255)), (420, 130))

            kanye.draw(current_area)
            earl.draw(current_area)
            if (robot_purchased and not robot["should_draw"]) or not robot_purchased and day not in [10,20,30]: michael.draw(current_area, 0)
            if election_started: joy.draw(current_area)
            if election_started: randy.draw(current_area)

            if is_interacting(player_pos, kanye, current_area, interact_key_down):
                if electioncounter == 1 and not talked_about_elections[2]:
                    npc_text = ["Kanye: Give your opinion about the rights to protest. (1: Keep it legal, 2: Make it illegal)", "Kanye: Geef je mening over de rechten om te protesteren. (1: Houd het legaal, 2: Maak het illegaal)"][taal]
                    npc_text_timer = current_time + 5000
                    if keys[pygame.K_1]:
                        npc_text = ["*Election change is recorded.*", "*Verkiezingsverandering is opgenomen."][taal]
                        npc_text_timer = current_time + 5000
                        electionresult -= 1
                        talked_about_elections[2] = True
                    if keys[pygame.K_2]:
                        npc_text = ["*Election change is recorded.*", "*Verkiezingsverandering is opgenomen."][taal]
                        npc_text_timer = current_time + 5000
                        electionresult += 1
                        talked_about_elections[2] = True
                elif finished_list[0] and not finished_list[1]:
                    journal.remove('list1')
                    money -= 100
                    finished_list[1] = True
                    npctext.set_message(["Kanye West: Thank you for the money. It'll be well spent... heh heh.", "Kanye West: Bedankt voor het geld. Ik zal het goed besteden... heh heh."][taal],kanye.pos)
                elif met_kanye1:
                    npctext.set_message(["Kanye West: By the way, watch your wallet.", "Kanye West: Let trouwens op je portemonnee."][taal],kanye.pos)
                else:
                    npctext.set_message(["Kanye West: I give permission.", "Kanye West: Ik geef toestemming."][taal],kanye.pos)
                    interacted_npcs.append('kanye')
                    met_kanye1 = True
            
            if is_interacting(player_pos, earl, current_area, interact_key_down): 
                if electioncounter == 1 and not talked_about_elections[3]:
                    npc_text = ["Earl: Give your opinion about a higher speed limit (1: Increase the speedlimit, 2: Keep it the same)", "Earl: Geef je mening over een hogere snelheidslimiet. (1: Verhoog de snelheidslimiet, 2: Houd het hetzelfde)"][taal]
                    npc_text_timer = current_time + 5000
                    if keys[pygame.K_1]:
                        npc_text = ["*Election change is recorded.*", "*Verkiezingsverandering is opgenomen."][taal]
                        npc_text_timer = current_time + 5000
                        electionresult += 1
                        talked_about_elections[3] = True
                    if keys[pygame.K_2]:
                        npc_text = ["*Election change is recorded.*", "*Verkiezingsverandering is opgenomen."][taal]
                        npc_text_timer = current_time + 5000
                        electionresult -= 1
                        talked_about_elections[3] = True
                elif not finished_list[1]:
                    npctext.set_message([
                    ["Earl: My name is Earl.","Earl: Mijn naam is Earl."][taal],
                    ["Earl: I have a list of all the bad things I've ever done that I want to make right.","Earl: Ik heb hier een lijst met alle slechte dingen die ik ooit heb gedaan en die wil ik goed maken."][taal],
                    ["Earl: Can you help me with a few?","Earl: Kun je me met een paar helpen?"][taal],
                    ["Earl: Check your journal.","Earl: Check je logboek."][taal],
                    ],earl.pos)
                    npc_text_timer = current_time + 5000
                    finished_list[0] = True
                    journal.append('list1')
                elif finished_list[1] and not finished_list[2]:
                    npctext.set_message(["Earl: Check your journal.", "Earl: Check je logboek."][taal],earl.pos)
                    journal.append('list2')
                elif finished_list[2] and not finished_list[3]:
                    npctext.set_message(["Earl: Check your journal.", "Earl: Check je logboek."][taal],earl.pos)
                    journal.append('list3')
                elif finished_list[3]:
                    npctext.set_message(["Earl: Thanks. Karma will reward you.", "Earl: Bedankt. Karma zal je belonen."][taal],earl.pos)
                    money += 5000
                    finished_list[4] = True
                    journal.remove('list4')
            
            if is_interacting(player_pos, michael, current_area) and ((robot_purchased and not robot["should_draw"]) or not robot_purchased):
                in_selling_range = True
                if interact_key_down:
                    journal.remove('find_michael')
                    if electioncounter == 1 and not talked_about_elections[1]:
                        npc_text = ["Michael: Give your opinion about more police. (1: More police, 2: Keep it the same)", "Michael: Geef je mening over meer politie. (1: Meer politie, 2: Houd het hetzelfde)"][taal]
                        npc_text_timer = current_time + 5000
                        if keys[pygame.K_1]:
                            npc_text = ["*Election change is recorded.*", "*Verkiezing verandering is opgenomen."][taal]
                            npc_text_timer = current_time + 5000
                            electionresult += 1
                            talked_about_elections[1] = True
                        if keys[pygame.K_2]:
                            npc_text = ["*Election change is recorded.*", "*Verkiezing verandering is opgenomen."][taal]
                            npc_text_timer = current_time + 5000
                            electionresult -= 1
                            talked_about_elections[1] = True
                    elif perfection and not election_started:
                        npctext.set_message(["Michael: The day after tomorrow there will be elections: You VS Earl. I'll be rooting for you! Inform the people tommorow.", "Michael: Overmorgen zullen er verkiezingen zijn: Jij VS Earl. Ik duim voor je! Informeer morgen de mensen."][taal],michael.pos)
                        journal.remove('election1')
                        election_started = True
                    elif finished_list[1] and not finished_list[2]:
                        journal.remove('list2')
                        finished_list[2] = True
                        npctext.set_message(["Michael: I forgive him.", "Michael: Ik vergeef hem."][taal],michael.pos)
                    elif has_keys[1]:
                        npctext.set_message(["Michael: This was the key to his chicken coop. Leah knows a lot about animals, just ask her.","Michael: Dit was de sleutel van zijn kippenhok. Leah weet veel van dieren, vraag het maar aan haar."][taal],michael.pos)
                        journal.remove('key2')
                        journal.append('key3')
                        has_keys[2] = True
            else: in_selling_range = False

            if is_interacting(player_pos, joy, current_area, interact_key_down): 
                if electioncounter == 1 and not talked_about_elections[0]:
                    npc_text = ["Joy: Give your opinion about the rights to have a gun. (1: Make it legal, 2: Keep it illegal)", "Joy: Geef je mening over de rechten om een geweer te hebben. (1: Maak het legaal, 2: Houd het illegaal)"][taal]
                    npc_text_timer = current_time + 5000
                    if keys[pygame.K_1]:
                        npc_text = ["*Election change is recorded.*", "*Verkiezing verandering is opgenomen."][taal]
                        npc_text_timer = current_time + 5000
                        electionresult += 1
                        talked_about_elections[0] = True
                    if keys[pygame.K_2]:
                        npc_text = ["*Election change is recorded.*", "*Verkiezing verandering is opgenomen."][taal]
                        npc_text_timer = current_time + 5000
                        electionresult -= 1
                        talked_about_elections[0] = True
                else:
                    npc_text = ["Joy: What's up dummy?", "Joy: Hoe gaat het dombo?"][taal]
                    npc_text_timer = current_time + 5000
            if is_interacting(player_pos, randy, current_area, interact_key_down): 
                if electioncounter == 1 and not talked_about_elections[4]:                    
                    npc_text = ["Randy: Give your opinion about corruption. (1: The mayor shouldn't be able to get arrested anymore, 2: Keep it the same)", "Randy: Geef je mening over corruptie. (1: De burgemeester hoort niet meer gearresteerd te kunnen worden, 2: Houd het hetzelfde)"][taal]
                    npc_text_timer = current_time + 5000
                    if keys[pygame.K_1]:
                        electionresult += 1
                        talked_about_elections[4] = True
                        npc_text = ["Randy: I didn't hear that, but it sounded cool. I'll vote for you.", "Randy: Dat hoorde ik niet, maar het klonk cool. Ik zal op jou stemmen."][taal]
                        npc_text_timer = current_time + 5000
                    if keys[pygame.K_2]:
                        electionresult += 1
                        talked_about_elections[4] = True
                        npc_text = ["Randy: I didn't hear that, but it sounded cool. I'll vote for you.", "Randy: Dat hoorde ik niet, maar het klonk cool. Ik zal op jou stemmen."][taal]
                        npc_text_timer = current_time + 5000
                else:
                    npctext.set_message(["Randy: I am too stupid to have my own opinion.", "Randy: Ik ben te dom om mijn eigen mening te hebben."][taal],randy.pos)

            if player_pos[0] + player_size > crab_shack_rect.left and player_pos[0] < crab_shack_rect.right and \
            player_pos[1] + player_size > crab_shack_rect.top and player_pos[1] < crab_shack_rect.bottom and \
            interact_key_down:
                npctext.set_message((["There is a faint scent of crab... and beer.","Er hangt hier een geur van krab... en bier."][taal],{'thinking':True}),player_pos)

            if player_pos[0] + player_size > motel_rect.left and player_pos[0] < motel_rect.right and \
            player_pos[1] + player_size > motel_rect.top and player_pos[1] < motel_rect.bottom and \
            interact_key_down:
                npctext.set_message((["The motel room smells like regret.","De motelkamer ruikt naar spijt."][taal],{'thinking':True}),player_pos)
        
        elif old_area == 12: #Gus' Dock with the Ferryman
            if 'jelly' in daily_mods: draw_jelly(current_area)

            if ferryquest == 3 and not fman.spokento:
                fboat = load_img_from_assets("Tur_boat.png")
                screen.blit(fboat,(433-camera_pos[0],650-camera_pos[1]))

            fman.draw(current_area)
            if is_interacting(player_pos, fman, current_area):
                if interact_key_down:
                    interacted_npcs.append('fman')
                    if ferryquest == 0 or (ferryquest == 1 and fman.spokento):
                        ferryquest = 1
                        fman.spokento = True
                        npc_text = "The Ferryman: " + ["Aye, I can take ye to 'nother isle... for a small toll, o' course. Just give me a moment to ready the boat.","Aye, ik kan je naar 'n ander eiland brengen... voor een klein tolletje, natuurlijk. Geef me even de tijd om de boot gereed te maken."][taal]
                        npc_text_timer = current_time + 5000
                    elif ferryquest == 1 and not fman.spokento:
                        npc_text = "The Ferryman: " + ["Almost done. Just need a couple o' logs from ya. Three of 'em should do. (1: give)","Bijna klaar. 'K heb alleen nog een paar boomstammen van je nodig. Drie stuks zou genoeg moeten zijn. (1: geef)"][taal]
                        npc_text_timer = current_time + 5000
                        if keys[pygame.K_1] and inventory.get_nth_tagged('ferry',delete=True,amount=3):
                            ferryquest = 2
                    if (ferryquest == 2 or (ferryquest == 3 and fman.spokento)):
                        npc_text = "The Ferryman: " + ["Thank you. The boat will be done by tomorrow.","Dankjewel. De boot zou morgen klaar moeten zijn."][taal]
                        npc_text_timer = current_time + 5000
                        ferryquest = 3
                        fman.spokento = True
                    elif ferryquest == 3 and not fman.spokento:
                        ferry_price = 1000
                        if island:
                            npc_text = "The Ferryman: " + [f"The ferry is open for business! You can now travel to Turmeric Island for {ferry_price}. (1: travel)",f"De veerboot is beschikbaar! Je kan nu naar Turmeric Island voor {ferry_price}. (1: reis)"][taal]
                            if keys[pygame.K_1] and money >= ferry_price:
                                accumulated_money -= ferry_price
                                current_area = 13
                                player_img = pygame.image.load(os.path.join(ASSETS_PATH, "Player1.png"))
                                player_img = pygame.transform.scale(player_img, (player_size, player_size)) 
                                npc_text = ""
                                npc_text_timer = current_time + 5000
                                fade_out()
                        else:
                            npc_text = "The Ferryman: " + ["No islands in sight, sir. But mark me words — them isles drift in and out with each day.","Geen eiland in zicht, meneer. Maar vergeet niet — ze verschijnen en verdwijnen met de dag."][taal]
                        npc_text_timer = current_time + 5000
            
            elif ferryquest == 3 and not fman.spokento: pass

            if interact_key_just_pressed and has_rod and current_minigame == None and helped_bouncer and 'fman' not in interacted_npcs: fishing_game()
        
        elif old_area == 13: #Turmeric Island
            player_rect = pygame.Rect(player_pos[0], player_pos[1], player_size, player_size)
            if island.current_area == 0:
                screen.fill(LARSGROEN)
                fman.draw(current_area)
                if is_interacting(player_pos, fman, current_area, interact_key_down):
                    npc_text = "The Ferryman: " + ["Do you want to go back? (1: Return)","Wil je teruggaan? (1: Ga terug)"][taal]
                    npc_text_timer = current_time + 5000
                    if keys[pygame.K_1]:
                        current_area = 12
                        player_img = pygame.image.load(os.path.join(ASSETS_PATH, "Player1.png"))
                        player_img = pygame.transform.scale(player_img, (player_size, player_size)) 
                        npc_text = ""
                        fade_out()
            elif island.current_area == 1: 
                screen.fill(GREEN)
            elif island.current_area == 2: 
                screen.fill(BROWN)
                mine_size = 150
                entrance_size = 110
                entrance_rect = pygame.Rect((WIDTH - entrance_size) // 2, (HEIGHT - mine_size) // 2 + (mine_size - entrance_size), entrance_size, entrance_size)
                pygame.draw.rect(screen,GREY,((WIDTH - mine_size) // 2, (HEIGHT - mine_size) // 2, mine_size, mine_size))
                pygame.draw.rect(screen,BLACK,(entrance_rect))
                if entrance_rect.colliderect(player_rect) and interact_key_down:
                    current_area = 14
                    player_pos = [WIDTH // 2, HEIGHT - player_size - 100]
                    fade_out()
            elif island.current_area == 3: 
                screen.fill(GREEN)
                lake_size = HEIGHT // 3
                lake_rect = pygame.Rect((WIDTH - lake_size) // 2, (HEIGHT - lake_size) // 2, lake_size, lake_size)
                pygame.draw.rect(screen,(50,50,250),lake_rect)
                if lake_rect.colliderect((player_pos[0],player_pos[1],player_size,player_size)):
                    if not lake_rect.colliderect((old_player_pos[0],player_pos[1],player_size,player_size)): player_pos[0] = old_player_pos[0]
                    else: player_pos[1] = old_player_pos[1]
                if convert_rect_to_interactrect(lake_rect, 10).colliderect((player_pos[0],player_pos[1],player_size,player_size)) and interact_key_just_pressed and current_minigame == None: fishing_game()

            screen.blit(island.ocean,(0,0))

            if island.pos[0] == 0:
                player_pos[0] = max(player_pos[0], island.ocean_indent)
            if island.pos[0] == island.sizex - 1:
                player_pos[0] = min(player_pos[0], WIDTH - island.ocean_indent - player_size)
            if island.pos[1] == 0:
                player_pos[1] = max(player_pos[1], island.ocean_indent)
            if island.pos[1] == island.sizey - 1:
                player_pos[1] = min(player_pos[1], HEIGHT - island.ocean_indent - player_size)
            
            direction = -1
            if player_pos[1] < 10: 
                player_pos[1] = HEIGHT - player_size - 10
                direction = 3
            elif player_pos[0] < 10: 
                player_pos[0] = WIDTH - player_size - 10
                direction = 1
            elif player_pos[0] > WIDTH - player_size - 10:
                player_pos[0] = 10
                direction = 0
            elif player_pos[1] > HEIGHT - player_size - 10:
                player_pos[1] = 10
                direction = 2
            if direction != -1: island.move(direction)
        
        elif old_area == 14: #Turmeric Cave
            screen.fill((55,37,12))
            altar_pos = (WIDTH-player_size)//2,(HEIGHT-player_size)//2

            if in_cutscene:
                pygame.draw.rect(screen,BLACK,(0,0,WIDTH,HEIGHT//10))
                pygame.draw.rect(screen,BLACK,(0,9*HEIGHT//10,WIDTH,HEIGHT//10))
                in_cutscene += 60 * last_frame_time
                round_in_cutscene = round(in_cutscene)
                if in_cutscene > 240 + 360:
                    pygame.draw.rect(screen,BLACK,(altar_pos[0],altar_pos[1],player_size,player_size))
                    pygame.draw.rect(screen,GREY,(altar_pos[0] + (360 - 120) // 4,altar_pos[1],player_size,player_size))
                elif in_cutscene > 240 + 120:
                    pygame.draw.rect(screen,BLACK,(altar_pos[0],altar_pos[1],player_size,player_size))
                    pygame.draw.rect(screen,GREY,(altar_pos[0] + (round_in_cutscene - 120 - 240) // 4,altar_pos[1],player_size,player_size))
                elif in_cutscene > 120:
                    pygame.draw.rect(screen,GREY,(altar_pos[0],altar_pos[1],player_size,player_size))
                    altar_img = pygame.transform.scale(pygame.image.load(os.path.join(ASSETS_PATH, 'Altar.png')), (player_size, player_size)).convert_alpha()
                    altar_img.set_alpha(255 - min(255,round((in_cutscene - 120) * 255 / 180)))
                    screen.blit(altar_img, altar_pos)
                else:
                    pygame.draw.rect(screen,GREY,(altar_pos[0],altar_pos[1],player_size,player_size))
                    altar.draw(current_area)
                if in_cutscene > 240 + 360 + 3 * 120:
                    in_cutscene = False
                    npc_text = "Mia: " + ["You saved me from those dark depths! Here's a thank you.","Je hebt me gered uit die duistere diepten! Hier, een bedankje."][taal]
                    npc_text_timer = current_time + 5000
                    accumulated_money += 10000
                if in_cutscene > 240 + 360 + 120 + 120:
                    mia_img = pygame.transform.scale(pygame.image.load(os.path.join(ASSETS_PATH, 'Mia.png')), (player_size, player_size))
                    screen.blit(mia_img,(altar_pos[0],altar_pos[1] + player_size // 2 + (round_in_cutscene - (240 + 360 + 2 * 120)) // 2))
                elif in_cutscene > 240 + 360 + 120:
                    mia_img = pygame.transform.scale(pygame.image.load(os.path.join(ASSETS_PATH, 'Mia.png')), (player_size, player_size))
                    screen.blit(mia_img,(altar_pos[0],altar_pos[1] + player_size // 2))
            elif altar.spokento:
                pygame.draw.rect(screen,BLACK,(altar_pos[0],altar_pos[1],player_size,player_size))
                pygame.draw.rect(screen,GREY,(altar_pos[0] + (360 - 120) // 4,altar_pos[1],player_size,player_size))
                mia.draw(current_area)
                if is_interacting(player_pos, mia, current_area, interact_key_down):
                    interacted_npcs.append('mia')
                    if npc_text == '':
                        npc_text = "Mia: " + ["I wouldn't go in that hole if I were you. It's way too dangerous!","Als ik jou was, zou ik niet in dat gat gaan. 'T is daar veel te gevaarlijk!"][taal]
                        npc_text_timer = current_time + 5000
                if is_interacting(player_pos, altar, current_area, interact_key_down):
                    if mia.spokento or True:
                        current_area = 15
                        fade_out()
                        interact_key_down = False
                        player_pos = [5000 // 2, 5000 // 2]
                        area_size = (5000,5000)
                    else:
                        npc_text = "Mia: " + ["Don't you dare go in there. For your own safety!","Waag het niet om daar naar binnen te gaan. Voor je eigen veiligheid!"][taal]
                        npc_text_timer = current_time + 3000
            else:
                pygame.draw.rect(screen,GREY,(altar_pos[0],altar_pos[1],player_size,player_size))
                altar.draw(current_area)
                if is_interacting(player_pos, altar, current_area, interact_key_down):
                    if altar.spokento:
                        pass
                    else:
                        npc_text = ["It seems you have to sacrifice something... crimson.","Het lijkt erop dat je iets... bloedroods op moet offeren."][taal]
                        journal.append("altar")
                        if inventory.get_nth_named("crimsonfish"):
                            npc_text += [" (Press 1)"," (Druk op 1)"][taal]
                            if keys[pygame.K_1] and inventory.get_nth_named("crimsonfish",delete=True):
                                journal.mark_done("altar")
                                altar.spokento = True
                                npc_text = ''
                                in_cutscene = 1
                                fade_out()
                                player_pos = [altar_pos[0],altar_pos[1] + HEIGHT // 5]
                                pygame.draw.rect(screen,GREY,(altar_pos[0],altar_pos[1],player_size,player_size))
                        npc_text_timer = current_time + 5000
            
            if player_pos[1] > HEIGHT - player_size - 10 and current_area == 14:
                fade_out()
                player_pos = [(WIDTH - player_size) // 2, HEIGHT // 2 + 40]
                current_area = 13
        
        elif old_area == 15: #Lower cave
            area_size = (5000,5000)
            screen.fill(BROWN)
            vision = 400 if has_torch else 80
            camera_pos = (max(min(player_pos[0] + (player_size - WIDTH) // 2, area_size[0] - WIDTH), 0), max(min(player_pos[1] + (player_size - HEIGHT) // 2, area_size[1] - HEIGHT), 0))
            player_screen_pos = [player_pos[0] - camera_pos[0],player_pos[1] - camera_pos[1]]
            light_rects.append(pygame.Rect(player_screen_pos[0] - vision // 2, player_screen_pos[1] - vision // 2, vision + player_size, vision + player_size))
            stones = island.areainfo[island.pos[1]][island.pos[0]]
            print(island.types[(island.pos[1],island.pos[0])])
            for y, col in enumerate(stones):
                for x, stone in enumerate(col):
                    if stone:
                        if stone in {1,2,3,4}:
                            color = [
                                (80,0,80),
                                (10,10,20),
                                (20,20,10),
                                (0,50,255)
                            ][stone - 1]
                            pygame.draw.rect(screen, color, (x * 100 - camera_pos[0], y * 100 - camera_pos[1], 100, 100))
                        elif stone == -1:
                            screen.blit(pygame.transform.scale(load_img_from_assets("Ladder.png"),(100,100)),(x * 100 - camera_pos[0], y * 100 - camera_pos[1]))
            
            cmidpoint = (player_pos[0] // 100, player_pos[1] // 100)
            player_rect = pygame.Rect(player_pos[0], player_pos[1], player_size, player_size)
            startx = max(cmidpoint[0] - 4, 0)
            starty = max(cmidpoint[1] - 4, 0)
            if interact_key_down: player_interact_rect = pygame.Rect(player_pos[0] - 6, player_pos[1] - 6, player_size + 12, player_size + 12)
            for y, col in enumerate(stones[starty : min(cmidpoint[1] + 4, len(stones))]):
                if current_area != 15: break
                for x, stone in enumerate(col[startx : min(cmidpoint[0] + 4, len(col))]):
                    if stone:
                        thisx = x + startx
                        thisy = y + starty
                        stone_rect = pygame.Rect(thisx * 100, thisy * 100, 100, 100)
                        if interact_key_down and stone_rect.colliderect(player_interact_rect):
                            if stone == -1:
                                current_area = 14
                                player_pos = [WIDTH // 2, HEIGHT // 2]
                                fade_out()
                                break
                            elif stamina >= 20 and stone != 1:
                                if not no_stamina_system: stamina -= 20
                                if stone == 4:
                                    if not inventory.pickup('diamond',value=500): print('inventory full!')
                                    npc_text = ["You found a diamond!","Je hebt een diamant gevonden!"][taal]
                                    npc_text_timer = current_time + 3000
                                stones[thisy][thisx] = 0
                                rockchanges.append((island.pos,(thisy,thisx),0))
                        if stone_rect.colliderect(player_rect) and stone != -1:
                            player_rect = pygame.Rect(old_player_pos[0], player_pos[1], player_size, player_size)
                            if not stone_rect.colliderect(player_rect): player_pos[0] = old_player_pos[0]
                            else:
                                player_rect = pygame.Rect(player_pos[0], old_player_pos[1], player_size, player_size)
                                if not stone_rect.colliderect(player_rect): player_pos[1] = old_player_pos[1]
                                else: player_pos = [old_player_pos[0], old_player_pos[1]]
        
        elif old_area == 16: #Tommywood
            screen.fill((240, 0, 255))

            for x in range(0, WIDTH, 100):
                for y in range(0, HEIGHT, 100):
                    pygame.draw.rect(screen, (x % 255, y % 255, (x * y) % 255), (x, y, 100, 100), 0)
            
            glitch_colors = [(255, 255, 255), (0, 255, 0), (0, 255, 255)]
            for i in range(0, WIDTH, 50):
                pygame.draw.line(screen, glitch_colors[(i + frame_counter) % 3], (i, 0), (i, HEIGHT), 1)

            tommycash.draw(current_area)

            if is_interacting(player_pos, tommycash, current_area, interact_key_down):
                if day == 50 and not fixed_geluidsoverlast1:
                    npc_text = "Tommy Cash: " + [
                        "Give this to Max as a sorry!",
                        "Geef dit aan Max als een sorry!"
                    ][taal]
                    npc_text_timer = current_time + 5000
                    fixed_geluidsoverlast1 = True
                    journal.remove('geluid1')
                    journal.append('geluid2')
                if day == 50 and fixed_geluidsoverlast1:
                    npc_text = "Tommy Cash: " + [
                        "Reality is a concept. Dance, my glitchy child.",
                        "Realiteit is een concept. Dans, mijn glitch-kind."
                    ][taal]
                    npc_text_timer = current_time + 5000

            studio_rect = pygame.Rect(WIDTH - 150, HEIGHT//2 - 50, 150, 100)
            pygame.draw.rect(screen, (200, 200, 0), studio_rect)
            screen.blit(font.render("STUDIO X", True, (0, 0, 0)), (studio_rect.x + 10, studio_rect.y + 35))

            if player_pos[0] + player_size > studio_rect.left and player_pos[0] < studio_rect.right and \
            player_pos[1] + player_size > studio_rect.top and player_pos[1] < studio_rect.bottom and \
            interact_key_down:
                current_area = 17
                fade_out()

        elif old_area == 17:  #Studio X 
            screen.fill((0, 255, 255))  
            player_rect = pygame.Rect(player_pos[0],player_pos[1],player_size,player_size)
            
            for x in range(0, WIDTH, 40):
                pygame.draw.line(screen, (0, 0, 0), (x, 0), (x, HEIGHT), 1)
            for y in range(0, HEIGHT, 40):
                pygame.draw.line(screen, (0, 0, 0), (0, y), (WIDTH, y), 1)

            for i in range(5):
                x = (i * 150 + pygame.time.get_ticks() // 10) % WIDTH
                y = (i * 70 + pygame.time.get_ticks() // 15) % HEIGHT
                pygame.draw.ellipse(screen, (255, i * 50, 255 - i * 50), (x, y, 60, 40))

            metakunst.draw(current_area)
            if is_interacting(player_pos, metakunst, current_area, interact_key_down):
                if npc_text == "":
                    npc_text = "Meta-Kunstenaar: " + [
                        "Is this game art, or are you the canvas? (1: Yes) (2: Bread)",
                        "Is dit spel kunst, of ben jij het canvas? (1: Ja) (2: Brood)"
                    ][taal]
                    npc_text_timer = current_time + 6000

                elif keys[pygame.K_1]:
                    npc_text = ["Meta-Kunstenaar: You ARE the art. Morph yourself.", "Meta-Kunstenaar: Jij BENT de kunst. Vervorm jezelf."][taal]
                    npc_text_timer = current_time + 5000
                elif keys[pygame.K_2]:
                    npc_text = ["Meta-Kunstenaar: Bread is the ultimate form.", "Meta-Kunstenaar: Brood is de ultieme vorm."][taal]
                    npc_text_timer = current_time + 5000

            glitch_rect = pygame.Rect(WIDTH//2 - 75, HEIGHT - 100, 150, 80)
            pygame.draw.rect(screen, (255, 255, 0), glitch_rect)
            screen.blit(font.render("GLITCH ZONE", True, (0, 0, 0)), (glitch_rect.x + 10, glitch_rect.y + 30))

            if player_rect.colliderect(glitch_rect):
                controls_modifier = -0.75
                npc_text = ["Reality breaks. Controls reversed!", "De werkelijkheid breekt. Besturing is omgekeerd!"][taal]
                npc_text_timer = current_time + 4000
            elif npc_text == '': controls_modifier = 1

            exit_rect = pygame.Rect(20, HEIGHT - 80, 190, 60)
            pygame.draw.rect(screen, (0, 0, 0), exit_rect)
            screen.blit(font.render("<- Tommywood", True, (255, 255, 255)), (exit_rect.x + 5, exit_rect.y + 20))

            if player_rect.colliderect(exit_rect) and interact_key_down:
                current_area = 16
                player_pos = [WIDTH - 100, HEIGHT // 2 - 30]
                fade_out()
        
        elif old_area == 18: #0->3
            pass

        elif old_area == 19: #Ben
            if day not in {10,20,30} and (game_time_minutes < 720 or game_time_minutes >= 900): ben.draw(current_area)
            
            if is_interacting(player_pos, ben, current_area, interact_key_down) and npc_text == "":
                interacted_npcs.append('ben')
                if worldmap.requirements[8] and not perfection:
                    npctext.set_message(["Ben: Thank you.","Ben: Dankje."][taal],ben.pos)
                    journal.remove('endgame1')
                    endgame[0] = True
                    journal.append('endgame2')
                elif has_keys[0]:
                    npctext.set_message(["Ben: This key belonged to your predecessor. Michael knew him well.","Ben: Deze sleutel was van jouw voorganger. Michael kende hem goed."][taal],ben.pos)
                    npc_text_timer = current_time + 5000
                    journal.remove('key1')
                    journal.append('key2')
                    has_keys[1] = True
                elif day == 1:
                    npctext.set_message(["Ben: Welcome to Hanztown, I am the mayor. Clear the wood and you will get money.","Ben: Welkom in Hanztown, ik ben de burgemeester. Ruim het hout op en je krijgt geld."][taal],ben.pos)
                elif day == 17 and not told_about_moonfish:
                    npctext.set_message(["Ben: Did you see that blue moon last night? The moonfish love it!", "Ben: Heb je die blauwe maan vannacht gezien? De maanvissen zijn er dol op!"][taal],ben.pos)
                    told_about_moonfish = True
                
                elif not has_keys[0]:
                    if day == 28 or day == 29: 
                        npctext.set_message(["Ben: Vote for me and you can travel to Tixcity and beyond for free forever!","Ben: Stem op mij en je mag voor altijd gratis naar Tixcity en daarbuiten reizen!"][taal],ben.pos)
                    elif day <= 8:
                        npctext.set_message("Ben: " + random.choice(DIALOOG_BEN1),ben.pos)
                        if money < 100 and day < 5: accumulated_money += 250
                    elif day <= 17:
                        npctext.set_message("Ben: " + random.choice(DIALOOG_BEN2),ben.pos)
                    elif day >= 17 and day != 25:
                        npctext.set_message("Ben: " + random.choice(DIALOOG_BEN3),ben.pos)
                        
                elif ben.messageOverride.endswith("...") and 2 not in visited:
                    npctext.set_message(ben.messageOverride,ben.pos)
                elif day == 5 and not has_rod:
                    npctext.set_message(["Ben: Pick up a free fishing rod.","Ben: Haal een gratis vishengel op."][taal],ben.pos)
                    journal.append('find_mstore')
                elif day == 25 and not has_card:
                    npctext.set_message(["Ben: Try fishing...","Ben: Probeer te vissen..."][taal],ben.pos)
                    card_available = True
                    journal.append('go_fish')
                elif day == 29 and not ben_mayor1 and not michael_mayor1:
                    npctext.set_message(["Ben: Vote for me and you can travel to Tixcity and beyond for free forever!","Ben: Stem op mij en je mag voor altijd gratis naar Tixcity en daarbuiten reizen!"][taal],ben.pos)
                elif claimed_tree_money == False: accumulated_money += 200

        elif old_area == 20: #Michael
            if (robot_purchased and not robot["should_draw"]) or not robot_purchased and day not in [10,20,30]: michael.draw(current_area, 0)

            if is_interacting(player_pos, michael, current_area):
                interacted_npcs.append('michael')
                in_selling_range = True
                if interact_key_down:
                    if finished_list[1] and not finished_list[2]:
                        journal.remove('list2')
                        michael_on_cooldown = True
                        finished_list[2] = True
                        npctext.set_message(["Michael: I forgive him.", "Michael: Ik vergeef hem."][taal],michael.pos)
                    elif has_keys[1] and not michael_on_cooldown:
                        npctext.set_message(["Michael: This was the key to his chicken coop. Leah knows a lot about animals, just ask her.","Michael: Dit was de sleutel van zijn kippenhok. Leah weet veel van dieren, vraag het maar aan haar."][taal],michael.pos)
                        journal.remove('key2')
                        journal.append('key3')
                        has_keys[2] = True
                    else:
                        if day == 1: npctext.set_message([
                                "Michael: Welcome to my store. Ben is already getting everything you need, so you don't have to buy anything here yet!",
                                "Michael: Welkom bij mijn winkel. Ben haalt al alles wat je nodig hebt, dus je hoeft hier nog niks te kopen!"
                            ][taal],michael.pos)
                        elif day == 5 and not has_rod:
                            npctext.set_message([
                                "Michael: Here's a fishing rod.",
                                "Michael: Hier is een vishengel."
                            ][taal],michael.pos)
                            has_rod = True
                            journal.mark_done('find_mstore')
                        elif day in [10, 20]: npctext.set_message(([
                                "Michael is enjoying the festival.",
                                "Michael is aan het genieten van het festival."
                            ][taal],{'thinking':True}),michael.pos)
                        elif day in [28, 29]: npctext.set_message([
                                "Michael: Vote for me and you can travel to Maxdesert for free forever!",
                                "Michael: Stem voor mij en je mag voor altijd gratis naar Maxdesert reizen!"
                            ][taal],michael.pos)

                        elif day == 30:
                            if michael_mayor1: npctext.set_message([
                                    "Michael: This is my victory party.",
                                    "Michael: Dit is mijn overwinningsfeestje."
                                ][taal],michael.pos)
                            else: npctext.set_message([
                                    "Michael: This is a sad day.",
                                    "Michael: Dit is een verdrietige dag."
                                ][taal],michael.pos)

                        elif michael_on_cooldown and not robot_purchased:
                            npc_text.set_message("Michael: " + ["Sorry, I'm busy right now. Come back later.","Sorry, ik ben even bezig. Kom later maar terug."][taal],michael.pos)
                        elif day >= 8 and not in_shop and not robot_purchased:
                            if keys[pygame.K_1]: in_shop = 'michael'

                            npctext.set_message("Michael: " + ["Do you want to buy anything? (1: Open shop)","Wil je iets kopen? (1: Open winkel)"][taal],michael.pos)

                            if npc_text == '' and not robot_purchased:
                                npc_text = npctext.set_message(michael.get_message(),michael.pos)

                        elif npc_text == '' and chicken_amount >= 1 and not robot_purchased:
                            npctext.set_message((["Michael is shocked by the giant chicken.","Michael is geschokeerd door de grote kip."][taal],{'thinking':True}),michael.pos)
                        elif not robot_purchased:
                            npc_text = npctext.set_message(michael.get_message(),michael.pos)

            else: in_selling_range = False
        elif old_area == 21: #Leah
            if not married or day % 4: leah.draw(current_area, 1 if married else 0)

            if is_interacting(player_pos, leah, current_area, interact_key_down):
                interacted_npcs.append('leah')
                if not given_gift: journal.append('romance')
                if has_keys[2]:
                    npctext.set_message(["Leah: The chicken coop was somewhere in the desert. Just ask the locals.","Leah: Het kippenhok stond ergens in de woestijn. Vraag het de lokale bewoners maar."][taal],leah.pos)
                    journal.remove('key3')
                    journal.append('key4')
                    has_keys[3] = True
                elif has_gift:
                    gift = inventory.get_nth_tagged('giftable',delete=True)
                    if has_gift and gift and not given_gift:
                        npctext.set_message(["Leah: You gave me a squirrel... that's the nicest thing anyone's ever done for me. Yeah... let's be together. You, me, and maybe a few more squirrels.","Leah: Je gaf me een eekhoorn... dat is het mooiste wat iemand ooit voor me gedaan heeft. Ja... laten we samen zijn. Jij, ik, en misschien nog een paar eekhoorns."][taal],leah.pos)
                        has_gift = False
                        given_gift = True
                        leah_on_cooldown = True
                        journal.mark_done('gift_leah')
                elif given_gift and not leah_on_cooldown:
                    if married:
                        npctext.set_message("Leah: " + ["I'm glad we have made this decision.","Ik ben blij dat we deze keuze hebben gemaakt."][taal],leah.pos)
                    else:
                        play_video('movie1.mp4','movie1.mp3')
                        married = True
                        if not day % 4: leah.location = 7
                elif day % 4:
                    chicken_price = round((chicken_amount + 1)*chicken_price_increase * (0.75 if given_gift else 1))
                    if day == 1 and not leah_on_cooldown:
                        npctext.set_message([f"Leah: Hi, I'm Leah! You can buy cute animals from me for €{chicken_price}! (1: Buy a chicken)",f"Leah: Hallo, ik ben Leah! Je kunt bij mij schattige dieren kopen voor €{chicken_price}! (1: Koop een kip)"][taal],leah.pos)
                    elif day != 1 and not leah_on_cooldown:
                        npctext.set_message([f"Leah: You can buy cute animals from me for €{chicken_price}! (1: Buy a chicken)",f"Leah: Je kunt bij mij schattige dieren kopen voor €{chicken_price}! (1: Koop een kip)"][taal],leah.pos)
                    
                    if money >= chicken_price and keys[pygame.K_1]:
                        time.sleep(0.25)
                        accumulated_money -= chicken_price
                        chicken_amount += 1
                        if romancepoints < 25:
                            romancepoints += 1
                        wildlife.append(Wildlife([0,2,11], random.randint(1,10)**2, "chicken.gif",area_size=(tilemaps[0].pixsize if 0 in tilemaps else (WIDTH,HEIGHT))))

                    if not leah_on_cooldown and romancepoints < 25:
                        romancepoints += 1
                        leah_on_cooldown = True

                elif npc_text == '' and not leah_on_cooldown:
                    if not given_gift:
                        if romancepoints <= 8:
                            npctext.set_message("Leah: " + random.choice(DIALOOG_LEAH1),leah.pos)
                        elif romancepoints <= 16:
                            npctext.set_message("Leah: " + random.choice(DIALOOG_LEAH2),leah.pos)
                        elif romancepoints <= 24:
                            npctext.set_message("Leah: " + random.choice(DIALOOG_LEAH3),leah.pos)
                        if not leah_on_cooldown:
                            romancepoints = min(romancepoints + 2, 25)
                            leah_on_cooldown = True
                    else:
                        npctext.set_message((["Leah is admiring the scenery happily and doesn't seem to notice you.","Leah bewondert met plezier het landschap en lijkt jou niet op te merken."][taal],{'thinking':True}),leah.pos)

        elif old_area == 22: #Snackbar
            mscoffi.draw(current_area)
            journal.remove('key8')
            if election_day == 2: mailbox.draw(current_area, 1 if mail_content or day == 29 else 0)

            if not in_shop and is_interacting(player_pos, mscoffi, current_area, interact_key_down):
                if election_day == 2:
                    npc_text = [
                        ["Ms. Coffi: I will now explain what the positions of the two candidates are:", "Ms. Coffi: Ik ga nu uitleggen wat de standpunten zijn van de twee kandidaten:"][taal],
                        ["Ms. Coffi: Michael is going to give money to Tumeric Island so they can build a mega resort where tourists can chill out, so the tourist flow will decrease.", "Ms. Coffi: Michael gaat geld geven aan Tumeric Island, zodat zij een megaresort kunnen bouwen waar toeristen kunnen chillen, zodat de toeristenstroom daalt."][taal],
                        ["Ms. Coffi: Ben is going to give money to local businesses so they can lower prices by 10%.", "Ben gaat geld geven aan de lokale ondernemers, zodat zij de prijzen kunnen verlagen met 10%."][taal],
                    ]
                elif election_day != 2:
                    npctext.set_message("Ms. Coffi: " + ["Hi! Would you like to buy some coffee? (1: View shop)", "Hoi! Wil je wat koffie kopen? (1: Bekijk winkel)"][taal],leah.pos)
                    if keys[pygame.K_1]: in_shop = 'coffee'

            if player_pos[1] > HEIGHT - player_size - 10: 
                fade_out()
                player_pos = [WIDTH // 2, HEIGHT // 2]
                current_area = 0

            if is_interacting(player_pos, mailbox, current_area, interact_key_down):
                if election_day == 2 and (not ben_mayor2 and not michael_mayor2):
                    npc_text = ["Vote! (1: Ben, 2: Michael)","Stem! (1: Ben, 2: Michael)"][taal]
                    if keys[pygame.K_1]: 
                        ben_mayor2 = True
                        michael_mayor2 = False
                        npc_text = ["You voted for Ben.","Je hebt gestemd voor Ben."][taal]
                        npc_text_timer = current_time + 5000
                    if keys[pygame.K_2]:           
                        ben_mayor2 = False
                        michael_mayor2 = True       
                        npc_text = ["You voted for Michael.","Je hebt gestemd voor Michael."][taal]
                        npc_text_timer = current_time + 5000
            
        if old_area == 0:
            if False: screen.blit(forest_area_overlay,camera_offset)
        if old_area == 0: #Overworld #elif
            if "flags" in daily_mods: draw_flags()

            if 'chat' in server_data: display_text_pro(server_data['chat'], (WIDTH//2, 100), (0,0,0,255), pygame.font.Font(None, 50))


            if "rain" in daily_mods:
                for p in particles:
                    p.draw(CYAN)
            
            if "rain" in daily_mods:
                for drop in raindrops:
                    pygame.draw.line(screen, (0, 0, 255), (drop["x"]+camera_offset[0], drop["y"]+camera_offset[1]), (drop["x"]+camera_offset[0], drop["y"]+camera_offset[1] + 10), 2)
                    drop["y"] += rain_speed
                    if drop["y"] > tilemaps[0].pixsize[1]:
                        drop["x"] = random.randint(0, tilemaps[0].pixsize[0])
                        drop["y"] = random.randint(-tilemaps[0].pixsize[1], 0)
            if "thunder" in daily_mods:
                if random.randint(0,round(5/last_frame_time)) == 0: bolts.append(LightningBolt(area_size))
                for b in bolts:
                    if b.tick_and_draw(last_frame_time):
                        bolts.remove(b)
                        continue
                        
            for i, tree in [(i, tree) for i, tree in trees.items() if i in server_data['trees'] and i not in deleted_trees]:
                if chop_tree(player_pos, tree, tree_size) and interact_key_down and stamina >= 15:
                    deleted_trees.append(i)
                    treechanges.append(i)
                    if not no_stamina_system: stamina -= 15
                    inventory.pickup('wood', value=0, dispName=["Wood", "Hout"][taal])
                    break
            if not server_data['trees']:
                if is_interacting(player_pos, ben, current_area, interact_key_down):
                    interacted_npcs.append('ben')
                    if ben.messageOverride.endswith("...") and 2 not in visited:
                        npctext.set_message(ben.messageOverride,ben.pos)
                    elif day == 5 and not has_rod:
                        npctext.set_message(["Ben: Pick up a free fishing rod.","Ben: Haal een gratis vishengel op."][taal],ben.pos)
                        journal.append('find_mstore')
                    elif day in [10,20]:
                        npctext.set_message(["Ben: Tix is a very good player. You try to beat him!","Ben: Tix is een erg goede speler. Probeer jij hem maar te verslaan!"][taal],ben.pos) 
                    elif day == 25 and not has_card:
                        npctext.set_message(["Ben: Try fishing...","Ben: Probeer te vissen..."][taal],ben.pos)
                        card_available = True
                        journal.append('go_fish')
                    elif day == 29 and not ben_mayor1 and not michael_mayor1:
                        npctext.set_message(["Ben: Vote for me and you can travel to Tixcity and beyond for free forever!","Ben: Stem voor mij en je mag voor altijd gratis naar Tixcity en daarbuiten reizen!"][taal],ben.pos)
                    elif day == 30:
                        if ben_mayor1:
                            npctext.set_message(["Ben: This is my victory party.","Ben: Dit is mijn overwinningsfeestje."][taal],ben.pos)
                        else:
                            npctext.set_message(["Ben: This is a sad day.","Ben: Dit is een verdrietige dag."][taal],ben.pos)
                    elif claimed_tree_money == False: accumulated_money += 200

            if is_interacting(player_pos, mailbox, current_area, interact_key_down):
                if mail_content: 
                    if not (len(npc_text) > 5 and npc_text[:5] == "Mail:"):
                        if isinstance(mail_content[0], list):
                            if mail_content[0][1] == 'timedquest':
                                npc_text = mail_content[0][0]
                                journal.timedquest.activate(day)
                        else:
                            npc_text = mail_content[0]
                        mail_content.pop(0)
                        npc_text_timer = current_time + 5000
                        if day == 6:
                            journal.append('find_tixcity')
                        elif day == 18:
                            journal.append('find_max')
                        elif day == 40:
                            journal.append('max')
                elif day == 29 and not ben_mayor1 and not michael_mayor1:
                    npc_text = ["Vote! (1: Ben, 2: Michael)","Stem! (1: Ben, 2: Michael)"][taal]
                    if keys[pygame.K_1]: 
                        ben_mayor1 = True
                        michael_mayor1 = False
                        npc_text = ["You voted for Ben.","Je hebt gestemd voor Ben."][taal]
                        npc_text_timer = current_time + 5000
                    if keys[pygame.K_2]:           
                        ben_mayor1 = False
                        michael_mayor1 = True       
                        npc_text = ["You voted for Michael.","Je hebt gestemd voor Michael."][taal]
                        npc_text_timer = current_time + 5000
                elif npc_text == '':
                    npc_text = ["The mailbox is empty.","De mailbox is leeg."][taal]
                    npc_text_timer = current_time + 5000

            if day == 59: bouncer.draw(current_area)
            if is_interacting(player_pos, bouncer, current_area, interact_key_down) and day == 59:
                if not has_goedje:
                    npc_text = ["Bouncer: Do you want drugs? The effects will kick in tomorrow. (CAUTION: IT WILL MAKE THE GAME A LOT WEIRDER) (1: Take)","Bouncer: Wil je drugs? De effecten zullen morgen merkbaar zijn. (LET OP: HET ZAL HET SPEL EEN STUK RAARDER MAKEN) (1: Neem)"][taal]
                    if keys[pygame.K_1]:
                        has_goedje = True
                if has_goedje:
                    npctext.set_message(["Bouncer: Thanks.","Bouncer: Bedankt."][taal],bouncer.pos)
            #elif is_interacting(player_pos, random_person, current_area, interact_key_down) and 5 not in visited and day != 59:
                #npc_text = random_person.check_quest(npc_text) 
            if is_interacting(player_pos, ben, current_area, interact_key_down) and trees and npc_text == "":
                if day in [10,20]:
                    npctext.set_message(["Ben: Tix is a very good player. You try to beat him!","Ben: Tix is een erg goede speler. Probeer jij hem maar te verslaan!"][taal],ben.pos)
                if day == 30:
                    if ben_mayor1:
                        npctext.set_message(["Ben: This is my victory party.","Ben: Dit is mijn overwinningsfeestje."][taal],ben.pos)
                    else:
                        npctext.set_message(["Ben: This is a sad day.","Ben: Dit is een verdrietige dag."][taal],ben.pos)
                
            if is_interacting(player_pos, leah, current_area, interact_key_down):
                pass

            if is_interacting(player_pos, michael, current_area):
                if day in [10, 20]: npctext.set_message(([
                    "Michael is enjoying the festival.",
                    "Michael is aan het genieten van het festival."
                ][taal],{'thinking':True}),michael.pos)
                if day == 30:
                    if michael_mayor1: npctext.set_message([
                            "Michael: This is my victory party.",
                            "Michael: Dit is mijn overwinningsfeestje."
                        ][taal],michael.pos)
                    else: npctext.set_message([
                            "Michael: This is a sad day.",
                            "Michael: Dit is een verdrietige dag."
                        ][taal],michael.pos)

            if is_interacting(player_pos, tix, current_area, interact_key_down):
                interacted_npcs.append('tix')
                if day == 10:
                    npc_text = ["Tix: Do you want to play a game? (1: Yes, 2: Rules)","Tix: Wil je een spelletje spelen? (1: Ja, 2: Regels)"][taal]
                    if keys[pygame.K_1]:
                        festival_game1()
                    if keys [pygame.K_2]:
                        npc_text = ["Tix: Score higher than me under 21. H = Hit and S = Stand.","Tix: Scoor hoger dan ik onder 21. H = Hit en S = Stand."][taal]
                    npc_text_timer = current_time + 5000   
                elif day == 20:
                    npc_text = ["Tix: Do you want to play a game? (1: Yes, 2: Rules)","Tix: Wil je een spelletje spelen? (1: Ja, 2: Regels)"][taal]
                    if keys[pygame.K_1]: 
                        festival_game2()
                    if keys [pygame.K_2]:
                        npc_text = ["Tix: It's rock, paper, scissors, but with two hands.","Tix: Het is steen, papier, schaar, maar dan met twee handen."][taal]
                    npc_text_timer = current_time + 5000
                elif day == 30:
                    npc_text = ["Tix: I am politically neutral, but every good businessman comes to an afterparty.","Tix: Ik ben politiek neutraal, maar iedere goede zakenman komt naar een afterparty."][taal]
                    npc_text_timer = current_time + 5000
            def festival_game1():
                font = pygame.font.Font(None, 36)

                RANKS1 = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"]
                RANKS2 = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]

                def create_deck(ranks):
                    deck = [rank for rank in ranks for _ in range(4)]
                    random.shuffle(deck)
                    return deck

                def card_value(card):
                    return int(card)

                def calculate_score(hand):
                    return sum(card_value(card) for card in hand)

                def reset_game():
                    nonlocal deck, player_hand, dealer_hand, game_over, player_turn, result_text, result_color
                    deck = create_deck(RANKS2)
                    player_hand = [random.choice(RANKS1), deck.pop()]
                    dealer_hand = [random.choice(RANKS1), deck.pop()]
                    game_over = False
                    player_turn = True
                    result_text = ""
                    result_color = WHITE

                deck = create_deck(RANKS2)
                player_hand = [random.choice(RANKS1), deck.pop()]
                dealer_hand = [random.choice(RANKS1), deck.pop()]
                game_over = False
                player_turn = True
                result_text = ""
                result_color = WHITE

                def render_text(text, x, y, color=WHITE):
                    surface = font.render(text, True, color)
                    screen.blit(surface, (x, y))

                running = True
                
                while running:
                    screen.fill(GREEN)

                    for event in pygame.event.get():
                        if not game_over and player_turn:
                            if event.type == pygame.KEYDOWN:
                                keys = pygame.key.get_pressed()
                                if keys[pygame.K_ESCAPE]:
                                    return
                                if event.key == pygame.K_h:  
                                    player_hand.append(deck.pop())
                                    if calculate_score(player_hand) > 21:
                                        game_over = True
                                        result_text = "Tix: Volgende keer beter!"
                                        result_color = RED
                                if event.key == pygame.K_s:  
                                    player_turn = False

                    if not player_turn and not game_over:
                        while calculate_score(dealer_hand) < 17:
                            dealer_hand.append(deck.pop())
                        game_over = True

                        player_score = calculate_score(player_hand)
                        dealer_score = calculate_score(dealer_hand)

                        if player_score > 21:
                            result_text = "Tix: Volgende keer beter!"
                            result_color = RED
                        elif dealer_score > 21 or player_score > dealer_score:
                            result_text = "Tix: Je hebt gewonnen..."
                            result_color = WHITE
                        elif player_score == dealer_score:
                            result_text = "Tix: Gelijkspel!"
                            result_color = WHITE
                        else:
                            result_text = "Tix: Volgende keer beter!"
                            result_color = RED

                    render_text("Jouw hand:", 50, 50)
                    for i, card in enumerate(player_hand):
                        render_text(f"{card}", 50, 100 + i * 30)

                    render_text("Tix' hand:", 400, 50)
                    for i, card in enumerate(dealer_hand):
                        if not game_over and i == 0:
                            render_text("?", 400, 100)
                        else:
                            render_text(f"{card}", 400, 100 + i * 30)

                    if game_over:
                        render_text(result_text, 50, 450, result_color)
                        pygame.display.flip()
                        pygame.time.wait(3000)
                        if result_text != "Tix: Je hebt gewonnen...":
                            reset_game()
                        if result_text == "Tix: Je hebt gewonnen..." or keys[pygame.K_ESCAPE]:    
                            return

                    pygame.display.flip()
                    
            def festival_game2():
                              
                CHOICES = [["Rock","Paper","Scissors"],["Steen","Papier","Schaar"]][taal]

                class Player:
                    def __init__(self, name, x):
                        self.name = name
                        self.hands = [random.choice(CHOICES), random.choice(CHOICES)]
                        self.x = x
                        self.y = HEIGHT // 2
                        self.removed_hand = None
                    
                    def remove_hand(self,removedHand):
                        self.removed_hand = self.hands.pop(removedHand)
                    
                    def draw(self):
                        hand_text = f"{self.hands[0]}" if len(self.hands) == 1 else f"{self.hands[0]} & {self.hands[1]}"
                        text = font.render(f"{self.name}: {hand_text}", True, BLACK)
                        text_rect = text.get_rect(center=(self.x, self.y))
                        screen.blit(text, text_rect)
                
                def determine_winner(choice1, choice2):
                    choice1 = CHOICES.index(choice1)
                    choice2 = CHOICES.index(choice2)
                    if choice1 == choice2:
                        return "Winner: Tix."
                    elif (choice1 == 0 and choice2 == 2) or \
                        (choice1 == 2 and choice2 == 1) or \
                        (choice1 == 1 and choice2 == 0):
                        return f"Winner: {name}."
                    else:
                        return "Winner: Tix."
                
                running = True
                clock = pygame.time.Clock()
                player1 = Player(f"{name}", WIDTH // 4)
                player2 = Player("Tix", 3 * WIDTH // 4)
                phase = 1
                result = ""
                
                while running:
                    screen.fill(WHITE)
                    for event in pygame.event.get():
                        if event.type == pygame.KEYDOWN:
                            if phase == 1:
                                if event.key == pygame.K_1:
                                    player1.remove_hand(1)
                                if event.key == pygame.K_2:
                                    player1.remove_hand(0)
                                player2.remove_hand(random.randint(0,1))
                                phase = 2
                                result = determine_winner(player1.hands[0], player2.hands[0])
                            if event.key == pygame.K_ESCAPE:
                                return
                    
                    player1.draw()
                    player2.draw()
                    
                    if phase == 1:
                        instruction = ["Press 1 to engage your left hand and 2 to engage your right hand.","Druk op 1 om je linkerhand en op 2 om je rechterhand in te zetten."][taal]
                    else:
                        instruction = ["Press Esc to go back.","Druk op Esc om terug te gaan."][taal]
                    
                    text = font.render(instruction, True, BLACK)
                    text_rect = text.get_rect(center=(WIDTH // 2, 100))
                    screen.blit(text, text_rect)
                    
                    pygame.display.flip()
                    clock.tick(30)
        if current_area == 0:
            if day in [10,20,30]: 
                tix.draw(current_area)
                michael.draw(current_area)
            
            if day not in {10,20,30} and game_time_minutes >= 720 and game_time_minutes < 900: ben.draw(current_area)
            if day in {10,20,30}: ben.draw(current_area)
    
            mailbox.draw(current_area, 1 if mail_content or day == 29 else 0)

            tree_tex = pygame.transform.scale(pygame.image.load(os.path.join(ASSETS_PATH, 'Tree.png')), (tree_size, tree_size))
            for i, tree in [(i, tree) for i, tree in trees.items() if i in server_data['trees'] and i not in deleted_trees]:
                if camera_pos: screen.blit(tree_tex, (tree[0]-camera_pos[0],tree[1]-camera_pos[1]))
                else: screen.blit(tree_tex, (tree[0],tree[1]))
        
        #Hier beginnen algemene handelingen

        if current_area in tile_areas: bounds = tilemaps[current_area].pixsize
        elif current_area in scrolling_areas: bounds = area_size
        else: bounds = (WIDTH, HEIGHT)
        if bounds:
            if player_pos[0] < 0:
                player_pos[0] = 0
            elif player_pos[0] + player_size > bounds[0]:
                player_pos[0] = bounds[0] - player_size
            if player_pos[1] < 0:
                player_pos[1] = 0
            elif player_pos[1] + player_size > bounds[1]:
                player_pos[1] = bounds[1] - player_size

        for interactible in simple_npcs:
            if day == 40: interactible.draw(current_area)
            if interact_key_down and interactible.is_interacting(player_pos,area=current_area):
                npctext.set_message(interactible.get_message(),interactible.pos)
        
        if old_area in tile_areas and old_area == current_area:
            player_rect = pygame.Rect(player_pos[0],player_pos[1],player_size,player_size)
            if any(player_rect.colliderect(r) for r in tilemaps[current_area].collisionrects):
                old_player_rect = pygame.Rect(old_player_pos[0],player_pos[1],player_size,player_size)
                if not any(old_player_rect.colliderect(r) for r in tilemaps[current_area].collisionrects): player_pos[0] = old_player_pos[0]
                else:
                    player_pos[1] = old_player_pos[1]
                    player_rect = pygame.Rect(player_pos[0],player_pos[1],player_size,player_size)
                    if any(player_rect.colliderect(r) for r in tilemaps[current_area].collisionrects): player_pos = [old_player_pos[0],old_player_pos[1]]
                #current_area = old_area
            for r, string in tilemaps[current_area].interactrects:
                if player_rect.colliderect(r): interacted_strings.add(string)
        
        if not stuck_in_area and tp_cooldown <= 0:
            # do all of the teleportation
            if current_area in tile_areas:
                touching_edge = (player_pos[0] < 10 or player_pos[1] < 10 or player_pos[0] > tilemaps[current_area].pixsize[0] - player_size - 10 or player_pos[1] > tilemaps[current_area].pixsize[1] - player_size - 10)
                if touching_edge and player_moved:
                    new_player_pos = [player_pos[0],player_pos[1]]
                    #if player_pos[0] < 10: new_player_pos[0] = WIDTH - player_size - 10
                    #elif player_pos[0] > WIDTH - player_size - 10: new_player_pos[0] = 10
                    #if player_pos[1] < 10: new_player_pos[1] = HEIGHT - player_size - 10
                    #elif player_pos[1] > HEIGHT - player_size - 10: new_player_pos[1] = 10
                    for area in tilemaps[current_area].transportrects.keys():
                        if current_area != old_area: break
                        rects = tilemaps[current_area].transportrects[area]
                        for r in rects:
                            if player_rect.colliderect(r) and (area not in worldmap.requirements or worldmap.requirements[area]):
                                if area not in tile_areas:
                                    herepos = worldmap.get_area_pos(current_area)
                                    therepos = worldmap.get_area_pos(area)
                                    if   therepos[0] > herepos[0]: player_pos = [WIDTH // 2, 20] #Down
                                    elif therepos[1] > herepos[1]: player_pos = [20, HEIGHT // 2] #Right
                                    elif therepos[0] < herepos[0]: player_pos = [WIDTH // 2, HEIGHT - player_size - 20] #Up
                                    elif therepos[1] < herepos[1]: player_pos = [WIDTH - player_size - 20, HEIGHT // 2] #Left
                                    else: raise ValueError("You moved, but did not move (5207)")
                                    if area == 5:
                                        if current_area == 0: 
                                            if day >= 6 and (money >= travel_cost or ben_mayor1):
                                                if not ben_mayor1:
                                                    accumulated_money -= travel_cost
                                                current_area = area
                                                journal.mark_done('find_tixcity')
                                            else: current_area = 0
                                    elif area == 4:
                                        journal.mark_done('found_swamp')
                                        current_area = area
                                    else: current_area = area
                                    fade_out()
                                    break
                                try:
                                    if area == 3:
                                        if current_area == 18:
                                            if day >= 18 and (money >= travel_cost or michael_mayor1):
                                                if not michael_mayor1:
                                                    accumulated_money -= travel_cost
                                                current_area = area
                                                journal.mark_done('find_max')
                                            else: current_area = 18
                                    else: current_area = area
                                    if current_area != old_area:
                                        newrect = random.choice(tilemaps[current_area].transportrects[old_area])
                                        dist = 20
                                        player_pos = [
                                            max(dist,min(tilemaps[current_area].pixsize[0]-dist,newrect[0] + (newrect[2] - player_size) // 2)),
                                            max(dist,min(tilemaps[current_area].pixsize[1]-dist,newrect[1] + (newrect[3] - player_size) // 2)),
                                        ]
                                        fade_out()
                                    break
                                except Exception as e:
                                    if True:
                                        player_pos = new_player_pos
                                        current_area = area
                                        tp_cooldown = 30
                                        fade_out()
                                        break
                                    else:
                                        npc_text = ["People are hard at work paving this road. Come back later.","Er wordt hard gewerkt aan het asfalteren van deze weg. Kom later nog eens terug."][taal]
                                        npc_text_timer = current_time + 3000
                                        current_area = old_area
                                    break
            
            elif worldmap.area_allowed(current_area):
                direction = -1
                if player_pos[1] < 10: #Up
                    player_pos[1] = HEIGHT - player_size - 10
                    direction = 3
                elif player_pos[0] < 10: #Left
                    player_pos[0] = WIDTH - player_size - 10
                    direction = 1
                elif player_pos[0] > WIDTH - player_size - 10: #Right
                    player_pos[0] = 10
                    direction = 0
                elif player_pos[1] > HEIGHT - player_size - 10: #Down
                    player_pos[1] = 10
                    direction = 2
                if direction >= 0:
                    new_area = worldmap.goto_dir(direction, current_area)
                    if new_area in tile_areas:
                        newrect = random.choice(tilemaps[new_area].transportrects[current_area])
                        dist = 20
                        player_pos = [
                            max(dist,min(tilemaps[new_area].pixsize[0]-dist,newrect[0] + (newrect[2] - player_size) // 2)),
                            max(dist,min(tilemaps[new_area].pixsize[1]-dist,newrect[1] + (newrect[3] - player_size) // 2)),
                        ]
                        tp_cooldown = 30
                        fade_out()
                    current_area = new_area
                    worldmap.current_pos = worldmap.get_area_pos(current_area)
        else:
            tp_cooldown -= 1

        if current_area == 2 and current_area not in tile_areas: # Is there ice in Snowfall?
            if is_prop_on_surface(player_pos,player_size,sea_pos,sea_size,12) and interact_key_just_pressed:
                if current_area == 0 and 'snow' in daily_mods:
                    npctext.set_message((["I cannot fish here because of the ice...","Ik kan hier door het ijs niet vissen..."][taal],{'thinking':True}),player_pos)
                elif has_rod and current_minigame == None: fishing_game()
            
            if current_area == 0 and 'snow' in daily_mods:
                pygame.draw.rect(screen, (150,150,240), (sea_pos[0], sea_pos[1], sea_size[0], sea_size[1]))
            else: pygame.draw.rect(screen, BLUE, (sea_pos[0], sea_pos[1], sea_size[0], sea_size[1]))
        
        if interact_key_just_pressed and has_rod and current_minigame == None and "fish" in interacted_strings: fishing_game()

        #Houses
        if interact_key_down and current_area in {0}:
            if "house_1" in interacted_strings: current_area = 19 
            if "house_2" in interacted_strings: current_area = 20
            if "house_3" in interacted_strings: current_area = 21
            if "house_4" in interacted_strings: current_area = 9
            if "snackbar" in interacted_strings and worldmap.requirements[22]:
                play_video('zwevendekiezer.mp4','zwevendekiezer.mp3')
                fade_out()
                current_area = 22 #Snackbar
            if current_area != old_area: fade_out()
        
        if interact_key_down and current_area in {9} and npc_text == '':
            if "bed_1" in interacted_strings: 
                npc_text = (["I should better go to work, sleep is for the rich!","Ik zou aan het werk moeten gaan, slapen is voor de rijken!"][taal],{'thinking':True})

        if interact_key_down and current_area in {19} and npc_text == '':
            if "torah_1" in interacted_strings: 
                npctext.set_message((["It seems like a holy book. One of the lines reads: *","Het lijkt wel een heilig boek. Een van de regels zegt: *"][taal] + random.choice(VARETORAH) + "*",{'thinking':True}),obj_pos=player_pos)
            
        for animal in (i for i in wildlife if old_area in i.location):
            if not has_gift and gift_available and animal.canPickUp and interact_key_down and is_prop_on_surface(player_pos, player_size, animal.getPos(), [animal.size,animal.size], -10):
                wildlife.remove(animal)
                if not inventory.pickup('squirrel',type='gift'):
                    npctext.set_message((["My inventory is full!","Mijn inventaris is vol!"][taal],{'thinking':True}))
                else:
                    has_gift = True
                    gift_available = False
                continue
            animal.tick(player_pos,area=old_area)
            animal.draw(old_area,camera_pos=(camera_pos or [0,0]))

        for m in (i for i in monsters if old_area in i.location):
            m.tick(player_pos, old_area)
            m.draw(old_area)
        for b in bullets:
            if b.tick():
                bullets.remove(b)
                continue
            b.draw(old_area)
        
        if old_area in [0,2]:
            for egg in eggs[old_area]:
                egg.draw()
        
        if old_area in [3,4]:
            color = {
                3 : ORANGE,
                4 : YELLOW
            }[old_area]
            lim = {
                3 : 25,
                4 : 25
            }[old_area]
            speed = {
                3 : 10,
                4 : 5
            }[old_area]
            light = {
                4 : 60
            }
            for p in (particles[:lim] if lim and lim < len(particles) else particles):
                p.move(spd=speed)
                p.draw(color)
                if old_area in light.keys():
                    intensity = light[old_area]
                    light_rects.append(pygame.Rect(p.x-intensity,p.y-intensity,2*intensity+p.size[0],2*intensity+p.size[1]))
        
        if robot_purchased:
            def get_vector_to_target(pos1,pos2,spd=1):
                vect = [pos2[0]-pos1[0],pos2[1]-pos1[1]]
                length = (vect[0]**2+vect[1]**2)**0.5
                return [vect[0]/length*spd,vect[1]/length*spd]
            
            if robot["time_left"] <= 0:
                # do stuff
                if robot["task"] == 'CUTTING':
                    deleted_trees.append(robot['target'])
                    treechanges.append(robot['target'])
                    robot["task"] = 'SCANNING'
                    robot["time_left"] = robot["cooldown"]
                elif robot["task"] == 'MOVING':
                    vector = get_vector_to_target(robot["pos"],trees[robot["target"]],spd=robot["speed"]*last_frame_time)
                    robot["pos"] = [robot["pos"][0]+vector[0],robot["pos"][1]+vector[1]]
                    print(robot["pos"])
                    if abs(robot["pos"][0]-trees[robot["target"]][0]) < 10 and abs(robot["pos"][1]-trees[robot["target"]][1]) < 10:
                        robot["task"] = 'CUTTING'
                        robot["time_left"] = robot["cutting_speed"]
                else:
                    possibletargets = [i for i in trees.keys() if i in server_data['trees'] and i not in deleted_trees]
                    if len(possibletargets) > 0:
                        robot["target"] = random.choice(possibletargets)
                        robot["task"] = 'MOVING'
                    else:
                        robot["task"] = 'IDLE'
                        robot["time_left"] = 1.0
            else: robot["time_left"] -= last_frame_time
            if current_area == 0 and robot["should_draw"]:
                robot_img = pygame.transform.scale(load_img_from_assets('Michael.png'),(40,40))
                screen.blit(robot_img,(round(robot["pos"][0]+camera_offset[0]),round(robot["pos"][1]+camera_offset[1])))
        
        if current_area == 13: player_img = "Player2.png"
        else: player_img = "Player1.png"
        player_img = pygame.transform.scale(load_img_from_assets(player_img), (player_size, player_size)) 
    	
        if server_data:
            money = server_data['total_money']
            for pid, pdata in server_data['players'].items():
                if pid != player_id:
                    if (isinstance(pdata['area'],tuple) and pdata['area'][0] == current_area and pdata['area'][1] == island.pos[0] and pdata['area'][2] == island.pos[1]) or pdata['area'] == current_area:
                        connected_pos = pdata['position']
                        screen.blit(player_img, ([connected_pos[0] - camera_pos[0],connected_pos[1] - camera_pos[1]] if camera_pos else connected_pos))
                        playerrect = pygame.Rect(player_pos[0],player_pos[1],player_size,player_size)
                        if 'grabbing' in pdata and isinstance(pdata['grabbing'],int):
                            if pdata['grabbing'] == player_id:
                                player_pos = [connected_pos[0]+10,connected_pos[1]+10]
                        elif interact_key_down:
                            if playerrect.colliderect((connected_pos[0],connected_pos[1],player_size,player_size)): events.append(['grabbing',pid])
                        else:
                            events.append(['grabbing',None])
                            
        else:
            npc_text = 'Disconnected...'
            npc_text_timer = current_time + 1000

        if current_area in scrolling_areas and player_screen_pos: screen.blit(player_img, (player_screen_pos[0], player_screen_pos[1]))
        else: screen.blit(player_img, (player_pos[0], player_pos[1]))

        if old_area == 2 or (old_area == 0 and 'snow' in daily_mods):
            snow_particles.tick_and_draw()
        
        if current_minigame != None:
            if current_minigame.tick(interact_key_down, player_screen_pos or player_pos, screen) == "done": current_minigame = None

        if interacted_npcs:
            timed_quest_info = journal.get_timed_quest_info()
            if timed_quest_info: 
                if timed_quest_info['npc'].lower() in interacted_npcs:
                    deleted_item = inventory.get_nth_named(timed_quest_info['item_name'],delete=True)
                    if deleted_item:
                        accumulated_money += 1000
                        journal.timedquest = None
        
        if current_area in outside_areas and current_area not in own_weather_areas and "mist" in daily_mods:
            mist_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            
            pygame.draw.rect(mist_surface,(200,200,200,128),(0,0,WIDTH,HEIGHT))
            for ray in mistrays:
                pygame.draw.line(mist_surface, (175, 175, 175, 200), (ray["x"], ray["y"]), (ray["x"] + 250, ray["y"]), 20)
                ray["x"] += mist_speed
                if ray["x"] > WIDTH:
                    ray["y"] = random.randint(0, HEIGHT)
                    ray["x"] = random.randint(-300, -250)
            screen.blit(mist_surface, (0, 0))
        
        if old_area not in visited or visit_animation:
            if old_area not in visited and not visit_animation:
                visited.append(old_area)
                stuck_in_area = True
            colorAlpha = 0
            if visit_animation < 100: colorAlpha = 0 + round(visit_animation*2)
            elif visit_animation > 200: colorAlpha = 200 - round((visit_animation-200)*2)
            else: colorAlpha = 200
            display_text_pro(all_area_info[old_area].name,(WIDTH // 2,round(HEIGHT*0.13+HEIGHT*(0.000012*colorAlpha)**0.3)),(255,255,255,colorAlpha),customFont=pygame.font.Font(None, 100))
            visit_animation += 1
            if visit_animation > 300:
                visit_animation = 0
        else:
            stuck_in_area = False
        
        dark_areas = {15}
        if old_area in dark_areas:
            global last_tick_time
            new_tick = pygame.time.get_ticks()
            elapsed_real_time = (new_tick - last_tick_time) / 1000.0

            seconds_till_next_time = 1
            minutes_per_time = 30
            day_time = game_time_minutes + (minutes_per_time * elapsed_real_time / seconds_till_next_time)
            if elapsed_real_time >= seconds_till_next_time: #SECONDEN
                #game_time_minutes = (game_time_minutes + minutes_per_time) % 1440
                game_time_minutes = server_data['time'] # problemen bij gokautomaat, los die op
                if game_time_minutes < minutes_per_time: day += 1
                last_tick_time = new_tick
        
            if old_area in dark_areas:
                night_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                night_overlay.fill((5, 5, 5, 180))
                if light_rects:
                    color = ((180, 150, 10, 50) if has_torch else (30, 30, 30, 150))
                    for rect in light_rects:
                        pygame.draw.rect(night_overlay, color, rect)
                screen.blit(night_overlay, (0, 0))
            else:
                light_levels = [
                    0, 200,
                    3, 200,
                    8, 0,
                    16, 50,
                    20, 150,
                    24, 200,
                ]
                for i in range(0,len(light_levels),2):
                    if light_levels[i] * 60 > game_time_minutes:
                        prog = (game_time_minutes-light_levels[i-2])/(light_levels[i]-light_levels[i-2])
                        alpha = light_levels[i+1]*prog + light_levels[i-1]*(1-prog)
                        break

                night_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                night_overlay.fill((0, 0, 0, alpha) if current_area != 15 else (5, 5, 5, 10))
                if light_rects:
                    color = {
                        4 : (255, 255, 50, alpha // 2),
                        6 : (50, 50, 255, alpha // 2),
                        12 : (50, 50, 255, alpha // 2),
                    }[current_area]
                    for rect in light_rects:
                        pygame.draw.rect(night_overlay, color, rect)
                night_overlay.set_alpha(alpha)

                screen.blit(night_overlay, (0, 0))
            
            draw_clock(game_time_minutes)

            if day == next_day and game_time_minutes >= 360:
                next_day += 1
                new_day()
        
        if current_time < npc_text_timer:
            if isinstance(npc_text,str):
                display_text(npc_text, (10, HEIGHT - 40), area = current_area)
            elif isinstance(npc_text,list):
                display_text(npc_text[0], (10, HEIGHT - 40), area = current_area)
        else:
            if isinstance(npc_text,str):
                npc_text = ""
            elif isinstance(npc_text,list):
                display_text(npc_text[0], (10, HEIGHT - 40), area = current_area)
                npc_text.pop(0)
                npc_text_timer = current_time + 5000
                if len(npc_text) == 1: npc_text = npc_text[0]
        npctext.display_message(interact_key_just_pressed)

        if current_area != old_area:
            if all_area_info[old_area].leave_pos: player_pos = all_area_info[old_area].leave_pos
            elif all_area_info[current_area].enter_pos: player_pos = all_area_info[current_area].enter_pos
            visit_animation = 0
            area_size = (WIDTH, HEIGHT)
            if current_area != 8:
                playmusic = True
                same_music = [
                    [16,17],
                ]
                for val in same_music:
                    if current_area in val and old_area in val: playmusic = False
                if playmusic: play_music(current_area)
            worldmap.current_pos = worldmap.get_area_pos(current_area)
            newareasize = tilemaps[current_area].pixsize if current_area in tilemaps.keys() else (WIDTH,HEIGHT)
            for p in particles:
                p.areasize = newareasize
                p.randomize()

        display_text(f"€{money}", (10, 10), area=current_area)
        display_text(day_str, (WIDTH - 20, 10), area=current_area,orientation='right')
        display_text(f"X: {player_pos[0]}, Y: {player_pos[1]}", (WIDTH - 20, 90), area=current_area,orientation='right')

        effects.draw((20,100))

        if in_shop:
            current_shop = shops[in_shop]
            stockdata = current_shop.draw(pygame.mouse.get_pos(),pygame.mouse.get_pressed()[0])
            if stockdata:
                itemname, price = stockdata
                if money >= price:
                    current_shop.states[current_shop.keys.index(itemname)] = 1
                    current_shop.tick()
                    accumulated_money -= price
                    if in_shop == "michael":
                        if itemname == 'robot':
                            robot_purchased = True
                            npc_text = "Michael: " + ["The robot is working. Look how fast it works man!","De robot doet het. Kijk hoe snel hij gaat man!"][taal]
                        elif itemname == 'shovel':
                            shovel_purchased = True
                            npc_text = "Michael: " + ["Here you go. Enjoy your purchase! Well, what plants can you even dig out here?","Hier is het. Geniet van je aankoop! Nou, welke planten kun je hier überhaupt uitgraven?"][taal]
                                
                    elif in_shop == "coffee":
                        if itemname == 'coffee':
                            effects.add_effect('energetic',1,'days')
                            npc_text = "Ms. Coffi: " + ["Have a nice day!","Fijne dag verder!"][taal]
                else:
                    npc_text = {
                        'michael': "Michael",
                        'coffee': "Ms. Coffi",
                    }[in_shop] + ": Het lijkt erop dat je niet genoeg geld hebt. Kom later maar terug."
                npc_text_timer = current_time + 60*len(npc_text)

            if in_shop and keys[pygame.K_ESCAPE]: in_shop = False

        if not no_stamina_system: draw_stamina()
        accumulated_money += inventory.draw(pygame.mouse.get_pos(),mouse_down if in_selling_range else False)

        if pause_menu_open:
            mousePos = pygame.mouse.get_pos()
            global music_slider_down

            overlay = pygame.Surface((WIDTH,HEIGHT),flags=pygame.SRCALPHA)
            overlay.fill((50,50,50,100))
            screen.blit(overlay,(0,0))

            letter_font = pygame.font.Font(None, 80)
            key_desc = [
                'Up',
                'Down',
                'Right',
                'Left',
                'Interact',
                'Journal',
                'Chat',
            ]
            if keybinds_open or (mouse_down and pygame.Rect(20,20,64,64).collidepoint(mousePos)):
                keybinds_open = True
                for i, keycode in enumerate(controls):
                    if pygame.draw.rect(screen,GREY,(25,100+100*i,310,80)).collidepoint(mousePos) and mouse_down:
                        selected_keybind = i
                        not_waiting_for_key = False
                    display_text("[ ]" if selected_keybind == i else pygame.key.name(keycode), (70,140+100*i), orientation='center', custom_font = letter_font)
                    if selected_keybind == i and not_waiting_for_key:
                        controls[i] = not_waiting_for_key
                        selected_keybind = -1
                    display_text(key_desc[i], (110,120+100*i), orientation='left')
                    display_text(["REBIND","TOETS WIJZIGEN"][taal], (110,150+100*i), orientation='left')
            else:
                screen.blit(button_textures["settings"], (20,20))
                if draw_button((WIDTH//2,HEIGHT//2-35,200,50),["Continue","Verdergaan"][taal],WHITE,BLACK,centered=True).collidepoint(mousePos) and mouse_down:
                    pause_menu_open = False
                    music_slider_down = False
                    settings['language'] = taal
                    settings['mvolume'] = music_volume
                    settings['controls'] = controls
                    with open(os.path.join(JSON_PATH, "settings.json"), "w") as json_file:
                        json.dump(settings, json_file, indent=4)
                if draw_button((WIDTH//2,HEIGHT//2+35,200,50),["Exit","Stoppen"][taal],WHITE,BLACK,centered=True).collidepoint(mousePos) and mouse_down: terminate_game()

                slider_base = (50,HEIGHT-70)
                pygame.draw.rect(screen,WHITE,(slider_base[0],slider_base[1],100,20))
                slider_size = (14,30)
                slider_rect = pygame.Rect(slider_base[0]+music_volume-slider_size[0]//2,slider_base[1]-5,slider_size[0],slider_size[1])
                if mouse_down and (music_slider_down or slider_rect.collidepoint(mousePos)):
                    music_slider_down = True
                    music_volume = max(min(100,mousePos[0]-slider_base[0]),0)
                else: music_slider_down = False
                pygame.draw.rect(screen,GREY,(slider_base[0]+music_volume,slider_base[1],100-music_volume,20))
                pygame.draw.rect(screen,(50,50,50),slider_rect)

                pygame.mixer.music.set_volume(music_volume/100)

        if has_rod: display_text([
            f"Fish caught: {fish_caught}",
            f"Aantal vissen: {fish_caught}"
        ][taal], (WIDTH / 2 - 100, 10), area = current_area)
        
        def open_law_editor():
            global screen, data, border_open, server_data

            menu_open = True
            font = pygame.font.Font(None, 50)

            button_rect = pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 - 100, 300, 60)
            save_button_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 140, 200, 50)

            here_border_open = border_open
            here_player_speed = server_data.get("player_speed", 5)

            slider_x = WIDTH // 2 - 150
            slider_y = HEIGHT // 2 + 30
            slider_width = 300
            slider_height = 20
            knob_radius = 10

            while menu_open:
                screen.fill((180, 220, 255))
                mx, my = pygame.mouse.get_pos()
                mouse_down = False

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        menu_open = False
                    elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        menu_open = False
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_down = True
                        if button_rect.collidepoint(mx, my):
                            here_border_open = not here_border_open
                        elif save_button_rect.collidepoint(mx, my):
                            global changed_sdata
                            changed_sdata['border'] = here_border_open
                            changed_sdata['player_speed'] = here_player_speed
                            border_open = here_border_open
                            #with open(os.path.join(BASE_PATH, "data.json"), 'w', encoding='utf-8') as f:
                            #    json.dump(data, f, indent=4)
                            menu_open = False
                    elif event.type == pygame.MOUSEBUTTONUP:
                        mouse_down = False

                pygame.draw.rect(screen, (0, 200, 0) if here_border_open else (200, 0, 0), button_rect)
                status_text = "Grens is OPEN" if here_border_open else "Grens is DICHT"
                text_surface = font.render(status_text, True, WHITE)
                screen.blit(text_surface, (button_rect.centerx - text_surface.get_width() // 2, button_rect.centery - text_surface.get_height() // 2))

                knob_x = slider_x + int((here_player_speed - 1) / 9 * slider_width)
                pygame.draw.rect(screen, BLACK, (slider_x, slider_y, slider_width, slider_height), 2)
                pygame.draw.circle(screen, RED, (knob_x, slider_y + slider_height // 2), knob_radius)
                speed_text = font.render(f"Snelheid spelers: {here_player_speed}", True, BLACK)
                screen.blit(speed_text, (slider_x + slider_width + 20, slider_y - 10))

                if mouse_down and (slider_y <= my <= slider_y + slider_height) and (slider_x <= mx <= slider_x + slider_width):
                    relative_x = mx - slider_x
                    here_player_speed = max(1, min(10, round((relative_x / slider_width) * 9 + 1)))

                pygame.draw.rect(screen, (50, 50, 200), save_button_rect)
                save_text = font.render("Opslaan", True, WHITE)
                screen.blit(save_text, (save_button_rect.centerx - save_text.get_width() // 2, save_button_rect.centery - save_text.get_height() // 2))

                pygame.display.flip()
                clock.tick(FPS)

        if journal_open:
            pygame.draw.rect(screen, (240, 230, 140), (WIDTH // 4, HEIGHT // 4, WIDTH // 2, HEIGHT // 2)) 
            pygame.draw.rect(screen, BLACK, (WIDTH // 4, HEIGHT // 4, WIDTH // 2, HEIGHT // 2), 3) 

            title_font = pygame.font.Font(None, 50)
            entry_font = pygame.font.Font(None, 36)
            
            title_surface = title_font.render("Journal", True, BLACK)
            screen.blit(title_surface, (WIDTH // 2 - title_surface.get_width() // 2, HEIGHT // 4 + 10))

            tasks = journal.get_tasks(day)
            statuses = journal.get_statuses()
            taskcolors = [
                BLACK,
                (180,180,170),
                YELLOW,
                BLUE
            ]
            for i, task in enumerate(tasks):
                task_surface = entry_font.render(f"- {task}", True, taskcolors[statuses[i]])
                screen.blit(task_surface, (WIDTH // 4 + 30, HEIGHT // 4 + 60 + i * 40))
        if stamina < max_stamina:
            stamina = min(max_stamina, stamina + stamina_regen_rate)
        pygame.display.flip()
        last_frame_time = clock.tick(FPS) / 1000
        frame_counter += 1



overworld()






