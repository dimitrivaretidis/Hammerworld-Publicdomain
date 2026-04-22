import sys, os
import socket, pickle, struct
import threading
import time, random
import json
import array

SERVER_SIZE = 456
players = {} 
playerevents = {}
players_in_use = set()
global has_to_send
has_to_send = dict()
compressed_tdata = None
chat_messages = {}

TREE_AREA = '0'
tree_area_collision = []

def prints(string):
    print("SERVER: " + str(string))

def decompress_list(l):
    return_value = []
    for i, val in enumerate(l):
        if type(val) == list and len(val) != 3:
            return_value += [val[1] for _ in range(val[0])]
        else:
            return_value.append(val)
    return return_value

if hasattr(sys, '_MEIPASS'):
    BASE_PATH = SERVER_PATH = sys._MEIPASS
    JSON_PATH = os.path.join(os.getenv('APPDATA'),"Hammerworld")
    EXE_PATH = os.path.dirname(sys.executable)
    os.makedirs(JSON_PATH, exist_ok=True)
else:
    BASE_PATH = EXE_PATH = os.path.dirname(os.path.abspath(__file__))
    SERVER_PATH = JSON_PATH = os.path.join(BASE_PATH,"server")

def extract_json(path):
    if hasattr(sys, '_MEIPASS'):
        if os.path.isfile(path): 
            with open(path, 'r', encoding='utf-8') as file:
                data = json.load(file)
        elif path.endswith("tile_data.json"):
            with open(os.path.join(SERVER_PATH,"tile_data.json"),'r',encoding='utf-8') as file:
                data = json.load(file)
        else: return dict()
    else:
        with open(path,'r',encoding='utf-8') as file:
            try:
                data = json.load(file)
            except:
                prints(f"File {path} does not have extractable data")
                return dict()
    return data

playerjson = os.path.join(JSON_PATH,"player_data.json")
pdata = extract_json(playerjson)
if pdata: prints(f"Players: {', '.join([i['name'] for i in pdata])}")
else:
    prints("No players found")
    pdata = []
sdata = extract_json(os.path.join(JSON_PATH,"server_data.json"))
tilejson = os.path.join(JSON_PATH,"tile_data.json")
prints(tilejson)
tdata = extract_json(tilejson)
if not tdata: raise ValueError("No tilemap was included in the tile_data.json file. Please create one using tile_editor.py and try again.")
if not os.path.isfile(tilejson):
    with open(tilejson,'w') as json_file:
        json.dump(tdata, json_file)
tdata = tdata['tiles']
for key in tdata.keys():
    tdata[key][1] = decompress_list(tdata[key][1])

if sdata:
    global_server_storage = sdata['sstorage']
    day = sdata['day']
else:
    global_server_storage = {"president": -1, "border": True, 'player_speed': 5}
    day = 1
total_money = sdata['money'] if 'money' in sdata.keys() else (day * 20) + 200 - 20

global uncompressed_areainfo
uncompressed_areainfo = None

initial_time = time.time()

def recv_all(sock, length):
    data = b''
    while len(data) < length:
        packet = sock.recv(min(4096, length - len(data)))
        if not packet:
            raise EOFError("Connection closed")
        data += packet
    return data

def recv_pickle(sock):
    length_bytes = recv_all(sock, 4)
    length = struct.unpack("!I", length_bytes)[0]
    data = recv_all(sock, length)
    return pickle.loads(data)

def send_pickle(sock, obj):
    data = pickle.dumps(obj)
    length = struct.pack("!I", len(data))
    sock.sendall(length + data)

