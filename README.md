# nanokvm-typer

I wanted to fiddle around with scripting and automation with my nanoKVM _without_ AI, but all I found was this [issue](https://github.com/sipeed/NanoKVM/issues/199).

So I wrote a python script that generates a working script for my nanoKVM's


## Requirements

- Python
- A Sipeed NanoKVM

nothing else so it can run on the nanoKVM itself

## Quick start

```bash
# 1. Write what should be typed
echo '<SUPER+r><SLEEP 0.5>notepad<ENTER><SLEEP 1>Hello World!' > input.txt

# 2. Generate output.sh to upload to the nanokvm
python3 nanokvm_typer.py
```

## Input syntax

Everything in `input.txt` is typed as-is, except tokens in angle brackets. Tokens are case-insensitive (`<enter>` = `<ENTER>`).

### Special keys

| Token | Key |
|---|---|
| `<ENTER>` | Enter / Return |
| `<TAB>` | Tab |
| `<BACK>`, `<BACKSPACE>` | Backspace |
| `<SPACE>` | Space |
| `<ESC>` | Escape |
| `<UP>` `<DOWN>` `<LEFT>` `<RIGHT>` | Arrow keys |
| `<F1>` … `<F12>` | Function keys |
| `<DEL>`, `<DELETE>` | Delete (forward) |
| `<INSERT>` | Insert |
| `<HOME>` `<END>` | Home / End |
| `<PGUP>` `<PGDN>` | Page Up / Page Down |

### Modifiers

Modifiers can be pressed on their own (e.g. `<SUPER>` opens the Start menu on Windows) or combined with other keys.

| Token(s) | Modifier |
|---|---|
| `<CTRL>`, `<LCTRL>` | Left Control |
| `<RCTRL>` | Right Control |
| `<SHIFT>`, `<LSHIFT>` | Left Shift |
| `<RSHIFT>` | Right Shift |
| `<ALT>`, `<OPTION>`, `<LALT>` | Left Alt / Option (⌥) |
| `<ALTGR>`, `<RALT>` | Right Alt / AltGr |
| `<SUPER>`, `<GUI>`, `<WIN>`, `<CMD>` | Windows key / Command (⌘) |

### Combinations

Join keys with `+`. Any number of modifiers come first, followed by exactly one final key:

```
<MODIFIER+MODIFIER+...+KEY>
```

The final key can be:

| Final key | Example | Notes |
|---|---|---|
| A special key | `<CTRL+ALT+DEL>`, `<ALT+F4>`, `<CTRL+SHIFT+ESC>`, `<SHIFT+TAB>`, `<CMD+SPACE>` | |
| A single character | `<CTRL+c>`, `<SUPER+r>`, `<CMD+q>`, `<CTRL+->`, `<CTRL+1>` | Letters are always sent as the plain key: `<CTRL+C>` = `<CTRL+c>`. Add `SHIFT` explicitly if needed: `<CTRL+SHIFT+t>` |
| Another modifier | `<CTRL+SHIFT>`, `<ALT+SHIFT>` | Presses the modifiers together, e.g. to switch input language on Windows |

What does **not** work as a combination:

- `+`, `<`, `>` as final key! (`<CTRL++>`/`<CTRL+<>`/`<CTRL+>>`)
- Characters that need more than one keystroke in the chosen layout (dead keys such as `^`, `´`, `` ` ``, `~` on `mac-de`, or umlauts on `mac-us`)
- Characters that do not exist in the chosen layout
- Unknown Function Keys (`<FOO>`, `<CTRL+FOO>`)

If a token is not valid, it is **not** an error (*except F00-99!*): the `<` is typed as a normal character and the rest is typed as text.

### Pauses

```
<SLEEP 1>      wait 1 second
<SLEEP 0.5>    wait half a second
```

### Line breaks

Line breaks in `input.txt` are ignored by default, so you can spread a long input over several lines. Use `<ENTER>` where Enter should be pressed, or pass `--newline-enter` to turn every line break into an Enter.

### Example

```
<F11><SLEEP 1><UP><DOWN><ENTER>
<SUPER+r><SLEEP 0.5>notepad<ENTER><SLEEP 1>
Hello World! Size: 5 < 10, Mail: test@example.com <TAB>{ok}<BACK><ESC>
<CTRL+ALT+DEL>
```

## Keyboard layouts

The keyboard layout must match the layout configured on the **target machine**, otherwise characters come out wrong (e.g. `@` turning into `«`).

| `--layout` | Target | Notes |
|---|---|---|
| `de` (default) | Windows / Linux, German (QWERTZ) | Special characters via AltGr. Dead keys `^`, `´` and `` ` `` are followed by Space automatically |
| `us` | Windows / Linux, US (QWERTY) | ASCII only, no umlauts |
| `mac-de` | macOS, German | Special characters via Option: `@` = ⌥L, `{` `}` = ⌥8 ⌥9, `[` `]` = ⌥5 ⌥6, `\|` = ⌥7, `\` = ⌥⇧7, `€` = ⌥E, `~` = ⌥N + Space |
| `mac-us` | macOS, US | ASCII plus `€ § ° ß µ « »` via Option; umlauts `ä ö ü Ä Ö Ü` via the ⌥U dead key |

Characters that are not available in the chosen layout are skipped with a warning.

### macOS: `^` and `<` swapped

Depending on which keyboard type macOS detected for the NanoKVM, the keys `^` and `<` may come out swapped on German Macs. Add `--swap-iso` to fix this.

## Command-line options

| Flag | Default | Description |
|---|---|---|
| `-i`, `--input FILE` | `input.txt` | Input file |
| `-o`, `--output FILE` | `output.sh` | Generated script (ignored with `--run`) |
| `-l`, `--layout NAME` | `de` | Target layout: `de`, `us`, `mac-de`, `mac-us` |
| `--hold SECONDS` | `0.05` | How long each key is held down |
| `--gap SECONDS` | `0.02` | Pause between two keystrokes |
| `--device PATH` | `/dev/hidg0` | HID keyboard device on the NanoKVM |
| `--newline-enter` | off | Send Enter for every line break in the input file |
| `--swap-iso` | off | Swap the `^` and `<` keys (macOS) |
| `--run` | off | Execute the input instead of writing `output.sh` |
| `--host USER@HOST` | – | With `--run`: execute on the NanoKVM via SSH |
| `-h`, `--help` | | Show help |

### Modes

| Command | What happens | Where it runs |
|---|---|---|
| `nanokvm_typer.py` | Writes `output.sh` | Anywhere; copy `output.sh` to the NanoKVM and run it with `sh` |
| `nanokvm_typer.py --run` | Writes the HID reports directly to `--device` | On the NanoKVM (needs Python there) |
| `nanokvm_typer.py --run --host root@<ip>` | Generates the script and pipes it into `ssh root@<ip> sh` | On your PC; the typing happens on the NanoKVM |

`--host` without `--run` is rejected with an error.

### Flag combinations

All other flags can be combined freely with each other and with every mode. Some examples:

```bash
# Generate a script for a German Mac, custom file names
python3 nanokvm_typer.py -l mac-de -i login.txt -o login.sh

# Same, but ^ and < are swapped on that Mac
python3 nanokvm_typer.py -l mac-de --swap-iso

# Slow typing for machines that drop characters (e.g. BIOS, boot menus)
python3 nanokvm_typer.py --hold 0.2 --gap 0.1

# Every line in input.txt is a separate command followed by Enter
python3 nanokvm_typer.py --newline-enter

# Run directly from your PC over SSH, US Mac, newlines as Enter
python3 nanokvm_typer.py --run --host root@192.168.1.50 -l mac-us --newline-enter

# Run on the NanoKVM itself with a different input file
python3 nanokvm_typer.py --run -i commands.txt

# Use a different HID device
python3 nanokvm_typer.py --device /dev/hidg1
```

## Generated script format

Each keystroke becomes a press, a hold delay, a release and a gap:

```sh
echo -ne \\x00\\x00\\x44\\x00\\x00\\x00\\x00\\x00 > /dev/hidg0   # <F11> pressed
sleep 0.05
echo -ne \\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00 > /dev/hidg0   # <F11> released
sleep 0.02
```

The 8 bytes are a standard USB HID keyboard report: modifier byte, reserved byte, key code, five unused key slots.

## Troubleshooting

| Problem | Fix |
|---|---|
| Wrong characters (e.g. `@` becomes `«`, `y` and `z` swapped) | Use the `--layout` that matches the target machine |
| `^` and `<` swapped on a Mac | Add `--swap-iso` |
| Characters missing or doubled | Increase `--hold` and `--gap` |
| `Warning: character '…' not available in layout` | The character cannot be typed with that layout; pick another layout or rephrase |
| `Cannot open /dev/hidg0` | `--run` without `--host` must run on the NanoKVM, as root |


# LICENSE
This project is licensed under the [**GNU Affero General Public License (AGPL)**](LICENSE).