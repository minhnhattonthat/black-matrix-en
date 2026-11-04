"""stress_build.py: a marker build with chosen strings replaced, for what the marker text can't show: the glyph torture line, boxes filled to
the limit, a text long enough to overflow its window, strings too long for their place. Then warp.py --build the listed scenes.
usage: stress_build.py"""
import sys

import build
import check_rom

ASCII = ''.join(chr(c) for c in range(0x20, 0x7F) if chr(c) != '{')
R = lambda n, c: (c * n)[:n]
QA = {
    # 9 rows in a 3-row box: does the game page by itself?
    's64:0039e': '\n'.join(f'Row {i} too long for its box' for i in range(1, 10)),
    # the same with no breaks
    's64:003d6': 'A text that never breaks and is long enough to fill three rows of the portrait box and carry on to the next page by itself, to see what the game does then.',
    # 34 letters is the portrait box's row; row 3 fills up to the arrow
    's64:00402': '\n'.join(['1' * 34, '2' * 34, '3' * 32]),
    # the torture line, over two boxes' width
    's64:00456': ASCII[:34] + ASCII[34:68] + ASCII[68:],
    # diary window (19 cols), to the limit
    's27:00118': '\n'.join(['1' * 38, '2' * 38, '3' * 36]),
    # strings that outgrow their place: the long table
    '3rd:8011b778': 'Long string replacing a 2-word title',
    'slps:80076e00': 'Status (long)',
    # exactly full row followed by \n: does it skip a row?
    's64:00486': 'x' * 34 + '\nThe row after a full row',
}


def main():
    check_rom.check()
    docs = build.documents(True, QA.items())
    for disc in build.DISCS:
        print(build.make_image(disc, build.disc_files(disc, docs), build.output(disc)))


if __name__ == '__main__':
    sys.exit(main())
