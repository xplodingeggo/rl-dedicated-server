"""Build the `!map` chat line for the dedicated server: pick a map and settings, press Copy, paste it in game.

usage: python mapurl.py [--game <server copy, default .\\game>]
Only reads the map names from the game folder; it never touches the server.
"""
import json
import os
import re
import sys
import tkinter as tk
from tkinter import filedialog, ttk

from fs import find
from mutators import BOTS, MODES, SETTINGS

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, 'mapurl.json')   # remembers the game folder
CHAT_LIMIT = 120                              # Rocket League cuts longer chat messages
NOT_MAPS = {'MENU_Main', 'Music', 'Stadium_P_Tutorial'}
BOT_LEVELS = ['None', 'Easy', 'Medium', 'Hard', 'Unfair']


def game_folder():
    args = sys.argv[1:]
    if '--game' in args:
        return args[args.index('--game') + 1]
    try:
        return json.load(open(CONFIG))['game']
    except (OSError, KeyError, ValueError):
        return os.path.join(HERE, 'game')


def find_maps(game):
    """-> {map name: shown name} from the *_P.upk files in the game's CookedPCConsole folder"""
    folder = find(game, 'TAGame', 'CookedPCConsole')
    maps = {}
    if os.path.isdir(folder):
        for f in os.listdir(folder):
            m = re.fullmatch(r'(.+_P)\.upk', f, re.I)
            if m and m.group(1)[:-2] not in NOT_MAPS and 'Music' not in f:
                maps[m.group(1)] = m.group(1)[:-2].replace('_', ' ')
    return dict(sorted(maps.items(), key=lambda kv: kv[1].lower()))


def build_line(map_name, mode, tags, bots, noreplay, extra):
    """-> the chat line. mode: game class or ''; tags: game tags; bots: number of bots; extra: raw `Key=value?Key2=value2` text"""
    parts = [map_name]
    if mode:
        parts.append('game=TAGame.' + mode)
    if tags:
        parts.append('GameTags=' + ','.join(tags))
    if bots:
        parts.append(f'NumBots={bots}')
    if noreplay:
        parts.append('noreplay')
    extra = extra.strip().lstrip('?')
    if extra:
        parts.append(extra)
    return '!map ' + '?'.join(parts)


