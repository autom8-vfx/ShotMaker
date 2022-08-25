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
# Module : ShotMaker.py
# ============================================================================
"""

"""

# built-in imports
import os
import sys
import csv
from pprint import pprint

# Sniper imports
from ui import *
from modules import *
from au_utils import au_config
from au_shotgun import au_sg_connect
from au_core.UniQt import QtCore, QtGui, QtWidgets, QtCompat
from au_utils import au_logger, au_sysutils

TOOL_NAME = os.path.basename(__file__)
CSV_FIELDS = ["Project", "Sequence", "Shot Code", "Client Code", "Start Frame", "End Frame", "Client Start",
              "Client End", "Scan Path"]


class ShotMaker(QtWidgets.QWidget):
    """ShotMaker tool description.

    """

    def __init__(self, parent=None):
        super(ShotMaker, self).__init__(parent)
        self.ParentDir = os.path.dirname(__file__)
        self.Log = None
        __ui_file_path = os.path.join(self.ParentDir, "ui", "autom8_shot_maker.ui")
        QtCompat.loadUi(__ui_file_path, self)
        self.CommonConfig = au_config.load(["common", "settings.yml"])
        self.SG = au_sg_connect.Shotgun(p_create_scan_bln=True).get_shotgun()
        self.traverse = None
        self.worker = None
        self.CreateDirs = False
        self.ImgLib = {"autom8_white.png": self.lbl_logo, "insert.png": self.btn_upload,
                       "download.png": self.btn_download, "bugs.png": self.btn_bug, "question.png": self.btn_help, }
        self.init_ui()

    def init_ui(self):
        self.lbl_version.setText("Ver: [{}]".format(version))
        self.lbl_prog.setText("")
        self.prog_bar.setVisible(False)
        self.lbl_prog.setVisible(False)
        for key in self.ImgLib.keys():
            self.set_images_and_icons(self.ImgLib[key], key)
        self.btn_upload.clicked.connect(self.btn_upload_clicked)
        self.btn_download.clicked.connect(self.btn_download_clicked)
        self.btn_create.clicked.connect(self.btn_create_clicked)
        self.btn_bug.clicked.connect(self.btn_bug_clicked)
        self.btn_help.clicked.connect(self.btn_help_clicked)

    def set_images_and_icons(self, widget, image):
        # print(widget.__class__.__name__)
        img_path = os.path.join(self.ParentDir, "icons", image)
        pixmap = QtGui.QPixmap.fromImage(img_path)
        if isinstance(widget, QtWidgets.QLabel):
            widget.setPixmap(pixmap)
        elif isinstance(widget, QtWidgets.QPushButton):
            widget.setIcon(pixmap)

    def start_logging(self):
        self.Log = au_logger.create("ShotMaker")
        d_now, t_now = au_sysutils.get_time_stamp(True)
        timestamp = "{}, {}".format(d_now, t_now)
        details = au_sysutils.get_system_details()
        info_str = "TOOL NAME".ljust(20) + ": {}\n".format(TOOL_NAME)
        info_str += "USER".ljust(20) + ": {}\n".format(details[2])
        info_str += "EXECUTED FROM".ljust(20) + ": {}\n".format(details[1])
        info_str += "MACHINE NAME".ljust(20) + ": {}\n".format(details[0])
        info_str += "OPERATING SYSTEM".ljust(20) + ": {}\n".format(details[3])
        info_str += "TIME-STAMP".ljust(20) + ": {}\n".format(timestamp)
        self.Log.info("\n\n{dec}\n[ * LOG BASICS * ]\n{inf}{dec}\n".format(dec="*" * 50, inf=info_str))
        self.Log.info("I am in ShotMaker [Ver: {:s}] tool".format(version))

    def read_csv_data(self, csv_path=None):
        info_list = []
        self.lbl_prog.setText("")
        self.prog_bar.setVisible(False)

        with open(csv_path, "r") as infile:
            reader = csv.reader(infile)
            header_flag = True
            for row in reader:
                # print(row)
                info_dict = {}
                for i in range(0, len(row)):
                    if header_flag:
                        if row[i].strip() != CSV_FIELDS[i]:
                            return False, "[ERROR]: CSV not as per defined template {} != {}".format(
                                row[i].strip(), CSV_FIELDS[i]), {}
                    else:
                        info_dict[CSV_FIELDS[i]] = row[i].strip()
                header_flag = False
                info_list.append(info_dict)
        info_list.pop(0)  # Removing Headers
        # pprint(info_list, indent=4)
        self.prog_bar.setMaximum(len(info_list))
        self.prog_bar.setValue(0)
        self.prog_bar.setVisible(True)
        self.lbl_prog.setVisible(True)
        return True, "Success", info_list

    def pass_data_to_publish_thread(self):
        items_list = []
        # Read data from UI:
        for ind in range(self.lst_shots.count()):
            item = self.lst_shots.item(ind)
            wid = self.lst_shots.itemWidget(item)
            item_dict = {"show_code": wid.lbl_show.text(), "seq": wid.lbl_seq.text(), "shot": wid.lbl_shot.text(),
                         "client_name": wid.lbl_client.text(), "start": wid.lbl_start.text(), "end": wid.lbl_end.text(),
                         "client_start": wid.lbl_cs.text(), "client_end": wid.lbl_ce.text(),
                         "scan_path": str(wid.accessibleName())}
            # pprint(item_dict, indent=4)
            items_list.append(item_dict)
        self.prog_bar.setValue(0)
        self.worker = publish_shot.Autom8PublishShots(self.SG, self.Log, items_list)
        self.worker.createDirStart.connect(self.create_dirs_started)
        self.worker.hardlinkStart.connect(self.hard_linking_started)
        self.worker.hardlinkProgress.connect(self.hard_linking_progress)
        self.worker.hardLinkFinish.connect(self.hard_linking_finished)
        self.worker.shotgunUpdateFinish.connect(self.shotgun_update_finished)
        self.worker.publishProcessFinish.connect(self.publish_process_finished)
        self.worker.start()

    def generate_list_item(self, data=None):
        """Updates signal emitted by CreateListItem thread. This signal was emitted after each list item generation.
        Updates the population of shots using CustomShotWidget, coming from the list generation thread.

        :param data: list of data needed to create a custom list widget.
        [0: Project, 1: Sequence , 2: Shot Code, 3: Client Code, 4: Start Frame, 5: End Frame, 6: Client Start,
        7: Client End, 8: Scan Path]
        :type data: list
        """
        val = self.prog_bar.value() + 1
        wid = CustomShotWidget(data)
        item = QtWidgets.QListWidgetItem()
        item.setSizeHint(QtCore.QSize(200, 36))
        item.setSelected(True)
        # # test block
        # if val == 2:
        #     pixmap = QtGui.QPixmap.fromImage(os.path.join(self.ParentDir, "icons", "folder.png"))
        #     wid.lbl_icon.setPixmap(pixmap.scaled(32, 32, QtCore.Qt.KeepAspectRatio))

        self.lst_shots.addItem(item)
        self.lst_shots.setItemWidget(item, wid)
        self.prog_bar.setValue(val)

    def generate_item_finished(self):
        self.lbl_prog.setText("CSV loaded successfully...")
        self.btn_create.setEnabled(True)
        self.lst_shots.setFocus()

    def create_dirs_started(self, shot_code):
        self.lbl_prog.setText("Creating Directories for Shot: [{}]".format(shot_code))
        self.Log.info("Creating Directories for Shot: [{}]".format(shot_code))

    def hard_linking_started(self, shot_code):
        self.lbl_prog.setText("Hard-linking Scans for Shot: [{}]".format(shot_code))
        self.Log.info("Hard-linking Scans for Shot: [{}]".format(shot_code))

    def hard_linking_progress(self, message):
        msg_split = str(message).split("|")
        if msg_split[0] == "1":
            self.Log.info(msg_split[-1])
        elif msg_split[0] == "2":
            self.Log.warning(msg_split[-1])
        elif msg_split[0] == "3":
            self.Log.error(msg_split[-1])
        elif msg_split[0] == "4":
            self.Log.exception(msg_split[-1])

    def hard_linking_finished(self, data_list):
        if data_list[1]:
            self.lbl_prog.setText("Updating Shotgun for shot [{}]".format(data_list[-1]))
            self.Log.info("Updating Shotgun for shot [{}]".format(data_list[-1]))
        else:
            item = self.lst_shots.item(data_list[0])
            wid = self.lst_shots.itemWidget(item)
            if data_list[2] == "#CD5C5C":
                wid.setStyleSheet("color: #111; background-color: #CD5C5C;")
                wid.setToolTip("[Alert]: Issue with hard-linking. Check log for details")
            elif data_list[2] == "#e6c740":
                wid.setStyleSheet("color: #111; background-color: #e6c740;")
                wid.setToolTip("[Alert]: No scans available to publish")

            self.prog_bar.setValue(data_list[0] + 1)

    def shotgun_update_finished(self, proc_list):
        count = int(proc_list[0])
        item = self.lst_shots.item(proc_list[0])
        wid = self.lst_shots.itemWidget(item)
        if proc_list[1]:
            msg = "Shotgun updated successfully the details are as follows:\n"
            msg += "[SHOW]    : {}\n".format(proc_list[2])
            msg += "[SEQUENCE]: {}\n".format(proc_list[3])
            msg += "[SHOT]    : {}\n".format(proc_list[4])
            msg += "[TASK]    : {}\n".format(proc_list[5])
            msg += "[VERSION] : {}\n".format(proc_list[6])
            self.Log.info(msg)
            wid.setStyleSheet("color: #111; background-color: #7CFC00;")
            wid.setToolTip("Successfully published")
        else:
            wid.setStyleSheet("color: #111; background-color: #CD5C5C;")
            wid.setToolTip("[Alert]: Issue publishing Check log for details")
        self.prog_bar.setValue(count + 1)

    def publish_process_finished(self, msg):
        msg_box = QtWidgets.QMessageBox()
        msg_box.setWindowTitle("Bingo !")
        msg_box.setText("Shot Publish process completed successfully")
        msg_box.setIcon(QtWidgets.QMessageBox.Information)
        ret_val = msg_box.exec_()
        if ret_val:
            self.btn_create.setEnabled(False)

    def btn_upload_clicked(self):
        dialog = QtWidgets.QFileDialog()
        dialog.setWindowTitle("Open CSV")
        dialog.setNameFilter("CSV Files(*.csv *.CSV)")
        if dialog.exec_():
            self.lst_shots.clear()
            sel_path = str(dialog.selectedFiles()[0])
            res, msg, data = self.read_csv_data(sel_path)
            if not res:
                print(msg)
            else:
                self.traverse = Autom8ListItem(data=data)
                self.traverse.listItemUpdateProgress.connect(self.generate_list_item)
                self.traverse.csvReadFinished.connect(self.generate_item_finished)
                self.traverse.start()

    def btn_download_clicked(self):
        dn_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory")
        if dn_path:
            template = os.path.join(dn_path, "shots_template.csv")
            with open(template, "w") as dn_file:
                dn_file.write(", ".join(CSV_FIELDS))
            msg_box = QtWidgets.QMessageBox()
            msg_box.setWindowTitle("Bingo !")
            msg_box.setText("`shots_template.csv` downloaded on selected location !\nPlease check...")
            msg_box.setIcon(QtWidgets.QMessageBox.Information)
            msg_box.exec_()

    def btn_create_clicked(self):
        """Starts execution of Publishing shots and EXRs (if any), and publish shots to shotgun.

        """
        msg_box = QtWidgets.QMessageBox()
        msg_box.setWindowTitle("Alert !")
        msg_box.setText("Do you want to publish everything loaded ?")
        msg_box.setIcon(QtWidgets.QMessageBox.Question)
        msg_box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        ret_val = msg_box.exec_()
        if ret_val == 16384:
            self.start_logging()
            self.pass_data_to_publish_thread()

    def btn_bug_clicked(self):
        pass

    def btn_help_clicked(self):
        pass


