import matplotlib.pyplot as plt
import pandas as pd
import configparser
import numpy as np
import pyqtgraph
import nidaqmx
import glob
import math
import sys
import ast
import os

from nidaqmx.stream_readers import AnalogMultiChannelReader
from PyQt5 import QtWidgets, uic,QtCore
from PyQt5.QtWidgets import QMessageBox,QFileDialog,QLabel
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
        # Labels
        self.graphicsView_Load_X.setLabel(axis='left', text='N')
        self.graphicsView_Load_X.setLabel(axis='bottom', text='Time (Sec)')
        self.graphicsView_Load_Y.setLabel(axis='left', text='N')
        self.graphicsView_Load_Y.setLabel(axis='bottom', text='Time (Sec)')
        self.graphicsView_Load_Z.setLabel(axis='left', text='N')
        self.graphicsView_Load_Z.setLabel(axis='bottom', text='Time (Sec)')

        self.graphicsView_X.setLabel(axis='left', text='N')
        self.graphicsView_Y.setLabel(axis='left', text='N')
        self.graphicsView_Z.setLabel(axis='left', text='N')
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
        self.cleanCSV.clicked.connect(self.cleanCsvFile)

        self.calculate.clicked.connect(self.calculateCsvFile)
        self.timer.timeout.connect(self.updatePlot)
        
        
        # Check
        self.checkPathExist(self.dataPath)
        self.checkPathExist(self.configPath)
        self.checkConfigFile()

        # LoadCSV


          
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
            c0 = np.array(vals[0]) * float(self.channel0_value.value())
            c1 = np.array(vals[1]) * float(self.channel1_value.value())
            c2 = np.array(vals[2]) * float(self.channel2_value.value())
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
            self.config['Load'] = {'frequency':5000}
            self.config.write(open(self.configFile, 'w'))

        except Exception as e:
            self.handleErrorMsgBox(e)

    def setConfigFile(self):
        self.autoLoad.setChecked(ast.literal_eval(self.config['Other']['autoload']))
        self.closeSave.setChecked(ast.literal_eval(self.config['Other']['closesave']))

        self.channel0_value.setValue(float(self.config['Channel']['channel0']))	
        self.channel1_value.setValue(float(self.config['Channel']['channel1']))
        self.channel2_value.setValue(float(self.config['Channel']['channel2']))

        self.sample_rate_value.setValue(int(self.config['Timing']['samplerate']))
        self.number_samples_value.setValue(int(self.config['Timing']['numberofsamples']))

        self.physicalChannel.setText(self.config['Other']['physicalChannel'])
        self.maxVal.setValue(int(self.config['Other']['maxVal']))
        self.minVal.setValue(int(self.config['Other']['minVal']))

    def autoLoadConfigFile(self):
        self.autoLoad.setChecked(ast.literal_eval(self.config['Other']['autoload']))
        self.closeSave.setChecked(ast.literal_eval(self.config['Other']['closesave']))
        if ast.literal_eval(self.config['Other']['autoload']):
            self.channel0_value.setValue(float(self.config['Channel']['channel0']))	
            self.channel1_value.setValue(float(self.config['Channel']['channel1']))
            self.channel2_value.setValue(float(self.config['Channel']['channel2']))

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
        load_frequency = self.config['Load']['frequency']
        self.frequency, done = QtWidgets.QInputDialog.getInt(self, '輸入Hz', '輸入擷取資料時的頻率',int(load_frequency))
        if self.frequency and done :
            self.config['Load'] = {'frequency':self.frequency}
            self.config.write(open(self.configFile, 'w'))
            filename, _ = QFileDialog.getOpenFileName(self, '開啟檔案', self.dataPath,'CSV Files (*.csv)')
            if filename:
                self.datas = pd.read_csv(filename,header=None)
                self.max_time = len(self.datas[0]) // int(self.frequency)
                self.time_steps = np.linspace(0, self.max_time, len(self.datas[0]))
                self.c0_load_data.setData(self.time_steps,self.datas[0].tolist())
                self.c1_load_data.setData(self.time_steps,self.datas[1].tolist())
                self.c2_load_data.setData(self.time_steps,self.datas[2].tolist())
        else:
            self.handleErrorMsgBox('檔案開啟錯誤')

    def calculateCsvFile(self):
        times, done = QtWidgets.QInputDialog.getText(self, '時間範圍', '輸入需要擷取的時間範圍 1-10',)
        if done:
            time1,time2 = times.split('-')
            time1 = int(float(time1) * self.frequency)
            time2 = int(float(time2) * self.frequency)

            self.max_time = len(self.datas[0][time1:time2]) // int(self.frequency)
            self.time_steps = np.linspace(0, self.max_time, len(self.datas[0][time1:time2]))

            self.c0_load_data.setData(self.time_steps,self.datas[0][time1:time2].tolist())
            self.c1_load_data.setData(self.time_steps,self.datas[1][time1:time2].tolist())
            self.c2_load_data.setData(self.time_steps,self.datas[2][time1:time2].tolist())
            
            avg1 = round(sum(self.datas[0][time1:time2]) / len(self.datas[0][time1:time2]),2)
            avg2 = round(sum(self.datas[1][time1:time2]) / len(self.datas[1][time1:time2]),2)
            avg3 = round(sum(self.datas[2][time1:time2]) / len(self.datas[2][time1:time2]),2)
            f =  round(math.sqrt(math.pow(avg1,2) + math.pow(avg2,2) + math.pow(avg3,2)),2)

            self.graphicsView_Load_X.setLabel(axis='top', text='avg X ： ' + str(avg1) + ' N ， Resultant Force ： ' + str(f) + ' N')
            self.graphicsView_Load_Y.setLabel(axis='top', text='avg Y ： ' + str(avg2) + ' N ， Resultant Force ： ' + str(f) + ' N')
            self.graphicsView_Load_Z.setLabel(axis='top', text='avg Z ： ' + str(avg3) + ' N ， Resultant Force ： ' + str(f) + ' N')

    def cleanCsvFile(self,event):
        load_frequency = self.config['Load']['frequency']
        self.frequency, done = QtWidgets.QInputDialog.getInt(self, '輸入Hz', '輸入擷取資料時的頻率',int(load_frequency))
        if self.frequency and done :
            self.config['Load'] = {'frequency':self.frequency}
            self.config.write(open(self.configFile, 'w'))
            filename, _ = QFileDialog.getOpenFileName(self, '開啟檔案', self.dataPath,'CSV Files (*.csv)')
            pardir = os.path.abspath(os.path.join(filename, os.path.pardir))

            if filename:
                df = pd.read_csv(filename, header=None, names=['x', 'y', 'z'])
                # 計算每列數據的標準差
                std_x = df['x'].std()
                std_y = df['y'].std()
                std_z = df['z'].std()

                # 設定閾值為標準差的2倍
                threshold_x = 2 * std_x
                threshold_y = 2 * std_y
                threshold_z = 2 * std_z

                # 找到前段和後段的索引位置
                start_index = 0
                end_index = len(df) - 1

                for i in range(len(df)):
                    if abs(df.loc[i, 'x']) > threshold_x or abs(df.loc[i, 'y']) > threshold_y or abs(df.loc[i, 'z']) > threshold_z:
                        start_index = i
                        break

                for i in range(len(df) - 1, -1, -1):
                    if abs(df.loc[i, 'x']) > threshold_x or abs(df.loc[i, 'y']) > threshold_y or abs(df.loc[i, 'z']) > threshold_z:
                        end_index = i
                        break

                # 刪除前段和後段
                df = df.iloc[start_index:end_index+1]
                df.to_csv(os.path.join(pardir,'clean.csv'),header=None,index=None)

                # 計算每個軸向的平均切削力
                mean_x = df['x'].mean()
                mean_y = df['y'].mean()
                mean_z = df['z'].mean()

                # 計算三個軸向的平均切削力的合力
                force = np.sqrt(mean_x**2 + mean_y**2 + mean_z**2)

                max_time = len(df['x']) // 50000
                time_steps = np.linspace(0, max_time,  len(df['x']))

                # 分開繪製x、y、z三列的折線圖
                plt.figure(figsize=(16, 12))

                plt.subplot(3, 1, 1)
                plt.plot(time_steps,df['x'])
                plt.title(f"F: {force:.2f} \n Mean Cutting Force: {mean_x:.2f}")
                plt.ylabel('X-Axis')


                plt.subplot(3, 1, 2)
                plt.plot(time_steps,df['y'])
                plt.ylabel('Y-Axis')
                plt.title(f"Mean Cutting Force: {mean_y:.2f}", transform=plt.gca().transAxes)

                plt.subplot(3, 1, 3)
                plt.plot(time_steps,df['z'])
                plt.ylabel('Z-Axis')
                plt.xlabel('Time')
                plt.title(f"Mean Cutting Force: {mean_z:.2f}", transform=plt.gca().transAxes)

                plt.savefig(os.path.join(pardir,f'clean.jpg'))
                plt.close()

                self.datas = pd.read_csv(os.path.join(pardir,'clean.csv'),header=None)
                self.max_time = len(self.datas[0]) // int(self.frequency)
                self.time_steps = np.linspace(0, self.max_time, len(self.datas[0]))
                avg1 = round(sum(self.datas[0]) / len(self.datas[0]),2)
                avg2 = round(sum(self.datas[1]) / len(self.datas[1]),2)
                avg3 = round(sum(self.datas[2]) / len(self.datas[2]),2)
                f =  round(math.sqrt(math.pow(avg1,2) + math.pow(avg2,2) + math.pow(avg3,2)),2)

                self.graphicsView_Load_X.setLabel(axis='top', text='avg X ： ' + str(avg1) + ' N ， Resultant Force ： ' + str(f) + ' N')
                self.graphicsView_Load_Y.setLabel(axis='top', text='avg Y ： ' + str(avg2) + ' N ， Resultant Force ： ' + str(f) + ' N')
                self.graphicsView_Load_Z.setLabel(axis='top', text='avg Z ： ' + str(avg3) + ' N ， Resultant Force ： ' + str(f) + ' N')
                self.c0_load_data.setData(self.time_steps,self.datas[0].tolist())
                self.c1_load_data.setData(self.time_steps,self.datas[1].tolist())
                self.c2_load_data.setData(self.time_steps,self.datas[2].tolist())
        else:
            self.handleErrorMsgBox('檔案開啟錯誤')

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
