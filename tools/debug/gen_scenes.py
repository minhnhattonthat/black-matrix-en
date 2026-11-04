"""Writes tools/debug/scenes.tsv: the warp scene list. Everything derivable (battles, movies, cards) comes from the scripts and the
EXE's movie table; hand-picked entries are below. Column meanings: docs/re/debug-tool.md. Re-run after changing this file.
Needs work/debug/all.txt: run `psidump.py` with no arguments first."""
import re, struct, sys
sys.path.insert(0, 'tools')
import mips, dat, psi

COLS = ['name', 'disc', 'script', 'pc', 'stub', 'until', 'master', 'vars', 'patch', 'later', 'route', 'mash', 'frames', 'every', 'proof', 'expect', 'note']
EVENT = '09/17,09/09'  # ops a chapter script runs before anything else in the event engine (overlay + init)
HOME = '09/17,09/01'   # same, home screens (script 38)
CH_HEADS = [(5, 1), (121, 2), (144, 3), (193, 4), (242, 5), (278, 6), (321, 7), (363, 8), (403, 9), (454, 10), (490, 11), (515, 12)]
TITLE = '2400 -;6 start;200 -'


def chapter(script):
    ch = 1
    for head, c in CH_HEADS:
        if script >= head:
            ch = c
    return ch


def disc(script):
    return 2 if chapter(script) >= 7 else 1


rows = []


def add(name, script='-', pc='-', stub='-', until='-', master=1, vars='', patch='-', later='-', route='-', mash=0, frames=600, every=60, proof='-', expect='-', note='', d=None):
    if script != '-':
        vs = f'a18={chapter(script)}'
        vars = vs + (',' + vars if vars else '')
        d = d or disc(script)
    rows.append(dict(zip(COLS, [name, d or 1, script, pc, stub, until, master, vars or '-', patch, later, route, mash, frames, every, proof, expect, note])))


def sites(rx):
    """(script, offset, line) for all.txt lines matching rx."""
    sid, out = None, []
    r = re.compile(rx)
    for ln in open('work/debug/all.txt', encoding='utf-8'):
        m = re.match(r'=== script (\d+)', ln)
        if m:
            sid = int(m.group(1))
        elif r.search(ln):
            out.append((sid, int(ln.split()[0], 16), ln.strip()))
    return out


# Title and system screens, by route alone (the menu opens on LOAD GAME: up = NEW GAME, down = CONFIG)
add('title', route='2400 -', frames=2400, every=600, note='title screen, PUSH START')
add('title_menu', route=TITLE, frames=2700, every=300, note='NEW GAME / LOAD GAME / CONFIG')
add('title_load', route=TITLE + ';6 circle;400 -', frames=3200, every=200, note='LOAD GAME: card check and slots')
add('title_config', route=TITLE + ';6 down;40 -;6 circle;300 -', frames=3200, every=200, note='CONFIG screen (SYSTEM/4)')
add('title_newgame', route=TITLE + ';6 up;40 -;6 circle;200 -', frames=3200, every=100, note='NEW GAME: difficulty or next screen')
add('title_config_d2', route=TITLE + ';6 down;40 -;6 circle;300 -', frames=3200, every=200, d=2, note='CONFIG on Disc 2')
add('master_select', 5, 'bb6', master=0, frames=900, every=60, note='09/31: master select, SYSTEM/21 art')
add('master_confirm', 5, 'bb6', master=0, route='500 -;6 circle;240 -', frames=900, every=60, note='09/31: master confirm, SYSTEM/20')
add('rank_record', 5, 'd52', '08/35', frames=600, every=120, note='RANK RECORD (SYSTEM/16)')
add('special_room', 5, 'd52', '08/3d', frames=600, every=120, note='SPECIAL ROOM and sound test (SYSTEM/17)')
add('disc_swap', 321, 'e8', frames=400, d=1, every=60, note='Disc 1 asks for Disc 2 (SYSTEM/29)')
add('save_prompt', 144, frames=240, note='save prompt text choice')
add('save_screen', 144, '7c', route='120 -', frames=1500, every=120, note='save screen (SYSTEM/3), card check')

# Chapter opening cards: the real cold-boot flow for chapter 1, stubbed entry for the others
add('ch01_flow', 5, mash=30, frames=2400, every=120, note='NEW GAME flow: PROLOGUE movie, chapter 1 card; mash skips')
cards = [(121, 0xcd2), (150, 0xb74), (199, 0xe56), (249, 0xc6e), (284, 0xcc2), (327, 0xde2), (367, 0x1126), (408, 0xcee), (461, 0x7b0), (496, 0x748), (522, 0x50)]
for ch, (s, off) in zip(range(2, 13), cards):
    add(f'ch{ch:02d}_card', s, f'{off:x}', EVENT, frames=240, every=60, note=f'chapter {ch} title card')
