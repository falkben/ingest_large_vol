'''
Command line script to expand a tiff stack into separate TIFF files
'''

from pathlib import Path
import argparse
import os

import numpy as np
import tifffile as tiff
from tqdm import tqdm


def parse_args():
    parser = argparse.ArgumentParser(
        description='Splits a tiff stack into separate tiff files')

    parser.add_argument(
        '--tiffstack', type=str, help='Full file path of tiff stack input')
    parser.add_argument(
        '--outpath', type=str, help='Full path for output files')
    parser.add_argument(
        '--datatype',
        type=str,
        help=
        'Cast images as a particular dtype (uint8/uint16/uint64), note that data can be lost this way'
    )
    parser.add_argument(
        '--split_RGB',
        action='store_true',
        help='Splits the RGB channels into separate folders')
    # parser.add_argument('--scale_to_datatype', action='store_true',
    #                     help='flag to scale the input datatype to the datatype specified')

    args = parser.parse_args()

    # validate args
    if args.tiffstack is None:
        raise ValueError('No input file')

    return args


def expand_stack(args):
    stackfile = Path(args.tiffstack)
    assert stackfile.exists()

    if args.outpath is None:
        outname = stackfile.parent / stackfile.stem
    else:
        outname = Path(args.outpath)
    outname.mkdir(exist_ok=True, parents=True)

    if args.split_RGB:
        # create RGB channel directories if they don't exist
        channels = 'r', 'g', 'b'
        [(outname / ch).mkdir(exist_ok=True) for ch in channels]

    # reads the stack into memory (seems to be unavoidable with using tifffile library)
    stack = tiff.imread(str(stackfile))

    num_slices = len(stack)
    digits = len(str(abs(num_slices)))
    outfname = '{0:0{1}d}'

    for idx, page in tqdm(enumerate(stack), total=num_slices):
        if args.datatype:
            page = page.astype(args.datatype)

        if args.split_RGB:
            for ch_idx, ch in enumerate(channels):
                tiff.imsave(
                    str(outname / ch /
                        (outfname.format(idx, digits) + '.tif')),
                    data=page[:, :, ch_idx])
        else:
            tiff.imsave(
                str(outname / (outfname.format(idx, digits) + '.tif')),
                data=page)


def main():
    args = parse_args()

    expand_stack(args)


if __name__ == '__main__':
    main()
