import os
import re
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AVATAR_PATH_TXT = os.path.join(SCRIPT_DIR, "avatar_path.txt")
SOURCE_HTML = r"c:\Users\jayap\Downloads\avatar_rubik_morph.html"
OUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "assets"))
os.makedirs(OUT_DIR, exist_ok=True)

# Banner layout (1180 x 610)
W_BANNER, H_BANNER = 1180, 610

# Visual Map tile placement inside 1180x610 banner
# Left panel box: x=28, y=82, width=424, height=500 -> center (240, 332)
# 400x400 tile fits nicely centered at x=40, y=132
TILE_X, TILE_Y = 40, 132
SIZE = 400
CX = CY = SIZE / 2
AVATAR_R = 188

# Exact timing constants from avatar_rubik_morph.html
TIMING_HOLD = 2.0
TIMING_MORPH_IN = 1.6
TIMING_MORPH_OUT = 1.6
TIMING_BEAT = 0.0
RUBIK_AT = 0.6

RUBIK_MOVES = 14
RUBIK_SLOT = 0.42
RUBIK_REST = 1.2

CYC = 2 * RUBIK_MOVES * RUBIK_SLOT + RUBIK_REST
SOLVED = (2 * RUBIK_MOVES - 1) * RUBIK_SLOT + 0.7 * RUBIK_SLOT
T_IN = TIMING_HOLD
T_RUN = T_IN + TIMING_MORPH_IN * RUBIK_AT
T_OUT = max(T_RUN + SOLVED + TIMING_BEAT, T_IN + TIMING_MORPH_IN)
LOOP = T_OUT + TIMING_MORPH_OUT


def sm(x):
    return 0.0 if x <= 0.0 else (1.0 if x >= 1.0 else x * x * (3.0 - 2.0 * x))


def win(x, a, b):
    return sm((x - a) / (b - a))


def clamp01(x):
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def hashD(a, b):
    h = math.sin(a * 12.9898 + b * 78.233) * 43758.5453
    return h - math.floor(h)


def make_proj(yaw, tilt, cx, cy, scale):
    st, ct = math.sin(tilt), math.cos(tilt)
    sy, cyw = math.sin(yaw), math.cos(yaw)

    def proj(x, y, z):
        x1 = x * cyw + z * sy
        z1 = -x * sy + z * cyw
        y1 = y * ct - z1 * st
        z2 = y * st + z1 * ct
        return cx + x1 * scale, cy - y1 * scale, z2

    return proj


def radius_scale(size, pow_v):
    return (size / 300.0) ** pow_v


def make_moves(count):
    moves = []
    for i in range(count):
        axis = min(2, math.floor(hashD(i, 2.3) * 3))
        lo = -1.0 + 0.5 * min(3, math.floor(hashD(i, 5.9) * 4))
        dir_v = 1 if hashD(i, 7.7) < 0.5 else -1
        moves.append((axis, lo, lo + 0.5, dir_v * math.pi / 2.0))
    return moves


def solve_cycle(time_val, count, slot_dur, rest):
    cyc = 2 * count * slot_dur + rest
    tc = time_val % cyc
    amount = [0.0] * count
    active = -1
    if tc < 2 * count * slot_dur:
        slot = math.floor(tc / slot_dur)
        p = (tc - slot * slot_dur) / slot_dur
        cl = min(1.0, p / 0.7)
        ep = 1.0 - (1.0 - cl) ** 3
        if slot < count:
            for i in range(slot):
                amount[i] = 1.0
            amount[slot] = ep
            active = slot
        else:
            u = 2 * count - 1 - slot
            for i in range(u):
                amount[i] = 1.0
            amount[u] = 1.0 - ep
            active = u
    return amount, active


def apply_moves(pt3, moves, amount, active):
    x, y, z = pt3
    in_active = False
    for i, (axis, lo, hi, ang) in enumerate(moves):
        amt = amount[i]
        if amt <= 0.0:
            continue
        coord = x if axis == 0 else (y if axis == 1 else z)
        if coord < lo or coord >= hi:
            continue
        if i == active:
            in_active = True
        a = ang * amt
        ca, sa = math.cos(a), math.sin(a)
        if axis == 0:
            y2 = y * ca - z * sa
            z = y * sa + z * ca
            y = y2
        elif axis == 1:
            x2 = x * ca + z * sa
            z = -x * sa + z * ca
            x = x2
        else:
            x2 = x * ca - y * sa
            y = x * sa + y * ca
            x = x2
    return x, y, z, in_active


