#!/usr/bin/env python3
import curses
import time
import random
import sys
import math
import copy
import os

# Terminal Tetris with hold, colors, start screen, split-screen local multiplayer
# Constants
W = 10
H = 20

# Tetromino definitions: each piece has 4 rotation states, each state is a list of (x,y) cells
TETROMINOES = {
    "I": [
        [(0,1),(1,1),(2,1),(3,1)],
        [(2,0),(2,1),(2,2),(2,3)],
        [(0,2),(1,2),(2,2),(3,2)],
        [(1,0),(1,1),(1,2),(1,3)],
    ],
    "O": [
        [(1,0),(2,0),(1,1),(2,1)], 
        [(1,0),(2,0),(1,1),(2,1)],
        [(1,0),(2,0),(1,1),(2,1)],
        [(1,0),(2,0),(1,1),(2,1)],
    ],
    "T": [
        [(1,0),(0,1),(1,1),(2,1)],
        [(1,0),(1,1),(2,1),(1,2)],
        [(0,1),(1,1),(2,1),(1,2)],
        [(1,0),(0,1),(1,1),(1,2)],
    ],
    "S": [
        [(1,0),(2,0),(0,1),(1,1)],
        [(1,0),(1,1),(2,1),(2,2)],
        [(1,1),(2,1),(0,2),(1,2)],
        [(0,0),(0,1),(1,1),(1,2)],
    ],
    "Z": [
        [(0,0),(1,0),(1,1),(2,1)],
        [(2,0),(1,1),(2,1),(1,2)],
        [(0,1),(1,1),(1,2),(2,2)],
        [(1,0),(0,1),(1,1),(0,2)],
    ],
    "J": [
        [(0,0),(0,1),(1,1),(2,1)],
        [(1,0),(2,0),(1,1),(1,2)],
        [(0,1),(1,1),(2,1),(2,2)],
        [(1,0),(1,1),(0,2),(1,2)],
    ],
    "L": [
        [(2,0),(0,1),(1,1),(2,1)],
        [(1,0),(1,1),(1,2),(2,2)],
        [(0,1),(1,1),(2,1),(0,2)],
        [(0,0),(1,0),(1,1),(1,2)],
    ],
}

PIECE_ORDER = list(TETROMINOES.keys())

PIECE_COLORS = {
    "I": curses.COLOR_CYAN,
    "O": curses.COLOR_YELLOW,
    "T": curses.COLOR_MAGENTA,
    "S": curses.COLOR_GREEN,
    "Z": curses.COLOR_RED,
    "J": curses.COLOR_BLUE,
    "L": curses.COLOR_WHITE,
}

# Global runtime settings (user-configurable via Adv. Options)
SETTINGS = {
    'colored_art': True,
    'art_palette': 'default',  # options: 'default','mono','high-contrast'
}

# control piece coloring separately from ASCII art
SETTINGS.setdefault('colored_pieces', True)
# piece palette selection
SETTINGS.setdefault('piece_palette', 'default')


def get_piece_palette(name):
    """Return a mapping piece -> curses color for the named palette."""
    # base default mapping
    default = {
        "I": curses.COLOR_CYAN,
        "O": curses.COLOR_YELLOW,
        "T": curses.COLOR_MAGENTA,
        "S": curses.COLOR_GREEN,
        "Z": curses.COLOR_RED,
        "J": curses.COLOR_BLUE,
        "L": curses.COLOR_WHITE,
    }
    name = (name or 'default').lower()
    if name == 'default':
        return default
    if name == 'greyscale':
        # use white/black shades (terminals typically have limited greyscale)
        return {p: curses.COLOR_WHITE for p in default}
    if name in ('electronika', 'green'):
        # Use standard green color for this palette.
        return {p: curses.COLOR_GREEN for p in default}
    if name == 'camo':
        # various greens / olive using available colors
        camo = {
            "I": curses.COLOR_GREEN,
            "O": curses.COLOR_GREEN,
            "T": curses.COLOR_YELLOW,
            "S": curses.COLOR_GREEN,
            "Z": curses.COLOR_GREEN,
            "J": curses.COLOR_YELLOW,
            "L": curses.COLOR_GREEN,
        }
        return camo
    if name == 'usa':
        usa = {
            "I": curses.COLOR_BLUE,
            "O": curses.COLOR_WHITE,
            "T": curses.COLOR_RED,
            "S": curses.COLOR_BLUE,
            "Z": curses.COLOR_RED,
            "J": curses.COLOR_WHITE,
            "L": curses.COLOR_BLUE,
        }
        return usa
    if name == 'ussr':
        ussr = {
            "I": curses.COLOR_RED,
            "O": curses.COLOR_YELLOW,
            "T": curses.COLOR_RED,
            "S": curses.COLOR_YELLOW,
            "Z": curses.COLOR_RED,
            "J": curses.COLOR_YELLOW,
            "L": curses.COLOR_RED,
        }
        return ussr
    if name == 'bananarama' or name == 'poopy':
        return {p: curses.COLOR_YELLOW for p in default}
    if name == 'emoji':
        # color mapping remains same as default; visual change is in
        # drawing (pieces become emojis). Keep colors for panel/text.
        return default
    if name == 'modern':
        # color mapping remains same as default; visual change is in
        # drawing (pieces become specific colored emojis).
        return default
    # fallback
    return default

# Emoji support: a small list of single-codepoint emojis used when the
# 'emoji' piece palette is selected. PIECE_EMOJI_MAP stores the chosen
# emoji for each piece type (assigned when the palette is enabled).
EMOJI_LIST = [
    '�','😃','😄','😁','😆','😅','😂','🤣','😊','😇','🙂','🙃','😉','😌','😍','🥰','😘','😗','😙','😚','😜','😝','😛','🤪','😎','🤩','🥳','😏','😒','😞','😔','😟','😕'
]
# Specific emojis for 'modern' palette
MODERN_EMOJIS = {
    "I": "🟦",  # blue
    "O": "🟨",  # yellow
    "T": "🟪",  # purple
    "S": "🟩",  # green
    "Z": "🟥",  # red
    "J": "🟦",  # blue
    "L": "🟧",  # orange
}
PIECE_EMOJI_MAP = {}


def init_color_pairs():
    """Initialize curses color pairs according to current SETTINGS.
    This can be called at runtime when the user changes palettes so the
    new colors apply immediately.
    """
    if not curses.has_colors():
        return
    try:
        curses.start_color()
        try:
            curses.use_default_colors()
        except Exception:
            pass
    except Exception:
        return

    # Piece colors
    if SETTINGS.get('colored_pieces', True):
        ordering = ["I","O","T","S","Z","J","L"]
        palette = SETTINGS.get('piece_palette', 'default').lower()
        if palette == 'electronika':
            for i in range(1, 8):
                try:
                    curses.init_pair(i, curses.COLOR_GREEN, -1)
                except Exception:
                    pass
        else:
            palette_map = get_piece_palette(SETTINGS.get('piece_palette', 'default'))
            for i, p in enumerate(ordering, start=1):
                fg = palette_map.get(p, curses.COLOR_WHITE)
                try:
                    curses.init_pair(i, fg, -1)
                except Exception:
                    pass

        # If emoji palette is selected, pick a random emoji for each piece
        try:
            if palette == 'emoji':
                PIECE_EMOJI_MAP.clear()
                for p in ordering:
                    PIECE_EMOJI_MAP[p] = random.choice(EMOJI_LIST)
            elif palette == 'modern':
                PIECE_EMOJI_MAP.clear()
                PIECE_EMOJI_MAP.update(MODERN_EMOJIS)
        except Exception:
            pass

    # ASCII art colors
    if SETTINGS.get('colored_art', True):
        try:
            if SETTINGS.get('piece_palette', 'default').lower() == 'electronika':
                for i in range(21, 30):
                    try:
                        curses.init_pair(i, curses.COLOR_GREEN, -1)
                    except Exception:
                        pass
            else:
                curses.init_pair(21, curses.COLOR_RED, -1)
                curses.init_pair(22, curses.COLOR_YELLOW, -1)
                curses.init_pair(23, curses.COLOR_MAGENTA, -1)
                curses.init_pair(24, curses.COLOR_CYAN, -1)
                curses.init_pair(25, curses.COLOR_GREEN, -1)
                curses.init_pair(26, curses.COLOR_YELLOW, -1)
                curses.init_pair(27, curses.COLOR_RED, -1)
                curses.init_pair(28, curses.COLOR_MAGENTA, -1)
                curses.init_pair(29, curses.COLOR_CYAN, -1)
        except Exception:
            pass

# --- Controls configuration and rebinding helpers ---
# Stored as lists of name-strings (e.g. 'a', ' ', 'KEY_LEFT', 'SPACE') so
# they can be displayed and reverted to defaults easily.
DEFAULT_CONTROLS = {
    'single': {
        'left': ['KEY_LEFT', 'a'],
        'right': ['KEY_RIGHT', 'd'],
        'soft': ['KEY_DOWN', 's'],
        'rot_cw': ['KEY_UP', 'x', 'w'],
        'rot_ccw': ['z'],
        'hard': ['SPACE'],
        'hold': ['c'],
        'pause': ['p'],
        'restart': ['r'],
    },
    'local_p1': {
        'left': ['a'],
        'right': ['d'],
        'soft': ['s'],
        'rot_cw': ['x', 'w'],
        'rot_ccw': ['z'],
        'hard': ['2'],
        'hold': ['1'],
        'pause': ['P'],
    },
    'local_p2': {
        'left': ['KEY_LEFT'],
        'right': ['KEY_RIGHT'],
        'soft': ['KEY_DOWN'],
        'rot_cw': ['KEY_UP'],
        'rot_ccw': [],
        'hard': ['.'],
        'hold': [','],
    }
}

# runtime controls (mutable)
CONTROLS = {k: {a: v[:] for a, v in DEFAULT_CONTROLS[k].items()} for k in DEFAULT_CONTROLS}

def _name_to_codes(name):
    """Map a stored name to a set of key codes to compare with getch() values."""
    codes = set()
    if not name:
        return codes
    # common named curses keys
    if name == 'KEY_LEFT':
        codes.add(curses.KEY_LEFT)
    elif name == 'KEY_RIGHT':
        codes.add(curses.KEY_RIGHT)
    elif name == 'KEY_UP':
        codes.add(curses.KEY_UP)
    elif name == 'KEY_DOWN':
        codes.add(curses.KEY_DOWN)
    elif name == 'SPACE':
        codes.add(ord(' '))
    else:
        # single character: accept both lower and upper case ASCII
        if len(name) == 1:
            ch = name
            codes.add(ord(ch.lower()))
            codes.add(ord(ch.upper()))
        else:
            # fallback: try to convert to int if possible
            try:
                codes.add(int(name))
            except Exception:
                pass
    return codes

def codes_for(scope, action):
    """Return a set of key codes for a given control scope and action."""
    out = set()
    for name in CONTROLS.get(scope, {}).get(action, []):
        out |= _name_to_codes(name)
    return out

def code_to_name(code):
    """Convert a getch() code to a display-friendly name string."""
    if code == curses.KEY_LEFT:
        return 'KEY_LEFT'
    if code == curses.KEY_RIGHT:
        return 'KEY_RIGHT'
    if code == curses.KEY_UP:
        return 'KEY_UP'
    if code == curses.KEY_DOWN:
        return 'KEY_DOWN'
    if code == ord(' '):
        return 'SPACE'
    try:
        if 0 <= code < 256:
            ch = chr(code)
            return ch
    except Exception:
        pass
    return str(code)

def controls_display_names(scope, action):
    return ", ".join(CONTROLS.get(scope, {}).get(action, []) or [''])


MENU_ART = [
    r"                            .",
    r"                            T",
    r"                           ( )",
    r"                          <===>",
    r"                           F|J",
    r"                           ===",
    r"                          J|||F",
    r"                          F|||J",
    r"                         /\/ \/\ ",
    r"                         F+++++J",
    r"                        J{}{|}{}F         .",
    r"                     .  F{}{|}{}J         T",
    r"          .          T J{}{}|{}{}F        ;;",
    r"          T         /|\F/\/\|/\/\J  .   ,;;;;.",
    r"         /:\      .'/|\\:'''''''''F T ./;;;;;;\ ",
    r"       ./:/:/.   ///|||\\\'''''''' /x\T\;;;;;;/",
    r"      //:/:/:/\  \\\\|////..[ ]...xXXXx.|====|",
    r"      \:/:/:/:T7 :.:.:.:.:||[ ]|/xXXXXXx\|||||",
    r"      ::.:.:.:A. `;:;:;:;'=== ==\XXXXXXX/=====.",
    r"      `;\"\"/xxx\.|,|,|,| ( ) ( )| | | |.=..=.|",
    r"       :. :`\xxx/(_)(_)(_) _   _ | | | |'-''-'|",
    r"     :T-'-.:\"\":|-------|/ \ / \|=====|======|",
    r"     .A.^ ^ ^||_|| ,. .. || | | |/\/\/\/ | | ||",
    r"   :;:////\:::.'.| || || ||-| |-|/\/\/\+|+| | |",
    r"  ;:;;\////::::,='======='=============/\/\=====.",
    r" :;:::;] [:::::;:|__..,__|============/||\|\====|",
    r" :::::;|=:::;:;::|,;:::::          |========|   |",
    r" ::l42::::::(}:::::;::::::_________|========|___|__",
    r"------------------------------------------------",
]

ART_W = max(len(line) for line in MENU_ART)
ART_H = len(MENU_ART)

# helpers
def new_bag():
    bag = PIECE_ORDER[:]
    random.shuffle(bag)
    return bag

def empty_board():
    return [[None for _ in range(W)] for _ in range(H)]

def cells_of(piece, rot, px, py):
    return [(px + x, py + y) for (x, y) in TETROMINOES[piece][rot % 4]]

def collides(board, piece, rot, px, py):
    for x, y in cells_of(piece, rot, px, py):
        if x < 0 or x >= W or y >= H:
            return True
        if y >= 0 and board[y][x] is not None:
            return True
    return False

def lock_piece(board, piece, rot, px, py):
    for x, y in cells_of(piece, rot, px, py):
        if y >= 0:
            board[y][x] = piece

