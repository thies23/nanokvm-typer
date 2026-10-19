#!/usr/bin/env python3
import argparse
import os
import re
import stat
import subprocess
import sys
import time

L_CTRL, L_SHIFT, L_ALT, L_GUI = 0x01, 0x02, 0x04, 0x08
R_CTRL, R_SHIFT, R_ALT, R_GUI = 0x10, 0x20, 0x40, 0x80

MODIFIERS = {
    "CTRL": L_CTRL, "LCTRL": L_CTRL, "RCTRL": R_CTRL,
    "SHIFT": L_SHIFT, "LSHIFT": L_SHIFT, "RSHIFT": R_SHIFT,
    "ALT": L_ALT, "OPTION": L_ALT, "LALT": L_ALT,
    "ALTGR": R_ALT, "RALT": R_ALT,
    "SUPER": L_GUI, "GUI": L_GUI, "WIN": L_GUI, "CMD": L_GUI,
}

SPECIAL = {
    "ENTER": 0x28, "ESC": 0x29, "BACK": 0x2A, "BACKSPACE": 0x2A,
    "TAB": 0x2B, "SPACE": 0x2C,
    "INSERT": 0x49, "HOME": 0x4A, "PGUP": 0x4B, "DEL": 0x4C, "DELETE": 0x4C,
    "END": 0x4D, "PGDN": 0x4E,
    "RIGHT": 0x4F, "LEFT": 0x50, "DOWN": 0x51, "UP": 0x52,
}
for _n in range(1, 13):
    SPECIAL[f"F{_n}"] = 0x3A + _n - 1

SPACE_STROKE = (0, 0x2C)


def _common():
    m = {}
    for i, c in enumerate("abcdefghijklmnopqrstuvwxyz"):
        m[c] = [(0, 0x04 + i)]
        m[c.upper()] = [(L_SHIFT, 0x04 + i)]
    for i, c in enumerate("1234567890"):
        m[c] = [(0, 0x1E + i)]
    m[" "] = [SPACE_STROKE]
    m["\t"] = [(0, 0x2B)]
    return m


def layout_us():
    m = _common()
    for i, c in enumerate("!@#$%^&*()"):
        m[c] = [(L_SHIFT, 0x1E + i)]
    pairs = {
        0x2D: "-_", 0x2E: "=+", 0x2F: "[{", 0x30: "]}", 0x31: "\\|",
        0x33: ";:", 0x34: "'\"", 0x35: "`~", 0x36: ",<", 0x37: ".>", 0x38: "/?",
    }
    for key, (plain, shifted) in pairs.items():
        m[plain] = [(0, key)]
        m[shifted] = [(L_SHIFT, key)]
    return m


def layout_mac_us():
    m = layout_us()
    O, S = L_ALT, L_SHIFT
    table = {
        "€": (O | S, 0x1F),
        "§": (O, 0x23),
        "°": (O | S, 0x25),
        "ß": (O, 0x16),
        "µ": (O, 0x10),
        "«": (O, 0x31), "»": (O | S, 0x31),
    }
    for c, stroke in table.items():
        m[c] = [stroke]
    umlaut_dead = (O, 0x18)
    for c in "aouAOU":
        target = {"a": "ä", "o": "ö", "u": "ü", "A": "Ä", "O": "Ö", "U": "Ü"}[c]
        m[target] = [umlaut_dead] + m[c]
    return m