class App(ttk.Frame):
    def __init__(self, root):
        super().__init__(root, padding=12)
        self.pack(fill='both', expand=True)
        root.title('Rocket League server: map line generator')
        root.geometry('980x640')
        root.minsize(760, 480)
        self.game = game_folder()
        self.maps = find_maps(self.game)
        if not self.maps:
            self.pick_folder()
        self.shown = list(self.maps.items())
        self.build()
        self.update_line()

    def pick_folder(self):
        folder = filedialog.askdirectory(title='Select the server copy (the folder that contains TAGame)')
        self.maps = find_maps(folder) if folder else {}
        if self.maps:
            self.game = folder
            json.dump({'game': folder}, open(CONFIG, 'w'))

    def build(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(self, text='Map', padding=8)
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 8))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)
        self.search = tk.StringVar()
        self.search.trace_add('write', lambda *_: self.filter())
        ttk.Entry(left, textvariable=self.search).grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 6))
        self.list = tk.Listbox(left, exportselection=False, activestyle='none', width=26)
        self.list.grid(row=1, column=0, sticky='nsew')
        bar = ttk.Scrollbar(left, command=self.list.yview)
        bar.grid(row=1, column=1, sticky='ns')
        self.list.config(yscrollcommand=bar.set)
        self.list.bind('<<ListboxSelect>>', lambda e: self.update_line())
        ttk.Label(left, text='Type to search the maps', foreground='gray').grid(row=2, column=0, sticky='w', pady=(4, 0))
        self.fill()

        right = ttk.LabelFrame(self, text='Settings', padding=8)
        right.grid(row=0, column=1, sticky='nsew')
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)
        canvas = tk.Canvas(right, highlightthickness=0)
        scroll = ttk.Scrollbar(right, command=canvas.yview)
        canvas.config(yscrollcommand=scroll.set)
        canvas.grid(row=0, column=0, sticky='nsew')
        scroll.grid(row=0, column=1, sticky='ns')
        inner = ttk.Frame(canvas, padding=(0, 0, 8, 0))
        window = canvas.create_window((0, 0), window=inner, anchor='nw')
        inner.bind('<Configure>', lambda e: canvas.config(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(window, width=e.width))
        canvas.bind_all('<MouseWheel>', lambda e: canvas.yview_scroll(-1 * (e.delta // 120), 'units'))
        for c in (1, 3):
            inner.columnconfigure(c, weight=1)

        self.mode = self.combo(inner, 0, 0, 'Game mode', [m[0] for m in MODES])
        ttk.Label(inner, text='Pick a map made for the mode (Hoops: Hoops..., Dropshot: ShatterShot)', foreground='gray').grid(
            row=0, column=2, columnspan=2, sticky='w')
        self.bots = self.slider(inner, 1, 'Bots', 0, 6, 0)
        self.level = self.combo(inner, 1, 2, 'Bot skill', BOT_LEVELS)
        self.combos = []
        for i, (label, options) in enumerate(SETTINGS):
            row, col = divmod(i, 2)
            self.combos.append(self.combo(inner, row + 2, col * 2, label, [o[0] for o in options]))
        row = len(SETTINGS) // 2 + 3
        self.noreplay = tk.BooleanVar()
        ttk.Checkbutton(inner, text='Skip goal replays', variable=self.noreplay, command=self.update_line).grid(
            row=row, column=0, columnspan=2, sticky='w', pady=(12, 0))
        ttk.Label(inner, text='Extra options (advanced), like  Key=value?Key2=value2').grid(
            row=row + 1, column=0, columnspan=4, sticky='w', pady=(10, 2))
        self.extra = tk.StringVar()
        self.extra.trace_add('write', lambda *_: self.update_line())
        ttk.Entry(inner, textvariable=self.extra).grid(row=row + 2, column=0, columnspan=4, sticky='ew')
        ttk.Button(inner, text='Reset all', command=self.reset).grid(row=row + 3, column=3, sticky='e', pady=(12, 0))

        bottom = ttk.Frame(self)
        bottom.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(12, 0))
        bottom.columnconfigure(0, weight=1)
        self.line = tk.StringVar()
        ttk.Entry(bottom, textvariable=self.line, state='readonly', font=('Consolas', 11)).grid(
            row=0, column=0, sticky='ew', ipady=4)
        ttk.Button(bottom, text='Copy', command=self.copy).grid(row=0, column=1, padx=(8, 0), ipadx=14, ipady=2)
        self.status = ttk.Label(bottom, text='')
        self.status.grid(row=1, column=0, columnspan=2, sticky='w', pady=(4, 0))
        ttk.Label(self, text='In game: press Copy, open chat, paste, Enter. You must be logged in with !admin <password>.',
                  foreground='gray').grid(row=2, column=0, columnspan=2, sticky='w', pady=(8, 0))

    def combo(self, parent, row, col, label, values):
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky='w', padx=(0, 8), pady=4)
        box = ttk.Combobox(parent, values=values, state='readonly', width=24)
        box.current(0)
        box.grid(row=row, column=col + 1, sticky='ew', padx=(0, 16), pady=4)
        box.bind('<<ComboboxSelected>>', lambda e: self.update_line())
        return box

    def slider(self, parent, row, label, lo, hi, start):
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=0, columnspan=2, sticky='ew', padx=(0, 16), pady=4)
        frame.columnconfigure(1, weight=1)
        var = tk.IntVar(value=start)
        value = ttk.Label(frame, width=2, anchor='e', text=str(start))
        ttk.Label(frame, text=label, width=10).grid(row=0, column=0, sticky='w')
        ttk.Scale(frame, from_=lo, to=hi, variable=var, command=lambda v: self.snap(var, value, v)).grid(
            row=0, column=1, sticky='ew', padx=8)
        value.grid(row=0, column=2)
        var.label = value
        return var

    def snap(self, var, label, raw):
        var.set(round(float(raw)))
        label.config(text=str(var.get()))
        self.update_line()

    def fill(self):
        query = self.search.get().lower()
        self.shown = [(k, v) for k, v in self.maps.items() if query in v.lower() or query in k.lower()]
        self.list.delete(0, 'end')
        for _, name in self.shown:
            self.list.insert('end', name)
        if self.shown:
            self.list.selection_set(0)

    def filter(self):
        self.fill()
        self.update_line()

    def reset(self):
        self.search.set('')
        self.bots.set(0)
        self.bots.label.config(text='0')
        for box in [self.mode, self.level, *self.combos]:
            box.current(0)
        self.noreplay.set(False)
        self.extra.set('')
        self.update_line()

    def tags(self):
        tags = [options[box.current()][1] for box, (_, options) in zip(self.combos, SETTINGS)]
        if self.bots.get() and self.level.current():
            tags.append(BOTS[self.level.current()])
        return [t for t in tags if t]

    def update_line(self):
        sel = self.list.curselection()
        if not sel or not self.shown:
            self.line.set('')
            self.status.config(text='No map selected' if self.maps else 'No maps found: restart and pick the server folder',
                               foreground='red')
            return
        line = build_line(self.shown[sel[0]][0], MODES[self.mode.current()][1] if self.mode.current() else '', self.tags(), self.bots.get(), self.noreplay.get(), self.extra.get())
        self.line.set(line)
        n = len(line)
        if n > CHAT_LIMIT:
            self.status.config(text=f'{n} characters: too long for chat (limit {CHAT_LIMIT}). Pick fewer settings.',
                               foreground='red')
        else:
            self.status.config(text=f'{n} / {CHAT_LIMIT} characters', foreground='gray')

    def copy(self):
        self.clipboard_clear()
        self.clipboard_append(self.line.get())
        self.update()   # keep the text on the clipboard after the window closes
        self.status.config(text='Copied. Paste it in the game chat.', foreground='green')


if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
