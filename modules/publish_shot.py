#!/usr/bin/env python
# -*- coding:utf-8
# ============================================================================
# Copyright (C) 2022 SAutom8 Consultancy Services. All Rights Reserved.
# The coded instructions, statements, computer programs, and/or related
# material (collectively the "Data") in these files contain unpublished
# information proprietary to Autom8 Consultancy Services, which is protected by Indian
# copyright law.
#
# Author : autom8.helpdesk@gmail.com (Swapnil Soni)
# Module : publish_shot.py
# ============================================================================
"""

"""

# # built-in imports

# # autom8 imports
import os
import re
from pprint import pprint
from au_core.UniQt import QtCore
from au_shotgun import au_sg_project, au_sg_sequence, au_sg_shot, au_sg_task, au_sg_version
from au_utils import au_fileutils


class Autom8PublishShots(QtCore.QThread):

    createDirStart = QtCore.Signal(str)
    hardlinkStart = QtCore.Signal(str)
    hardlinkProgress = QtCore.Signal(str)
    hardLinkFinish = QtCore.Signal(list)
    shotgunUpdateFinish = QtCore.Signal(list)
    publishProcessFinish = QtCore.Signal(str)
    """
    @param createDirStart: Signal emitted before folder creation is started for a shot.
    @type createDirStart: class:`PySide.QtCore.Signal`
    @param hardLinkStart: Signal emitted before hard-linking is started for a shot.
    @type hardlinkStart: class:`PySide.QtCore.Signal`
    @param hardLinkFinish: Signal emitted after hard-linking is finished for a shot.
    @type hardLinkFinish: class:`PySide.QtCore.Signal`
    @param shotgunUpdateFinish: Signal emitted after Shotgun update finished.
    @type shotgunUpdateFinish: class:`PySide.QtCore.Signal`

    """

    def __init__(self, sg_instance, logger, data, parent=None):
        """

        @param sg_instance:
        @param data:
        @param parent:
        """
        super(Autom8PublishShots, self).__init__(parent)
        self.Log = logger
        self.SG = sg_instance
        self.Show = self.Seq = self.Shot = self.Task = None
        self.Data = data

    def run(self, *args, **kwargs):
        """Override for default class:`QThread.run()` method.
        """
        if self.Data:
            ind = 0
            for item in self.Data:
                self.Show = self.Seq = self.Shot = self.Task = None
                self.Show = self.get_project(item["show_code"])
                if self.Show:
                    # print("[SHOW]: {}".format(self.Show))
                    self.Seq = self.get_sequence(item["show_code"], item["seq"])
                    if self.Seq:
                        # print("[SEQ]: {}".format(self.Seq))
                        seq_path = self.check_seq_dir_exists()
                        self.createDirStart.emit(item["shot"])
                        shot_path = self.create_shot_dirs(item["shot"], seq_path)
                        if shot_path:
                            self.hardlinkStart.emit(item["shot"])
                            # print("[SCAN PATH]: {}".format(item["scan_path"]))
                            if str(item["scan_path"]).strip() is not "" and os.path.exists(str(item["scan_path"])):
                                res_bln, res_col, res_data = self.hard_link_scans(shot_path, item)
                                # # Hard-link finished properly.
                                if res_bln:
                                    self.hardLinkFinish.emit([ind, res_bln, res_col, item["shot"]])
                                    if not self.get_shot(item["shot"]):
                                        self.Shot = self.add_shot_to_shotgun(item)
                                        if self.Shot:
                                            print("[SHOT]: {}".format(self.Shot))
                                            self.Task = self.add_scan_task_to_shotgun()
                                            if self.Task:
                                                print("[TASK]: {}".format(self.Task))
                                                ver = self.add_version_to_shotgun(item, res_data)
                                                if ver:
                                                    print("[Version]: {}".format(ver))
                                                    self.shotgunUpdateFinish.emit([ind, True, self.Show, self.Seq,
                                                                                   self.Shot, self.Task, ver])
                                                else:
                                                    self.shotgunUpdateFinish.emit([ind, False,
                                                                                   "Issue creating version."])
                                            else:
                                                self.shotgunUpdateFinish.emit([ind, False, "Issue creating task"])
                                        else:
                                            self.shotgunUpdateFinish.emit([ind, False, "Issue creating shot"])
                                else:
                                    self.hardLinkFinish.emit([ind, res_bln, res_col, res_data])
                            else:
                                self.hardLinkFinish.emit([ind, False, "#e6c740", item["shot_code"]])
                                print("[SHOT W/O SCANS]: {}".format(item["shot"]))
                ind += 1
            self.publishProcessFinish.emit("Success")

    def get_project(self, show_code):
        res_bool, res_msg, res_data = au_sg_project.get_project_by_code(self.SG, show_code,
                                                                        ["sg_linux_path", "sg_schema"])
        if res_bool:
            return res_data
        else:
            return {}

    def get_sequence(self, show_code, seq_name):
        res_bool, res_msg, res_data = au_sg_sequence.get_sequence(self.SG, show_code, seq_name)
        if res_bool:
            return res_data
        else:
            return {}

    def get_shot(self, shot_code):
        res_bin, res_msg, res_data = au_sg_shot.get_shot_by_code(self.SG, self.Show["id"], self.Seq["id"], shot_code)
        return res_bin

    def add_shot_to_shotgun(self, item_dict):
        shot_data = {
            "code": item_dict["shot"],
            "project": self.Show,
            "sg_sequence": self.Seq,
            "sg_start_frame": item_dict["start"],
            "sg_end_frame": item_dict["end"],
            "sg_client_name": item_dict["client_name"],
            "sg_client_start": item_dict["client_start"],
            "sg_client_end": item_dict["client_end"]
        }

        res_bln, res_msg, res_data = au_sg_shot.create_shot(self.SG, shot_data)
        if res_bln:
            return {'type': 'Shot', 'id': res_data["id"], 'code': res_data["code"]}
        else:
            return {}

    def add_scan_task_to_shotgun(self):
        tasks_dict = {'20': 'Tracking|133|Tracking', '30': 'Roto|134|Roto', '40': 'Prep|142|Paint',
                      '50': 'Layout|35|Layout', '60': 'Animation|106|Animation', '70': 'Hair|175|CFX and Folliage',
                      '80': 'Cloth|175|CFX and Folliage', '90': 'FX|6|FX', '100': 'Lighting|7|Light',
                      '110': 'Comp|8|Comp'}
        task_data = {
            'content': 'Plate Online',
            'step': {'type': 'Step', 'id': 2, 'name': 'Online'},
            'project': self.Show,
            'entity': self.Shot,
            'sg_sort_order': 10,
            'sg_status_list': 'act'
        }
        res_bln, res_msg, res_data = au_sg_task.create_task(self.SG, task_data)

        for each in tasks_dict.keys():
            step = str(tasks_dict[each]).split("|")  # content|step-id|step-name
            t_data = {'content': str(step[0]), 'step': {'type': 'Step', 'id': int(step[1]), 'name': step[2]},
                      'project': self.Show, 'entity': self.Shot, 'sg_sort_order': int(each), 'sg_status_list': 'wtg'}
            bln, msg, data = au_sg_task.create_task(self.SG, t_data)

        if res_bln:
            return {'type': 'Task', 'id': res_data["id"], 'step': res_data["step"]}
        else:
            return {}

    def add_version_to_shotgun(self, item_dict, scan_dict):
        layer = scan_dict[0]
        version = scan_dict[1]
        scan_dir = os.path.dirname(scan_dict[-1])
        # print("[LAYER]: {}\n[VERSION]: {}\n[SCAN PATH]: {}".format(layer, version, scan_dict[-1]))
        img_split = str(os.path.split(scan_dict[-1])[-1]).split(".")
        img_name = "{}.%0{}d.{}".format(img_split[0], len(img_split[1]), img_split[-1])
        frm_path = os.path.join(scan_dir, img_name)
        mov_path = os.path.join(scan_dir.replace("/linear/", "/mov/"), "{}.mov".format(img_split[0]))
        # print("[FRM PATH]: {}\n[MOV PATH]: {}".format(frm_path, mov_path))
        ver_dict = {
            'project': {'type': 'Project', 'id': self.Show["id"]},
            'entity': self.Shot,
            'sg_task': self.Task,
            'code': "{}_{}_{}".format(img_split[0], layer, version),
            'sg_first_frame': int(item_dict["start"]),
            'sg_last_frame': int(item_dict["end"]),
            'frame_count': int(item_dict["end"]) - int(item_dict["start"]) + 1,
            'sg_layer': layer,
            'sg_scan_version': version,
            'sg_path_to_frames': frm_path,
            'sg_path_to_movie': mov_path
        }
        # print("[VER DICT]:")
        # pprint(ver_dict)
        res_bln, res_msg, res_data = au_sg_version.create_version(self.SG, ver_dict)
        if res_bln:
            return {'type': 'Version', 'id': res_data["id"], 'code': res_data["code"]}
        else:
            return {}

    def check_seq_dir_exists(self):
        seq_path = os.path.join(self.Show["sg_linux_path"], self.Show["sg_schema"], self.Seq["code"])
        # print("[SEQ PATH]: {}".format(seq_path))
        if not os.path.exists(seq_path):
            try:
                os.system("mkdir {}".format(seq_path))
                os.system("chown autom8 {sq}/\nchgrp it {sq}/".format(sq=seq_path))
            except OSError as err:
                print("[ERROR]: {}".format(err))
        return seq_path

    def create_shot_dirs(self, shot_code, seq_path):
        src_path = "/tech/library/pipeline/after/config/templates/SHOT/"
        # print("[SHOT CODE]: {}\n[SEQ PATH]: {}".format(shot_code, seq_path))
        shot_path = os.path.join(seq_path, shot_code)
        if not os.path.exists(shot_path):
            cmd = "cp -rp --preserve {0} {1}".format(src_path, shot_path)
            try:
                os.system(cmd)
                return shot_path
            except OSError as err:
                print("[ERROR]: {}".format(err))
                return False
        else:
            return shot_path

    def get_hardlink_path(self, src_path, shot_path):
        dst_path = None
        # # Check for Layer 2 SCans
        layer = "l1"
        version = "v001"
        if re.findall("_L2", src_path) or re.findall("_L02", src_path):
            layer = "l2"
            if re.findall("V2", src_path) or re.findall("V02", src_path) or re.findall("V002", src_path):
                version = "v002"
                dst_path = os.path.join(shot_path, "sources/scan/l2/linear/v002")
            elif re.findall("V1", src_path) or re.findall("V01", src_path) or re.findall("V001", src_path):
                dst_path = os.path.join(shot_path, "sources/scan/l2/linear/v001")
            else:
                dst_path = os.path.join(shot_path, "sources/scan/l2/linear/v001")
        # # Check for Layer 1 Scans
        elif re.findall("_L1", src_path) or re.findall("_L01", src_path):
            if re.findall("V2", src_path) or re.findall("V02", src_path) or re.findall("V002", src_path):
                version = "v002"
                dst_path = os.path.join(shot_path, "sources/scan/l1/linear/v002")
            elif re.findall("V1", src_path) or re.findall("V01", src_path) or re.findall("V001", src_path):
                dst_path = os.path.join(shot_path, "sources/scan/l1/linear/v001")
            else:
                dst_path = os.path.join(shot_path, "sources/scan/l1/linear/v001")
        else:
            if re.findall("V2", src_path) or re.findall("V02", src_path) or re.findall("V002", src_path):
                version = "v002"
                dst_path = os.path.join(shot_path, "sources/scan/l1/linear/v002")
            elif re.findall("V1", src_path) or re.findall("V01", src_path) or re.findall("V001", src_path):
                dst_path = os.path.join(shot_path, "sources/scan/l1/linear/v001")
            else:
                dst_path = os.path.join(shot_path, "sources/scan/l1/linear/v001")
        return layer, version, dst_path

    def hard_link_scans(self, shot_path, data_dict):
        layer, version, dst_path = self.get_hardlink_path(data_dict["scan_path"], shot_path)
        # print("[DST_PATH]: {}".format(dst_path))
        if not os.path.exists(dst_path):
            os.makedirs(dst_path)
            cmd = "chown -R render {dp}\n chgrp -R prod {dp}".format(dp=dst_path)
            os.system(cmd)

        frm = int(data_dict["start"])
        img_list = [img for img in sorted(os.listdir(data_dict["scan_path"])) if str(img).split(".")[-1] in ("exr",
                                                                                                             "dpx")]
        count = 0
        failed_links = []
        dst_file = None
        for img in img_list:
            src_file = os.path.join(data_dict["scan_path"], img)
            new_img = ".".join([data_dict["shot"], str(frm), str(img).split(".")[-1]])
            dst_file = os.path.join(dst_path, new_img)
            # print("[SRC FILE]: {}\n[DST FILE]: {}".format(src_file, dst_file))
            # # Hard-link Image if not exists...
            if not os.path.exists(dst_file):
                try:
                    os.link(src_file, dst_file)
                    count += 1
                    self.hardlinkProgress.emit("1|Hard-linked: {} --> {}".format(src_file, dst_file))
                except OSError as err:
                    print("3|Error Hard-linking: ({})\n{}".format(new_img, err))
                    failed_links.append(img)
            else:
                msg = "1|frame ({}) already exists ! Skipping...".format(new_img)
                self.hardlinkProgress.emit(msg)
            frm += 1
        if count == len(img_list):
            return True, "#7CFC00", [layer, version, dst_file]
        else:
            return False, "#CD5C5C", failed_links


