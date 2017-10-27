#!/usr/bin/env python

import os
import shlex
from subprocess import list2cmdline

""" Script to generate ingest commands for ingest program """
""" Once generated, copy commands to terminal and run them """

""" Recommend copy this to a new location for editing """


script = "ingest_large_vol.py"

source_type = 's3'  # either 'local', 's3', or 'render'

# only used for 's3' source_type
s3_bucket_name = "BUCKET_NAME"
aws_profile = "default"

# only used for 'render' source_type
render_owner = 'OWNER_NAME'
render_project = 'PROJECT_NAME'
render_stack = 'STACK_NAME'
render_baseURL = 'BASEURL'
render_scale = 1  # 1 is full resolution, .5 is downsampled in half. None is scale = 1
render_window = '0 10000'  # set to None no windowing will be applied for 16bit to 8bit


boss_config_file = "neurodata.cfg"  # location on local system for boss API key

# Slack messages (optional)
# sends a slack message when ingest is finished with a link to the see the data
# set to a blank string (e.g. '') to exclude from command output
slack_token = "slack_token"  # Slack token for sending Slack messages
slack_username = "SLACKUSER"  # your slack username

# boss metadata
collection = 'COLL'
experiment = 'EXP'

# a single  channel name or None if there are multiple channels
channel = 'Ch1'
# channel = None

# path to a text file with names for each channel
# channels_list_file = 'channels.txt'
channels_list_file = None

# data_directory _with_ trailing slash
# set to None for render source_type
# <ch> indicates where the program will insert the channel name for paths when iterating over multiple channels
data_directory = "DATA_DIR/<ch>/"
# data_directory = None

# filename without extension (no '.tif')
# set to None for render source_type
# <p:4> indicates the z index of the tif file, with up to N leading zeros (4 in this example)
# <ch> indicates where the program will insert the channel name for file names when iterating over multiple channels (optional)
# can be ignored for 'render' data source
file_name = "FILENAME<ch>-<p:4>"
# file_name = None

# extension name for images, supported image types are PNG and TIFF
# set to None for render source_type
# extension needs to match the full filenames and can be any string (e.g.: ome, tif, png)
file_format = 'tif'
# file_format = None

# increment of filename numbering (always increment in steps of 1 in the boss, typically will be '1')
# set to None for render source_type
z_step = '1'
# z_step = None

# float or int supported
voxel_size = 'XXX YYY ZZZ'

# nanometers/micrometers/millimeters/centimeters
voxel_unit = 'micrometers'

# uint8 or uint16 for image channels, uint64 for annotations
data_type = 'uint16'

# name of the reference channel (in the same experiment) for an annotation channel(s)
# set to None for image data
# Warning: if set to any value other than None, uploaded data will be treated as 'annotation' type
reference_channel = None

# pixel -/+ extent (integers) for images in x (width), y (height) and z (slices)
x_extent = [0, X]
y_extent = [0, Y]
z_extent = [0, Z]

# if any of the extents are negative, they need to be offset to >= 0 for the boss
offset_extents = False

# first inclusive, last _exclusive_ list of sections to ingest for _this_ job (can be negative)
# typically the same as Z "extent"
zrange = [0, Z]

# Number of workers to use
# each worker loads additional 16 image files so watch out for out of memory errors
workers = 4


""" Code to generate the commands """


def gen_comm(zstart, zend):
    cmd = "python " + script + " "
    cmd += ' --datasource ' + source_type
    if source_type != 'render':
        if os.name == 'nt':
            cmd += ' --base_path ' + list2cmdline([data_directory])
            cmd += ' --base_filename ' + list2cmdline([file_name])
        else:
            cmd += ' --base_path ' + shlex.quote(data_directory)
            cmd += ' --base_filename ' + shlex.quote(file_name)
        cmd += ' --extension ' + file_format
        cmd += ' ----x_extent ' + x_extent
        cmd += ' ----y_extent ' + y_extent
        cmd += ' ----z_extent ' + z_extent
        cmd += ' --z_range %d %d ' % (zstart, zend)
        cmd += ' --z_step ' + z_step
        cmd += ' --warn_missing_files'

    if offset_extents:
        cmd += ' --offset_extents'

    if source_type == 's3':
        cmd += " --s3_bucket_name " + s3_bucket_name
        cmd += ' --aws_profile ' + aws_profile

    if source_type == 'render':
        cmd += ' --render_owner ' + render_owner
        cmd += ' --render_project ' + render_project
        cmd += ' --render_stack ' + render_stack
        cmd += ' --render_baseURL ' + render_baseURL
        cmd += ' --render_scale ' + render_scale
        cmd += ' --render_window ' + render_window

    cmd += ' --collection ' + collection
    cmd += ' --experiment ' + experiment
    if channel is not None:
        cmd += ' --channel ' + channel
    else:
        cmd += ' --channels_list_file ' + channels_list_file
    cmd += ' --voxel_size ' + voxel_size
    cmd += ' --voxel_unit ' + voxel_unit
    cmd += ' --datatype ' + data_type
    if reference_channel is not None:
        cmd += ' --source_channel ' + reference_channel
    cmd += ' --boss_config_file ' + boss_config_file

    if slack_token != '' and slack_username != '':
        cmd += ' --slack_token_file ' + slack_token
        cmd += " --slack_usr " + slack_username

    return cmd


range_per_worker = (zrange[1] - zrange[0]) // workers

print("# Range per worker: ", range_per_worker)

if range_per_worker % 16:  # supercuboids are 16 z slices
    range_per_worker = ((range_per_worker // 16) + 1) * 16

print("# Range per worker (rounded up): ", range_per_worker)

# amount of memory per worker
ddim_xy = [x_extent[1] - x_extent[0], y_extent[1] - y_extent[0]]
if data_type == 'uint8':
    mult = 1
elif data_type == 'uint16':
    mult = 2
elif data_type == 'uint64':
    mult = 8
mem_per_w = ddim_xy[0] * ddim_xy[1] * mult * 16 / 1024 / 1024 / 1024
print('# Expected memory usage per worker {:.1f} GB'.format(mem_per_w))

# amount of memory total
mem_tot = mem_per_w * workers
print('# Expected total memory usage: {:.1f} GB'.format(mem_tot))


cmd = gen_comm(zrange[0], zrange[1])
cmd += ' --create_resources '
print('\n' + cmd + '\n')

for worker in range(workers):
    start_z = max((worker * range_per_worker +
                   zrange[0]) // 16 * 16, zrange[0])
    if start_z < zrange[0]:
        start_z = zrange[0]
    if start_z > zrange[1]:
        # No point start a useless thread
        continue

    next_z = ((worker + 1) * range_per_worker + zrange[0]) // 16 * 16
    end_z = min(zrange[1], next_z)

    cmd = gen_comm(start_z, end_z)
    cmd += " &"
    print(cmd + '\n')
