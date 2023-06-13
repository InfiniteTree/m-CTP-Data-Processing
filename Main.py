
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMainWindow, QFileDialog, QGraphicsScene, QGraphicsPixmapItem, QGraphicsView, QGraphicsRectItem
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QPen
from PyQt5.QtCore import Qt, QRectF, pyqtSignal

import sys
import os
import csv
import numpy as np
import matplotlib.pyplot as plt

from MainWindow import Ui_MainWindow
import ReadData
import RemoveBG
import RemoveDB
import GetReflectance as gr



class Main(QMainWindow, Ui_MainWindow):
    settings = QtCore.QSettings("config.ini",
                            QtCore.QSettings.Format.IniFormat)
    
    ######----------------------------------------------------------------------------------------------------######
    #####----------------------------------Parameters definition start here------------------------------------#####
    ####--------------------------------------------------------------------------------------------------------####

    impFileNum = 0
    # in Windows: C:\...\... while in linux C:/.../...
    rawSpeFile_path = "" # The abs path of the raw spe file
    rawHdrFile_path = "" # The abs path of the raw hdr file
    rawsSpeFile_path = "" # The abs path of the raw spe files
    rawsHdrFile_path = "" # The abs path of the raw hdr files
    BRFSpeFile_path = "" # The abs path of the reference board spe file
    BRFHdrFile_path = "" # The abs path of the reference board hdr file


    # Data recording for selection rectangular
    scene = None
    selecting = False
    selection_rect = None
    selection_start = None
    selection_end = None

    BRF3_pos_range = [] # [BRF3%] [[3_x0,3_y0],[3_x1,3_y1]]
    BRF30_pos_range = [] # [BRF30%] [[30_x0,30_y0],[30_x1,30_y1]]

    # Data for single Hyperspectra image
    raw_HSI_info = []
    HSI_length = 0 # Default length value
    HSI_width = 0 # Default width value
    HSI_wl = 300 # Default wavelength value
    HSI = [[[]]] # 3-D HSI img
    wavelength = [] # ranging from apporximately 400nm to 1000nm

    # Data for reference board image
    BRF_HSI_info = []

    # rbg Image generated by the three bands of HSI
    rgbImg = []

    # NDVI_matrix
    NDVI = []

    # Threshold value of NDVI to seperate the plant from the background
    NDVI_TH = 0

    # Threshold value of amplititude of the hyperspectra to eliminate
    ampl_LowTH = 0
    ampl_HighTH = 4095

    BRFfile_paths = [] # ["3%BRF_filename", "30%BRF_filename"]

    # The proportion is initially set as 1
    cur_proportion = 1

    # class reflect
    reflect = None 
    k = []
    b = []
    
    ###-------------------------------------------The End line---------------------------------------------------###


    ######----------------------------------------------------------------------------------------------------######
    #####-------------------------------------_init_ Function start here---------------------------------------#####
    ####--------------------------------------------------------------------------------------------------------####
    def __init__(self, QMainWindow):
        QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)

        self.previousPage = None

        # ------------------------------------Tab1------------------------------------
        # Part 1. Raw Data Processing
        # Import the BRF HSI files
        self.impBRFImgBtn.clicked.connect(self.importBRFImg)
        
        # Mouse box selection for 3% board
        self.selectBox3Btn.clicked.connect(lambda: self.selectBox("3"))
        # Mouse box selection for 30% board
        self.selectBox30Btn.clicked.connect(lambda: self.selectBox("30"))

        # Get k and b of the reflectance equation
        self.importRftCaliFileBtn.clicked.connect(self.importRftCaliFile)
        self.RefCaliBtn.clicked.connect(self.RefCali)
        
        
        # Import the single raw HSI file
        self.impRawBtn.clicked.connect(self.importRaw)
        self.impRawBtn.setGeometry(50, 50, 200, 30)

        # Import the multiples raw HSI files
        self.impRawsBtn.clicked.connect(self.importRaws)


        # Read the raw file
        self.rgbGeneBtn.clicked.connect(lambda:self.getRgb("Gene"))
        # show the raw file
        self.rgbViewBtn.clicked.connect(lambda:self.getRgb("View"))
        # Save the raw rgb file
        self.rgbSaveBtn.clicked.connect(lambda:self.getRgb("Save"))

        # Read the raw BRF file
        self.BRFRawGeneBtn.clicked.connect(lambda:self.getBRFRgb("Gene"))
        # show the raw BRF file
        self.BRFRawViewBtn.clicked.connect(lambda:self.getBRFRgb("View"))
        # Save the raw BRF file
        self.BRFRawSaveBtn.clicked.connect(lambda:self.getBRFRgb("Save"))

        # Show the hsi information
        self.showHsiInfoBtn.clicked.connect(self.showHsiInfo)
        
        # Draw the hyperspectra curve
        self.HSCurveBtn.clicked.connect(self.HSCurve)

        # ------------------------------------Tab2------------------------------------
        # Part 2. Data Pre-processing
        # Handle Selection Changed
        self.bgParaDb.currentIndexChanged.connect(lambda: self.getPreProcessPara(1))
        self.amplLowThDb.currentIndexChanged.connect(lambda: self.getPreProcessPara(2))
        self.amplHighThDb.currentIndexChanged.connect(lambda: self.getPreProcessPara(3))

        # Level 1-2 pre-processing
        self.RmBgGeneBtn.clicked.connect(lambda: self.RmBg("Gene"))
        self.RmBgViewBtn.clicked.connect(lambda: self.RmBg("View"))
        self.RmBgSaveBtn.clicked.connect(lambda: self.RmBg("Save"))

        self.RmSdGeneBtn.clicked.connect(lambda: self.RmDb("Gene", "SD"))
        self.RmSdViewBtn.clicked.connect(lambda: self.RmDb("View", "SD"))
        self.RmSdSaveBtn.clicked.connect(lambda: self.RmDb("Save", "SD"))

        self.RmBtGeneBtn.clicked.connect(lambda: self.RmDb("Gene", "BT"))
        self.RmBtViewBtn.clicked.connect(lambda: self.RmDb("View", "BT"))
        self.RmBtSaveBtn.clicked.connect(lambda: self.RmDb("Save", "BT"))

        self.RefGeneBtn.clicked.connect(lambda: self.getReflect("Gene"))
        self.RefViewBtn.clicked.connect(lambda: self.getiReflect("View"))
        self.RefSaveBtn.clicked.connect(lambda: self.getReflect("Save"))


    ######----------------------------------------------------------------------------------------------------######
    #####-------------------------------------Helper Function start here---------------------------------------#####
    ####--------------------------------------------------------------------------------------------------------####
    # -------------------------------------Tab1-------------------------------------
    def importRaw(self):
        file_dialog = QFileDialog()
        selected_file, _ = file_dialog.getOpenFileName(QMainWindow(), '选择文件', '', '.spe(*.spe*)')
        if selected_file:
            self.rawSpeFile_path = selected_file
            self.rawSpeFile_path = self.rawSpeFile_path.replace("\\","/")
            self.rawHSIPathlineEdit.setText(self.rawSpeFile_path)
            
            self.rawHdrFile_path = self.rawSpeFile_path.replace(".spe",".hdr")
            self.impFileNum += 1

    def importRaws(self):  
        file_dialog = QFileDialog()
        selected_directory = file_dialog.getExistingDirectory(self, "选择文件夹")
        if selected_directory:
            file_names = os.listdir(selected_directory)
            #print(file_names)
        

    def importBRFImg(self):
        selected_file, _ = QFileDialog.getOpenFileName(QMainWindow(), '选择文件', '', '.spe(*.spe*)')
        if selected_file:
            self.BRFSpeFile_path = selected_file
            self.BRFSpeFile_path = self.BRFSpeFile_path.replace("\\","/")
            self.BRFPathlineEdit.setText(self.BRFSpeFile_path)
            
            self.BRFHdrFile_path = self.BRFSpeFile_path.replace(".spe",".hdr")

    def RefCali(self):
        self.reflect = gr.Reflectance(self.HSI_info, self.cur_proportion, [self.BRF3_pos_range, self.BRF30_pos_range], self.BRFfile_paths, [], [])
        # Get the k and b
        self.k, self.b = self.reflect.getReflectEquation()
        # Unlock the view and Save function
        QtWidgets.QMessageBox.about(self, "", "反射板校准已就绪")


    def getRgb(self, function):
        match function:
            case "Gene":
                self.HSI_info = ReadData.ReadData(self.rawHdrFile_path,self.rawSpeFile_path, 1)
                self.HSI_length = self.HSI_info[0]
                self.HSI_wl = self.HSI_info[1]
                self.HSI_width = self.HSI_info[2]
                self.HSI = self.HSI_info[3]
                self.wavelength = self.HSI_info[4]
                # Unlock the view and Save function
                self.rgbViewBtn.setEnabled(True)
                self.rgbSaveBtn.setEnabled(True)
                QtWidgets.QMessageBox.about(self, "", "高光谱原始数据处理成功")

            case "View":
                if self.rawSpeFile_path != "":                     
                    self.rawjpgFile_path = "figures/test/raw" + str(self.impFileNum) + ".jpg"
                    frame = QImage(self.rawjpgFile_path)
                    pix = QPixmap.fromImage(frame)
                    item = QGraphicsPixmapItem(pix)
                    # the rgb scene in Tab1
                    self.scene = QGraphicsScene()
                    self.scene.addItem(item)
                    self.hsiRawView.setScene(self.scene)

            case "Save":
                if self.rawSpeFile_path != "":
                    self.rgbImg = ReadData.drawImg(self.HSI_info)
                    self.rgbImg.save("figures/test/raw" + str(self.impFileNum) + ".jpg")
                    QtWidgets.QMessageBox.about(self, "", "高光谱可视化数据保存成功")

    def getBRFRgb(self, function):
        match function:
            case "Gene":
                self.HSI_info = ReadData.ReadData(self.BRFHdrFile_path,self.BRFSpeFile_path, 1)
                self.HSI_length = self.HSI_info[0]
                self.HSI_wl = self.HSI_info[1]
                self.HSI_width = self.HSI_info[2]
                self.HSI = self.HSI_info[3]
                self.wavelength = self.HSI_info[4]
                # Unlock the view and Save function
                self.BRFRawViewBtn.setEnabled(True)
                self.BRFRawSaveBtn.setEnabled(True)
                QtWidgets.QMessageBox.about(self, "", "高光谱反射板处理成功")

            case "View":
                if self.BRFSpeFile_path != "":                     
                    self.rawjpgFile_path = "figures/test/raw" + str(self.impFileNum) + ".jpg"
                    frame = QImage(self.rawjpgFile_path)
                    pix = QPixmap.fromImage(frame)
                    item = QGraphicsPixmapItem(pix)
                    # the rgb scene in Tab1
                    self.scene = QGraphicsScene()
                    self.scene.addItem(item)
                    self.hsiRawView.setScene(self.scene)

            case "Save":
                if self.BRFSpeFile_path != "":
                    self.rgbImg = ReadData.drawImg(self.HSI_info)
                    self.rgbImg.save("figures/test/raw" + str(self.impFileNum) + ".jpg")
                    QtWidgets.QMessageBox.about(self, "", "高光谱反射板可视化保存成功")

    def selectBox(self, brf_flag):
        self.view = hsiRawView(self.scene, brf_flag)
        #self.setCentralWidget(self.view)
        self.view.show()
        self.view.resize(600, 800)
        self.view.startSelection()

        
    def showHsiInfo(self):
        self.lenShowBtn.setText(str(self.HSI_length)+" pix")
        self.widthShowBtn.setText(str(self.HSI_width)+" pix")
        self.wlShowBtn.setText(str(self.HSI_wl)+" bands")

    # ------------------------------------Tab2------------------------------------
    def getPreProcessPara(self, index):
        combo_box = self.sender()
        match index:
            case 1:
                self.NDVI_TH = combo_box.currentText()
            case 2:
                self.ampl_LowTH = combo_box.currentText()
            case 3:
                self.ampl_HighTH = combo_box.currentText()

    # Remove the background by NDVI
    def RmBg(self, function):
        match function:        
            case "Gene":
                l1 = RemoveBG.level1(self.HSI_info, self.NDVI_TH)
                level1 = l1.getLevel1()
                self.HSI_info = level1[0]
                self.cur_proportion = level1[2]
                self.NDVI = level1[3]
                # Unlock the view and Save function
                self.RmBgViewBtn.setEnabled(True)
                self.RmBgSaveBtn.setEnabled(True)
                QtWidgets.QMessageBox.about(self, "", "NDVI背景处理成功")

            case "View":
                fig, ax = plt.subplots(figsize=(6, 8))
                im = ax.imshow(self.NDVI, cmap='gray',interpolation='nearest')
                ax.set_title("Pseudo_Color Map of the Relative Values on NDVI", y=1.05)
                fig.colorbar(im)
                plt.show()
                
            case "Save":
                fig, ax = plt.subplots(figsize=(6, 8))
                im = ax.imshow(self.NDVI, cmap='gray',interpolation='nearest')
                ax.set_title("Pseudo_Color Map of the Relative Values on NDVI", y=1.05)
                fig.colorbar(im)
                fig.savefig("figures/test/pre_process/" + str(self.impFileNum) + "_level1.jpg")
                QtWidgets.QMessageBox.about(self, "", "NDVI背景生成成功")
                
    
    # Remove the too bright and to dark img
    def RmDb(self, function, RmType):
        match RmType:
            # To remove the shadow
            case "SD":
                match function:
                    case "Gene":
                        level2_1 = RemoveDB.RemoveDB(self.HSI_info, [0,0,0], self.cur_proportion, "SD")
                        self.HSI_info = level2_1[0]
                        self.cur_proportion = level2_1[3]
                        # Unlock the view and Save function
                        self.RmSdViewBtn.setEnabled(True)
                        self.RmSdSaveBtn.setEnabled(True)
                    case "View":
                        # Consider to draw persudo color map here!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!1
                        l1_rgbImg = ReadData.drawImg(self.HSI_info)
                        l1_rgbImg.show()
                    case "Save":
                        l1_rgbImg.save("figures/test/pre_process/"+ self.impFileNum +"_level2_1.jpg")
                        # Save 

            # To remove the bright
            case "BT":
                match function:
                    case "Gene":
                        level2_1 = RemoveDB.RemoveDB(self.HSI_info, [0,0,0], self.cur_proportion, "BT")
                        self.HSI_info = level2_1[0]
                        self.cur_proportion = level2_1[3]
                        # Unlock the view and Save function
                        self.RmBtViewBtn.setEnabled(True)
                        self.RmBtSaveBtn.setEnabled(True)
                    case "View":
                        # Consider to draw persudo color map here!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!1
                        l1_rgbImg = ReadData.drawImg(self.HSI_info)
                        l1_rgbImg.show()
                    case "Save":
                        l1_rgbImg.save("figures/test/pre_process/"+ self.impFileNum +"_level2_2.jpg")


    # import the amplititude along diferent wavelengths of 3% and 30% BRF
    def importRftCaliFile(self):
        file_dialog = QFileDialog()
        selected_directory = file_dialog.getExistingDirectory(self, "选择文件夹")
        if selected_directory:
            BRFfile_names = os.listdir(selected_directory)
            BRFfile_names = [item.replace("\\","/") for item in BRFfile_names]
            selected_directory = selected_directory.replace("\\","/")
            self.BRFCaliPathlineEdit.setText(selected_directory)
            
            self.BRFfile_paths = [selected_directory + "/" + item for item in BRFfile_names]
 
    def getReflect(self, function):
        match function:        
            case "Gene":
                self.reflect = gr.Reflectance(self.HSI_info, self.cur_proportion, [self.BRF3_pos_range, self.BRF30_pos_range], self.BRFfile_paths, self.k, self.b)
                self.reflect.getReflect()
                # Unlock the view and Save function
                self.RefViewBtn.setEnabled(True)
                self.RefSaveBtn.setEnabled(True)
                QtWidgets.QMessageBox.about(self, "", "反射率校准处理成功")

            case "View":
                self.reflect.visualizeReflect(0)
                return

            case "Save":
                self.reflect.visualizeReflect(1)
                return
            
    def HSCurve(self):

        return





    # ----------------------------Tab3-----------------------------


    # ----------------------------Tab4-----------------------------


