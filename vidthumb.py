#!/usr/bin/env python
import argparse
import tempfile
import subprocess
import os.path
import sys
import re
import math
import contextlib
import shutil

def ratio_parser(expression):
    (u, v) = re.match(r'^(\d*\.?\d+)(/(\d*\.?\d+))?$', expression).group(1, 3)
    u = float(u)
    if v:
        return u / float(v)
    else:
        return u;

parser = argparse.ArgumentParser(description='Makes video thumbnails using ffmpegthumbnailer.')
parser.add_argument('input', metavar='video_file', nargs='+',
        help='the input video file(s) to be processed')
parser.add_argument('-o', '--output', dest='output', required=True,
        help='the output image')
parser.add_argument('-w', '--width', dest='width', type=int, default=1024,
        help='one thumbnail width')
parser.add_argument('-x', dest='x', type=int, default=3,
        help='number of thumbnails horizontally')
parser.add_argument('-y', dest='y', type=int, default=8,
        help='number of thumbnails vertically')
parser.add_argument('--aspect', dest='aspect', type=ratio_parser,
        help='aspect ratio of thumbnails (i.e. 16/9)')
parser.add_argument('-f', '--force', dest='force', default=False, action='store_true',
        help='overwrite the destination file')
parser.add_argument('-d', '--debug', dest='debug', default=False, action='store_true',
        help='debugging on - print ffmpegthumbnailer output (use when ffmpegthumbnailer fails)')
parser.add_argument('--offset', dest='offset', type=int, default=0,
        help='shift the thumbnails positions by this amount of %%')
args = parser.parse_args()

if os.path.exists(args.output) and not args.force:
    print "The output file {0} already exists.".format(args.output)
    sys.exit(2)

twidth = args.width / args.x - 4
theight = ''
if args.aspect:
    theight = twidth * args.aspect
n = args.x * args.y + 1

@contextlib.contextmanager
def tempdir():
    tdir = tempfile.mkdtemp('thumbs')
    try:
        yield tdir
    finally:
        shutil.rmtree(tdir)

sys.stdout.flush()
ofiles = []
if args.debug:
    ffout = None # print everything to stdout
else:
    ffout = open(os.path.devnull, 'w')

with tempdir() as tdir:
    for i in range(1, n):
        (part, fileno) = math.modf(float(i) * len(args.input) / n)
        ifile = args.input[int(fileno)]
        ofile = os.path.join(tdir, '%03d.png' % i)
        percent = max(0, min(99, 100 * part + args.offset))
        print "{0} <- {1} {2}%".format(ofile, ifile, int(percent))
        ofiles.append(ofile)
        if subprocess.call(
              [ 'ffmpegthumbnailer'
              , '-i{0}'.format(ifile)
              , '-t{0}%'.format(percent)
              , '-o{0}'.format(ofile)
              , '-s0'
              ], stdout = ffout, stderr = subprocess.STDOUT ):
            print "Failed to execute ffmpegthumbnailer."
            sys.exit(1)
    if ffout:
        ffout.close()

    subprocess.call(
        [ 'gm'
        , 'montage'
        , '-interlace', 'Line'
        , '-background', 'gray'
        , '+label'
        , '-borderwidth', '1x1'
        , '-geometry', "{0}x{1}".format(twidth, theight)
        , '-tile', "{0}x{1}".format(args.x, args.y)
        ] + ofiles
          + [ args.output ])
print "Written {0}".format(args.output)
