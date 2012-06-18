#!/usr/bin/env python
'''
Copyright 2012 Petr Pudlak

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''

import argparse
import tempfile
import subprocess
import os.path
import sys
import re
import math
import contextlib
import shutil
from multiprocessing import Pool
# PIL
import Image

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
parser.add_argument('-p', '--processes', dest='processes', type=int,
        help='the number of ffmpegthumbnailer processes to run simultaneously')
args = parser.parse_args()

if os.path.exists(args.output) and not args.force:
    print "The output file {0} already exists.".format(args.output)
    sys.exit(2)

border = 1
twidth = args.width / args.x
theight = None
if args.aspect:
    theight = twidth * args.aspect
n = args.x * args.y

@contextlib.contextmanager
def tempdir():
    tdir = tempfile.mkdtemp('thumbs')
    try:
        yield tdir
    finally:
        shutil.rmtree(tdir)

if args.debug:
    ffout = None # print everything to stdout
else:
    ffout = open(os.path.devnull, 'w')

def ofile_name(i):
    return os.path.join(tdir, '%03d.png' % i)

def mkthumb(i):
    (part, fileno) = math.modf(float(i + 1) * len(args.input) / (n + 1))
    ifile = args.input[int(fileno)]
    ofile = ofile_name(i)
    percent = max(0, min(99, 100 * part + args.offset))
    print "{0} <- {1} {2}%".format(ofile, ifile, int(percent))
    if subprocess.call(
          [ 'ffmpegthumbnailer'
          , '-i{0}'.format(ifile)
          , '-t{0}%'.format(percent)
          , '-o{0}'.format(ofile)
          , '-s0'
          ], stdout = ffout, stderr = subprocess.STDOUT ):
        print "Failed to execute ffmpegthumbnailer."
        sys.exit(1)

with tempdir() as tdir:
    # Create video thumbnails as separate image files.
    if args.processes:
        pool = Pool(processes=args.processes)
        for i in range(0, n):
            pool.apply_async(mkthumb, (i, ))
        pool.close()
        pool.join()
    else:
        for i in range(0, n):
            mkthumb(i)
    if ffout:
        ffout.close()

    # Read the image files and combine them into one big image.
    im = Image.open(ofile_name(0))
    if not theight:
        # Open the first image to get its size
        (iw, ih) = im.size
        theight = twidth * ih / iw
    big = Image.new("RGB", (args.width, theight * args.y), (0x80, 0x80, 0x80))
    for i in range(0, n):
        (iy, ix) = divmod(i, args.x)
        ofile = ofile_name(i)
        im = Image.open(ofile)
        im.thumbnail((twidth - 2*border, theight - 2*border), Image.ANTIALIAS)
        big.paste(im, (twidth * ix + border, theight * iy + border))
    big.save(args.output)
print "Written {0}".format(args.output)