class Autom8ListItem(QtCore.QThread):
    """Another custom Class derived from :class:`PySide.QtCore.QThread`, that processes the data required to create a
        list item. This class basically reads all the related information, e.g. shot-names, frame range, other parameters,
        etc. from the selected directory structure, processes it, and returns in a way that, this information is used to
        create new list item.

        :param listItemUpdateProgress: Signal emitted to update the UI with data to generate list item and update the progress bar.
        :type listItemUpdateProgress: class:`PySide.QtCore.Signal`
        :param csvReadFinished: Signal emitted after finishing the overall process. Returns the count of valid shots.
        :type csvReadFinished: class:`PySide.QtCore.Signal`
        :param sel_path: selected path from which we want to publish the footage(s).
        :type sel_path: str

        """
    # This is the signal that will be emitted during the processing.
    # By including int as an argument, it lets the signal know to expect an integer argument when emitting.
    listItemUpdateProgress = QtCore.Signal(list)
    csvReadFinished = QtCore.Signal(int)

    def __init__(self, project_base=None, data=None):
        """Constructor method

        """
        QtCore.QThread.__init__(self)
        self.data = data
        self.base_path = "/mnt/hq/projects"

    def run(self):
        """Override for default class:`QThread.run()` method.

        """
        self.generate_items_from_data()

    def generate_items_from_data(self):
        exception_list = ('.DS_Store', '.AppleDouble', 'Thumbs.db')
        count = 0
        for row in self.data:
            # print row
            proj, seq, shot = row["Project"], row["Sequence"], row["Shot Code"]
            # Validate shot code.
            shot = shot if len(shot.split("_")) == 3 else "_".join(shot.split("_")[:3])
            client_code = row["Client Code"]
            start, end, c_start, c_end = row["Start Frame"], row["End Frame"], row["Client Start"], row["Client End"]
            scan_path = row["Scan Path"]
            data = [proj, seq, shot, client_code, start, end, c_start, c_end, scan_path]
            self.listItemUpdateProgress.emit(data)
            count += 1
        self.csvReadFinished.emit(count)