add('ch01_card', 5, 'bce', EVENT, frames=240, every=60, note='chapter 1 title card')
ends = [(70, 0xe06, 1), (143, 0x3c06, 2), (188, 0x27ca, 3), (225, 0x3bb6, 4), (277, 0x1d7e, 5), (320, 0x2a2a, 6), (362, 0x287a, 7), (402, 0x1a6a, 8), (453, 0x1be8, 9), (489, 0x1966, 10), (514, 0xf0e, 11)]
for s, off, ch in ends:
    add(f'ch{ch:02d}_end', s, f'{off:x}', EVENT, frames=240, every=60, note=f'chapter {ch} end card')
add('time_next_day', 14, '10', HOME, frames=180, every=60, note='time card EVENT/106')
add('time_three_days', 14, '882', HOME, frames=180, every=60, note='time card EVENT/107')

# Real camp order: sortie, yes; twice (formation, then SP allotment): tutorial pages, done (Start), cursor from No to Yes, confirm.
# Starting the route at the camp op makes the same input sequence work for story battles and free battles.
SORTIE = '500 -;6 up;40 -;6 circle;90 -;6 circle;240 -;' + '6 circle;90 -;' * 20 + ('300 -;6 start;200 -;6 up;40 -;6 circle;200 -;' + '6 circle;90 -;' * 12) * 2

# Every battle: leave camp through SORTIE, then prove the title card or battlefield, not the camp menu.
chains = sites(r' 10 CHAIN ')
camps = sites(r' 08/(?:1c|23) ')
CHAIN_AFTER_CAMP = {222: 224}  # script 222 branches on b[158], which is 0 on a warp: its second CHAIN
# Battle rosters with no Abel (08/27 allowed, 08/19 forced): none of them have joined on a warp, so formation shows 0/0 and
# won't let you sortie. Point one operand of each at unit 0. The battlefield is the real one, its cast is not.
ROSTER_PATCH = {298: '54:0,7c:0', 506: '60:0,a0:0'}
for s, _, _ in sites(r' 0b/01 '):
    b = next(l for sid, _, l in sites(r' 0b/02 ') if sid == s)
    bid = re.search(r'#(\d+)', b).group(1)
    camp = next(((o, line) for sid, o, line in camps if sid == s), None)
    if camp is None:  # script 127 enters its battlefield directly
        add(f'battle_{s}_b{bid}', s, frames=1200, every=120, note=f'battlefield, BATTLE/{bid}')
        continue
    off, line = camp
    target = s
    if ' 08/1c ' in line:
        target = CHAIN_AFTER_CAMP.get(s) or int(next(re.search(r'CHAIN \(#(\d+)\)', l).group(1) for sid, o, l in chains if sid == s and o > off))
    same = ' (BATTLE/64 and BATTLE/66 are byte-identical, so the same picture as its twin is correct)' if bid in ('64', '66') else ''
    add(f'battle_{s}_b{bid}', s, until=f'{off:x}', route=SORTIE, frames=7800, every=300, patch=ROSTER_PATCH.get(s, '-'),
        expect=f'a17={target}', note=f'battle BATTLE/{bid}: camp sortie, title card and battlefield (script {target}){same}')
add('battle_ui', 127, route='1100 -', mash=60, frames=3000, every=150, note='battle: dialogue, placement, command menu')
add('game_over', 127, patch='1d8:8', frames=1500, every=120, note='0b/05 replaced by 0b/08: game over (BATTLE/1)')
add('battle_report', 132, '213c', route='300 -;6 start;60 -;6 cross;60 -;6 triangle;60 -;6 square;60 -;6 select;60 -;6 l1;60 -;6 r1;60 -', frames=900, every=60, note='08/1b: battle report (SYSTEM/15, 5TH.BIN)')
add('battle_sortie', 131, until='b6', route=SORTIE, frames=7800, every=300, expect='a17=132', note='camp menu, sortie, into the battle (132)')
# Pre-battle camp menu (08/1c, 3RD.BIN). Items in order: status, rite, items, shop, skills list, system, sortie
add('camp_menu', 160, until='be', route='60 -', frames=360, every=60, note='camp menu')
for i, name in enumerate(['status', 'rite', 'items', 'shop', 'skills', 'system']):
    moves = ';'.join(['6 down;30 -'] * i)
    route = ('500 -;' + (moves + ';' if moves else '') + '6 circle;240 -')
    add(f'camp_{name}', 160, until='be', route=route, frames=1200, every=120, note=f'camp menu, {name}')

