import os
import re
import time
import unittest
from datetime import datetime

import numpy as np
import png
import tifffile as tiff

from ingest_large_vol import *


class IngestLargeVolTest(unittest.TestCase):

    def setUp(self):
        self.startTime = time.time()

        self.rmt = BossRemote('neurodata.cfg')

        coll_name = 'ben_dev'
        exp_name = 'dev_ingest_4'
        ch_name = 'def_files'
        self.boss_res_params = BossResParams(coll_name, exp_name, ch_name)

        self.x_size = 1000
        self.y_size = 1024
        self.dtype = 'uint16'

        self.z = 0
        self.z_rng = [0, 16]
        self.fileprefix = 'img_<p:4>'
        self.data_directory = 'local_img_test_data\\'
        self.z_step = 1

    def tearDown(self):
        t = time.time() - self.startTime
        print('{:03.1f}s: {}'.format(t, self.id()))

    def test_send_msg(self):
        msg = 'test_message_' + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        send_msg(self.boss_res_params, msg)

        log_fname = gen_log_fname(self.boss_res_params)
        with open(log_fname) as f:
            log_data = f.readlines()

        self.assertIn(msg, log_data[-1])

    def test_get_img_fname(self):
        file_format = 'tif'
        img_fname = get_img_fname(
            self.fileprefix, self.data_directory, file_format, self.z, self.z_rng, self.z_step)

        img_fname_test = '{}img_{:04d}.tif'.format(self.data_directory, self.z)
        self.assertEqual(img_fname, img_fname_test)

    def test_get_img_info_uint16_tif(self):
        file_format = 'tif'

        img_fname = get_img_fname(
            self.fileprefix, self.data_directory, file_format, self.z, self.z_rng, self.z_step)
        create_img_file(self.x_size, self.y_size,
                        self.dtype, file_format, img_fname)

        im_width, im_height, im_datatype = get_img_info(
            self.boss_res_params, img_fname)
        self.assertEqual(im_width, self.x_size)
        self.assertEqual(im_height, self.y_size)
        self.assertEqual(im_datatype, self.dtype)

    def test_get_img_info_uint16_png(self):
        file_format = 'png'

        img_fname = get_img_fname(
            self.fileprefix, self.data_directory, file_format, self.z, self.z_rng, self.z_step)
        create_img_file(self.x_size, self.y_size,
                        self.dtype, file_format, img_fname)

        im_width, im_height, im_datatype = get_img_info(
            self.boss_res_params, img_fname)
        self.assertEqual(im_width, self.x_size)
        self.assertEqual(im_height, self.y_size)
        self.assertEqual(im_datatype, self.dtype)

    def test_read_uint16_img_stack(self):

        # generate some images
        file_format = 'tif'
        gen_images(self.z_rng[1], self.x_size, self.y_size,
                   self.dtype, file_format, self.fileprefix, self.data_directory)

        # load images into memory using ingest_large_vol function
        s3_res = None
        s3_bucket_name = None

        z_slices = range(self.z_rng[0], self.z_rng[1])
        z_step = 1
        self.boss_res_params.setup_resources(self.rmt)
        im_array = read_img_stack(self.boss_res_params, z_slices, self.fileprefix, self.data_directory,
                                  file_format, s3_res, s3_bucket_name, self.z_rng, self.z_step)

        # check to make sure each image is equal to each z index in the array
        for z in z_slices:
            img_fname = self.data_directory + 'img_{:04d}.tif'.format(z)
            im = Image.open(img_fname)
            self.assertTrue(np.array_equal(im_array[z, :, :], im))

    def test_post_uint16_cutout(self):
        x_size = 512
        y_size = 512
        bit_width = 16
        dtype = 'uint16'

        # generate a block of data
        data = np.random.randint(
            1, 2**bit_width, size=(self.z_rng[1], y_size, x_size), dtype=dtype)

        # post (non-zero) data to boss
        st_x, sp_x, st_y, sp_y, st_z, sp_z = (
            0, x_size, 0, y_size, 0, self.z_rng[1])

        self.boss_res_params.setup_resources(self.rmt)
        ret_val = post_cutout(self.boss_res_params, st_x, sp_x, st_y, sp_y,
                              st_z, sp_z, data, attempts=5, slack=None, slack_usr=None)

        self.assertEqual(ret_val, 0)

        # read data out of boss
        data_boss = self.rmt.get_cutout(self.boss_res_params.ch_resource, 0,
                                        [0, x_size], [0, y_size], self.z_rng)

        # assert they are the same
        self.assertTrue(np.array_equal(data_boss, data))


def create_img_file(x_size, y_size, dtype, file_format, img_fname):

    bit_width = int(''.join(filter(str.isdigit, dtype)))
    ar = np.random.randint(
        1, 2**bit_width, size=(y_size, x_size), dtype=dtype)

    directory = os.path.dirname(img_fname)
    if not os.path.isdir(directory):
        os.makedirs(directory)

    if file_format == 'tif':
        tiff.imsave(img_fname, ar)
    elif file_format == 'png':
        with open(img_fname, 'wb') as f:
            writer = png.Writer(width=x_size, height=y_size,
                                bitdepth=bit_width, greyscale=True)
            writer.write(f, ar.tolist())


def gen_images(n_images, x_size, y_size, dtype, file_format, fileprefix, directory, z_step=1):
    for z in range(0, n_images * z_step, z_step):
        img_fname = get_img_fname(
            fileprefix, directory, file_format, z, [0, n_images], z_step)
        create_img_file(x_size, y_size, dtype, file_format, img_fname)


if __name__ == '__main__':
    unittest.main()