class CustomShotWidget(QtWidgets.QWidget):
    """Class derived from :class:`PySide.QtGui.QWidget` which is a custom widget representing the custom list item.

    :param data: List having information to fill the custom list item created.
    :type data: list

    """

    def __init__(self, data=None):
        """Constructor method.

        """
        super(CustomShotWidget, self).__init__()
        self.ParentDir = os.path.dirname(__file__)
        self.setStyleSheet("QLabel{\ncolor: #ffffff;\nbackground-color: transparent;\n}")
        self.main_lay = QtWidgets.QHBoxLayout(self)
        self.main_lay.setContentsMargins(3, 3, 3, 3)
        # self.main_lay.setSpacing(2)
        self.lbl_spacer01 = QtWidgets.QLabel(self)
        self.lbl_spacer01.setMaximumSize(QtCore.QSize(5, 32))
        self.lbl_spacer01.setMinimumSize(QtCore.QSize(5, 32))
        self.main_lay.addWidget(self.lbl_spacer01)

        self.lbl_icon = QtWidgets.QLabel(self)
        self.lbl_icon.setMaximumSize(QtCore.QSize(32, 32))
        self.lbl_icon.setMinimumSize(QtCore.QSize(32, 32))
        self.main_lay.addWidget(self.lbl_icon)

        self.lbl_spacer02 = QtWidgets.QLabel(self)
        self.lbl_spacer02.setMaximumSize(QtCore.QSize(5, 32))
        self.lbl_spacer02.setMinimumSize(QtCore.QSize(5, 32))
        self.main_lay.addWidget(self.lbl_spacer02)

        self.lbl_show = QtWidgets.QLabel(self)
        self.lbl_show.setMaximumSize(QtCore.QSize(55, 32))
        self.lbl_show.setMinimumSize(QtCore.QSize(55, 32))
        self.main_lay.addWidget(self.lbl_show)

        self.lbl_seq = QtWidgets.QLabel(self)
        self.lbl_seq.setMaximumSize(QtCore.QSize(75, 32))
        self.lbl_seq.setMinimumSize(QtCore.QSize(75, 32))
        self.main_lay.addWidget(self.lbl_seq)

        self.lbl_shot = QtWidgets.QLabel(self)
        self.lbl_shot.setMaximumSize(QtCore.QSize(160, 32))
        self.lbl_shot.setMinimumSize(QtCore.QSize(160, 32))
        self.main_lay.addWidget(self.lbl_shot)

        self.lbl_client = QtWidgets.QLabel(self)
        self.lbl_client.setMaximumSize(QtCore.QSize(120, 32))
        self.lbl_client.setMinimumSize(QtCore.QSize(120, 32))
        self.main_lay.addWidget(self.lbl_client)

        self.lbl_start = QtWidgets.QLabel(self)
        self.lbl_start.setMaximumSize(QtCore.QSize(80, 32))
        self.lbl_start.setMinimumSize(QtCore.QSize(80, 32))
        self.main_lay.addWidget(self.lbl_start)

        self.lbl_end = QtWidgets.QLabel(self)
        self.lbl_end.setMaximumSize(QtCore.QSize(80, 32))
        self.lbl_end.setMinimumSize(QtCore.QSize(80, 32))
        self.main_lay.addWidget(self.lbl_end)

        self.lbl_cs = QtWidgets.QLabel(self)
        self.lbl_cs.setMaximumSize(QtCore.QSize(90, 32))
        self.lbl_cs.setMinimumSize(QtCore.QSize(90, 32))
        self.main_lay.addWidget(self.lbl_cs)

        self.lbl_ce = QtWidgets.QLabel(self)
        self.lbl_ce.setMaximumSize(QtCore.QSize(90, 32))
        self.lbl_ce.setMinimumSize(QtCore.QSize(90, 32))
        self.main_lay.addWidget(self.lbl_ce)
        self.load_shot_info(data)

    def load_shot_info(self, data=None):
        """Loads all the shot related information to itself and form a custom list item.
        :param data: List of shot related information.
        :type data: list [0: Project, 1: Sequence , 2: Shot Code, 3: Client Code, 4: Start Frame, 5: End Frame,
        6: Client Start, 7: Client End, 8: Scan Path]
        :return:
        """
        if data:
            if str(data[8]).strip() is not "":
                icon_path = os.path.join(self.ParentDir, "icons", "images.png")
                self.setAccessibleName(str(data[8]))
            else:
                icon_path = os.path.join(self.ParentDir, "icons", "folder.png")
            pixmap = QtGui.QPixmap.fromImage(icon_path)
            self.lbl_icon.setPixmap(pixmap.scaled(32, 32, QtCore.Qt.KeepAspectRatio))
            self.lbl_show.setText(str(data[0]))
            self.lbl_seq.setText(str(data[1]))
            self.lbl_shot.setText(str(data[2]))
            self.lbl_client.setText(str(data[3]))
            self.lbl_start.setText(str(data[4]))
            self.lbl_end.setText(str(data[5]))
            self.lbl_cs.setText(str(data[6]))
            self.lbl_ce.setText(str(data[7]))


def main():
    print("I am in ShotMaker [Ver: {:s}] tool".format(version))
    app = QtWidgets.QApplication(sys.argv)
    ssh_file = "config/blue_layout.css"
    with open(ssh_file, "r") as fh:
        app.setStyleSheet(fh.read())
    main_win = ShotMaker()
    main_win.show()
    app.exec_()


# fun start from here .......
if __name__ == '__main__':
    main()
