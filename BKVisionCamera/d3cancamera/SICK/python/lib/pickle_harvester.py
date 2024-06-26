# Copyright (c) 2023 SICK AG, Waldkirch
# SPDX-License-Identifier: Unlicense

"""Read/Write harvester buffers into/from pickle files"""

from logging import info, debug
from pickle import dump, load
from time import strftime, localtime


class Writer:
    """Class for storing harvesters buffer into pickle file"""

    def __init__(self, record_name="UNNAMED"):
        print("Writer")
        self.nodes_wl = None
        self.buffer_wl = None
        self.maps_wl = None
        self.record_name = record_name
        self.wl_written = False
        self.file = None

        # TODO(dedekst): How to handle chunk data dynamically?
        #     buffer.module.is_containing_chunk_data()
        #     buffer.module.num_chunks
        #     for n in nodeMap.nodes:
        #         print(n.node.name) # regex for "Chunk...Selector"

    def store(self, buffer, nodeMap):
        """Stores the provided buffer/frame to file"""
        if not self.wl_written:
            self._create_wl()
            self._store_wl()

        for name, source in self.nodes_wl.items():
            try:
                self._dump(buffer, nodeMap, source)
            except:
                # e.g. ExposureTime cannot be read while ExposureAuto is running
                dump("N/A", self.file)

        for name, source in self.buffer_wl.items():
            try:

                self._dump(buffer, nodeMap, source)
            except Exception as err:
                print(source)
                continue
                raise RuntimeError(f"Failed to buffer info {name}") from err

        for component in buffer.payload.components:
            for name, source in self.maps_wl.items():
                try:
                    self._dump(buffer, nodeMap, source, component)
                except Exception as err:
                    raise RuntimeError(f"Failed to component (map) info {name}") from err

    def _create_wl(self):
        """White lists define *what* is stored"""
        # yapf: disable
        self.nodes_wl = {
            "AcquisitionFrameRate": 'nodeMap.AcquisitionFrameRate.value',
            "ExposureTime": 'nodeMap.ExposureTime.value',
            "ExposureAuto": 'nodeMap.ExposureAuto.value',
            "ExposureAutoFrameRateMin": 'nodeMap.ExposureAutoFrameRateMin.value',
            "FieldOfView": 'nodeMap.FieldOfView.value',
            "MultiSlopeMode": 'nodeMap.MultiSlopeMode.value',
            "DataFilterEnable": 'nodeMap.Scan3dDataFilterEnable.value',
            "DepthValidationFilterLevel": 'nodeMap.Scan3dDataFilterSelector.value=\'ValidationFilter\';nodeMap.Scan3dDepthValidationFilterLevel.value',
        }
        self.buffer_wl = {
            'frame_id': 'buffer.module.frame_id',
            'timestamp_ns': 'buffer.timestamp_ns',
            'numComponents': 'len(buffer.payload.components)',
            'FocalLength': 'nodeMap.ChunkScan3dFocalLength.value',
            'AspectRatio': 'nodeMap.ChunkScan3dAspectRatio.value',
            'PrincipalPointU': 'nodeMap.ChunkScan3dPrincipalPointU.value',
            'PrincipalPointV': 'nodeMap.ChunkScan3dPrincipalPointV.value',
            # select CoordinateA
            'CoordinateScaleA': 'nodeMap.ChunkScan3dCoordinateSelector.value=\'CoordinateA\';nodeMap.ChunkScan3dCoordinateScale.value',
            'CoordinateOffsetA': 'nodeMap.ChunkScan3dCoordinateOffset.value',
            # select CoordinateB
            'CoordinateScaleB': 'nodeMap.ChunkScan3dCoordinateSelector.value=\'CoordinateB\';nodeMap.ChunkScan3dCoordinateScale.value',
            'CoordinateOffsetB': 'nodeMap.ChunkScan3dCoordinateOffset.value',
            # select CoordinateC
            'CoordinateScaleC': 'nodeMap.ChunkScan3dCoordinateSelector.value=\'CoordinateC\';nodeMap.ChunkScan3dCoordinateScale.value',
            'CoordinateOffsetC': 'nodeMap.ChunkScan3dCoordinateOffset.value',
        }
        self.maps_wl = {
            'data_format': 'c.data_format',
            'width': 'c.width',
            'height': 'c.height',
            'delivered_image_height': 'c.delivered_image_height',
            'data': 'c.data',  # data is numpy array
        }
        # yapf: enable

    def _store_wl(self):
        if self.wl_written:
            raise RuntimeError(
                "The white lists contract must be written once at beginning of the pickle recording"
            )
        filename = strftime("%Y-%m-%d_%H-%M-%S_", localtime()) + self.record_name + ".pickle"
        info(f"Open file for reading: {filename}")

        self.file = open(filename, 'wb')
        # store the WhiteList contracts
        dump(self.nodes_wl, self.file)
        dump(self.buffer_wl, self.file)
        dump(self.maps_wl, self.file)
        self.wl_written = True

    def _dump(self, buffer, nodeMap, sources, c=None):
        src_list = sources.split(';')
        for source in src_list[:-1]:
            exec(source)
        exec(f"dump({src_list[-1]}, self.file)")

    def __del__(self):
        if self.file:
            self.file.close()