class hsiRawView(QGraphicsView):
    def __init__(self, scene, brf_flag):
        super().__init__(scene)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.selection_rect = None
        self.selecting = False
        self.BRF_flag = brf_flag

    def startSelection(self):
        self.selecting = True
        self.selection_rect = QGraphicsRectItem()
        if self.BRF_flag == "3":
            self.selection_rect.setPen(Qt.blue)
        if self.BRF_flag == "30":
            self.selection_rect.setPen(Qt.red)
        self.scene().addItem(self.selection_rect)

    def stopSelection(self):
        if self.selection_rect is not None:
            selected_items = self.scene().items(self.selection_rect.rect(), Qt.IntersectsItemShape)

            # print x and y
            rect = self.selection_rect.rect()

            if self.BRF_flag == "3":
                BRF3_x0 = int(rect.x())
                BRF3_y0 = int(rect.y())
                BRF3_x1 = int(BRF3_x0 + rect.width())
                BRF3_y1 = int(BRF3_y0 + rect.height())
                md.BRF3_pos_range = [[BRF3_x0,BRF3_y0],[BRF3_x1, BRF3_y1]]
                
            
            elif self.BRF_flag == "30":
                BRF30_x0 = int(rect.x())
                BRF30_y0 = int(rect.y())
                BRF30_x1 = int(BRF30_x0 + rect.width())
                BRF30_y1 = int(BRF30_y0 + rect.height())
                md.BRF30_pos_range = [[BRF30_x0,BRF30_y0],[BRF30_x1, BRF30_y1]]
                
            #self.scene().removeItem(self.selection_rect)
            self.selection_rect = None
        self.selecting = False


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.selecting:
            pos_in_view = event.pos()
            pos_in_scene = self.mapToScene(pos_in_view)
            self.selection_rect.setRect(QRectF(pos_in_scene, pos_in_scene))
            self.scene().addItem(self.selection_rect)

    def mouseMoveEvent(self, event):
        if self.selecting and self.selection_rect is not None:
            pos_in_view = event.pos()
            pos_in_scene = self.mapToScene(pos_in_view)
            rect = QRectF(self.selection_rect.rect().topLeft(), pos_in_scene)
            self.selection_rect.setRect(rect.normalized())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.selecting:
            self.stopSelection()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    md = Main(QMainWindow)
    md.show()
    sys.exit(app.exec_())
            