def layout_de():
    m = _common()
    m["z"], m["Z"] = [(0, 0x1C)], [(L_SHIFT, 0x1C)]
    m["y"], m["Y"] = [(0, 0x1D)], [(L_SHIFT, 0x1D)]
    for i, c in enumerate('!"§$%&/()='):
        m[c] = [(L_SHIFT, 0x1E + i)]
    S, AG = L_SHIFT, R_ALT
    table = {
        "²": (AG, 0x1F), "³": (AG, 0x20),
        "{": (AG, 0x24), "[": (AG, 0x25), "]": (AG, 0x26), "}": (AG, 0x27),
        "ß": (0, 0x2D), "?": (S, 0x2D), "\\": (AG, 0x2D),
        "ü": (0, 0x2F), "Ü": (S, 0x2F),
        "+": (0, 0x30), "*": (S, 0x30), "~": (AG, 0x30),
        "#": (0, 0x32), "'": (S, 0x32),
        "ö": (0, 0x33), "Ö": (S, 0x33),
        "ä": (0, 0x34), "Ä": (S, 0x34),
        "°": (S, 0x35),
        ",": (0, 0x36), ";": (S, 0x36),
        ".": (0, 0x37), ":": (S, 0x37),
        "-": (0, 0x38), "_": (S, 0x38),
        "<": (0, 0x64), ">": (S, 0x64), "|": (AG, 0x64),
        "@": (AG, 0x14), "€": (AG, 0x08), "µ": (AG, 0x10),
    }
    for c, stroke in table.items():
        m[c] = [stroke]
    m["^"] = [(0, 0x35), SPACE_STROKE]
    m["´"] = [(0, 0x2E), SPACE_STROKE]
    m["`"] = [(S, 0x2E), SPACE_STROKE]
    return m


def layout_mac_de():
    m = layout_de()
    for c in ("²", "³"):
        m.pop(c, None)
    O, S = L_ALT, L_SHIFT
    table = {
        "@": (O, 0x0F),
        "€": (O, 0x08),
        "[": (O, 0x22), "]": (O, 0x23),
        "|": (O, 0x24),
        "\\": (O | S, 0x24),
        "{": (O, 0x25), "}": (O, 0x26),
        "µ": (O, 0x10),
        "«": (O, 0x14), "»": (O | S, 0x14),
    }
    for c, stroke in table.items():
        m[c] = [stroke]
    m["~"] = [(O, 0x11), SPACE_STROKE]
    return m


LAYOUTS = {
    "de": layout_de,
    "us": layout_us,
    "mac-de": layout_mac_de,
    "mac-us": layout_mac_us,
}

TOKEN_RE = re.compile(
    r"<(SLEEP\s+\d+(?:\.\d+)?|[A-Za-z]+[0-9]*(?:\+(?:[A-Za-z]+[0-9]*|[^<>\s+]))*)>",
    re.IGNORECASE,
)


def resolve_token(token, charmap):
    if token.upper().startswith("SLEEP"):
        return ("sleep", token.split()[1])

    parts = token.split("+")
    mods = 0
    for p in parts[:-1]:
        if p.upper() not in MODIFIERS:
            return None
        mods |= MODIFIERS[p.upper()]

    last = parts[-1]
    up = last.upper()
    label = "+".join(p.upper() if len(p) > 1 else p for p in parts)

    if up in SPECIAL:
        return ("key", mods, SPECIAL[up], f"<{label}>")
    if up in MODIFIERS:
        return ("key", mods | MODIFIERS[up], 0x00, f"<{label}>")
    if len(last) == 1 and len(parts) > 1:
        ch = last.lower() if last.isalpha() else last
        strokes = charmap.get(ch)
        if strokes and len(strokes) == 1:
            smod, key = strokes[0]
            return ("key", mods | smod, key, f"<{label}>")
    return None


def parse(text, charmap, newline_enter):
    actions = []
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text.endswith("\n"):
        text = text[:-1]

    def type_text(chunk):
        for ch in chunk:
            if ch == "\n":
                if newline_enter:
                    actions.append(("key", 0, SPECIAL["ENTER"], "ENTER (newline)"))
                continue
            strokes = charmap.get(ch)
            if not strokes:
                print(f"Warning: character {ch!r} not available in layout - skipped",
                      file=sys.stderr)
                continue
            for mod, key in strokes:
                actions.append(("key", mod, key, f"'{ch}'" if ch != "'" else '"\'"'))

    pos = 0
    while pos < len(text):
        m = TOKEN_RE.search(text, pos)
        if not m:
            type_text(text[pos:])
            break
        type_text(text[pos:m.start()])
        res = resolve_token(m.group(1), charmap)
        if res is None:
            type_text("<")
            pos = m.start() + 1
            continue
        actions.append(res)
        pos = m.end()
    return actions


def apply_swap_iso(actions):
    out = []
    for a in actions:
        if a[0] == "key" and a[2] in (0x35, 0x64):
            a = ("key", a[1], 0x64 if a[2] == 0x35 else 0x35, a[3])
        out.append(a)
    return out