def full_row_indices(board):
    rows = []
    for y in range(H):
        if all(board[y][x] is not None for x in range(W)):
            rows.append(y)
    return rows

def clear_lines(board):
    new_rows = [row for row in board if any(v is None for v in row)]
    cleared = H - len(new_rows)
    while len(new_rows) < H:
        new_rows.insert(0, [None]*W)
    return new_rows, cleared

def try_rotate(board, piece, rot, px, py, direction):
    new_rot = (rot + direction) % 4
    kicks = [0, -1, 1, -2, 2]
    for dx in kicks:
        if not collides(board, piece, new_rot, px + dx, py):
            return new_rot, px + dx
    return rot, px

def color_pair_for(piece):
    if piece is None:
        return 0
    ordering = ["I","O","T","S","Z","J","L"]
    try:
        return ordering.index(piece) + 1
    except ValueError:
        return 0


def piece_cell_str(piece):
    """Return the display string for a piece cell.

    If the 'emoji' piece palette is selected, return an emoji (plus a
    trailing space to match the two-column cell layout). Otherwise
    return the default bracket pair "[]".
    """
    if piece is None:
        return "  "
    try:
        palette = SETTINGS.get('piece_palette', 'default').lower()
        if palette in ('emoji', 'modern'):
            ch = PIECE_EMOJI_MAP.get(piece)
            if not ch:
                if palette == 'emoji':
                    ch = random.choice(EMOJI_LIST)
                    PIECE_EMOJI_MAP[piece] = ch
                else:
                    # For modern, should not happen, but fallback
                    ch = '[]'[:1]  # just in case
            return ch + ' '
    except Exception:
        pass
    return "[]"

