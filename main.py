import pandas as pd
import configparser
import numpy as np
import pyqtgraph
import nidaqmx
import glob
import sys
import ast
import os

from nidaqmx.stream_readers import AnalogMultiChannelReader
from PyQt5 import QtWidgets, uic,QtCore
from PyQt5.QtWidgets import QMessageBox,QFileDialog
from datetime import datetime
from ui.mainWindow import Ui_MainWindow

class MainWindow(QtWidgets.QMainWindow,Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        #Load the UI Page by PyQt5
        #uic.loadUi(os.path.join(os.getcwd(),"ui","mainWindow.ui"), self)    
        self.setupUi(self)    
        self.setWindowTitle("DAQ")

        #===========
        self.continueRunning = False
        self.timer = QtCore.QTimer()  
        

        self.c0_data = self.graphicsView_X.plot([],[])     
        self.c1_data = self.graphicsView_Y.plot([],[])    
        self.c2_data = self.graphicsView_Z.plot([],[]) 

        self.c0_load_data = self.graphicsView_Load_X.plot([],[])      
        self.c1_load_data = self.graphicsView_Load_Y.plot([],[])      
        self.c2_load_data = self.graphicsView_Load_Z.plot([],[])  
        self.config = configparser.ConfigParser()

        # Path
        self.basePath = os.getcwd()
        self.dataPath = os.path.join(self.basePath,'datas')
        self.configPath = os.path.join(self.basePath,'config')
        self.configFile = os.path.join(self.configPath,'settigns.ini')
        # Handle 
        self.Start.clicked.connect(self.toggleRun)
        self.saveConfig.clicked.connect(self.saveConfigFile)
        self.loadConfig.clicked.connect(self.setConfigFile)
        self.loadCsv.clicked.connect(self.selectCsvFile)
        self.timer.timeout.connect(self.updatePlot)
        
        # Check
        self.checkPathExist(self.dataPath)
        self.checkPathExist(self.configPath)
        self.checkConfigFile()

    def toggleRun(self):
        if self.continueRunning:
            self.continueRunning = False
            self.Start.setText("Start")
            self.stopTask()
        else:
            self.continueRunning = False
            self.Start.setText("Stop")
            self.startTask()
    
    def startTask(self):
        try:
            self.continueRunning = True
            self.timer.start(100)
            
            physicalChannel = self.physicalChannel.toPlainText()
            sampleRate = int(self.sample_rate_value.value())
            self.numberOfSamples = int(self.number_samples_value.value())
            self.nowTime = datetime.now().strftime("%Y%m%dT%H%M%S%f")
            self.nowTimePath = os.path.join(self.dataPath,self.nowTime)
            self.checkPathExist(os.path.join(self.nowTimePath,'npy'))
            # Create and start task
            self.task = nidaqmx.Task()
            self.task.ai_channels.add_ai_voltage_chan(physicalChannel, min_val=self.minVal.value(), max_val=self.maxVal.value())
            self.task.timing.cfg_samp_clk_timing(sampleRate, sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS, samps_per_chan=self.numberOfSamples)
            self.task.start()
        except Exception as e:
            self.stopTask()
            self.handleErrorMsgBox(e)
            
    def stopTask(self):
        try:
            self.continueRunning = False
            self.timer.stop()
            self.task.stop()
            self.task.close()
            self.Start.setText('Start')
            self.convertToCsv()
        except Exception as e:
            self.handleErrorMsgBox(e)
        
    def updatePlot(self):
        samplesAvailable = self.task._in_stream.avail_samp_per_chan
        if (samplesAvailable >= self.numberOfSamples):
            vals = self.task.read(self.numberOfSamples)
            c0 = np.array(vals[0]) * int(self.channel0_value.value())
            c1 = np.array(vals[1]) * int(self.channel1_value.value())
            c2 = np.array(vals[2]) * int(self.channel2_value.value())
            data = np.array((c0, c1, c2), dtype=float).T
            file = os.path.join(self.nowTimePath,'npy',f'id_{str(datetime.now().strftime("%Y%m%dT%H%M%S%f"))}.npy')
            np.save(file,data)
            self.c0_data.setData(c0)
            self.c1_data.setData(c1)
            self.c2_data.setData(c2)
            
    def handleErrorMsgBox(self,msg):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Warning)
        msgBox.setText(f"TASK Error : {msg}")
        msgBox.setWindowTitle("ERROR")
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.exec()
        
    def checkPathExist(self,path):
        isExist = os.path.exists(path)
        if not isExist:
            os.makedirs(path)
    
    def checkConfigFile(self):
        try:
            with open(self.configFile) as f:
                self.config.read_file(f)
                self.autoLoadConfigFile()

        except FileNotFoundError:
            self.config['Channel'] = {'Channel0':10, 'Channel1': 10,'Channel2': 10}
            self.config['Timing'] = {'SampleRate': 5000,'NumberOfSamples': 5000}
            self.config['Other'] = {'physicalChannel':'Dev1/ai0:2','MaxVal':10,'MinVal':-10,'AutoLoad':True,'CloseSave':True}
            self.config.write(open(self.configFile, 'w'))

        except Exception as e:
            self.handleErrorMsgBox(e)

    def setConfigFile(self):
        self.autoLoad.setChecked(ast.literal_eval(self.config['Other']['autoload']))
        self.closeSave.setChecked(ast.literal_eval(self.config['Other']['closesave']))

        self.channel0_value.setValue(int(self.config['Channel']['channel0']))	
        self.channel1_value.setValue(int(self.config['Channel']['channel1']))
        self.channel2_value.setValue(int(self.config['Channel']['channel2']))

        self.sample_rate_value.setValue(int(self.config['Timing']['samplerate']))
        self.number_samples_value.setValue(int(self.config['Timing']['numberofsamples']))

        self.physicalChannel.setText(self.config['Other']['physicalChannel'])
        self.maxVal.setValue(int(self.config['Other']['maxVal']))
        self.minVal.setValue(int(self.config['Other']['minVal']))

    def autoLoadConfigFile(self):
        self.autoLoad.setChecked(ast.literal_eval(self.config['Other']['autoload']))
        self.closeSave.setChecked(ast.literal_eval(self.config['Other']['closesave']))
        if ast.literal_eval(self.config['Other']['autoload']):
            self.channel0_value.setValue(int(self.config['Channel']['channel0']))	
            self.channel1_value.setValue(int(self.config['Channel']['channel1']))
            self.channel2_value.setValue(int(self.config['Channel']['channel2']))

            self.sample_rate_value.setValue(int(self.config['Timing']['samplerate']))
            self.number_samples_value.setValue(int(self.config['Timing']['numberofsamples']))

            self.physicalChannel.setText(self.config['Other']['physicalChannel'])
            self.maxVal.setValue(int(self.config['Other']['maxVal']))
            self.minVal.setValue(int(self.config['Other']['minVal']))

    def saveConfigFile(self):
            self.config['Channel'] = {'channel0':self.channel0_value.value(), 'channel1': self.channel1_value.value(),'channel2': self.channel2_value.value()}
            self.config['Timing'] = {'samplerate': self.sample_rate_value.value(),'numberofsamples': self.number_samples_value.value()}
            self.config['Other'] = {'physicalChannel':self.physicalChannel.toPlainText(),'maxVal':self.maxVal.value(),'minVal':self.minVal.value(),'autoload':bool(self.autoLoad.checkState()),'closesave':bool(self.closeSave.checkState())}
            self.config.write(open(self.configFile, 'w'))

    def convertToCsv(self):
        npfiles = glob.glob(os.path.join(self.nowTimePath,'npy',"*.npy"))
        npfiles.sort()
        temp = []
        if npfiles : 
            for npfile in npfiles:
                temp.append(pd.DataFrame(np.load(npfile).tolist()))
            df = pd.concat(temp)
            df.to_csv(os.path.join(self.nowTimePath,f'{self.nowTime}.csv'),index=False, header=False)

    def selectCsvFile(self):
        filename, _ = QFileDialog.getOpenFileName(self, '開啟檔案', self.dataPath,'CSV Files (*.csv)')
        if filename:
            datas = pd.read_csv(filename,header=None)
            self.c0_load_data.setData(datas[0].tolist())
            self.c1_load_data.setData(datas[1].tolist())
            self.c2_load_data.setData(datas[2].tolist())


    def closeEvent(self, event):
        if self.continueRunning:
            self.stopTask()
            
        if bool(self.closeSave.checkState()):
            self.saveConfigFile()

        

def main(): 
    app = QtWidgets.QApplication(sys.argv)  
    main = MainWindow()
    main.show()
    sys.exit(app.exec())  
      
if __name__ == '__main__':
    main()