class Reader:
    """Class for reading harvesters buffer from pickle file"""

    def __init__(self, filename):
        info(f"Open file for reading: {filename}")
        self.file = open(filename, 'rb')
        # restore the WhiteList contracts
        self.nodes_wl, self.buffer_wl, self.maps_wl = self._load_wl()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.file.close()

    def __len__(self):
        return self._get_number_of_frames()

    def __iter__(self):
        self._rewind_to_start_of_frames()
        return self

    def __next__(self):
        frame = self._restore()
        if frame:
            return frame
        else:
            self._rewind_to_start_of_frames()
            raise StopIteration

    def __del__(self):
        self.file.close()

    def get_next_frame(self):
        """Restores and returns the next frame from file. Alias for restore()"""
        return self._restore()

    def get_all_frames(self):
        """Load all available frames from file.
        Returns a list of all frames which could be read.
        Will rewind to beginning of the file in the end.
        """
        frames = list()
        while self.file.read(1):
            self.file.seek(-1, 1)
            frames.append(self.get_next_frame())
        self._rewind_to_start_of_frames()
        return frames

    def get_frames(self, skip, n=0):
        """Load n frames after skip frames were skipped"""
        if n == 0:
            n = self._get_number_of_frames()

        self._rewind_to_start_of_frames()
        self._skip_frames(skip)
        frames = list()
        while self.file.read(1) and len(frames) < n:
            self.file.seek(-1, 1)
            frames.append(self.get_next_frame())
        return frames

    def _get_number_of_frames(self):
        num_frames = sum(1 for _ in iter(self.get_next_frame, None))
        self._rewind_to_start_of_frames()
        return num_frames

    def _restore(self):
        """Restores and returns the next frame from file"""

        # Check EOF condition
        if not self.file.read(1):
            return None
        self.file.seek(-1, 1)

        frame = {}
        for node_name in self.nodes_wl:
            frame.update({node_name: load(self.file)})

        for buf_info in self.buffer_wl:
            try:
                frame.update({buf_info: load(self.file)})
            except:
                continue
        maps = list()
        print(frame)
        frame['numComponents'] = 1
        for i in range(frame['numComponents']):
            tmp = {}
            for mapInfo in self.maps_wl:

                try:
                    tmp.update({mapInfo: load(self.file)})
                except:
                    continue
            maps.append(tmp)
        frame.update({'maps': maps})
        return frame

    def debug_frame(self, frame):
        """Print all helpful information contained in the given frame"""
        info("##################################")
        info("######## Frame Debug Info ########")
        info("##################################")
        for k, v in frame.items():
            if k != 'maps':
                info("# {}: {}".format(k, v))
        info("# Contained maps:")
        for m in frame['maps']:
            info("#   Format {}, {}x{}({}), {}bpp, total items:{}".format(
                m['data_format'], m['width'], m['height'], m['delivered_image_height'],
                m['data'].itemsize, m['data'].size))
        info("##################################")

    def _skip_frames(self, num):
        for i in range(num):
            _ = self.get_next_frame()

    def _rewind_to_start_of_frames(self):
        self.file.seek(0)
        _ = self._load_wl()

    def _load_wl(self):
        # load the WhiteList contracts, from beginning of file
        if self.file.tell() != 0:
            raise RuntimeError(
                "Loading WL are only expected to be read from beginning of file, but file pos is: {}"
                .format(self.file.tell(0)))
        nodes_wl = load(self.file)
        buffer_wl = load(self.file)
        maps_wl = load(self.file)
        return nodes_wl, buffer_wl, maps_wl