def generate_island(sizex, sizey):
    return_data = dict() # will be [sizex,sizey,map,areainfo]
    return_data['x'] = sizex
    return_data['y'] = sizey

    map = [[1 for x in range(sizex)] for y in range(sizey)]
    map[0][sizex // 2] = 0 # spawn area

    for index, chance, amount in [
        (2, 1, 1), #Mine
        (3, 2, 3), #Lake
    ]:
        for _ in range(amount):
            if random.randint(1,chance) == 1:
                posx = posy = -1
                while map[posy][posx] != 1 or posx == -1: 
                    posx = random.randint(0,sizex-1)
                    posy = random.randint(0,sizey-1)
                map[posy][posx] = index
    
    flat_map = [tile for row in map for tile in row]
    return_data['map'] = array.array('B', flat_map).tobytes()

    global uncompressed_areainfo
    uncompressed_areainfo = [[map[y][x] for x in range(sizex)] for y in range(sizey)]
    for y1, row in enumerate(uncompressed_areainfo):
        for x1, val in enumerate(row):
            if val == 2:
                size = (5000 // 100, 5000 // 100)
                uncompressed_areainfo[y1][x1] = [[0,1][int(random.randint(1,1)==1)],[]]
                this_areainfo = uncompressed_areainfo[y1][x1][1]
                if uncompressed_areainfo[y1][x1][0] == 1: #Maze
                    for x in range(size[0]):
                        this_areainfo.append([])
                        for y in range(size[1]):
                            if x == size[0] // 2 and y == size[1] // 2: this_areainfo[x].append(-1)
                            elif abs(x - size[0] // 2) <= 1 and abs(y - size[1] // 2) <= 1: this_areainfo[x].append(0)
                            else: this_areainfo[x].append(1)

                    possible_cors = [[size[0]//2,size[1]//2,random.randint(0,3)]]
                    dirs = [(1,0),(0,1),(-1,0),(0,-1)]
                    def in_bounds(x,y,s):
                        return (x > 0 and y > 0 and x < s[0] - 1 and y < s[1] - 1)
                    def no_obstacles(x,y,direction,length,map):
                        maxindex = (len(map)-1,len(map[0])-1)
                        for l in range(length):
                            if direction == 0 and any([map[min(maxindex[0],x+l)][max(0,min(y+dy,maxindex[1]))] != 1 for dy in range(-1,2)]): return False
                            elif direction == 1 and any([map[max(0,min(x+dx,maxindex[0]))][min(maxindex[1],y+l)] != 1 for dx in range(-1,2)]): return False
                            elif direction == 2 and any([map[max(0,x-l)][max(0,min(y+dy,maxindex[1]))] != 1 for dy in range(-1,2)]): return False
                            elif direction == 3 and any([map[max(0,min(x+dx,maxindex[0]))][max(0,y-l)] != 1 for dx in range(-1,2)]): return False
                        return True
                    while len(possible_cors) != 0:
                        totalfreespots = 0
                        todelete = []
                        toappend = []
                        for i, cor in enumerate(possible_cors):
                            cor[0] += dirs[cor[2]][0]
                            cor[1] += dirs[cor[2]][1]
                            if ((totalfreespots < 100 and len(possible_cors) - len(todelete) < 8) or random.randint(1, max(round(10 - 0.01 * totalfreespots),2)) != 1) and in_bounds(cor[0],cor[1],size):
                                if no_obstacles(cor[0],cor[1],cor[2],2,this_areainfo):
                                    this_areainfo[cor[0]][cor[1]] = 0
                                    totalfreespots += 1
                                    if random.randint(1,3) == 1:
                                        toappend.append([cor[0],cor[1],random.randint(0,3)])
                            else:
                                todelete.append(i)
                        for key in todelete[::-1]:
                            possible_cors.pop(key)
                        for newcor in toappend:
                            possible_cors.append(newcor)
                else:
                    uncompressed_areainfo[y1][x1][1] = [[random.randint(2,3) for y in range(size[1])] for x in range(size[0])] #Normal stone
                    this_areainfo = uncompressed_areainfo[y1][x1][1]
                    for y, row in enumerate(this_areainfo):
                        for x, rock in enumerate(this_areainfo):
                            #Mine is generated in here
                            if x == size[0] // 2 and y == size[1] // 2: this_areainfo[y][x] = -1 #Ladder
                            elif abs(x - size[0] // 2) <= 1 and abs(y - size[1] // 2) <= 1: this_areainfo[y][x] = 0 #Empty
                            elif random.randint(1,100) == 1: this_areainfo[y][x] = 4 #Diamond
    
    global compressed_areainfo
    compressed_areainfo = dict()
    for y in range(len(uncompressed_areainfo)):
        for x in range(len(uncompressed_areainfo[y])):
            cell = uncompressed_areainfo[y][x]
            if isinstance(cell, list):
                flat = [val for row in cell[1] for val in row]
                compressed_areainfo[(y, x)] = {
                    "type": cell[0],
                    "size": (len(cell[1][0]), len(cell[1])),
                    "data": array.array("b", flat).tobytes()  # signed 8-bit
                }
    return_data['areas'] = compressed_areainfo
    
    return return_data

def update_areainfo_mine(changes : tuple): # changes = [((posy, posx), (posx, posy), newstate), ((posy, posx), (posx, posy), newstate), etc.]
    global uncompressed_areainfo
    for change in changes:
        uncompressed_areainfo[change[0][1]][change[0][0]][change[1][0]][change[1][1]] = change[2] # probably
    
    global compressed_areainfo
    compressed_areainfo = dict()
    for y in range(len(uncompressed_areainfo)):
        for x in range(len(uncompressed_areainfo[y])):
            cell = uncompressed_areainfo[y][x]
            if isinstance(cell, list):
                flat = [val for row in cell[1] for val in row]
                compressed_areainfo[(y, x)] = {
                    "type": cell[0],
                    "size": (len(cell[1][0]), len(cell[1])),
                    "data": array.array("b", flat).tobytes()  # signed 8-bit
                }
    global day_data
    day_data['island']['areas'] = compressed_areainfo

def new_day():
    rdata = {'mods':[],'day':day}
    if day in {10,20,30}:
        rdata['mods'].append('flags')
    if day in {5,25}:
        rdata['mods'].append("rain")
    elif day % 12 == 0: rdata['mods'].append("mist")

    season = ((day-1)%(28*4)) // 28
    sday = (day-1)%28 + 1
    if sday == 1: prints(f"Current season: {['spring','summer','fall','winter'][season]}")
    rain_chance, thunder_chance, snow_chance = [(10,0,0),(20,30,0),(3,0,0),(0,0,3)][season]
    if day > 5 and "flags" not in rdata['mods']:
        if "rain" not in rdata['mods'] and 'mist' not in rdata['mods']:
            if season == 1 and sday == 10: rdata['mods'].append('jelly') 
            if rain_chance and random.randint(1,rain_chance) == 1: rdata['mods'].append('rain')
            elif thunder_chance and random.randint(1,thunder_chance) == 1: rdata['mods'] += ['thunder', 'rain']
            elif snow_chance and random.randint(1,snow_chance) == 1: rdata['mods'].append('snow')
    
    global tree_area_collision
    def check_point_collision(rect,point):
        return (
            point[0] >= rect[0] and point[0] <= rect[0]+rect[2] and
            point[1] >= rect[1] and point[1] <= rect[1]+rect[3]
        )
    rdata['trees'] = {}
    tree_area_size = (tdata[TREE_AREA][0][0],tdata[TREE_AREA][0][1])
    if day not in {5,10,20,25,30}:
        for index in range(10):
            pos = None
            while not pos or any([check_point_collision(rect,pos) for rect in tree_area_collision]):
                pos = [random.randint(0, tree_area_size[0] - 1),random.randint(0, tree_area_size[1] - 1)]
            rdata['trees'][index] = (pos[0],pos[1])

    # island
    if random.randint(1,1) == 1: rdata['island'] = generate_island(random.randint(3,4),random.randint(3,4))

    sdata['sstorage'] = global_server_storage
    sdata['day'] = day
    sdata['money'] = total_money
    with open(os.path.join(JSON_PATH, "server_data.json"), "w") as json_file:
        json.dump(sdata, json_file, indent=4)

    return rdata

def get_game_time_minutes(tick_time=1,game_time_per_tick=30):
    now = time.time()
    global start_time, players_in_use
    if len(players_in_use) == 0:
        start_time = time.time() # reset the day time
    elapsed_time = round(now - start_time - 0.49)
    return (360 + (elapsed_time//tick_time)*game_time_per_tick) % (24*60)

def handle_status_request(conn):
    status = {
        'online': True,
        'player_count': len(players),
        'max_players': SERVER_SIZE,
        'day': day,
        'server_age': round(time.time()-initial_time)
    }
    prints(status)
    conn.sendall(pickle.dumps(status))
    conn.close()

def client_thread(conn, addr, id):
    global players, playerevents, has_to_send, total_money, day, day_data, chats
    chats = {}

    pre_initial_data = {
        'chars' : [(player['name'],(i in players_in_use)) for i, player in enumerate(pdata)]
    }
    send_pickle(conn, pre_initial_data)
    dataid = recv_pickle(conn)
    if dataid == 'disconnect':
        prints(f"Player {id} disconnected while choosing a character")
        return
    
    prints(f"len: {len(pdata)}, id: {dataid}")
    players_in_use.add(dataid)
    initial_data = {
        'player_id': id,
        'money': total_money,
        'day_data': day_data,
        'tiles': compressed_tdata,
    }
    if dataid == len(pdata):
        initial_data['chardata'] = False
        pdata.append(dict())
    else:
        initial_data['chardata'] = pdata[dataid]
    send_pickle(conn, initial_data)
    prints(id)
    prints(f"data sent to client {id}")

    playerevents[id] = {'grabbing' : None}
    has_to_send[id] = dict()

    framecounter = 0
    
    while True:
        framecounter += 1
        try:
            data = recv_pickle(conn)
            if not data:
                break  
            
            players[id] = {'area':data['area'],'position':data['position']}
            
            if 'money_change' in data:
                total_money += data['money_change']
                prints(f"Updated total money: {total_money}")
            if 'trees' in data:
                for val in data['trees']:
                    if isinstance(val,int) and val in day_data['trees']: del day_data['trees'][val]
            if 'rocks' in data:
                update_areainfo_mine(data['rocks'])
                for pid in has_to_send.keys():
                    if pid == id: continue
                    if 'rocks' not in has_to_send[pid]: has_to_send[pid]['rocks'] = []
                    for change in data['rocks']:
                        has_to_send[pid]['rocks'].append(change)
                    prints(f"{pid}: {has_to_send[pid]['rocks']}")
                del data['rocks']

            response_data = {
                'players': players,
                'total_money': total_money,
                'day': day,
                'trees': day_data['trees'],
                'time': get_game_time_minutes(),
                'border': global_server_storage['border'],
            }
            if 'player_speed' in global_server_storage: response_data['player_speed'] = global_server_storage['player_speed']
            if 'request' in data:
                data['request'] = {}
                for key in data['request']:
                    response_data['request'][key] = global_server_storage[key]
            if 'change' in data:
                prints(f"got data from player {id}: {data['change']}")
                for key, val in data['change'].items():
                    if key == 'player_speed': global_server_storage['player_speed'] = max(1, min(10, int(data['change']['player_speed'])))
                    else: global_server_storage[key] = val
                if global_server_storage['president'] != -1: prints(f"Player {id+1} is president!")
            if 'day_data' in playerevents[id] and playerevents[id]['day_data']:
                response_data['day_data'] = playerevents[id]['day_data']
                playerevents[id]['day_data'] = False
            if isinstance(playerevents[id]['grabbing'],int):
                response_data['players'][id]['grabbing'] = playerevents[id]['grabbing']
            if chat_messages:
                other_ids = [pid for pid in chat_messages if pid != id]
                if other_ids:
                    response_data['chat'] = chat_messages[other_ids[-1]]
            if 'newday' in data['events']:
                playerevents[id]['ready'] = True
                playerevents[id]['grabbing'] = None
                amountready = 0
                for pid in playerevents:
                    if playerevents[pid]['ready']:
                        amountready += 1
                sleepvals = [amountready,len(playerevents)]
                for pid in has_to_send.keys():
                    has_to_send[pid]['a_ready'] = sleepvals
                if sleepvals[0]==sleepvals[1]:
                    day += 1
                    day_data = new_day()
                    for pid in playerevents:
                        playerevents[pid]['ready'] = False
                        playerevents[pid]['day_data'] = day_data
            for event in data['events']:
                if isinstance(event,list):
                    if event[0] == 'grabbing':
                        playerevents[id]['grabbing'] = event[1]
                    elif event[0] == "chat":
                        chat_messages[id] = event[1]
                    elif event[0] == "save":
                        pdata[dataid] = event[1]
                        with open(playerjson, 'w', encoding='utf-8') as f:
                            json.dump(pdata, f, indent=4)

            if has_to_send[id]:
                for key in has_to_send[id].keys():
                    prints(f"Key: {key}, data: {has_to_send[id][key]}")
                    response_data[key] = has_to_send[id][key]
            send_pickle(conn, response_data)
            has_to_send[id] = {}
        except Exception as e:
            prints(f"Error with client {addr}: {e}\nnow disconnecting...")
            break
    
    if id in players:
        try:
            del players[id]
            del playerevents[id]
            players_in_use.remove(dataid)
        except Exception as e: prints(f"{players}")
    else: prints(f"Error with id {id}: couldn't find player in registry. Current players: {players}")
    conn.close()
    prints(f"Connection stopped.")

global start_time
start_time = None

def main():
    global SERVER_SIZE
    server = "0.0.0.0"
    port = sys.argv[1] if len(sys.argv) > 1 else "12345"
    port = int(port)
    if port == 5555:
        SERVER_SIZE = 2

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((server, port))
        s.listen()
        prints(f"Server started on {server}:{port}")
    except Exception as e:
        prints("An instance of Hammerworld is already running!")
        sys.exit()
    
    global compressed_tdata
    compressed_tdata = []

    for key in tdata.keys():
        flatdata = []
        for v in tdata[key][1]:
            if isinstance(v, list):
                flatdata.append(255)
                flatdata += v
            else:
                flatdata.append(v)

        compressed_tdata.append((
            int(key),
            tdata[key][0],
            array.array('B', flatdata).tobytes(),
            (tdata[key][2] if tdata[key][2] else None),
            tdata[key][3]
        ))
    
    global tree_area_collision
    tree_area_collision = []
    for rectinfo in tdata[TREE_AREA][3]:
        if rectinfo[1] == 0:
            tree_area_collision.append(rectinfo[0])

    global day_data
    day_data = new_day()

    prints("Server is ready for joining")
    global start_time
    start_time = time.time()
    print(get_game_time_minutes())

    id_count = 0
    while True:
        conn, addr = s.accept()
        prints("Accepted")
        try:
            initial_msg = conn.recv(2048)
            if initial_msg == b"STATUS":
                prints("asked for status...")
                handle_status_request(conn)
                continue
            elif initial_msg == b"JOIN":
                prints("Client requested join")
                if len(players) < SERVER_SIZE:
                    prints(f"Connected to: {addr}")
                    if len(players) == SERVER_SIZE - 1:
                        prints(f"Server full! ({len(players)+1}/{SERVER_SIZE})")
                    threading.Thread(target=client_thread, args=(conn, addr, id_count), daemon=True).start()
                    id_count += 1
                else:
                    prints("Server is full, closing connection.")
                    conn.close()
                continue
            else:
                prints(f"Unknown or binary connection from {addr}, ignoring.")
                conn.close()
                continue
        except Exception as e:
            prints(f"Error handling initial message: {e}")
            conn.close()
            continue
        
        if len(players) < SERVER_SIZE:
            prints(f"Connected to: {addr}")
            if len(players) == SERVER_SIZE - 1: prints(f"Server full! ({len(players)+1}/{SERVER_SIZE})")

            threading.Thread(target=client_thread, args=(conn, addr, id_count)).start()
            id_count += 1
        time.sleep(0.1)

if __name__ == "__main__":
    main() 