# Home life: hub, the eight activities, their manuals
add('home_hub', 38, frames=1200, every=120, note='home map; EVENT/0-5')
add('home_card_menu', 38, route='600 -;6 start;200 -;6 circle;400 -', frames=1400, every=100, note='home hub, Start then Save: memory-card slot prompt')
add('home_sweep', 38, route='600 -;150 up+left;' + ';'.join(['120 right;12 down;120 left;12 down'] * 4), frames=1800, every=15, proof=585, note='home hub: cursor sweep; lower-left Japanese Menu/hotspot label (#739/#740)')
add('home_confirm', 37, '106', HOME, vars='a272=33', frames=480, every=60, note='cooking confirmation: Japanese choice prompt on a black background')
GAMES = [(76, 50, 'fishing'), (77, 53, 'hunting'), (78, 57, 'wood'), (93, 62, 'farm'), (79, 61, 'cooking'), (35, 65, 'cleaning'), (39, 66, 'laundry'), (36, 70, 'meal')]
GAME_NOTES = {
    'fishing': 'fishing: home map with a horizontal TIME meter',
    'hunting': 'hunting: home map with green foliage and a bow icon',
    'wood': 'wood chopping: home map with a TIME counter',
    'farm': 'farm mini-game: home map with TIME and a yellow 0匹 counter',
    'cooking': 'cooking: kitchen interior with stove and cookware',
    'cleaning': 'cleaning: tiled room, two characters and a red TIME counter',
    'laundry': 'laundry: home map with a washtub, dirt label and timer',
    'meal': 'meal: dining table with covered serving dishes',
}
for s, pic, name in GAMES:
    # fishing and wood have faded out by the last frame
    add(f'game_{name}', 37, 'edc', HOME, vars=f'a296={s},a301={pic}', frames=1200, every=120, proof=720 if name in ('fishing', 'wood') else '-', note=GAME_NOTES[name])
for i in range(8):
    add(f'manual_{i}', 37, 'f8c', HOME, vars=f'a272={30 + i}', frames=480, every=120, note=f'manual EVENT/{71 + i}')
# Chain through the home dispatcher so the event overlay and the correct background are initialized.
add('home_town', 37, 'edc', HOME, vars='a296=64,a301=14', mash=30, frames=1200, every=120, note='town scene, first master')
add('home_diary', 27, '10', HOME, vars='a230=1', mash=30, frames=600, every=120, note='diary entry 1: Japanese diary text on a black background')
add('home_book', 37, 'edc', HOME, vars='a296=105,a301=12,a303=0', mash=30, frames=1200, every=120, proof=480, note='library: Japanese book text over the bookshelf room')

# Movies: 08/2a(id) from the EXE's table at 0x800759AC (id 1 = OPENING). Each on the disc that holds it.
c, l = mips.load_exe()
MOVIE_PROOF = {'0101': 1800, '0102': 120, 'STAFF': 1680, 'DEMO01': 1920, 'DEMO02': 720}  # frames past the fade-in and title text
for i in range(30):
    name_ptr, frames = struct.unpack_from('<II', c, 0x800759AC - l + i * 8)
    d = c[name_ptr - l:name_ptr - l + 32].split(b'\0')[0].decode()
    name = d.split('\\')[-1].split('.')[0]
    if name == '1202':
        continue  # in the EXE's table but on neither disc
    chain = 557 if name in ('DEMO01', 'DEMO02', 'STAFF') or name >= '0701' and name[0].isdigit() else 5
    if name == 'OPENING':
        chain = 5
    add(f'movie_{name}', chain, 'd52' if chain == 5 else '10', f'08/2c,08/2a({i + 1})', frames=min(frames + 120, 2400), every=240,
        proof=MOVIE_PROOF.get(name, max(1, min(240, frames // 2))), note=f'movie {name} playing (not a menu/black frame), {frames} frames, id {i + 1}', d=2 if chain == 557 else 1)

# Endings: script 557 branches on b[70]; cards are EVENT/292, 299-305. Master 6 selects Adam rather than Eve.
for v, off, name, master in [(1, '134', 'ending1', 1), (2, '134', 'ending2', 6), (4, '8d4', 'ending4', 1)]:
    add(name, 557, off, '09/17,09/09', master=master, vars=f'b70={v}', mash=30, frames=6000, every=120,
        proof={'ending1': 4920, 'ending2': 4920, 'ending4': 2400}[name], note=f'ending branch b[70]={v}, master {master}: its ending card / END illustration')
add('ending3', 557, 'c52', '09/17,09/09', vars='b70=3', frames=180, every=60, note='Satan ending: Japanese new-Satan card (EVENT/303)')
add('ending5', 557, 'e34', '09/17,09/09', vars='b70=5', mash=30, frames=360, every=120, note='ending branch b[70]=5: bright Game End angel illustration')
add('end_card_eve', 557, '700', '09/17,09/09', frames=180, every=60, note='EVENT/299')
add('end_card_adam', 557, '730', '09/17,09/09', frames=180, every=60, note='EVENT/300')
add('end_card_satan', 557, 'c52', '09/17,09/09', frames=180, every=60, note='EVENT/303')

with open('tools/debug/scenes.tsv', 'w', encoding='utf-8', newline='\n') as f:
    f.write('\t'.join(COLS) + '\n')
    for r in rows:
        f.write('\t'.join(str(r[k]) for k in COLS) + '\n')
print(len(rows), 'scenes')