# Precompute sphere lattice once
LAT_RINGS = 15
LON_DENSITY = 40
SPHERE_PTS = []
for li in range(LAT_RINGS + 1):
    lat = -math.pi / 2.0 + (li / LAT_RINGS) * math.pi
    cos_lat = math.cos(lat)
    sin_lat = math.sin(lat)
    lon_count = max(1, round(abs(cos_lat) * LON_DENSITY))
    for lj in range(lon_count):
        lon = (lj / lon_count) * 2.0 * math.pi
        SPHERE_PTS.append((cos_lat * math.cos(lon), sin_lat, cos_lat * math.sin(lon)))

MOVES = make_moves(RUBIK_MOVES)
RS = radius_scale(SIZE, 0.6)
R_SPHERE = (SIZE / 2.0) * 0.82


def frame_rubik(t):
    pt = make_proj(t * 0.55, 0.35 + 0.1 * math.sin(t * 0.9), CX, CY, R_SPHERE)
    amount, active = solve_cycle(t, RUBIK_MOVES, RUBIK_SLOT, RUBIK_REST)
    dots = []
    for idx, p0 in enumerate(SPHERE_PTS):
        x, y, z, in_active = apply_moves(p0, MOVES, amount, active)
        px, py, zr = pt(x, y, z)
        depth = (zr + 1.0) / 2.0
        r = (0.95 + 2.2 * depth + (0.4 if in_active else 0.0)) * RS
        r = max(0.4, r)
        white = 0.62 - 0.54 * depth - (0.14 if in_active else 0.0)
        dots.append((idx, px, py, zr, r, white))
    dots.sort(key=lambda d: d[3])
    return dots


def timeline(T):
    if T < T_IN:
        x, phase = 0.0, "still"
    elif T < T_IN + TIMING_MORPH_IN:
        x, phase = (T - T_IN) / TIMING_MORPH_IN, "in"
    elif T < T_OUT:
        x, phase = 1.0, "solve"
    else:
        x, phase = 1.0 - (T - T_OUT) / TIMING_MORPH_OUT, "out"
    return {
        "x": x,
        "c": x,
        "phase": phase,
        "bloom": win(x, 0.45, 0.85),
        "t": min(max(T - T_RUN, 0.0), CYC - 0.001),
    }