# ---------- START SCREEN ----------
def start_screen(stdscr):
    art = MENU_ART
    title = [
r"                   Caleb Katz's                 ",
r"  ____  ____  ____  _  _  __  __ _   __   __    ",
r" (_  _)(  __)(  _ \( \/ )(  )(  ( \ / _\ (  )   ",
r"   )(   ) _)  )   // \/ \ )( /    //    \/ (_/\ ",
r"  (__) (____)(__\_)\_)(_/(__)\_)__)\_/\_/\____/ ",
r"        ____  ____  ____  ____  __  ____        ",
r"       (_  _)(  __)(_  _)(  _ \(  )/ ___)       ",
r"         )(   ) _)   )(   )   / )( \___ \       ",
r"        (__) (____) (__) (__\_)(__)(____/       ",
r"                                                ",
r"                   (Web Version)                ",
r"                                                "
]
    # Removed direct-play and ESC hints to avoid misleading quit hints
    per_line_delay = 0.01

    dome_chars = set("TFJ+{}x/\\|A")
    accent_chars = set(".;:,=~")
    roof_chars = set("^\"_-")
    dark_chars = set("()[]")

    stdscr.nodelay(True)   # non-blocking during animation
    stdscr.keypad(True)
    curses.curs_set(0)

    has_colors = curses.has_colors() and SETTINGS.get('colored_art', True)
    green_palette = SETTINGS.get('piece_palette', 'default').lower() == 'electronika'
    if has_colors:
        curses.start_color()
        try:
            curses.use_default_colors()
        except Exception:
            pass
        try:
            if green_palette:
                for i in range(21, 30):
                    try:
                        curses.init_pair(i, curses.COLOR_GREEN, -1)
                    except Exception:
                        pass
                try:
                    stdscr.bkgd(' ', curses.color_pair(21))
                except curses.error:
                    pass
            else:
                curses.init_pair(21, curses.COLOR_RED, -1)
                curses.init_pair(22, curses.COLOR_YELLOW, -1)
                curses.init_pair(23, curses.COLOR_MAGENTA, -1)
                curses.init_pair(24, curses.COLOR_CYAN, -1)
                curses.init_pair(25, curses.COLOR_GREEN, -1)
                curses.init_pair(26, curses.COLOR_YELLOW, -1)
                curses.init_pair(27, curses.COLOR_RED, -1)
                curses.init_pair(28, curses.COLOR_MAGENTA, -1)
                curses.init_pair(29, curses.COLOR_CYAN, -1)
        except Exception:
            has_colors = False

    # fireworks list
    fireworks = []
    last_spawn = time.time()
    spawn_period = 0.9
    blink_on = True
    last_blink = time.time()
    blink_period = 0.6

    # fade-in start time: reveal art top-to-bottom over FADE_DURATION seconds
    fade_start = time.time()
    FADE_DURATION = 1.5
    # when exiting menu, do a faster fade-out
    FADE_OUT_DURATION = 0.35

    # New: menu with Local Multiplayer option, VS COM and Advanced Options
    options = ["Start", "Local Multiplayer", "VS COM", "Adv. Options", "Quit"]
    sel = 0
    while True:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()
        art_width = max(len(line) for line in art)
        art_height = len(art)
        needed_rows = len(title) + art_height + 8
        needed_cols = max(art_width, max(len(line) for line in title)) + 6

        if max_y < needed_rows or max_x < needed_cols:
            msg1 = "Terminal too small for start screen."
            msg2 = f"Resize to at least {needed_cols}x{needed_rows} (cols x rows)."
            try:
                stdscr.addstr(max_y//2 - 1, max(0, (max_x - len(msg1))//2), msg1, curses.A_REVERSE)
                stdscr.addstr(max_y//2,     max(0, (max_x - len(msg2))//2), msg2)
                stdscr.refresh()
            except curses.error:
                pass
            k = stdscr.getch()
            if k in (ord('q'), ord('Q')):
                # ignore 'q' on start screen to avoid accidental quit
                pass
            time.sleep(0.1)
            continue

        top = (max_y - needed_rows) // 2
        left = (max_x - art_width) // 2

        # draw title & art every frame
        try:
            for i, line in enumerate(title):
                stdscr.addstr(top + i, max(0, (max_x - len(line)) // 2), line, curses.A_BOLD)
            stdscr.addstr(top + len(title), max(0, (max_x - len(subtitle)) // 2), subtitle, curses.A_DIM)
        except curses.error:
            pass

        # compute fade progress and reveal art smoothly using easing and partial-character reveal
        now = time.time()
        elapsed = now - fade_start
        raw_frac = max(0.0, min(1.0, elapsed / FADE_DURATION))
        # ease in-out for smoother movement
        eased = 0.5 - 0.5 * math.cos(raw_frac * math.pi)
        # position across rows (may be fractional to allow partial reveal of next row)
        pos = eased * art_height
        full_rows = int(pos)
        partial = pos - full_rows
        for i, line in enumerate(art):
            y = top + len(title) + 2 + i
            x = left
            # draw full rows
            if i < full_rows:
                try:
                    for ch in line:
                        attr = curses.A_NORMAL
                        if has_colors:
                            if ch in dome_chars:
                                pair = 21 + (ord(ch) % 5)
                                attr = curses.color_pair(pair) | curses.A_BOLD
                            elif ch in accent_chars:
                                attr = curses.color_pair(22) | curses.A_BOLD
                            elif ch in roof_chars:
                                attr = curses.color_pair(24) | curses.A_BOLD
                            elif ch in dark_chars:
                                attr = curses.color_pair(25)
                        stdscr.addstr(y, x, ch, attr)
                        x += 1
                except curses.error:
                    pass
            # partial reveal for the next row
            elif i == full_rows and full_rows < art_height:
                try:
                    reveal_chars = int(partial * len(line))
                    for j, ch in enumerate(line):
                        attr = curses.A_NORMAL
                        if has_colors:
                            if ch in dome_chars:
                                pair = 21 + (ord(ch) % 5)
                                attr = curses.color_pair(pair) | curses.A_BOLD
                            elif ch in accent_chars:
                                attr = curses.color_pair(22) | curses.A_BOLD
                            elif ch in roof_chars:
                                attr = curses.color_pair(24) | curses.A_BOLD
                            elif ch in dark_chars:
                                attr = curses.color_pair(25)
                        if j < reveal_chars:
                            stdscr.addstr(y, x, ch, attr)
                        else:
                            stdscr.addstr(y, x, ' ')
                        x += 1
                except curses.error:
                    pass
            # rows below remain hidden until revealed
            else:
                continue

        # hints + menu: only show after fade completes
        try:
            hint_y = top + len(title) + 2 + art_height + 2
            if elapsed >= FADE_DURATION:
                # draw menu options centered under art
                for i, opt in enumerate(options):
                    attr = curses.A_REVERSE | curses.A_BOLD if i == sel else curses.A_BOLD if i==0 else curses.A_NORMAL
                    stdscr.addstr(hint_y + i, max(0, (max_x - len(opt)) // 2), opt, attr)
        except curses.error:
            pass

        # blink toggle
        now = time.time()
        if now - last_blink >= blink_period:
            blink_on = not blink_on
            last_blink = now

        # spawn occasional fireworks
        if now - last_spawn >= spawn_period:
            pad = max(6, art_width // 3)
            x_min = max(1, left - pad)
            x_max = min(max_x - 2, left + art_width - 1 + pad)
            if x_max >= x_min:
                x = random.randint(x_min, x_max)
                y_bottom = min(max_y - 3, top + len(title) + art_height + 1)
                target_y = max(1, top + len(title) + random.randint(1, 2))
                fireworks.append({
                    "x": x, "y": y_bottom, "phase": "rise", "target_y": target_y,
                    "age": 0, "parts": [], "tail": [], "tail_max": random.randint(2, 3)
                })
            last_spawn = now

        # update fireworks (same as before)
        updated = []
        for fw in fireworks:
            fw["age"] += 1
            if fw["phase"] == "rise":
                fw["tail"].append((fw["x"], fw["y"]))
                if len(fw["tail"]) > fw["tail_max"]:
                    fw["tail"] = fw["tail"][-fw["tail_max"]:]
                fw["y"] -= 1
                if fw["y"] <= fw["target_y"] or fw["age"] >= 40:
                    parts = []
                    count = random.randint(12, 16)
                    for _ in range(count):
                        dx = random.randint(-6, 6)
                        dy = random.randint(-3, 3)
                        life = random.randint(10, 16)
                        color = random.choice([26, 27, 28, 29]) if has_colors else 0
                        fx = fw["x"] + dx
                        fy = fw["y"] + dy
                        # velocity scaled so spread continues outward; tuned experimentally
                        vx = dx * 0.09
                        vy = dy * 0.06
                        parts.append({
                            "x": int(round(fx)),
                            "y": int(round(fy)),
                            "fx": fx,
                            "fy": fy,
                            "vx": vx,
                            "vy": vy,
                            "age": 0,
                            "life": life,
                            "color": color,
                        })
                    fw["phase"] = "explode"
                    fw["parts"] = parts
            elif fw["phase"] == "explode":
                alive = []
                for p in fw['parts']:
                    p['age'] += 1
                    if p['age'] <= p['life']:
                        p['fx'] = p.get('fx', p.get('x', 0)) + p.get('vx', 0)
                        grav = 0.06 if p['age'] > p['life']//2 else 0.0
                        p['fy'] = p.get('fy', p.get('y', 0)) + p.get('vy', 0) + grav
                        p['x'] = int(round(p['fx']))
                        p['y'] = int(round(p['fy']))
                        alive.append(p)
                fw['parts'] = alive
                if not fw["parts"]:
                    fw["phase"] = "done"
            if fw["phase"] != "done":
                updated.append(fw)
        fireworks = updated

        # draw fireworks on top
        for fw in fireworks:
            if fw["phase"] == "rise":
                for (tx, ty) in fw.get("tail", []):
                    try:
                        if 0 <= ty < max_y and 0 <= tx < max_x:
                            attr = curses.A_DIM
                            if has_colors:
                                attr |= curses.color_pair(22)
                            stdscr.addstr(ty, tx, ".", attr)
                    except curses.error:
                        pass
                try:
                    if 0 <= fw["y"] < max_y and 0 <= fw["x"] < max_x:
                        stdscr.addstr(fw["y"], fw["x"], "|", (curses.color_pair(22) | curses.A_BOLD) if has_colors else curses.A_BOLD)
                except curses.error:
                    pass
            elif fw["phase"] == "explode":
                for p in fw["parts"]:
                    try:
                        if not (0 <= p["y"] < max_y and 0 <= p["x"] < max_x):
                            continue
                        halfway = max(1, p["life"] // 2)
                        ch = "*" if p["age"] <= halfway else "."
                        attr = curses.A_BOLD if p["age"] <= halfway else curses.A_DIM
                        if has_colors and p["color"]:
                            attr |= curses.color_pair(p["color"])
                        stdscr.addstr(p["y"], p["x"], ch, attr)
                    except curses.error:
                        pass

        stdscr.refresh()

        # input handling for menu navigation
        stdscr.timeout(100)
        k = stdscr.getch()
        stdscr.timeout(-1)
        if k in (ord('q'), ord('Q')):
            # ignore 'q' in menu; use the Quit option instead
            pass
        if k in (curses.KEY_UP, ord('k'), ord('K')):
            sel = (sel - 1) % len(options)
        if k in (curses.KEY_DOWN, ord('j'), ord('J')):
            sel = (sel + 1) % len(options)
        if k in (10, 13, curses.KEY_ENTER):
            choice = options[sel]
            if choice == "Start":
                return "single"
            if choice == "Local Multiplayer":
                return "local"
            if choice == "VS COM":
                return "vscom"
            if choice == "Adv. Options":
                try:
                    adv_options_menu(stdscr)
                except Exception:
                    pass
                # return to start screen after adjusting options
                continue
            return False
        # loop continues, redraw next frame

# ---------- DRAW GAME ----------
def draw(
    stdscr, board, piece, rot, px, py,
    next_piece, hold_piece, score, level, lines, paused,
    flash_rows=None, flash_on=False, in_game_fireworks=None
):
    if curses.has_colors():
        try:
            if SETTINGS.get('piece_palette', 'default').lower() == 'electronika':
                stdscr.bkgd(' ', curses.color_pair(1))
            else:
                stdscr.bkgd(' ', curses.A_NORMAL)
        except curses.error:
            pass
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()

    PANEL_W = 22
    ART_PAD = 3
    GAME_WIDTH = (2 * W) + 6 + PANEL_W + ART_PAD + ART_W
    GAME_HEIGHT = max(H, 25, ART_H + 2)

    ox = max(2, (max_x - GAME_WIDTH) // 2)
    oy = max(1, (max_y - GAME_HEIGHT) // 2)

    panel_x = ox + 2*W + 6

    # panel text
    try:
        stdscr.addstr(oy, panel_x, "TETRIS (terminal)")
        stdscr.addstr(oy+2, panel_x, f"Score: {score}")
        stdscr.addstr(oy+3, panel_x, f"Level: {level}")
        stdscr.addstr(oy+4, panel_x, f"Lines: {lines}")
        stdscr.addstr(oy+6, panel_x, "Next:")
        stdscr.addstr(oy+12, panel_x, "Hold:")
        stdscr.addstr(oy+18, panel_x, "Controls:")
        stdscr.addstr(oy+19, panel_x, "←/→ or A/D move")
        stdscr.addstr(oy+20, panel_x, "↓ or S soft drop")
        stdscr.addstr(oy+21, panel_x, "↑/X or W rot cw")
        stdscr.addstr(oy+22, panel_x, "Z rot ccw")
        stdscr.addstr(oy+23, panel_x, "Space hard (lock)")
        stdscr.addstr(oy+24, panel_x, "P pause, C hold")
        stdscr.addstr(oy+25, panel_x, "R restart, ESC menu")
        stdscr.addstr(oy+26, panel_x, "Quit via menu")
    except curses.error:
        pass

    # next preview
    np_cells = TETROMINOES.get(next_piece, [[]])[0]
    for y in range(4):
        for x in range(4):
            ch = "  "
            attr = curses.A_NORMAL
            if (x,y) in np_cells:
                ch = piece_cell_str(next_piece)
                if curses.has_colors() and SETTINGS.get('colored_pieces', True):
                    attr = curses.color_pair(color_pair_for(next_piece)) | curses.A_BOLD
                else:
                    attr = curses.A_NORMAL
            try:
                stdscr.addstr(oy+7+y, panel_x+2*x, ch, attr)
            except curses.error:
                pass

    # hold preview
    hp_cells = TETROMINOES.get(hold_piece, [[]])[0] if hold_piece else []
    for y in range(4):
        for x in range(4):
            ch = "  "
            attr = curses.A_NORMAL
            if (x,y) in hp_cells:
                ch = piece_cell_str(hold_piece)
                if curses.has_colors() and SETTINGS.get('colored_pieces', True):
                    attr = curses.color_pair(color_pair_for(hold_piece)) | curses.A_BOLD
                else:
                    attr = curses.A_NORMAL
            try:
                stdscr.addstr(oy+13+y, panel_x+2*x, ch, attr)
            except curses.error:
                pass

    # board border
    for y in range(H):
        try:
            stdscr.addstr(oy+y, ox-2, "||")
            stdscr.addstr(oy+y, ox + 2*W, "||")
        except curses.error:
            pass
    try:
        stdscr.addstr(oy-1, ox-2, "=="*(W+2))
        stdscr.addstr(oy+H, ox-2, "=="*(W+2))
    except curses.error:
        pass

    # ghost and active
    gpy = py
    while not collides(board, piece, rot, px, gpy+1):
        gpy += 1
    ghost_cells = set(cells_of(piece, rot, px, gpy))
    active_cells = set(cells_of(piece, rot, px, py))

    flash_rows = set(flash_rows or [])

    for y in range(H):
        for x in range(W):
            ch = "  "
            attr = curses.A_NORMAL
            cell = board[y][x]

            if y in flash_rows:
                if flash_on:
                    # flash existing cell if present, otherwise show an empty flash
                    ch = piece_cell_str(cell) if cell is not None else "  "
                    attr = curses.A_REVERSE | curses.A_BOLD
                else:
                    ch = "  "
                    attr = curses.A_NORMAL
            else:
                if cell is not None:
                    ch = piece_cell_str(cell)
                    if curses.has_colors() and SETTINGS.get('colored_pieces', True):
                        attr = curses.color_pair(color_pair_for(cell)) | curses.A_BOLD
                    else:
                        attr = curses.A_NORMAL
                if (x,y) in ghost_cells and (x,y) not in active_cells and y >= 0:
                    ch = ".."
                    attr = curses.A_DIM
                if (x,y) in active_cells and y >= 0:
                    ch = piece_cell_str(piece)
                    if curses.has_colors() and SETTINGS.get('colored_pieces', True):
                        attr = curses.color_pair(color_pair_for(piece)) | curses.A_BOLD
                    else:
                        attr = curses.A_NORMAL

            try:
                stdscr.addstr(oy+y, ox + 2*x, ch, attr)
            except curses.error:
                pass

    if paused:
        msg = " PAUSED "
        try:
            stdscr.addstr(oy + H//2, ox + (2*W - len(msg))//2, msg, curses.A_REVERSE)
        except curses.error:
            pass

    # draw cathedral art on the far right
    art_x = panel_x + 22 + 1 + 2
    art_y = oy
    dome_chars = set("TFJ+{}x/\\|A")
    accent_chars = set(".;:,=~")
    roof_chars = set("^\"_-")
    dark_chars = set("()[]")
    for i, line in enumerate(MENU_ART):
        yy = art_y + i
        xx = art_x
        if yy < 0 or yy >= max_y:
            continue
        try:
            for ch in line:
                if xx >= max_x:
                    break
                attr = curses.A_NORMAL
                if curses.has_colors() and SETTINGS.get('colored_art', True):
                    if ch in dome_chars:
                        pair = 21 + (ord(ch) % 5)
                        attr = curses.color_pair(pair) | curses.A_BOLD
                    elif ch in accent_chars:
                        attr = curses.color_pair(22) | curses.A_BOLD
                    elif ch in roof_chars:
                        attr = curses.color_pair(24) | curses.A_BOLD
                    elif ch in dark_chars:
                        attr = curses.color_pair(25)
                stdscr.addstr(yy, xx, ch, attr)
                xx += 1
        except curses.error:
            pass

    # in-game fireworks (draw on top of art region)
    if in_game_fireworks:
        max_y, max_x = stdscr.getmaxyx()
        for fw in in_game_fireworks:
            if fw["phase"] == "rise":
                for (tx, ty) in fw.get("tail", []):
                    try:
                        if 0 <= ty < max_y and 0 <= tx < max_x:
                            attr = curses.A_DIM | (curses.color_pair(22) if (curses.has_colors() and SETTINGS.get('colored_art', True)) else 0)
                            stdscr.addstr(ty, tx, ".", attr)
                    except curses.error:
                        pass
                try:
                    if 0 <= fw["y"] < max_y and 0 <= fw["x"] < max_x:
                        stdscr.addstr(fw["y"], fw["x"], "|", (curses.color_pair(22)|curses.A_BOLD) if (curses.has_colors() and SETTINGS.get('colored_art', True)) else curses.A_BOLD)
                except curses.error:
                    pass
            elif fw["phase"] == "explode":
                for p in fw["parts"]:
                    try:
                        if not (0 <= p["y"] < max_y and 0 <= p["x"] < max_x):
                            continue
                        halfway = max(1, p["life"]//2)
                        ch = "*" if p["age"] <= halfway else "."
                        attr = (curses.A_BOLD if p["age"] <= halfway else curses.A_DIM)
                        if (curses.has_colors() and SETTINGS.get('colored_art', True)) and p.get("color"):
                            attr |= curses.color_pair(p["color"])
                        stdscr.addstr(p["y"], p["x"], ch, attr)
                    except curses.error:
                        pass

    stdscr.refresh()

def draw_local_split(stdscr, p1, p2, in_game_fireworks, stars, p1_ctrl_lines=None, p2_ctrl_lines=None, p1_flash_rows=None, p1_flash_on=False, p2_flash_rows=None, p2_flash_on=False):
    if curses.has_colors():
        try:
            if SETTINGS.get('piece_palette', 'default').lower() == 'electronika':
                stdscr.bkgd(' ', curses.color_pair(1))
            else:
                stdscr.bkgd(' ', curses.A_NORMAL)
        except curses.error:
            pass
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()

    # compute layout: left board, center art, right board
    gap = 4
    left_width = 2 * W
    right_width = 2 * W
    center_width = ART_W
    total_w = left_width + gap + center_width + gap + right_width
    ox = max(2, (max_x - total_w) // 2)
    oy = max(1, (max_y - max(H, ART_H)) // 2)

    left_x = ox
    center_x = left_x + left_width + gap
    right_x = center_x + center_width + gap

    # draw P1 border and cells
    try:
        stdscr.addstr(oy-2, left_x, "P1" + (" " + ('*'*min(stars.get('p1',0),5)) + (f" x {stars['p1']}" if stars.get('p1',0)>5 else "")))
    except curses.error:
        pass
    for y in range(H):
        try:
            stdscr.addstr(oy+y, left_x-2, "||")
            stdscr.addstr(oy+y, left_x + left_width, "||")
        except curses.error:
            pass

    # draw P2 border and cells
    try:
        stdscr.addstr(oy-2, right_x, "P2" + (" " + ('*'*min(stars.get('p2',0),5)) + (f" x {stars['p2']}" if stars.get('p2',0)>5 else "")))
    except curses.error:
        pass
    for y in range(H):
        try:
            stdscr.addstr(oy+y, right_x-2, "||")
            stdscr.addstr(oy+y, right_x + right_width, "||")
        except curses.error:
            pass

    # center art
    dome_chars = set("TFJ+{}x/\\|A")
    accent_chars = set(".;:,=~")
    roof_chars = set("^\"_-")
    dark_chars = set("()[]")
    for i, line in enumerate(MENU_ART):
        yy = oy + i
        xx = center_x
        if yy < 0 or yy >= max_y:
            continue
        try:
            for ch in line:
                if xx >= max_x:
                    break
                attr = curses.A_NORMAL
                if curses.has_colors() and SETTINGS.get('colored_art', True):
                    if ch in dome_chars:
                        pair = 21 + (ord(ch) % 5)
                        attr = curses.color_pair(pair) | curses.A_BOLD
                    elif ch in accent_chars:
                        attr = curses.color_pair(22) | curses.A_BOLD
                    elif ch in roof_chars:
                        attr = curses.color_pair(24) | curses.A_BOLD
                    elif ch in dark_chars:
                        attr = curses.color_pair(25)
                try:
                    stdscr.addstr(yy, xx, ch, attr)
                except curses.error:
                    pass
                xx += 1
        except curses.error:
            pass

    # helper to draw a player's board
    def draw_player(board_obj, board_x, flash_rows=None, flash_on=False):
        board = board_obj['board']
        piece = board_obj['cur']
        rot = board_obj['rot']
        px = board_obj['px']
        py = board_obj['py']
        # ghost
        gpy = py
        while not collides(board, piece, rot, px, gpy+1):
            gpy += 1
        ghost_cells = set(cells_of(piece, rot, px, gpy))
        active_cells = set(cells_of(piece, rot, px, py))
        flash_rows = set(flash_rows or [])
        for y in range(H):
            for x in range(W):
                ch = "  "
                attr = curses.A_NORMAL
                cell = board[y][x]

                # Handle flashing rows
                if y in flash_rows:
                    if flash_on:
                        ch = piece_cell_str(cell) if cell is not None else "  "
                        attr = curses.A_REVERSE | curses.A_BOLD
                    else:
                        ch = "  "
                        attr = curses.A_NORMAL
                else:
                    if cell is not None:
                        ch = piece_cell_str(cell)
                        if curses.has_colors() and SETTINGS.get('colored_pieces', True):
                            attr = curses.color_pair(color_pair_for(cell)) | curses.A_BOLD
                        else:
                            attr = curses.A_NORMAL
                # ghost overlay (draw small dots for projected landing)
                if (x,y) in ghost_cells and (x,y) not in active_cells and y >= 0:
                    ch = ".."
                    attr = curses.A_DIM

                # active piece overlay (draw current falling piece)
                # but don't draw it on rows that are flashing
                if (x,y) in active_cells and y >= 0 and y not in flash_rows:
                    ch = piece_cell_str(piece)
                    if curses.has_colors() and SETTINGS.get('colored_pieces', True):
                        attr = curses.color_pair(color_pair_for(piece)) | curses.A_BOLD
                    else:
                        attr = curses.A_NORMAL

                try:
                    stdscr.addstr(oy+y, board_x + 2*x, ch, attr)
                except curses.error:
                    pass

        # draw previews for Next and Hold. Prefer above the board; if there's
        # insufficient space, move previews to the side (left for left board,
        # right for right board) so they don't intrude on gameplay or center art.
        needed = 1 + 4 + 1 + 4  # labels and pieces
        preview_y = oy - (needed + 1)
        preview_x = board_x
        # If not enough space above, place previews to the side of the board
        if preview_y < 0:
            # try placing to the left of the board if it fits
            side_left_x = board_x - 10
            side_right_x = board_x + (2 * W) + 4
            if side_left_x >= 0:
                preview_x = side_left_x
                preview_y = oy
            else:
                preview_x = side_right_x
                preview_y = oy

        # Next label and piece
        try:
            stdscr.addstr(preview_y, preview_x, "Next:")
        except curses.error:
            pass
        npiece = board_obj.get('nxt')
        if npiece:
            cells = TETROMINOES.get(npiece, [[]])[0]
            for yy in range(4):
                for xx in range(4):
                    ch = "  "
                    attr = curses.A_NORMAL
                    if (xx,yy) in cells:
                        ch = piece_cell_str(npiece)
                        if curses.has_colors() and SETTINGS.get('colored_pieces', True):
                            attr = curses.color_pair(color_pair_for(npiece)) | curses.A_BOLD
                        else:
                            attr = curses.A_NORMAL
                    try:
                        stdscr.addstr(preview_y+1+yy, preview_x + 2*xx, ch, attr)
                    except curses.error:
                        pass
        # Hold label and piece (below Next)
        hold_label_y = preview_y + 1 + 4
        try:
            stdscr.addstr(hold_label_y, preview_x, "Hold:")
        except curses.error:
            pass
        hpiece = board_obj.get('hold')
        if hpiece:
            cells = TETROMINOES.get(hpiece, [[]])[0]
            for yy in range(4):
                for xx in range(4):
                    ch = "  "
                    attr = curses.A_NORMAL
                    if (xx,yy) in cells:
                        ch = piece_cell_str(hpiece)
                        if curses.has_colors() and SETTINGS.get('colored_pieces', True):
                            attr = curses.color_pair(color_pair_for(hpiece)) | curses.A_BOLD
                        else:
                            attr = curses.A_NORMAL
                    try:
                        stdscr.addstr(hold_label_y+1+yy, preview_x + 2*xx, ch, attr)
                    except curses.error:
                        pass
        # score under the board
        try:
            stdscr.addstr(oy + H + 1, board_x, f"Score: {board_obj.get('score',0)}")
        except curses.error:
            pass

    draw_player(p1, left_x, p1_flash_rows, p1_flash_on)
    draw_player(p2, right_x, p2_flash_rows, p2_flash_on)

    # show scores (already printed) and controls under each board
    # P1/P2 controls (can be overridden by caller)
    if p1_ctrl_lines is None:
        p1_controls = ["Controls:", "W:Rot", "A:Left", "S:Down", "D:Right", "2:Place", "1:Hold"]
    else:
        p1_controls = p1_ctrl_lines
    if p2_ctrl_lines is None:
        p2_controls = ["Controls:", "Up:Rot", "Left:Left", "Down:Down", "Right:Right", ".:Place", ",:Hold"]
    else:
        p2_controls = p2_ctrl_lines
    # Try to place P1 controls to the left of the left board
    try:
        left_ctrl_x = max(0, left_x - 20)
        for i, line in enumerate(p1_controls):
            stdscr.addstr(oy + i, left_ctrl_x, line)
    except curses.error:
        # fallback: under left board
        try:
            stdscr.addstr(oy + H + 2, left_x, " ".join(p1_controls)[:max_x-left_x])
        except curses.error:
            pass
    # Try to place P2 controls to the right of the right board
    try:
        right_ctrl_x = right_x + right_width + 2
        for i, line in enumerate(p2_controls):
            stdscr.addstr(oy + i, right_ctrl_x, line)
    except curses.error:
        # fallback: under right board
        try:
            stdscr.addstr(oy + H + 2, right_x, " ".join(p2_controls)[:max_x-right_x])
        except curses.error:
            pass

    # in-game fireworks in center
    if in_game_fireworks:
        for fw in in_game_fireworks:
            if fw["phase"] == "rise":
                for (tx, ty) in fw.get("tail", []):
                    try:
                        if 0 <= ty < max_y and 0 <= tx < max_x:
                            attr = curses.A_DIM | (curses.color_pair(22) if (curses.has_colors() and SETTINGS.get('colored_art', True)) else 0)
                            stdscr.addstr(ty, tx, ".", attr)
                    except curses.error:
                        pass
                try:
                    if 0 <= fw["y"] < max_y and 0 <= fw["x"] < max_x:
                        stdscr.addstr(fw["y"], fw["x"], "|", (curses.color_pair(22)|curses.A_BOLD) if (curses.has_colors() and SETTINGS.get('colored_art', True)) else curses.A_BOLD)
                except curses.error:
                    pass
            elif fw["phase"] == "explode":
                for p in fw["parts"]:
                    try:
                        if not (0 <= p["y"] < max_y and 0 <= p["x"] < max_x):
                            continue
                        halfway = max(1, p["life"]//2)
                        ch = "*" if p["age"] <= halfway else "."
                        attr = (curses.A_BOLD if p["age"] <= halfway else curses.A_DIM)
                        if (curses.has_colors() and SETTINGS.get('colored_art', True)) and p.get("color"):
                            attr |= curses.color_pair(p["color"])
                        stdscr.addstr(p["y"], p["x"], ch, attr)
                    except curses.error:
                        pass

    stdscr.refresh()

# ---------- Game Over screen ----------
def game_over_screen(stdscr, score):
    # Keep final game screen visible, fade ASCII art top-to-bottom, and prompt Play Again? Y/N
    stdscr.nodelay(False)
    stdscr.keypad(True)
    curses.curs_set(0)

    if curses.has_colors():
        try:
            if SETTINGS.get('piece_palette', 'default').lower() == 'green':
                stdscr.bkgd(' ', curses.color_pair(1))
            else:
                stdscr.bkgd(' ', curses.A_NORMAL)
        except curses.error:
            pass

    max_y, max_x = stdscr.getmaxyx()

    # Compute art area using same layout as draw()
    PANEL_W = 22
    ART_PAD = 3
    GAME_WIDTH = (2 * W) + 6 + PANEL_W + ART_PAD + ART_W
    GAME_HEIGHT = max(H, 25, ART_H + 2)
    ox = max(2, (max_x - GAME_WIDTH) // 2)
    oy = max(1, (max_y - GAME_HEIGHT) // 2)
    panel_x = ox + 2*W + 6
    art_x = panel_x + PANEL_W + ART_PAD
    art_y = oy

    # Attempt to preserve the current board render (do not clear entire screen)
    try:
        stdscr.refresh()
    except Exception:
        pass

    # Draw the MENU_ART into the reserved art area in white
    try:
        for i, line in enumerate(MENU_ART):
            y = art_y + i
            if 0 <= y < max_y:
                for j, char in enumerate(line):
                    if art_x + j < max_x:
                        stdscr.addch(y, art_x + j, char, curses.color_pair(7))  # white color
        stdscr.refresh()
    except Exception:
        pass

    # Fade out ASCII art top-to-bottom, replacing art lines with blanks
    try:
        FADE_OUT_ART_DUR = 0.6
        per_line = FADE_OUT_ART_DUR / max(1, ART_H)
        for i in range(ART_H):
            y = art_y + i
            if 0 <= y < max_y:
                try:
                    for cx in range(art_x, art_x + ART_W):
                        stdscr.addch(y, cx, ' ')
                except curses.error:
                    pass
                stdscr.refresh()
                time.sleep(per_line)
    except Exception:
        pass

    # Place the Play Again prompt where the art was
    prompt = "Play Again? Y/N"
    try:
        prompt_y = art_y + (ART_H // 2)
        prompt_x = art_x + max(0, (ART_W - len(prompt)) // 2)
        stdscr.addstr(prompt_y, prompt_x, prompt, curses.A_BOLD | curses.A_REVERSE)
        # Show score and short instructions below prompt
        info = f"Score: {score}"
        info_y = prompt_y + 2
        info_x = art_x + max(0, (ART_W - len(info)) // 2)
        stdscr.addstr(info_y, info_x, info)
        stdscr.refresh()
    except curses.error:
        pass

    # Wait for Y/N choice; return 'restart' on Y, 'menu' on N
    try:
        while True:
            k = stdscr.getch()
            if k in (ord('y'), ord('Y')):
                stdscr.nodelay(True)
                return "restart"
            if k in (ord('n'), ord('N')) or k == 27:
                stdscr.nodelay(True)
                return "menu"
    finally:
        try:
            stdscr.nodelay(True)
        except Exception:
            pass

def pause_menu(stdscr):
    # Blocking pause submenu shown on ESC. Returns one of: 'resume','menu','restart','quit'
    stdscr.nodelay(False)
    stdscr.keypad(True)
    curses.curs_set(0)
    options = ["Resume", "Customize Controls", "Adv. Options", "Back to menu", "Restart", "Quit Game"]
    sel = 0
    try:
        while True:
            stdscr.erase()
            max_y, max_x = stdscr.getmaxyx()
            title = " PAUSED "
            ox = (max_x - 30)//2
            oy = (max_y - 8)//2
            try:
                stdscr.addstr(oy, ox + (30 - len(title))//2, title, curses.A_REVERSE | curses.A_BOLD)
            except curses.error:
                pass
            for i, opt in enumerate(options):
                attr = curses.A_REVERSE | curses.A_BOLD if i == sel else curses.A_NORMAL
                try:
                    stdscr.addstr(oy + 2 + i, ox + 4, opt, attr)
                except curses.error:
                    pass
            stdscr.refresh()
            k = stdscr.getch()
            if k in (curses.KEY_UP, ord('k'), ord('K')):
                sel = (sel - 1) % len(options)
            elif k in (curses.KEY_DOWN, ord('j'), ord('J')):
                sel = (sel + 1) % len(options)
            elif k in (10, 13, curses.KEY_ENTER):
                choice = options[sel]
                stdscr.nodelay(True)
                if choice == "Resume":
                    return 'resume'
                if choice == "Customize Controls":
                    try:
                        controls_customize_menu(stdscr)
                    except Exception:
                        pass
                    # return to pause menu after customization
                    continue
                if choice == "Adv. Options":
                    try:
                        adv_options_menu(stdscr)
                    except Exception:
                        pass
                    continue
                if choice == "Back to menu":
                    return 'menu'
                if choice == "Restart":
                    return 'restart'
                if choice == "Quit Game":
                    return 'quit'
            elif k == 27:
                # ESC again -> resume
                stdscr.nodelay(True)
                return 'resume'
    finally:
        try:
            stdscr.nodelay(True)
        except Exception:
            pass


def controls_customize_menu(stdscr):
    """Top-level customization menu that selects single vs local player bindings."""
    stdscr.nodelay(False)
    stdscr.keypad(True)
    curses.curs_set(0)
    options = ["Single Player", "Local Multiplayer", "Back"]
    sel = 0
    try:
        while True:
            stdscr.erase()
            max_y, max_x = stdscr.getmaxyx()
            title = " Customize Controls "
            ox = max(0, (max_x - 40)//2)
            oy = max(0, (max_y - 8)//2)
            try:
                stdscr.addstr(oy, ox + (40 - len(title))//2, title, curses.A_REVERSE | curses.A_BOLD)
            except curses.error:
                pass
            for i, opt in enumerate(options):
                attr = curses.A_REVERSE | curses.A_BOLD if i == sel else curses.A_NORMAL
                try:
                    stdscr.addstr(oy + 2 + i, ox + 4, opt, attr)
                except curses.error:
                    pass
            stdscr.refresh()
            k = stdscr.getch()
            if k in (curses.KEY_UP, ord('k'), ord('K')):
                sel = (sel - 1) % len(options)
            elif k in (curses.KEY_DOWN, ord('j'), ord('J')):
                sel = (sel + 1) % len(options)
            elif k in (10, 13, curses.KEY_ENTER):
                choice = options[sel]
                if choice == "Single Player":
                    controls_rebind_menu(stdscr, 'single')
                elif choice == "Local Multiplayer":
                    # submenu for P1/P2
                    subopts = ["P1", "P2", "Back"]
                    s = 0
                    while True:
                        stdscr.erase()
                        try:
                            stdscr.addstr(oy, ox + (40 - len(" Local Multiplayer "))//2, " Local Multiplayer ", curses.A_REVERSE | curses.A_BOLD)
                        except curses.error:
                            pass
                        for i, opt in enumerate(subopts):
                            attr = curses.A_REVERSE | curses.A_BOLD if i == s else curses.A_NORMAL
                            try:
                                stdscr.addstr(oy + 2 + i, ox + 4, opt, attr)
                            except curses.error:
                                pass
                        stdscr.refresh()
                        kk = stdscr.getch()
                        if kk in (curses.KEY_UP, ord('k'), ord('K')):
                            s = (s - 1) % len(subopts)
                        elif kk in (curses.KEY_DOWN, ord('j'), ord('J')):
                            s = (s + 1) % len(subopts)
                        elif kk in (10, 13, curses.KEY_ENTER):
                            ch = subopts[s]
                            if ch == 'P1':
                                controls_rebind_menu(stdscr, 'local_p1')
                            elif ch == 'P2':
                                controls_rebind_menu(stdscr, 'local_p2')
                            else:
                                break
                        elif kk == 27:
                            break
                else:
                    break
            elif k == 27:
                break
    finally:
        try:
            stdscr.nodelay(True)
        except Exception:
            pass


def controls_rebind_menu(stdscr, scope):
    """Menu for rebinding controls in a given scope ('single','local_p1','local_p2')."""
    stdscr.nodelay(False)
    stdscr.keypad(True)
    curses.curs_set(0)
    actions = list(CONTROLS.get(scope, {}).keys())
    # prefer a consistent order when possible
    preferred = ['left', 'right', 'soft', 'rot_cw', 'rot_ccw', 'hard', 'hold', 'pause', 'restart']
    actions = [a for a in preferred if a in actions] + [a for a in actions if a not in preferred]
    options = [f"{a}: {controls_display_names(scope,a)}" for a in actions]
    options.append("Revert to Defaults")
    options.append("Back")
    sel = 0
    try:
        while True:
            stdscr.erase()
            max_y, max_x = stdscr.getmaxyx()
            title = f" Rebind ({scope}) "
            ox = max(0, (max_x - 60)//2)
            oy = max(0, (max_y - (4 + len(options)))//2)
            try:
                stdscr.addstr(oy, ox + (60 - len(title))//2, title, curses.A_REVERSE | curses.A_BOLD)
            except curses.error:
                pass
            for i, opt in enumerate(options):
                attr = curses.A_REVERSE | curses.A_BOLD if i == sel else curses.A_NORMAL
                try:
                    stdscr.addstr(oy + 2 + i, ox + 2, opt[:58], attr)
                except curses.error:
                    pass
            stdscr.refresh()
            k = stdscr.getch()
            if k in (curses.KEY_UP, ord('k'), ord('K')):
                sel = (sel - 1) % len(options)
            elif k in (curses.KEY_DOWN, ord('j'), ord('J')):
                sel = (sel + 1) % len(options)
            elif k in (10, 13, curses.KEY_ENTER):
                if sel < len(actions):
                    action = actions[sel]
                    # prompt for new key
                    prompt = f"Press new key for {action} (ESC to cancel)"
                    try:
                        stdscr.addstr(oy + len(options) + 4, ox + 2, prompt, curses.A_BOLD)
                    except curses.error:
                        pass
                    stdscr.refresh()
                    stdscr.nodelay(False)
                    nk = stdscr.getch()
                    stdscr.nodelay(True)
                    if nk == 27:
                        # cancelled
                        continue
                    name = code_to_name(nk)
                    # store single binding as the chosen name
                    CONTROLS[scope][action] = [name]
                    options[sel] = f"{action}: {controls_display_names(scope, action)}"
                else:
                    choice = options[sel]
                    if choice == 'Revert to Defaults':
                        # restore
                        for a,v in DEFAULT_CONTROLS.get(scope, {}).items():
                            CONTROLS[scope][a] = v[:] if isinstance(v, list) else [v]
                        options = [f"{a}: {controls_display_names(scope,a)}" for a in actions] + ['Revert to Defaults', 'Back']
                    elif choice == 'Back':
                        break
            elif k == 27:
                break
    finally:
        try:
            stdscr.nodelay(True)
        except Exception:
            pass


def difficulty_menu(stdscr):
    """Prompt to choose AI difficulty for VS COM mode."""
    stdscr.nodelay(False)
    stdscr.keypad(True)
    curses.curs_set(0)
    options = ["NORMAL", "HARD", "RASPUTIN", "Back"]
    sel = 0
    try:
        while True:
            stdscr.erase()
            max_y, max_x = stdscr.getmaxyx()
            title = " Select Difficulty "
            ox = max(0, (max_x - 30)//2)
            oy = max(0, (max_y - (4 + len(options)))//2)
            try:
                stdscr.addstr(oy, ox + (30 - len(title))//2, title, curses.A_REVERSE | curses.A_BOLD)
            except curses.error:
                pass
            for i, opt in enumerate(options):
                attr = curses.A_REVERSE | curses.A_BOLD if i == sel else curses.A_NORMAL
                try:
                    stdscr.addstr(oy + 2 + i, ox + 4, opt, attr)
                except curses.error:
                    pass
            stdscr.refresh()
            k = stdscr.getch()
            if k in (curses.KEY_UP, ord('k'), ord('K')):
                sel = (sel - 1) % len(options)
            elif k in (curses.KEY_DOWN, ord('j'), ord('J')):
                sel = (sel + 1) % len(options)
            elif k in (10, 13, curses.KEY_ENTER):
                choice = options[sel]
                if choice == 'Back':
                    return None
                return choice
            elif k == 27:
                return None
    finally:
        try:
            stdscr.nodelay(True)
        except Exception:
            pass


def adv_options_menu(stdscr):
    """Advanced options: toggle colored ASCII art, pick art palette, and pick piece palette."""
    stdscr.nodelay(False)
    stdscr.keypad(True)
    curses.curs_set(0)
    art_palettes = ['Default', 'Mono', 'High-Contrast']
    piece_palettes = ['Default', 'Greyscale', 'Electronika', 'Camo', 'USA', 'USSR', 'Bananarama', 'Emoji', 'Modern']

    sel = 0
    options = [
        lambda: f"Colored ASCII Art: {'On' if SETTINGS.get('colored_art', True) else 'Off'}",
        lambda: f"Art Palette: {SETTINGS.get('art_palette','default').title()}",
        lambda: f"Piece Colors: {SETTINGS.get('piece_palette','default').title()}",
        lambda: "Back",
    ]

    try:
        while True:
            stdscr.erase()
            max_y, max_x = stdscr.getmaxyx()
            title = " Advanced Options "
            ox = max(0, (max_x - 48)//2)
            oy = max(0, (max_y - (4 + len(options)))//2)
            try:
                stdscr.addstr(oy, ox + (48 - len(title))//2, title, curses.A_REVERSE | curses.A_BOLD)
            except curses.error:
                pass

            for i, opt_fn in enumerate(options):
                txt = opt_fn()
                attr = curses.A_REVERSE | curses.A_BOLD if i == sel else curses.A_NORMAL
                try:
                    stdscr.addstr(oy + 2 + i, ox + 4, txt, attr)
                except curses.error:
                    pass

            stdscr.refresh()
            k = stdscr.getch()
            if k in (curses.KEY_UP, ord('k'), ord('K')):
                sel = (sel - 1) % len(options)
            elif k in (curses.KEY_DOWN, ord('j'), ord('J')):
                sel = (sel + 1) % len(options)
            elif k in (10, 13, curses.KEY_ENTER):
                # handle selection
                if sel == 0:
                    # toggle colored ASCII art
                    SETTINGS['colored_art'] = not SETTINGS.get('colored_art', True)
                    # apply immediately
                    init_color_pairs()
                elif sel == 1:
                    # cycle art palette
                    cur = SETTINGS.get('art_palette', 'default').lower()
                    art_lower = [p.lower() for p in art_palettes]
                    idx = art_lower.index(cur) if cur in art_lower else 0
                    idx = (idx + 1) % len(art_palettes)
                    SETTINGS['art_palette'] = art_palettes[idx].lower()
                    init_color_pairs()
                elif sel == 2:
                    # cycle piece palette
                    cur = SETTINGS.get('piece_palette', 'default').lower()
                    piece_lower = [p.lower() for p in piece_palettes]
                    idx = piece_lower.index(cur) if cur in piece_lower else 0
                    idx = (idx + 1) % len(piece_palettes)
                    SETTINGS['piece_palette'] = piece_palettes[idx].lower()
                    init_color_pairs()
                elif sel == 3:
                    break
            elif k == 27:
                break
    finally:
        try:
            stdscr.nodelay(True)
        except Exception:
            pass


# ---------- MAIN GAME ----------
def tetris(stdscr):
    curses.curs_set(0)
    stdscr.keypad(True)
    # automated VS COM mode (controlled via env vars):
    AUTO_VS = os.environ.get('AUTO_VS_COM', '') == '1'
    AUTO_VS_DIFF = os.environ.get('AUTO_VS_COM_DIFF', 'RASPUTIN')
    try:
        AUTO_VS_RUNS = int(os.environ.get('AUTO_VS_COM_RUNS', '3'))
    except Exception:
        AUTO_VS_RUNS = 3
    AUTO_VS_COUNT = 0

    while True:
        choice = start_screen(stdscr)
        if choice is False:
            return

        # init colors
        # initialize color pairs according to current SETTINGS
        init_color_pairs()

        # ensure non-blocking input before games
        stdscr.nodelay(True)

        def run_one_game():
            board = empty_board()
            bag = new_bag()
            def pop_piece():
                nonlocal bag
                if not bag:
                    bag = new_bag()
                return bag.pop()

            cur = pop_piece()
            nxt = pop_piece()
            hold = None
            hold_used = False
            rot = 0
            px, py = 3, -1
            score = 0
            lines = 0
            level = 1
            paused = False

            last_fall = time.time()

            # in-game fireworks & their visual tick
            in_game_fireworks = []

            # Game start fade-in: reveal the play area over 1.5 seconds
            try:
                fade_start_game = time.time()
                FADE_IN_GAME = 1.5
                while True:
                    f_elapsed = time.time() - fade_start_game
                    frac = max(0.0, min(1.0, f_elapsed / FADE_IN_GAME))
                    max_y, max_x = stdscr.getmaxyx()
                    draw(stdscr, board, cur, rot, px, py, nxt, hold, score, level, lines, paused,
                         flash_rows=None, flash_on=False, in_game_fireworks=in_game_fireworks)
                    # hide rows below reveal line to create top-to-bottom reveal
                    reveal_lines = int(frac * max_y)
                    try:
                        for yy in range(reveal_lines, max_y):
                            stdscr.move(yy, 0)
                            stdscr.clrtoeol()
                    except curses.error:
                        pass
                    stdscr.refresh()
                    if frac >= 1.0:
                        break
                    time.sleep(0.016)
            except Exception:
                pass

            def fall_delay(lvl):
                return max(0.08, 0.6 - (lvl-1)*0.05)
            fw_last_tick = time.time()
            fw_tick = 0.08  # visual update step for fireworks (controls speed)

            def spawn_in_game_firework(art_left, art_width_local, art_top, max_x_local, max_y_local, fireworks_list):
                x_min = art_left
                x_max = min(max_x_local-2, art_left + art_width_local -1)
                if x_max < x_min:
                    return
                x = random.randint(x_min, x_max)
                y_bottom = min(max_y_local - 3, art_top + ART_H - 1)
                target_y = max(art_top + 1, art_top + random.randint(1,2))
                fireworks_list.append({
                    "x": x, "y": y_bottom, "phase": "rise", "target_y": target_y,
                    "age": 0, "parts": [], "tail": [], "tail_max": random.randint(1,3),
                    "art_left": art_left, "art_right": x_max,
                })

            def spawn_multiple_fireworks(count):
                max_y, max_x = stdscr.getmaxyx()
                PANEL_W = 22
                ART_PAD = 3
                GAME_WIDTH = (2 * W) + 6 + PANEL_W + ART_PAD + ART_W
                ox = max(2, (max_x - GAME_WIDTH) // 2)
                oy = max(1, (max_y - max(H, 25, ART_H+2)) // 2)
                panel_x = ox + 2*W + 6
                art_x = panel_x + 22 + 1 + 2
                art_y = oy
                for _ in range(count):
                    spawn_in_game_firework(art_x, ART_W, art_y, max_x, max_y, in_game_fireworks)

            def do_flash_if_tetris(full_rows):
                if len(full_rows) != 4:
                    return
                for i in range(6):
                    draw(stdscr, board, cur, rot, px, py, nxt, hold, score, level, lines, paused,
                         flash_rows=full_rows, flash_on=(i%2==0), in_game_fireworks=in_game_fireworks)
                    time.sleep(0.08)

            def lock_and_resolve():
                nonlocal board, cur, nxt, hold_used, rot, px, py, score, lines, level
                lock_piece(board, cur, rot, px, py)
                full_rows = full_row_indices(board)
                if len(full_rows) == 4:
                    do_flash_if_tetris(full_rows)
                board2, cleared = clear_lines(board)
                for i in range(H):
                    board[i] = board2[i]
                if cleared:
                    lines += cleared
                    score += {1:100,2:300,3:500,4:800}[cleared] * level
                    level = 1 + (lines // 10)
                    spawn_count = 8 if cleared == 4 else cleared
                    spawn_multiple_fireworks(spawn_count)
                cur = nxt
                nxt = pop_piece()
                rot = 0
                px, py = 3, -1
                hold_used = False

            while True:
                now = time.time()

                # update in-game fireworks only on fw_tick intervals
                if now - fw_last_tick >= fw_tick:
                    fw_last_tick = now
                    updated = []
                    for fw in in_game_fireworks:
                        fw["age"] += 1
                        if fw["phase"] == "rise":
                            fw["tail"].append((fw["x"], fw["y"]))
                            if len(fw["tail"]) > fw["tail_max"]:
                                fw["tail"] = fw["tail"][-fw["tail_max"]:]
                            fw["y"] -= 1
                            if fw["y"] <= fw["target_y"] or fw["age"] >= 60:
                                parts = []
                                count = random.randint(10, 16)
                                for _ in range(count):
                                    dx = random.randint(-6, 6)
                                    dy = random.randint(-3, 3)
                                    life = random.randint(12, 18)
                                    color = random.choice([26,27,28,29]) if (curses.has_colors() and SETTINGS.get('colored_art', True)) else 0
                                    fx = fw["x"] + dx
                                    fy = fw["y"] + dy
                                    vx = dx * 0.09
                                    vy = dy * 0.06
                                    parts.append({
                                        "x": int(round(fx)),
                                        "y": int(round(fy)),
                                        "fx": fx,
                                        "fy": fy,
                                        "vx": vx,
                                        "vy": vy,
                                        "age": 0,
                                        "life": life,
                                        "color": color,
                                    })
                                pass
                                fw["phase"] = "explode"
                                fw["parts"] = parts
                        elif fw["phase"] == "explode":
                            alive = []
                            # determine art bounds from firework (fallback to screen)
                            try:
                                max_y2, max_x2 = stdscr.getmaxyx()
                            except Exception:
                                max_x2 = 1000
                            art_left = fw.get('art_left', 0)
                            art_right = fw.get('art_right', max_x2 - 1)
                            for p in fw["parts"]:
                                p["age"] += 1
                                if p["age"] <= p["life"]:
                                    # update float positions using stored velocities
                                    p["fx"] = p.get("fx", p.get("x", 0)) + p.get("vx", 0)
                                    grav = 0.06 if p["age"] > p["life"]//2 else 0.0
                                    p["fy"] = p.get("fy", p.get("y", 0)) + p.get("vy", 0) + grav
                                    p["x"] = int(round(p["fx"]))
                                    p["y"] = int(round(p["fy"]))
                                    # clamp into this firework's art bounds so particles remain visible
                                    if p["x"] < art_left:
                                        p["x"] = art_left
                                    if p["x"] > art_right:
                                        p["x"] = art_right
                                    alive.append(p)
                            fw["parts"] = alive
                            if not fw["parts"]:
                                fw["phase"] = "done"
                        if fw["phase"] != "done":
                            updated.append(fw)
                    in_game_fireworks[:] = updated

                # input
                key = stdscr.getch()
                if key != -1:
                    if key in (ord('q'), ord('Q')):
                        # ignore 'q' during single-player; user should use menu options
                        pass
                    if key == 27:  # ESC -> pause menu
                        action = pause_menu(stdscr)
                        if action == 'menu':
                            return 'menu'
                        if action == 'restart':
                            return 'restart'
                        if action == 'quit':
                            return 'quit'
                        # resume continues otherwise

                    # Restart / Pause using configurable keys
                    if key in codes_for('single', 'restart'):
                        return "restart"
                    if key in codes_for('single', 'pause'):
                        paused = not paused

                    if not paused:
                        if key in codes_for('single', 'left'):
                            if not collides(board, cur, rot, px-1, py):
                                px -= 1
                        elif key in codes_for('single', 'right'):
                            if not collides(board, cur, rot, px+1, py):
                                px += 1
                        elif key in codes_for('single', 'soft'):
                            if not collides(board, cur, rot, px, py+1):
                                py += 1
                                score += 1
                        elif key in codes_for('single', 'rot_cw'):
                            rot, px = try_rotate(board, cur, rot, px, py, +1)
                        elif key in codes_for('single', 'rot_ccw'):
                            rot, px = try_rotate(board, cur, rot, px, py, -1)
                        elif key in codes_for('single', 'hard'):
                            # instant hard drop + lock
                            drop = 0
                            while not collides(board, cur, rot, px, py+1):
                                py += 1
                                drop += 1
                            score += 2 * drop
                            lock_and_resolve()
                            if collides(board, cur, rot, px, py):
                                result = game_over_screen(stdscr, score)
                                return result
                        elif key in codes_for('single', 'hold'):
                            if not hold_used:
                                if hold is None:
                                    hold = cur
                                    cur = nxt
                                    nxt = pop_piece()
                                else:
                                    cur, hold = hold, cur
                                rot = 0
                                px, py = 3, -1
                                hold_used = True

                # gravity
                if not paused and (now - last_fall) >= fall_delay(level):
                    last_fall = now
                    if not collides(board, cur, rot, px, py+1):
                        py += 1
                    else:
                        lock_and_resolve()
                        if collides(board, cur, rot, px, py):
                            result = game_over_screen(stdscr, score)
                            return result

                # draw (pass in_game_fireworks)
                draw(stdscr, board, cur, rot, px, py, nxt, hold, score, level, lines, paused,
                     flash_rows=None, flash_on=False, in_game_fireworks=in_game_fireworks)
        # --- Local multiplayer runner ---
        def add_garbage(board, n):
            for _ in range(n):
                hole = random.randint(0, W-1)
                # remove top row, append garbage row at bottom
                board.pop(0)
                row = ['G' for _ in range(W)]
                row[hole] = None
                board.append(row)

        def compute_attack(cleared, combo):
            if cleared == 0:
                return 0
            if cleared == 1:
                return 1 if combo >= 1 else 0
            if cleared == 2:
                return 1
            if cleared == 3:
                return 2
            if cleared == 4:
                return 4
            return 0

        def run_local_multiplayer(stars):
            # stars: dict {'p1':n,'p2':n} persists across rematches
            # initialize both players
            def make_player():
                b = empty_board()
                bag = new_bag()
                def pop_piece_local():
                    nonlocal bag
                    if not bag:
                        bag = new_bag()
                    return bag.pop()
                cur = pop_piece_local()
                nxt = pop_piece_local()
                return {
                    'board': b,
                    'bag': bag,
                    'pop': pop_piece_local,
                    'cur': cur,
                    'nxt': nxt,
                    'hold': None,
                    'hold_used': False,
                    'rot': 0,
                    'px': 3,
                    'py': -1,
                    'score': 0,
                    'lines': 0,
                    'level': 1,
                    'paused': False,
                    'last_fall': time.time(),
                    'last_ai_lr': 0.0,
                    'combo': 0,
                }

            p1 = make_player()
            p2 = make_player()

            # Initialize fireworks list before fade-in
            in_game_fireworks = []

            # Game start fade-in for local multiplayer: reveal the screen over 1.5 seconds
            try:
                fade_start_game = time.time()
                FADE_IN_GAME = 1.5
                while True:
                    f_elapsed = time.time() - fade_start_game
                    frac = max(0.0, min(1.0, f_elapsed / FADE_IN_GAME))
                    max_y, max_x = stdscr.getmaxyx()
                    draw_local_split(stdscr, p1, p2, in_game_fireworks, stars)
                    reveal_lines = int(frac * max_y)
                    try:
                        for yy in range(reveal_lines, max_y):
                            stdscr.move(yy, 0)
                            stdscr.clrtoeol()
                    except curses.error:
                        pass
                    stdscr.refresh()
                    if frac >= 1.0:
                        break
                    time.sleep(0.016)
            except Exception:
                pass

            fw_last_tick = time.time()
            fw_tick = 0.08

            def fall_delay(lvl):
                return max(0.08, 0.6 - (lvl-1)*0.05)

            def lock_and_resolve_for(player, opponent):
                # lock piece for player and resolve lines, send garbage to opponent
                board = player['board']
                lock_piece(board, player['cur'], player['rot'], player['px'], player['py'])
                full_rows = full_row_indices(board)
                if len(full_rows) == 4:
                    # flash for tetris
                    for i in range(6):
                        if player == p1:
                            draw_local_split(stdscr, p1, p2, in_game_fireworks, stars, 
                                           p1_flash_rows=full_rows, p1_flash_on=(i%2==0))
                        else:
                            draw_local_split(stdscr, p1, p2, in_game_fireworks, stars,
                                           p2_flash_rows=full_rows, p2_flash_on=(i%2==0))
                        stdscr.refresh()
                        time.sleep(0.08)
                
                board2, cleared = clear_lines(board)
                for i in range(H):
                    board[i] = board2[i]
                if cleared:
                    player['lines'] += cleared
                    player['score'] += {1:100,2:300,3:500,4:800}[cleared] * player['level']
                    player['level'] = 1 + (player['lines'] // 10)
                    # compute attack
                    attack = compute_attack(cleared, player['combo'])
                    if cleared > 0:
                        player['combo'] += 1
                    else:
                        player['combo'] = 0
                    if attack:
                        add_garbage(opponent['board'], attack)
                    # spawn fireworks proportional
                    spawn_count = 8 if cleared == 4 else cleared
                    for _ in range(spawn_count):
                        side = 'left' if player is p1 else 'right'
                        spawn_in_game_firework_center(in_game_fireworks, side=side)

                player['cur'] = player['nxt']
                player['nxt'] = player['pop']()
                player['rot'] = 0
                player['px'], player['py'] = 3, -1
                try:
                    if player is p2:
                        player['last_ai_lr'] = time.time()
                except Exception:
                    pass
                player['hold_used'] = False

            # helper to spawn fireworks centered
            def spawn_in_game_firework_center(fireworks_list, side=None):
                # spawn a firework roughly within one of the three screen regions
                max_y, max_x = stdscr.getmaxyx()
                gap = 4
                left_width = 2 * W
                center_width = ART_W
                right_width = 2 * W
                total_w = left_width + gap + center_width + gap + right_width
                ox = max(2, (max_x - total_w) // 2)
                oy = max(1, (max_y - max(H, ART_H)) // 2)
                left_x = ox
                center_x = left_x + left_width + gap
                right_x = center_x + center_width + gap

                # always use the center (castle) art area for multiplayer fireworks
                art_x = center_x
                art_w = center_width

                art_y = oy
                # keep fireworks roughly inside the chosen area with a margin
                max_spread = 4
                x_min = art_x + max_spread
                x_max = min(max_x-2, art_x + art_w -1 - max_spread)
                if x_max < x_min:
                    x = art_x + art_w // 2
                else:
                    x = random.randint(x_min, x_max)
                y_bottom = min(max_y - 3, art_y + ART_H - 1)
                target_y = max(art_y + 1, art_y + random.randint(1,2))
                fireworks_list.append({
                    "x": x, "y": y_bottom, "phase": "rise", "target_y": target_y,
                    "age": 0, "parts": [], "tail": [], "tail_max": random.randint(1,3),
                    "art_left": art_x, "art_right": art_x + art_w - 1,
                })

            def check_game_over(player):
                # if spawn collides
                return collides(player['board'], player['cur'], player['rot'], player['px'], player['py'])

            # main multiplayer loop
            while True:
                now = time.time()
                # fireworks tick
                if now - fw_last_tick >= fw_tick:
                    fw_last_tick = now
                    updated = []
                    for fw in in_game_fireworks:
                        fw['age'] += 1
                        if fw['phase'] == 'rise':
                            fw['tail'].append((fw['x'], fw['y']))
                            if len(fw['tail']) > fw['tail_max']:
                                fw['tail'] = fw['tail'][-fw['tail_max']:]
                            fw['y'] -= 1
                            if fw['y'] <= fw['target_y'] or fw['age'] >= 60:
                                parts = []
                                count = random.randint(10, 16)
                                for _ in range(count):
                                    # use same spread as single-player but constrained to this art area
                                    dx = random.randint(-6, 6)
                                    dy = random.randint(-3, 3)
                                    life = random.randint(10, 16)
                                    color = random.choice([26,27,28,29]) if (curses.has_colors() and SETTINGS.get('colored_art', True)) else 0
                                    fx = fw['x'] + dx
                                    fy = fw['y'] + dy
                                    vx = dx * 0.09
                                    vy = dy * 0.06
                                    parts.append({
                                        "x": int(round(fx)),
                                        "y": int(round(fy)),
                                        "fx": fx,
                                        "fy": fy,
                                        "vx": vx,
                                        "vy": vy,
                                        "age": 0,
                                        "life": life,
                                        "color": color,
                                    })
                                fw['phase'] = 'explode'
                                fw['parts'] = parts
                        elif fw['phase'] == 'explode':
                            alive = []
                            # use per-firework stored art bounds so left/right spawns remain in their area
                            try:
                                max_y2, max_x2 = stdscr.getmaxyx()
                            except Exception:
                                max_x2 = 1000
                            art_left = fw.get('art_left', 0)
                            art_right = fw.get('art_right', max_x2 - 1)
                            for p in fw['parts']:
                                p['age'] += 1
                                if p['age'] <= p['life']:
                                    # update float positions using stored velocities
                                    p['fx'] = p.get('fx', p.get('x', 0)) + p.get('vx', 0)
                                    grav = 0.06 if p['age'] > p['life']//2 else 0.0
                                    p['fy'] = p.get('fy', p.get('y', 0)) + p.get('vy', 0) + grav
                                    p['x'] = int(round(p['fx']))
                                    p['y'] = int(round(p['fy']))
                                    # clamp into art bounds so particles remain visible
                                    if p['x'] < art_left:
                                        p['x'] = art_left
                                    if p['x'] > art_right:
                                        p['x'] = art_right
                                    alive.append(p)
                            fw['parts'] = alive
                            if not fw['parts']:
                                fw['phase'] = 'done'
                        if fw['phase'] != 'done':
                            updated.append(fw)
                    in_game_fireworks[:] = updated

                # input
                key = stdscr.getch()
                if key != -1:
                    if key in (ord('q'), ord('Q')):
                        # ignore quit key in multiplayer; use pause menu's Quit option
                        pass
                    if key == 27:
                        action = pause_menu(stdscr)
                        if action == 'menu':
                            return 'menu'
                        if action == 'restart':
                            return 'restart'
                        if action == 'quit':
                            return 'quit'
                        # resume continues
                    if key in (ord('r'), ord('R')):
                        return 'restart'
                    # P1 controls (configurable)
                    if key in codes_for('local_p1', 'pause') or key in codes_for('local_p2', 'pause'):
                        p1['paused'] = not p1['paused']
                        p2['paused'] = not p2['paused']
                    if not p1['paused']:
                        if key in codes_for('local_p1', 'left'):
                            if not collides(p1['board'], p1['cur'], p1['rot'], p1['px']-1, p1['py']):
                                p1['px'] -= 1
                        elif key in codes_for('local_p1', 'right'):
                            if not collides(p1['board'], p1['cur'], p1['rot'], p1['px']+1, p1['py']):
                                p1['px'] += 1
                        elif key in codes_for('local_p1', 'soft'):
                            if not collides(p1['board'], p1['cur'], p1['rot'], p1['px'], p1['py']+1):
                                p1['py'] += 1
                                p1['score'] += 1
                        elif key in codes_for('local_p1', 'rot_cw'):
                            p1['rot'], p1['px'] = try_rotate(p1['board'], p1['cur'], p1['rot'], p1['px'], p1['py'], +1)
                        elif key in codes_for('local_p1', 'rot_ccw'):
                            p1['rot'], p1['px'] = try_rotate(p1['board'], p1['cur'], p1['rot'], p1['px'], p1['py'], -1)
                        elif key in codes_for('local_p1', 'hard'):
                            drop = 0
                            while not collides(p1['board'], p1['cur'], p1['rot'], p1['px'], p1['py']+1):
                                p1['py'] += 1
                                drop += 1
                            p1['score'] += 2 * drop
                            lock_and_resolve_for(p1, p2)
                            if check_game_over(p1):
                                winner = 'p2'
                                return ('win', winner, p1, p2)
                        elif key in codes_for('local_p1', 'hold'):
                            if not p1['hold_used']:
                                if p1['hold'] is None:
                                    p1['hold'] = p1['cur']
                                    p1['cur'] = p1['nxt']
                                    p1['nxt'] = p1['pop']()
                                else:
                                    p1['cur'], p1['hold'] = p1['hold'], p1['cur']
                                p1['rot'] = 0
                                p1['px'], p1['py'] = 3, -1
                                p1['hold_used'] = True
                    # P2 controls (configurable)
                    if not p2['paused']:
                        if key in codes_for('local_p2', 'left'):
                            if not collides(p2['board'], p2['cur'], p2['rot'], p2['px']-1, p2['py']):
                                p2['px'] -= 1
                        elif key in codes_for('local_p2', 'right'):
                            if not collides(p2['board'], p2['cur'], p2['rot'], p2['px']+1, p2['py']):
                                p2['px'] += 1
                        elif key in codes_for('local_p2', 'soft'):
                            if not collides(p2['board'], p2['cur'], p2['rot'], p2['px'], p2['py']+1):
                                p2['py'] += 1
                                p2['score'] += 1
                        elif key in codes_for('local_p2', 'rot_cw'):
                            p2['rot'], p2['px'] = try_rotate(p2['board'], p2['cur'], p2['rot'], p2['px'], p2['py'], +1)
                        elif key in codes_for('local_p2', 'rot_ccw'):
                            p2['rot'], p2['px'] = try_rotate(p2['board'], p2['cur'], p2['rot'], p2['px'], p2['py'], -1)
                        elif key in codes_for('local_p2', 'hard'):
                            drop = 0
                            while not collides(p2['board'], p2['cur'], p2['rot'], p2['px'], p2['py']+1):
                                p2['py'] += 1
                                drop += 1
                            p2['score'] += 2 * drop
                            lock_and_resolve_for(p2, p1)
                            if check_game_over(p2):
                                winner = 'p1'
                                return ('win', winner, p1, p2)
                        elif key in codes_for('local_p2', 'hold'):
                            if not p2['hold_used']:
                                if p2['hold'] is None:
                                    p2['hold'] = p2['cur']
                                    p2['cur'] = p2['nxt']
                                    p2['nxt'] = p2['pop']()
                                else:
                                    p2['cur'], p2['hold'] = p2['hold'], p2['cur']
                                p2['rot'] = 0
                                p2['px'], p2['py'] = 3, -1
                                p2['hold_used'] = True

                # gravity for each player
                for player, opponent in ((p1,p2),(p2,p1)):
                    if player['paused']:
                        continue
                    if (now - player['last_fall']) >= fall_delay(player['level']):
                        player['last_fall'] = now
                        if not collides(player['board'], player['cur'], player['rot'], player['px'], player['py']+1):
                            player['py'] += 1
                        else:
                            lock_and_resolve_for(player, opponent)
                            if check_game_over(player):
                                # other player wins
                                winner = 'p1' if player is p2 else 'p2'
                                return ('win', winner, p1, p2)

                # draw both boards and center art
                draw_local_split(stdscr, p1, p2, in_game_fireworks, stars)

        # runner selection
        def run_vs_com(stars, difficulty):
            """Run a local-style match where P2 is a computer opponent.
            Difficulty: 'NORMAL','HARD','RASPUTIN'
            """
            # helper player maker (same as local)
            def make_player():
                b = empty_board()
                bag = new_bag()
                def pop_piece_local():
                    nonlocal bag
                    if not bag:
                        bag = new_bag()
                    return bag.pop()
                cur = pop_piece_local()
                nxt = pop_piece_local()
                return {
                    'board': b,
                    'bag': bag,
                    'pop': pop_piece_local,
                    'cur': cur,
                    'nxt': nxt,
                    'hold': None,
                    'hold_used': False,
                    'rot': 0,
                    'px': 3,
                    'py': -1,
                    'score': 0,
                    'lines': 0,
                    'level': 1,
                    'paused': False,
                    'last_fall': time.time(),
                    'last_ai_lr': 0.0,
                    'combo': 0,
                }

            p1 = make_player()
            p2 = make_player()

            # display-friendly control hints: use single-player controls for P1
            p1_ctrl_lines = ["Controls:",
                             f"Left: {controls_display_names('single','left')}",
                             f"Right: {controls_display_names('single','right')}",
                             f"Down: {controls_display_names('single','soft')}",
                             f"Rot: {controls_display_names('single','rot_cw')}",
                             f"Hard: {controls_display_names('single','hard')}",
                             f"Hold: {controls_display_names('single','hold')}"]
            p2_ctrl_lines = ["Computer"]

            # Initialize fireworks list before fade-in
            in_game_fireworks = []

            # Game start fade-in similar to local
            try:
                fade_start_game = time.time()
                FADE_IN_GAME = 1.5
                while True:
                    f_elapsed = time.time() - fade_start_game
                    frac = max(0.0, min(1.0, f_elapsed / FADE_IN_GAME))
                    max_y, max_x = stdscr.getmaxyx()
                    draw_local_split(stdscr, p1, p2, in_game_fireworks, stars, p1_ctrl_lines=p1_ctrl_lines, p2_ctrl_lines=p2_ctrl_lines)
                    reveal_lines = int(frac * max_y)
                    try:
                        for yy in range(reveal_lines, max_y):
                            stdscr.move(yy, 0)
                            stdscr.clrtoeol()
                    except curses.error:
                        pass
                    stdscr.refresh()
                    if frac >= 1.0:
                        break
                    time.sleep(0.016)
            except Exception:
                pass

            fw_last_tick = time.time()
            fw_tick = 0.08

            def fall_delay(lvl):
                return max(0.08, 0.6 - (lvl-1)*0.05)

            def spawn_in_game_firework_center(fireworks_list, side=None):
                max_y, max_x = stdscr.getmaxyx()
                gap = 4
                left_width = 2 * W
                center_width = ART_W
                right_width = 2 * W
                total_w = left_width + gap + center_width + gap + right_width
                ox = max(2, (max_x - total_w) // 2)
                oy = max(1, (max_y - max(H, ART_H)) // 2)
                left_x = ox
                center_x = left_x + left_width + gap
                right_x = center_x + center_width + gap

                # always use the center (castle) art area for multiplayer fireworks
                art_x = center_x
                art_w = center_width

                art_y = oy
                max_spread = 4
                x_min = art_x + max_spread
                x_max = min(max_x-2, art_x + art_w -1 - max_spread)
                if x_max < x_min:
                    x = art_x + art_w // 2
                else:
                    x = random.randint(x_min, x_max)
                y_bottom = min(max_y - 3, art_y + ART_H - 1)
                target_y = max(art_y + 1, art_y + random.randint(1,2))
                fireworks_list.append({
                    "x": x, "y": y_bottom, "phase": "rise", "target_y": target_y,
                    "age": 0, "parts": [], "tail": [], "tail_max": random.randint(1,3),
                    "art_left": art_x, "art_right": art_x + art_w - 1,
                })

            def lock_and_resolve_for(player, opponent):
                board = player['board']
                lock_piece(board, player['cur'], player['rot'], player['px'], player['py'])
                full_rows = full_row_indices(board)
                if len(full_rows) == 4:
                    # flash for tetris
                    for i in range(6):
                        if player == p1:
                            draw_local_split(stdscr, p1, p2, in_game_fireworks, stars, 
                                           p1_flash_rows=full_rows, p1_flash_on=(i%2==0))
                        else:
                            draw_local_split(stdscr, p1, p2, in_game_fireworks, stars,
                                           p2_flash_rows=full_rows, p2_flash_on=(i%2==0))
                        stdscr.refresh()
                        time.sleep(0.08)
                
                board2, cleared = clear_lines(board)
                for i in range(H):
                    board[i] = board2[i]
                if cleared:
                    player['lines'] += cleared
                    player['score'] += {1:100,2:300,3:500,4:800}[cleared] * player['level']
                    player['level'] = 1 + (player['lines'] // 10)
                    attack = compute_attack(cleared, player.get('combo',0))
                    if cleared > 0:
                        player['combo'] = player.get('combo',0) + 1
                    else:
                        player['combo'] = 0
                    if attack:
                        add_garbage(opponent['board'], attack)
                    spawn_count = 8 if cleared == 4 else cleared
                    for _ in range(spawn_count):
                        side = 'left' if player is p1 else 'right'
                        spawn_in_game_firework_center(in_game_fireworks, side=side)
                player['cur'] = player['nxt']
                player['nxt'] = player['pop']()
                player['rot'] = 0
                player['px'], player['py'] = 3, -1
                try:
                    if player is p2:
                        player['last_ai_lr'] = time.time()
                except Exception:
                    pass
                player['hold_used'] = False

            def check_game_over(player):
                return collides(player['board'], player['cur'], player['rot'], player['px'], player['py'])

            # AI helpers: simulation & heuristic
            def board_clone(board):
                return [row[:] for row in board]

            def simulate_lock(board, piece, rot, px, py):
                # returns new_board, cleared
                b = board_clone(board)
                # drop to landing
                gpy = py
                while not collides(b, piece, rot, px, gpy+1):
                    gpy += 1
                for x,y in cells_of(piece, rot, px, gpy):
                    if 0 <= y < H and 0 <= x < W:
                        b[y][x] = piece
                b2, cleared = clear_lines(b)
                return b2, cleared

            def aggregate_height(b):
                heights = [0]*W
                for x in range(W):
                    for y in range(H):
                        if b[y][x] is not None:
                            heights[x] = H - y
                            break
                return sum(heights), heights

            def count_holes(b, heights):
                holes = 0
                for x in range(W):
                    col_has_block = False
                    for y in range(H):
                        if b[y][x] is not None:
                            col_has_block = True
                        elif col_has_block:
                            holes += 1
                return holes

            def bumpiness(heights):
                s = 0
                for i in range(len(heights)-1):
                    s += abs(heights[i]-heights[i+1])
                return s

            def evaluate_board(b, cleared):
                agg, heights = aggregate_height(b)
                holes = count_holes(b, heights)
                bump = bumpiness(heights)
                score = 1.5*cleared - 0.45*agg - 1.2*holes - 0.35*bump
                return score

            def ai_best_placement(player, lookahead=True):
                board = player['board']
                piece = player['cur']
                nxt = player['nxt']
                best = (-9e9, 0, 0)  # score, rot, px
                for rot_try in range(4):
                    for px_try in range(-2, W+2):
                        if collides(board, piece, rot_try, px_try, player['py']):
                            continue
                        sb, c = simulate_lock(board, piece, rot_try, px_try, player['py'])
                        val = evaluate_board(sb, c)
                        if lookahead and difficulty in ('HARD','RASPUTIN','NORMAL'):
                            best_next = -9e9
                            for r2 in range(4):
                                for px2 in range(-2, W+2):
                                    if collides(sb, nxt, r2, px2, -1):
                                        continue
                                    sb2, c2 = simulate_lock(sb, nxt, r2, px2, -1)
                                    v2 = evaluate_board(sb2, c2)
                                    if v2 > best_next:
                                        best_next = v2
                            if difficulty == 'RASPUTIN':
                                weight = 0.85
                            elif difficulty == 'HARD':
                                weight = 0.5
                            else:
                                weight = 0.15
                            val += weight * best_next
                        if val > best[0]:
                            best = (val, rot_try, px_try)
                return best[1], best[2]
            # Final values:
            #  - NORMAL: slightly slower than before (less difficult)
            #  - HARD: adopt previous NORMAL responsiveness
            #  - RASPUTIN: remain fastest but not instant
            # Make NORMAL a bit easier by increasing its decision delay (slower).
            ai_last = time.time()
            ai_delay = 0.28 if difficulty == 'NORMAL' else 0.12 if difficulty == 'HARD' else 0.04
            # lateral move delay (seconds per horizontal unit) - faster on harder difficulties
            ai_lr_delay = 0.5 if difficulty == 'NORMAL' else 0.28 if difficulty == 'HARD' else 0.12

            # main loop
            target_rot = None
            target_px = None
            while True:
                now = time.time()
                # fireworks tick
                if now - fw_last_tick >= fw_tick:
                    fw_last_tick = now
                    updated = []
                    for fw in in_game_fireworks:
                        fw['age'] += 1
                        if fw['phase'] == 'rise':
                            fw['tail'].append((fw['x'], fw['y']))
                            if len(fw['tail']) > fw['tail_max']:
                                fw['tail'] = fw['tail'][-fw['tail_max']:]
                            fw['y'] -= 1
                            if fw['y'] <= fw['target_y'] or fw['age'] >= 60:
                                parts = []
                                count = random.randint(10, 16)
                                for _ in range(count):
                                    dx = random.randint(-6, 6)
                                    dy = random.randint(-3, 3)
                                    life = random.randint(12, 18)
                                    color = random.choice([26,27,28,29]) if (curses.has_colors() and SETTINGS.get('colored_art', True)) else 0
                                    # determine art bounds; prefer per-firework stored bounds
                                    try:
                                        max_y2, max_x2 = stdscr.getmaxyx()
                                    except Exception:
                                        max_x2 = 1000
                                    # fallback center art bounds (kept for compatibility)
                                    PANEL_W2 = 22
                                    ART_PAD2 = 3
                                    GAME_WIDTH2 = (2 * W) + 6 + PANEL_W2 + ART_PAD2 + ART_W
                                    ox2 = max(2, (max_x2 - GAME_WIDTH2) // 2)
                                    oy2 = max(1, (max_y2 - max(H, 25, ART_H+2)) // 2) if 'max_y2' in locals() else 0
                                    panel_x2 = ox2 + 2*W + 6
                                    art_x2 = panel_x2 + 22 + 1 + 2
                                    default_left = art_x2
                                    default_right = art_x2 + ART_W - 1
                                    art_left = fw.get('art_left', default_left)
                                    art_right = fw.get('art_right', default_right)
                                    pxp = fw['x'] + dx
                                    if pxp < art_left:
                                        pxp = art_left
                                    if pxp > art_right:
                                        pxp = art_right
                                    fx = pxp
                                    fy = fw['y'] + dy
                                    vx = dx * 0.09
                                    vy = dy * 0.06
                                    parts.append({
                                        "x": int(round(fx)),
                                        "y": int(round(fy)),
                                        "fx": fx,
                                        "fy": fy,
                                        "vx": vx,
                                        "vy": vy,
                                        "age": 0,
                                        "life": life,
                                        "color": color,
                                    })
                                fw['phase'] = 'explode'
                                fw['parts'] = parts
                        elif fw['phase'] == 'explode':
                            alive = []
                            # use per-firework stored art bounds so left/right spawns remain in their area
                            try:
                                max_y2, max_x2 = stdscr.getmaxyx()
                            except Exception:
                                max_x2 = 1000
                            art_left = fw.get('art_left', 0)
                            art_right = fw.get('art_right', max_x2 - 1)
                            for p in fw['parts']:
                                p['age'] += 1
                                if p['age'] <= p['life']:
                                    # update float positions using stored velocities
                                    p['fx'] = p.get('fx', p.get('x', 0)) + p.get('vx', 0)
                                    grav = 0.06 if p['age'] > p['life']//2 else 0.0
                                    p['fy'] = p.get('fy', p.get('y', 0)) + p.get('vy', 0) + grav
                                    p['x'] = int(round(p['fx']))
                                    p['y'] = int(round(p['fy']))
                                    # clamp into art bounds so particles remain visible
                                    if p['x'] < art_left:
                                        p['x'] = art_left
                                    if p['x'] > art_right:
                                        p['x'] = art_right
                                    alive.append(p)
                            fw['parts'] = alive
                            if not fw['parts']:
                                fw['phase'] = 'done'
                        if fw['phase'] != 'done':
                            updated.append(fw)
                    in_game_fireworks[:] = updated

                # input for P1 (human)
                key = stdscr.getch()
                if key != -1:
                    if key == 27:
                        action = pause_menu(stdscr)
                        if action == 'menu':
                            return 'menu'
                        if action == 'restart':
                            return 'restart'
                        if action == 'quit':
                            return 'quit'
                    if key in (ord('r'), ord('R')):
                        return 'restart'
                    if key in codes_for('single', 'pause'):
                        p1['paused'] = not p1['paused']
                        p2['paused'] = not p2['paused']
                    if not p1['paused']:
                        if key in codes_for('single', 'left'):
                            if not collides(p1['board'], p1['cur'], p1['rot'], p1['px']-1, p1['py']):
                                p1['px'] -= 1
                        elif key in codes_for('single', 'right'):
                            if not collides(p1['board'], p1['cur'], p1['rot'], p1['px']+1, p1['py']):
                                p1['px'] += 1
                        elif key in codes_for('single', 'soft'):
                            if not collides(p1['board'], p1['cur'], p1['rot'], p1['px'], p1['py']+1):
                                p1['py'] += 1
                                p1['score'] += 1
                        elif key in codes_for('single', 'rot_cw'):
                            p1['rot'], p1['px'] = try_rotate(p1['board'], p1['cur'], p1['rot'], p1['px'], p1['py'], +1)
                        elif key in codes_for('single', 'rot_ccw'):
                            p1['rot'], p1['px'] = try_rotate(p1['board'], p1['cur'], p1['rot'], p1['px'], p1['py'], -1)
                        elif key in codes_for('single', 'hard'):
                            drop = 0
                            while not collides(p1['board'], p1['cur'], p1['rot'], p1['px'], p1['py']+1):
                                p1['py'] += 1
                                drop += 1
                            p1['score'] += 2 * drop
                            lock_and_resolve_for(p1, p2)
                            if check_game_over(p1):
                                winner = 'p2'
                                return ('win', winner, p1, p2)
                        elif key in codes_for('single', 'hold'):
                            if not p1['hold_used']:
                                if p1['hold'] is None:
                                    p1['hold'] = p1['cur']
                                    p1['cur'] = p1['nxt']
                                    p1['nxt'] = p1['pop']()
                                else:
                                    p1['cur'], p1['hold'] = p1['hold'], p1['cur']
                                p1['rot'] = 0
                                p1['px'], p1['py'] = 3, -1
                                p1['hold_used'] = True

                # AI decision tick
                if not p2['paused'] and (now - ai_last) >= ai_delay:
                    ai_last = now
                    # recompute target (rotation applied immediately; lateral moves are rate-limited)
                    r, x = ai_best_placement(p2, lookahead=True)
                    target_rot = r
                    target_px = x
                    # Probabilistic hard-drop by difficulty.
                    # HARD now uses the former NORMAL aggressiveness; NORMAL is softened.
                    # Only consider hard-drop when AI is aligned (px and rot) and has had time to move
                    ai_ready_for_drop = False
                    try:
                        ai_ready_for_drop = (
                            p2['px'] == target_px and p2.get('rot') == target_rot
                            and (now - p2.get('last_ai_lr', 0.0)) >= ai_lr_delay
                        )
                    except Exception:
                        ai_ready_for_drop = False

                    if ai_ready_for_drop and ((difficulty == 'RASPUTIN' and random.random() < 0.85)
                        or (difficulty == 'HARD' and random.random() < 0.45)
                        or (difficulty == 'NORMAL' and random.random() < 0.18)):
                        drop = 0
                        while not collides(p2['board'], p2['cur'], p2['rot'], p2['px'], p2['py']+1):
                            p2['py'] += 1
                            drop += 1
                        p2['score'] += 2 * drop
                        lock_and_resolve_for(p2, p1)
                        if check_game_over(p2):
                            winner = 'p1'
                            return ('win', winner, p1, p2)

                # gravity for P1
                if not p1['paused'] and (now - p1['last_fall']) >= fall_delay(p1['level']):
                    p1['last_fall'] = now
                    if not collides(p1['board'], p1['cur'], p1['rot'], p1['px'], p1['py']+1):
                        p1['py'] += 1
                    else:
                        lock_and_resolve_for(p1, p2)
                        if check_game_over(p1):
                            winner = 'p2'
                            return ('win', winner, p1, p2)

                    # AI lateral movement: step toward `target_px` at most once per 0.5s
                    if target_px is not None and not p2['paused']:
                        try:
                            last_lr = p2.get('last_ai_lr', 0.0)
                            if p2['px'] != target_px and (now - last_lr) >= ai_lr_delay:
                                # move one cell toward the target if not colliding
                                step = 1 if target_px > p2['px'] else -1
                                if not collides(p2['board'], p2['cur'], p2['rot'], p2['px'] + step, p2['py']):
                                    p2['px'] += step
                                    p2['last_ai_lr'] = now
                        except Exception:
                            pass

                    # AI rotation: attempt one rotation step toward target_rot when safe
                    if target_rot is not None and not p2['paused'] and p2['rot'] != target_rot:
                        try:
                            # choose a single rotation direction that moves toward target_rot
                            diff = (target_rot - p2['rot']) % 4
                            if diff == 3:
                                direction = -1
                            else:
                                direction = 1
                            new_rot, new_px = try_rotate(p2['board'], p2['cur'], p2['rot'], p2['px'], p2['py'], direction)
                            if new_rot != p2['rot']:
                                p2['rot'] = new_rot
                                p2['px'] = new_px
                        except Exception:
                            pass

                    # gravity for P2 (if AI hasn't hard-dropped yet)
                if not p2['paused'] and (now - p2['last_fall']) >= fall_delay(p2['level']):
                    p2['last_fall'] = now
                    if not collides(p2['board'], p2['cur'], p2['rot'], p2['px'], p2['py']+1):
                        p2['py'] += 1
                    else:
                        lock_and_resolve_for(p2, p1)
                        if check_game_over(p2):
                            winner = 'p1'
                            return ('win', winner, p1, p2)

                # draw both boards and center art with overridden controls
                draw_local_split(stdscr, p1, p2, in_game_fireworks, stars, p1_ctrl_lines=p1_ctrl_lines, p2_ctrl_lines=p2_ctrl_lines)

        
        if choice == 'single':
            # loop to support restart without returning to menu
            while True:
                stdscr.nodelay(True)
                result = run_one_game()
                if result == "restart":
                    continue
                if result == "menu":
                    break
                if result == "quit":
                    return
        elif choice == 'vscom':
            # VS COM: ask difficulty then run AI match
            stars = {'p1': 0, 'p2': 0}
            diff = difficulty_menu(stdscr)
            if diff is None:
                # user cancelled difficulty -> return to menu
                continue
            while True:
                stdscr.nodelay(True)
                result = run_vs_com(stars, diff)
                if result == 'restart':
                    continue
                if result == 'menu':
                    break
                if result == 'quit':
                    return
                if isinstance(result, tuple) and result[0] == 'win':
                    if len(result) >= 4:
                        _, winner, p1_final, p2_final = result
                    else:
                        _, winner = result
                        p1_final = None
                        p2_final = None
                    if winner == 'p1':
                        stars['p1'] += 1
                    else:
                        stars['p2'] += 1
                    # log automated match result (if running in AUTO_VS mode)
                    try:
                        if AUTO_VS:
                            with open('/tmp/ai_match.log','a') as _lf:
                                _lf.write(f"MATCH {AUTO_VS_COUNT+1}: winner={winner} stars_p1={stars['p1']} stars_p2={stars['p2']}\n")
                    except Exception:
                        pass
                    try:
                        if p1_final is not None and p2_final is not None:
                            draw_local_split(stdscr, p1_final, p2_final, [], stars)
                        else:
                            draw_local_split(stdscr, {'board': empty_board(), 'cur': None, 'rot':0,'px':3,'py':-1,'nxt':None,'hold':None,'score':0},
                                             {'board': empty_board(), 'cur': None, 'rot':0,'px':3,'py':-1,'nxt':None,'hold':None,'score':0}, [], stars)
                    except Exception:
                        pass
                    # Compute layout for VS COM game over screen
                    max_y, max_x = stdscr.getmaxyx()
                    gap = 4
                    left_width = 2 * W
                    center_width = ART_W
                    right_width = 2 * W
                    total_w = left_width + gap + center_width + gap + right_width
                    ox = max(2, (max_x - total_w) // 2)
                    oy = max(1, (max_y - max(H, ART_H)) // 2)
                    left_x = ox
                    center_x = left_x + left_width + gap
                    right_x = center_x + center_width + gap
                    # Draw the MENU_ART into the center art area in white
                    try:
                        for i, line in enumerate(MENU_ART):
                            y = oy + i
                            if 0 <= y < max_y:
                                for j, char in enumerate(line):
                                    if center_x + j < max_x:
                                        stdscr.addch(y, center_x + j, char, curses.color_pair(7))
                        stdscr.refresh()
                    except Exception:
                        pass

                    # fade out art and prompt similarly to local
                    try:
                        FADE_OUT_ART_DUR = 0.6
                        per_line = FADE_OUT_ART_DUR / max(1, ART_H)
                        for i in range(ART_H):
                            y = oy + i
                            if 0 <= y < max_y:
                                try:
                                    for cx in range(center_x, center_x + center_width):
                                        stdscr.addch(y, cx, ' ')
                                except curses.error:
                                    pass
                                stdscr.refresh()
                                time.sleep(per_line)
                    except Exception:
                        pass
                    prompt = "Play Again? Y/N"
                    try:
                        prompt_y = oy + (ART_H // 2)
                        prompt_x = center_x + max(0, (center_width - len(prompt)) // 2)
                        stdscr.addstr(prompt_y, prompt_x, prompt, curses.A_BOLD | curses.A_REVERSE)
                        s1 = ('*'*min(stars['p1'], 5)) + (f" x {stars['p1']}" if stars['p1']>5 else '')
                        s2 = ('*'*min(stars['p2'], 5)) + (f" x {stars['p2']}" if stars['p2']>5 else '')
                        info = f"{winner.upper()} WINS!   P1: {s1}   P2: {s2}"
                        info_y = prompt_y + 2
                        info_x = max(0, center_x + max(0, (center_width - len(info)) // 2))
                        stdscr.addstr(info_y, info_x, info)
                        stdscr.refresh()
                    except curses.error:
                        pass
                    # if automated VS COM testing is enabled, auto-advance without waiting for input
                    if AUTO_VS:
                        try:
                            AUTO_VS_COUNT += 1
                            stdscr.nodelay(True)
                            if AUTO_VS_COUNT >= AUTO_VS_RUNS:
                                return
                            else:
                                # start next match immediately
                                continue
                        except Exception:
                            pass
                    else:
                        # Wait for Y/N choice without erasing the rest of the screen
                        stdscr.nodelay(False)
                        stdscr.keypad(True)
                        curses.curs_set(0)
                        goto_menu = False
                        while True:
                            k = stdscr.getch()
                            if k in (ord('y'), ord('Y')):
                                stdscr.nodelay(True)
                                break
                            if k in (ord('n'), ord('N')):
                                stdscr.nodelay(True)
                                goto_menu = True
                                break
                        if goto_menu:
                            break
        else:
            # local multiplayer
            stars = {'p1': 0, 'p2': 0}
            while True:
                stdscr.nodelay(True)
                result = run_local_multiplayer(stars)
                if result == 'restart':
                    continue
                if result == 'menu':
                    break
                if result == 'quit':
                    return
                if isinstance(result, tuple) and result[0] == 'win':
                    # unpack possible returned player states (some callers return p1,p2)
                    if len(result) >= 4:
                        _, winner, p1_final, p2_final = result
                    else:
                        _, winner = result
                        p1_final = None
                        p2_final = None
                    # update stars
                    if winner == 'p1':
                        stars['p1'] += 1
                    else:
                        stars['p2'] += 1

                    # Keep the final game screen visible (draw boards and art)
                    try:
                        if p1_final is not None and p2_final is not None:
                            draw_local_split(stdscr, p1_final, p2_final, [], stars)
                        else:
                            # fallback: redraw using current stars only
                            draw_local_split(stdscr, {'board': empty_board(), 'cur': None, 'rot':0,'px':3,'py':-1,'nxt':None,'hold':None,'score':0},
                                             {'board': empty_board(), 'cur': None, 'rot':0,'px':3,'py':-1,'nxt':None,'hold':None,'score':0}, [], stars)
                    except Exception:
                        pass

                    # Compute center art position (same math as draw_local_split)
                    max_y, max_x = stdscr.getmaxyx()
                    gap = 4
                    left_width = 2 * W
                    center_width = ART_W
                    total_w = left_width + gap + center_width + gap + 2 * W
                    ox = max(2, (max_x - total_w) // 2)
                    oy = max(1, (max_y - max(H, ART_H)) // 2)
                    center_x = ox + left_width + gap

                    # Draw the MENU_ART into the center art area in white
                    try:
                        for i, line in enumerate(MENU_ART):
                            y = oy + i
                            if 0 <= y < max_y:
                                for j, char in enumerate(line):
                                    if center_x + j < max_x:
                                        stdscr.addch(y, center_x + j, char, curses.color_pair(7))
                        stdscr.refresh()
                    except Exception:
                        pass

                    # Fade out ASCII art top-to-bottom, replacing art lines with blanks
                    try:
                        FADE_OUT_ART_DUR = 0.6
                        per_line = FADE_OUT_ART_DUR / max(1, ART_H)
                        for i in range(ART_H):
                            y = oy + i
                            if 0 <= y < max_y:
                                try:
                                    for cx in range(center_x, center_x + ART_W):
                                        stdscr.addch(y, cx, ' ')
                                except curses.error:
                                    pass
                                stdscr.refresh()
                                time.sleep(per_line)
                    except Exception:
                        pass

                    # Place the Play Again prompt where the art was
                    prompt = "Play Again? Y/N"
                    try:
                        prompt_y = oy + (ART_H // 2)
                        prompt_x = center_x + max(0, (ART_W - len(prompt)) // 2)
                        stdscr.addstr(prompt_y, prompt_x, prompt, curses.A_BOLD | curses.A_REVERSE)
                        # Also show winner and star counts just below
                        s1 = ('*'*min(stars['p1'], 5)) + (f" x {stars['p1']}" if stars['p1']>5 else '')
                        s2 = ('*'*min(stars['p2'], 5)) + (f" x {stars['p2']}" if stars['p2']>5 else '')
                        info = f"{winner.upper()} WINS!   P1: {s1}   P2: {s2}"
                        info_y = prompt_y + 2
                        info_x = max(0, center_x + max(0, (ART_W - len(info)) // 2))
                        stdscr.addstr(info_y, info_x, info)
                        stdscr.refresh()
                    except curses.error:
                        pass

                    # Wait for Y/N choice without erasing the rest of the screen
                    stdscr.nodelay(False)
                    stdscr.keypad(True)
                    curses.curs_set(0)
                    goto_menu = False
                    while True:
                        k = stdscr.getch()
                        if k in (ord('y'), ord('Y')):
                            stdscr.nodelay(True)
                            break
                        if k in (ord('n'), ord('N')):
                            stdscr.nodelay(True)
                            goto_menu = True
                            break
                    # if user chose N, break out to main menu loop
                    if goto_menu:
                        break

def main():
    curses.wrapper(tetris)

if __name__ == "__main__":
    main()