def report_bytes(mod, key):
    return bytes([mod, 0x00, key, 0, 0, 0, 0, 0])


def render_script(actions, hold, gap, device):
    def esc(data):
        return "".join(f"\\\\x{b:02x}" for b in data)

    release = esc(report_bytes(0, 0))
    lines = ["#!/bin/sh", "# generated by: https://github.com/thies23/nanokvm-typer", ""]
    for a in actions:
        if a[0] == "sleep":
            lines.append(f"sleep {a[1]}   # Pause")
            continue
        _, mod, key, label = a
        lines.append(f"echo -ne {esc(report_bytes(mod, key))} > {device}   # {label} pressed")
        if hold > 0:
            lines.append(f"sleep {hold}")
        lines.append(f"echo -ne {release} > {device}   # {label} released")
        if gap > 0:
            lines.append(f"sleep {gap}")
    return "\n".join(lines) + "\n"


def run_local(actions, hold, gap, device):
    release = report_bytes(0, 0)
    try:
        fd = os.open(device, os.O_WRONLY)
    except OSError as e:
        sys.exit(f"Cannot open {device}: {e}")
    try:
        for a in actions:
            if a[0] == "sleep":
                time.sleep(float(a[1]))
                continue
            _, mod, key, _label = a
            os.write(fd, report_bytes(mod, key))
            time.sleep(hold)
            os.write(fd, release)
            time.sleep(gap)
    finally:
        try:
            os.write(fd, release)
        except OSError:
            pass
        os.close(fd)


def run_remote(script, host):
    try:
        result = subprocess.run(["ssh", host, "sh"], input=script.encode("utf-8"))
    except FileNotFoundError:
        sys.exit("ssh not found")
    if result.returncode != 0:
        sys.exit(f"Remote execution failed (exit code {result.returncode})")


def main():
    ap = argparse.ArgumentParser(description="input.txt -> NanoKVM HID keyboard input")
    ap.add_argument("-i", "--input", default="input.txt",
                    help="input file (default: input.txt)")
    ap.add_argument("-o", "--output", default="output.sh",
                    help="generated script (default: output.sh)")
    ap.add_argument("-l", "--layout", choices=LAYOUTS, default="de",
                    help="keyboard layout of the target machine (default: de)")
    ap.add_argument("--hold", type=float, default=0.05,
                    help="seconds a key is held down (default: 0.05)")
    ap.add_argument("--gap", type=float, default=0.02,
                    help="pause between two keys (default: 0.02)")
    ap.add_argument("--device", default="/dev/hidg0",
                    help="HID keyboard device (default: /dev/hidg0)")
    ap.add_argument("--newline-enter", action="store_true",
                    help="send Enter for line breaks in the input file")
    ap.add_argument("--swap-iso", action="store_true",
                    help="swap the '^' and '<' keys (for Macs that swap them)")
    ap.add_argument("--run", action="store_true",
                    help="execute the input directly instead of writing output.sh")
    ap.add_argument("--host",
                    help="with --run: execute on this SSH host, e.g. root@192.168.1.50")
    args = ap.parse_args()

    if args.host and not args.run:
        ap.error("--host requires --run")

    try:
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        sys.exit(f"File not found: {args.input}")

    actions = parse(text, LAYOUTS[args.layout](), args.newline_enter)
    if args.swap_iso:
        actions = apply_swap_iso(actions)
    presses = sum(1 for a in actions if a[0] == "key")

    if args.run and args.host:
        print(f"Running {presses} keystrokes on {args.host}, layout {args.layout} ...")
        run_remote(render_script(actions, args.hold, args.gap, args.device), args.host)
        print("Done")
        return

    if args.run:
        print(f"Running {presses} keystrokes on {args.device}, layout {args.layout} ...")
        run_local(actions, args.hold, args.gap, args.device)
        print("Done")
        return

    with open(args.output, "w", encoding="utf-8", newline="\n") as f:
        f.write(render_script(actions, args.hold, args.gap, args.device))
    os.chmod(args.output, os.stat(args.output).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"Wrote {args.output}: {presses} keystrokes, layout {args.layout}")


if __name__ == "__main__":
    main()