def mulberry32(seed):
    a = seed & 0xFFFFFFFF

    def rng():
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = ((a ^ (a >> 15)) * (1 | a)) & 0xFFFFFFFF
        t = (t ^ (t + ((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0

    return rng


def extract_avatar_pixels(theme="dark"):
    if os.path.exists(AVATAR_PATH_TXT):
        with open(AVATAR_PATH_TXT, "r", encoding="utf-8") as f:
            d_str = f.read()
    else:
        with open(SOURCE_HTML, "r", encoding="utf-8") as f:
            html = f.read()
        m = re.search(r'<script type="text/plain" id="avatar-d">([\s\S]*?)</script>', html)
        if not m:
            raise RuntimeError("Could not find avatar-d path in avatar_rubik_morph.html")
        d_str = m.group(1)
    xs, ys = [], []
    for match in re.finditer(r"M(-?[\d.]+),(-?[\d.]+)h([\d.]+)", d_str):
        x0 = float(match.group(1))
        y0 = float(match.group(2))
        n = int(float(match.group(3)))
        for i in range(n):
            xs.append(x0 + i)
            ys.append(y0)
    if theme == "light":
        # Light mode: dots draw the dark regions inside the portrait circle (eyes, lines, shadow)
        lit_grid = np.zeros((SIZE, SIZE), dtype=bool)
        ix = np.clip(np.round(xs).astype(int), 0, SIZE - 1)
        iy = np.clip(np.round(ys).astype(int), 0, SIZE - 1)
        lit_grid[iy, ix] = True
        yy, xx = np.ogrid[:SIZE, :SIZE]
        cmask = (xx - CX) ** 2 + (yy - CY) ** 2 <= (AVATAR_R - 2) ** 2
        dark_grid = cmask & (~lit_grid)
        ys_inv, xs_inv = np.where(dark_grid)
        xs = xs_inv.tolist()
        ys = ys_inv.tolist()
    n = len(xs)
    fx = np.array(xs, dtype=np.float32) + 0.5
    fy = np.array(ys, dtype=np.float32)
    rnd = mulberry32(20240607)
    r_arr = np.array([rnd() for _ in range(n)], dtype=np.float32)
    rho = np.minimum(1.0, np.hypot(fx - CX, fy - CY) / AVATAR_R)
    dly = 0.5 * (1.0 - rho) + 0.5 * r_arr
    return fx, fy, dly


def assign_dots(fx, fy, t_ref):
    dots = frame_rubik(timeline(t_ref)["t"])
    front = [d for d in dots if d[3] >= 0.0]
    dx = np.array([d[1] for d in front], dtype=np.float32)
    dy = np.array([d[2] for d in front], dtype=np.float32)
    ids = np.array([d[0] for d in front], dtype=np.int32)

    # Vectorized nearest-neighbor lookup in chunks
    out = np.empty(len(fx), dtype=np.int32)
    chunk = 2000
    for s in range(0, len(fx), chunk):
        e = min(len(fx), s + chunk)
        ex = fx[s:e, None] - dx[None, :]
        ey = fy[s:e, None] - dy[None, :]
        dd = ex * ex + ey * ey
        out[s:e] = ids[np.argmin(dd, axis=1)]
    return out


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def draw_terminal_base(theme="dark"):
    if theme == "dark":
        pal = {
            "outer_bg": "#0D1117",
            "win_bg": "#0A101F",
            "panel_bg": "#070B14",
            "border": "#1E293B",
            "ink": "#A1A1AA",
            "chrome": "#22D3EE",
            "chrome_dim": "#38BDF8",
            "accent": "#10B981",
            "violet": "#A78BFA",
            "text": "#F8FAFC",
            "muted": "#64748B",
            "leader": "#1E293B",
            "row_alt": (12, 19, 34),
            "pill_bg": (14, 38, 58),
            "inner_ring": (32, 38, 52),
            "live_halo": (60, 22, 36),
            "live": "#EF4444",
        }
    else:
        pal = {
            "outer_bg": "#FFFFFF",
            "win_bg": "#F8FAFC",
            "panel_bg": "#FFFFFF",
            "border": "#CBD5E1",
            "ink": "#3F3F46",
            "chrome": "#0891B2",
            "chrome_dim": "#0284C7",
            "accent": "#059669",
            "violet": "#7C3AED",
            "text": "#0F172A",
            "muted": "#64748B",
            "leader": "#CBD5E1",
            "row_alt": (241, 245, 249),
            "pill_bg": (224, 242, 254),
            "inner_ring": (226, 232, 240),
            "live_halo": (254, 226, 226),
            "live": "#DC2626",
        }

    # 2x supersampled static UI for razor-sharp text & borders, then downscale
    S = 2
    img = Image.new("RGB", (W_BANNER * S, H_BANNER * S), hex_to_rgb(pal["outer_bg"]))
    draw = ImageDraw.Draw(img)

    font_path = "C:/Windows/Fonts/CascadiaMono.ttf"
    if not os.path.exists(font_path):
        font_path = "C:/Windows/Fonts/consola.ttf"

    f_11 = ImageFont.truetype(font_path, 11 * S)
    f_12 = ImageFont.truetype(font_path, 12 * S)
    f_13 = ImageFont.truetype(font_path, 13 * S)
    f_14 = ImageFont.truetype(font_path, 14 * S)

    # Outer terminal frame
    draw.rounded_rectangle(
        [0, 0, W_BANNER * S - 1, H_BANNER * S - 1],
        radius=16 * S,
        fill=hex_to_rgb(pal["win_bg"]),
        outline=hex_to_rgb(pal["border"]),
        width=2 * S,
    )

    # Top bar divider
    draw.line([0, 54 * S, W_BANNER * S, 54 * S], fill=hex_to_rgb(pal["border"]), width=1 * S)

    # Traffic lights
    for cx_d, col in [(28, "#EF4444"), (48, "#F59E0B"), (68, "#10B981")]:
        draw.ellipse(
            [(cx_d - 5.5) * S, (27 - 5.5) * S, (cx_d + 5.5) * S, (27 + 5.5) * S],
            fill=hex_to_rgb(col),
        )

    # Title: profile.sh --live
    draw.text((96 * S, 20 * S), "profile.sh", font=f_13, fill=hex_to_rgb(pal["muted"]))
    draw.text((184 * S, 20 * S), "--live", font=f_13, fill=hex_to_rgb(pal["chrome"]))

    # Handle pill: Xylus
    draw.rounded_rectangle(
        [978 * S, 15 * S, 1070 * S, 39 * S],
        radius=12 * S,
        fill=pal["pill_bg"],
        outline=hex_to_rgb(pal["chrome"]),
        width=1 * S,
    )
    draw.ellipse([(990 - 3) * S, (27 - 3) * S, (990 + 3) * S, (27 + 3) * S], fill=hex_to_rgb(pal["chrome"]))
    draw.text((1001 * S, 20 * S), "Xylus", font=f_12, fill=hex_to_rgb(pal["chrome"]))

    # LIVE badge (glowing outer ring + core dot; kept static so delta-cropped GIF stays tiny)
    live_rgb_val = hex_to_rgb(pal["live"])
    draw.ellipse([(1100 - 7) * S, (27 - 7) * S, (1100 + 7) * S, (27 + 7) * S], fill=pal["live_halo"])
    draw.ellipse([(1100 - 4) * S, (27 - 4) * S, (1100 + 4) * S, (27 + 4) * S], fill=live_rgb_val)
    draw.text((1112 * S, 20 * S), "LIVE", font=f_12, fill=live_rgb_val)

    # Left panel: // VISUAL.MAP
    draw.text((28 * S, 62 * S), "// VISUAL.MAP", font=f_12, fill=hex_to_rgb(pal["chrome"]))
    draw.text((388 * S, 62 * S), "400x400", font=f_11, fill=hex_to_rgb(pal["muted"]))
    draw.rounded_rectangle(
        [28 * S, 82 * S, 452 * S, 582 * S],
        radius=12 * S,
        fill=hex_to_rgb(pal["panel_bg"]),
        outline=hex_to_rgb(pal["border"]),
        width=1 * S,
    )

    # Corner reticles
    ret_col = hex_to_rgb(pal["chrome"])
    for rx, ry, dx, dy in [
        (38, 92, 14, 14),
        (442, 92, -14, 14),
        (38, 572, 14, -14),
        (442, 572, -14, -14),
    ]:
        draw.line([rx * S, ry * S, (rx + dx) * S, ry * S], fill=ret_col, width=2 * S)
        draw.line([rx * S, ry * S, rx * S, (ry + dy) * S], fill=ret_col, width=2 * S)

    # Dashed ring + subtle inner ring inside VISUAL.MAP tile (at center 240, 332)
    tcx, tcy = (TILE_X + CX) * S, (TILE_Y + CY) * S
    r_outer = 188 * S
    # Draw dashed circle
    steps = 100
    ring_col = hex_to_rgb(pal["border"])
    for k in range(0, steps, 2):
        a0 = (k / steps) * 2 * math.pi
        a1 = ((k + 1) / steps) * 2 * math.pi
        x0, y0 = tcx + r_outer * math.cos(a0), tcy + r_outer * math.sin(a0)
        x1, y1 = tcx + r_outer * math.cos(a1), tcy + r_outer * math.sin(a1)
        draw.line([x0, y0, x1, y1], fill=ring_col, width=int(1.5 * S))

    r_inner = 176 * S
    draw.ellipse(
        [tcx - r_inner, tcy - r_inner, tcx + r_inner, tcy + r_inner],
        outline=pal["inner_ring"],
        width=1 * S,
    )

    # Bottom caption inside VISUAL.MAP
    cap = "MONO_01  <=>  SOLVING [RUBIK-3D]"
    cb = draw.textbbox((0, 0), cap, font=f_11)
    cw = cb[2] - cb[0]
    draw.text((tcx - cw / 2, 554 * S), cap, font=f_11, fill=hex_to_rgb(pal["muted"]))

    # Right panel: // SYSTEM.INFO
    draw.text((476 * S, 62 * S), "// SYSTEM.INFO", font=f_12, fill=hex_to_rgb(pal["chrome"]))
    status_txt = "SECURE SHELL"
    sb = draw.textbbox((0, 0), status_txt, font=f_11)
    draw.text((1150 * S - (sb[2] - sb[0]), 62 * S), status_txt, font=f_11, fill=hex_to_rgb(pal["accent"]))

    draw.rounded_rectangle(
        [476 * S, 82 * S, 1152 * S, 582 * S],
        radius=12 * S,
        fill=hex_to_rgb(pal["panel_bg"]),
        outline=hex_to_rgb(pal["border"]),
        width=1 * S,
    )
    draw.rounded_rectangle(
        [476 * S, 82 * S, 1152 * S, 116 * S],
        radius=12 * S,
        fill=hex_to_rgb(pal["win_bg"]),
        outline=hex_to_rgb(pal["border"]),
        width=1 * S,
    )
    draw.text((496 * S, 92 * S), "KEY / PARAMETER", font=f_11, fill=hex_to_rgb(pal["muted"]))
    tv_txt = "TELEMETRY VALUE"
    tvb = draw.textbbox((0, 0), tv_txt, font=f_11)
    draw.text((1132 * S - (tvb[2] - tvb[0]), 92 * S), tv_txt, font=f_11, fill=hex_to_rgb(pal["muted"]))

    info_rows = [
        ("Subject", "Xylus", pal["chrome"]),
        ("Role", "Independent Explorer", pal["text"]),
        ("Origin", "India", pal["text"]),
        ("Status", "Thinking · Exploring · Building", pal["accent"]),
        ("Core.Physics", "Mechanics · Dynamics · Simulations", pal["violet"]),
        ("Core.Math", "Logic · Linear Algebra · Geometry", pal["violet"]),
        ("Core.Logic", "Algorithmic Thinking · First Principles", pal["text"]),
        ("ToolChain", "Python · Rust · VS Code · Git", pal["text"]),
        ("Grid.Mail", "xtreame.1825@gmail.com", pal["chrome_dim"]),
        ("Grid.Signal", "Email ideas anytime — open to collabs", pal["accent"]),
        ("Orb.Engine", "frameRubik // 14-Move 3D Lattice", pal["ink"]),
    ]

    start_y = 140
    spacing = 38
    left_x = 496 * S
    right_x = 1132 * S

    for i, (k_txt, v_txt, v_col) in enumerate(info_rows):
        y_p = (start_y + i * spacing) * S
        if i % 2 == 1:
            draw.rounded_rectangle(
                [488 * S, y_p - 7 * S, 1140 * S, y_p + 21 * S],
                radius=6 * S,
                fill=pal["row_alt"],
            )

        draw.text((left_x, y_p), k_txt, font=f_14, fill=hex_to_rgb(pal["chrome"]))
        kb = draw.textbbox((0, 0), k_txt, font=f_14)
        kw = kb[2] - kb[0]

        vb = draw.textbbox((0, 0), v_txt, font=f_14)
        vw = vb[2] - vb[0]
        draw.text((right_x - vw, y_p), v_txt, font=f_14, fill=hex_to_rgb(v_col))

        # Dotted leader precisely filling space between label and value
        gap_start = left_x + kw + 14 * S
        gap_end = right_x - vw - 14 * S
        dot_y = y_p + 8 * S
        leader_col = hex_to_rgb(pal["leader"])
        for dx in range(int(gap_start), int(gap_end), 8 * S):
            draw.ellipse([dx, dot_y, dx + 2 * S, dot_y + 2 * S], fill=leader_col)

    base_1x = img.resize((W_BANNER, H_BANNER), Image.Resampling.LANCZOS)
    return np.array(base_1x, dtype=np.uint8), pal


def render_banner(theme="dark", fps=15):
    print(f"Building {theme} banner...")
    base_rgb, pal = draw_terminal_base(theme=theme)
    bg_tile_rgb = np.array(hex_to_rgb(pal["panel_bg"]), dtype=np.float32)
    ink_rgb = np.array(hex_to_rgb(pal["ink"]), dtype=np.float32)

    fx, fy, dly = extract_avatar_pixels(theme=theme)
    tid_in = assign_dots(fx, fy, T_IN + TIMING_MORPH_IN)
    tid_out = assign_dots(fx, fy, T_OUT)

    # Prebuild sample schedule:
    # 0.0 -> 2.0s is still avatar (single frame of 2000ms)
    # 2.0 -> LOOP at fps
    dt = 1.0 / fps
    schedule = [(0.0, int(TIMING_HOLD * 1000))]
    t_cur = TIMING_HOLD
    while t_cur < LOOP:
        step = min(dt, LOOP - t_cur)
        ms = max(20, int(round(step * 1000)))
        schedule.append((t_cur, ms))
        t_cur += dt

    # Extract clean 400x400 background tile from base_rgb
    tile_base = base_rgb[TILE_Y : TILE_Y + SIZE, TILE_X : TILE_X + SIZE].copy()
    frames = []
    durations = []

    n_dots = len(SPHERE_PTS)
    dx_arr = np.zeros(n_dots, dtype=np.float32)
    dy_arr = np.zeros(n_dots, dtype=np.float32)
    di_arr = np.zeros(n_dots, dtype=np.float32)

    SPREAD = 0.8

    for idx_f, (T, dur_ms) in enumerate(schedule):
        st = timeline(T)
        tile_img = Image.fromarray(tile_base.copy())
        c_val = st["c"]

        if st["x"] <= 0.0:
            # Pure avatar pixels at rest
            buf = np.array(tile_img)
            px = np.floor(fx + 0.5).astype(np.int32)
            py = np.floor(fy + 0.5).astype(np.int32)
            valid = (px >= 0) & (px < SIZE) & (py >= 0) & (py < SIZE)
            buf[py[valid], px[valid]] = ink_rgb.astype(np.uint8)
            tile_img = Image.fromarray(buf)
        else:
            fr = frame_rubik(st["t"])
            for d_id, dpx, dpy, dz, dr, dwhite in fr:
                dx_arr[d_id] = dpx
                dy_arr[d_id] = dpy
                di_arr[d_id] = clamp01(1.0 - dwhite)

            if st["bloom"] < 1.0:
                tid = tid_out if st["phase"] == "out" else tid_in
                e = c_val * (1.0 + SPREAD) - dly * SPREAD
                moving = e > 0.0
                e_clip = np.clip(e, 0.0, 1.0)
                e_smooth = e_clip * e_clip * (3.0 - 2.0 * e_clip)

                px = fx.copy()
                py = fy.copy()
                k_val = np.ones(len(fx), dtype=np.float32)

                j = tid[moving]
                em = e_smooth[moving]
                px[moving] += (dx_arr[j] - px[moving]) * em
                py[moving] += (dy_arr[j] - py[moving]) * em
                k_val[moving] += (di_arr[j] - 1.0) * em

                ix = np.floor(px + 0.5).astype(np.int32)
                iy = np.floor(py + 0.5).astype(np.int32)
                valid = (ix >= 0) & (ix < SIZE) & (iy >= 0) & (iy < SIZE)

                buf = np.array(tile_img)
                kv = k_val[valid, None]
                cols = (bg_tile_rgb * (1.0 - kv) + ink_rgb * kv + 0.5).astype(np.uint8)
                buf[iy[valid], ix[valid]] = cols
                tile_img = Image.fromarray(buf)

            if st["bloom"] > 0.02:
                # Render smooth anti-aliased dots at 2x and composite over the crisp pixel buffer
                dots_2x = Image.new("RGBA", (SIZE * 2, SIZE * 2), (0, 0, 0, 0))
                tile_draw = ImageDraw.Draw(dots_2x, "RGBA")
                bloom = st["bloom"]
                r_scale = 0.35 + 0.65 * bloom
                alpha = int(round(bloom * 255))
                for _, dpx, dpy, _, dr, dwhite in fr:
                    intensity = clamp01(1.0 - dwhite)
                    col = tuple(int(round(bg_tile_rgb[c] + (ink_rgb[c] - bg_tile_rgb[c]) * intensity)) for c in range(3)) + (alpha,)
                    rad = dr * r_scale * 2.0
                    cx2, cy2 = dpx * 2.0, dpy * 2.0
                    tile_draw.ellipse([cx2 - rad, cy2 - rad, cx2 + rad, cy2 + rad], fill=col)
                dots_1x = dots_2x.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
                tile_img = Image.alpha_composite(tile_img.convert("RGBA"), dots_1x).convert("RGB")

        # Compose full frame
        full_arr = base_rgb.copy()
        full_arr[TILE_Y : TILE_Y + SIZE, TILE_X : TILE_X + SIZE] = np.array(tile_img)
        full_img = Image.fromarray(full_arr)

        frames.append(full_img)
        durations.append(dur_ms)

    # Build deterministic 128-color palette (7-bit LZW keeps GIF well under GitHub's 5 MB limit):
    # 1) 48 MEDIANCUT colors from UI + morph frames for crisp anti-aliased text edges
    # 2) Clean 20-step neutral ramp between panel_bg and ink (prevents violet tint on orb/avatar)
    # 3) Exact UI accent colors & anti-aliased steps (traffic lights, LIVE dot & halo, cyan/emerald/violet)
    gif_path = os.path.join(OUT_DIR, f"banner-{theme}.gif")
    mid_idx = min(len(frames) - 1, len(frames) // 2)
    sample_strip = Image.new("RGB", (W_BANNER, H_BANNER * 2))
    sample_strip.paste(frames[0], (0, 0))
    sample_strip.paste(frames[mid_idx], (0, H_BANNER))
    mc_img = sample_strip.quantize(colors=48, method=Image.Quantize.MEDIANCUT)
    mc_pal = mc_img.getpalette() or []
    palette_colors = []
    for i in range(0, min(len(mc_pal), 48 * 3), 3):
        c = tuple(mc_pal[i : i + 3])
        if c not in palette_colors:
            palette_colors.append(c)

    def add_ramp(c0, c1, steps):
        for k in range(steps):
            t = k / max(1, steps - 1)
            c = tuple(int(round(c0[i] + (c1[i] - c0[i]) * t)) for i in range(3))
            if c not in palette_colors and len(palette_colors) < 128:
                palette_colors.append(c)

    p_bg = hex_to_rgb(pal["panel_bg"])
    w_bg = hex_to_rgb(pal["win_bg"])
    ink_c = hex_to_rgb(pal["ink"])
    add_ramp(p_bg, ink_c, 20)
    add_ramp(w_bg, hex_to_rgb(pal["live"]), 5)
    add_ramp(w_bg, hex_to_rgb("#F59E0B"), 5)
    add_ramp(w_bg, hex_to_rgb("#EF4444"), 5)
    add_ramp(w_bg, hex_to_rgb("#10B981"), 5)
    add_ramp(w_bg, hex_to_rgb(pal["chrome"]), 5)
    add_ramp(p_bg, hex_to_rgb(pal["violet"]), 5)
    add_ramp(p_bg, hex_to_rgb(pal["accent"]), 5)

    for exact_col in [
        hex_to_rgb(pal["outer_bg"]),
        w_bg,
        p_bg,
        hex_to_rgb(pal["border"]),
        ink_c,
        hex_to_rgb(pal["chrome"]),
        hex_to_rgb(pal["chrome_dim"]),
        hex_to_rgb(pal["accent"]),
        hex_to_rgb(pal["violet"]),
        hex_to_rgb(pal["text"]),
        hex_to_rgb(pal["muted"]),
        hex_to_rgb(pal["leader"]),
        pal["row_alt"],
        pal["pill_bg"],
        pal["inner_ring"],
        pal["live_halo"],
        hex_to_rgb(pal["live"]),
    ]:
        if exact_col not in palette_colors and len(palette_colors) < 128:
            palette_colors.append(exact_col)

    palette_colors = palette_colors[:128]
    while len(palette_colors) < 128:
        palette_colors.append(palette_colors[-1])

    palette_img = Image.new("P", (16, 16))
    palette_img.putpalette([v for rgb in palette_colors for v in rgb])

    gif_frames = [f.quantize(palette=palette_img, dither=Image.Dither.NONE) for f in frames]
    gif_frames[0].save(
        gif_path,
        save_all=True,
        append_images=gif_frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    print(f"Saved {gif_path}: {os.path.getsize(gif_path) / 1024:.1f} KB ({len(gif_frames)} frames)")


if __name__ == "__main__":
    render_banner("dark", fps=12)
    render_banner("light", fps=12)
