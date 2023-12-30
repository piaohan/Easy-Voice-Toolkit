import os
import sys
import time #import asyncio
import json
from pathlib import Path
from datetime import datetime
from PySide6 import __file__ as PySide6_File
from PySide6.QtCore import Qt, QObject, Signal, Slot, QThread
from PySide6.QtCore import QCoreApplication as QCA
from PySide6.QtWidgets import *

from EVT_GUI.QSimpleWidgets.Utils import *
from EVT_GUI.QSimpleWidgets.QTasks import *
from EVT_GUI.Window import Window_Customizing
from EVT_GUI.Functions import *
from EVT_GUI.EnvConfigurator import *

##############################################################################################################################

# Set current version
CurrentVersion = "v1.0.0"

##############################################################################################################################

# Check whether python file is compiled
FileName, IsFileCompiled = GetFileInfo()


# Set&Change working directory to current directory
CurrentDir = GetBaseDir(__file__ if IsFileCompiled == False else sys.executable)
os.chdir(CurrentDir)


# Set directory to store static dependencies
ResourceDir = CurrentDir if GetBaseDir(SearchMEIPASS = True) is None else GetBaseDir(SearchMEIPASS = True)


# Set up environment variables while python file is not compiled
if IsFileCompiled == False:
    SetEnvVar( # Redirect PATH variable 'QT_QPA_PLATFORM_PLUGIN_PATH' to Pyside6 '/plugins/platforms' folder's path
        Variable = 'QT_QPA_PLATFORM_PLUGIN_PATH',
        Value = NormPath(Path(GetBaseDir(PySide6_File)).joinpath('plugins', 'platforms'))
    )
# Set up environment variables while environment is configured
if Path(CurrentDir).joinpath('FFmpeg').exists():
    SetEnvVar(
        Variable = 'PATH',
        Value = NormPath(Path(CurrentDir).joinpath('FFmpeg', 'bin'))
    )
if Path(CurrentDir).joinpath('Python').exists():
    '''
    SetEnvVar(
        Variable = 'PYTHONPATH',
        Value = NormPath(Path(CurrentDir).joinpath('Python'))
    )
    '''
    SetEnvVar(
        Variable = 'PATH',
        Value = NormPath(Path(CurrentDir).joinpath('Python'), TrailingSlash = True)
    )
    SetEnvVar(
        Variable = 'PATH',
        Value = NormPath(Path(CurrentDir).joinpath('Python', 'Scripts'), TrailingSlash = True)
    )


# Set up config
ConfigPath = NormPath(Path(CurrentDir).joinpath('Config', 'Config.ini'))
Config = ManageConfig(ConfigPath)
Config.EditConfig('Info', 'CurrentVersion', str(CurrentVersion))
Config.EditConfig('Info', 'ExecuterName', str(FileName))

##############################################################################################################################

def UpdaterExecuter():
    '''
    Execute updater
    '''
    if Config.GetValue('Settings', 'AutoUpdate', 'Enabled') == 'Enabled':
        if Config.GetValue('Updater', 'Status', 'Checking') != 'Executed':
            subprocess.Popen(['python.exe', NormPath(Path(CurrentDir).joinpath('Updater.py'))] if IsFileCompiled == False else [NormPath(Path(CurrentDir).joinpath('Updater.exe'))], env = os.environ)
            #Config.EditConfig('Updater', 'Status', 'Executed')
            sys.exit()
        else:
            Config.EditConfig('Updater', 'Status', 'Unexecuted')

##############################################################################################################################

# Tools: AudioProcessor
class Execute_Audio_Processing(QObject):
    '''
    Change media format to WAV (and denoise) and cut off the silent parts
    '''
    started = Signal()
    finished = Signal(str)

    def __init__(self):
        super().__init__()

    @Slot(tuple)
    def Execute(self, Params: tuple):
        self.started.emit()

        Error = RunCMD(
            Args = [
                f'cd "{ResourceDir}"',
                'python -c "'
                'from EVT_Core.Process.Process import Audio_Processing; '
                f"AudioConvertandSlice = Audio_Processing{str(Params)}; "
                'AudioConvertandSlice.Process_Audio()"'
            ],
            PathType = 'Posix',
            ShowProgress = True,
            CommunicateThroughConsole = True,
            DecodeResult = True
        )[1]
        Error = None if 'traceback' not in str(Error).lower() else Error

        self.finished.emit(str(Error))


# Tools: VoiceIdentifier
class Execute_Voice_Identifying(QObject):
    '''
    Contrast the voice and filter out the similar ones
    '''
    started = Signal()
    finished = Signal(str)
    
    def __init__(self):
        super().__init__()

    @Slot(tuple)
    def Execute(self, Params: tuple):
        self.started.emit()

        Error = RunCMD(
            Args = [
                f'cd "{ResourceDir}"',
                'python -c "'
                'from EVT_Core.ASR.VPR.Identify import Voice_Identifying; '
                f"AudioContrastInference = Voice_Identifying{str(Params)}; "
                'AudioContrastInference.GetModel(); '
                'AudioContrastInference.Inference()"'
            ],
            PathType = 'Posix',
            ShowProgress = True,
            CommunicateThroughConsole = True,
            DecodeResult = True
        )[1]
        Error = None if 'traceback' not in str(Error).lower() else Error

        self.finished.emit(str(Error))


# Tools: VoiceTranscriber
class Execute_Voice_Transcribing(QObject):
    '''
    Transcribe WAV content to SRT
    '''
    started = Signal()
    finished = Signal(str)

    def __init__(self):
        super().__init__()

    @Slot(tuple)
    def Execute(self, Params: tuple):
        self.started.emit()

        LANGUAGES = {
            "中":       "zh",
            "Chinese":  "zh",
            "英":       "en",
            "English":  "en",
            "日":       "ja",
            "japanese": "ja"
        }
        Error = RunCMD(
            Args = [
                f'cd "{ResourceDir}"',
                'python -c "'
                'from EVT_Core.STT.Whisper.Transcribe import Voice_Transcribing; '
                f"WAVtoSRT = Voice_Transcribing{str(ItemReplacer(LANGUAGES, Params))}; "
                'WAVtoSRT.Transcriber()"'
            ],
            PathType = 'Posix',
            ShowProgress = True,
            CommunicateThroughConsole = True,
            DecodeResult = True
        )[1]
        Error = None if 'traceback' not in str(Error).lower() else Error

        self.finished.emit(str(Error))


# Tools: DatasetCreator
class Execute_Dataset_Creating(QObject):
    '''
    Convert the whisper-generated SRT to CSV and split the WAV
    '''
    started = Signal()
    finished = Signal(str)

    def __init__(self):
        super().__init__()

    @Slot(tuple)
    def Execute(self, Params: tuple):
        self.started.emit()

        Error = RunCMD(
            Args = [
                f'cd "{ResourceDir}"',
                'python -c "'
                'from EVT_Core.DAT.VITS.Create import Dataset_Creating; '
                f"SRTtoCSVandSplitAudio = Dataset_Creating{str(Params)}; "
                'SRTtoCSVandSplitAudio.CallingFunctions()"'
            ],
            PathType = 'Posix',
            ShowProgress = True,
            CommunicateThroughConsole = True,
            DecodeResult = True
        )[1]
        Error = None if 'traceback' not in str(Error).lower() else Error

        self.finished.emit(str(Error))


# Tools: VoiceTrainer
class Execute_Voice_Training(QObject):
    '''
    Preprocess and then start training
    '''
    started = Signal()
    finished = Signal(str)

    def __init__(self):
        super().__init__()

    @Slot(tuple)
    def Execute(self, Params: tuple):
        self.started.emit()

        Error = RunCMD(
            Args = [
                f'cd "{ResourceDir}"',
                'python -c "'
                'from EVT_Core.Train.VITS.Train import Voice_Training; '
                f"PreprocessandTrain = Voice_Training{str(Params)}; "
                'PreprocessandTrain.Preprocessing_and_Training()"'
            ],
            PathType = 'Posix',
            ShowProgress = True,
            CommunicateThroughConsole = True,
            DecodeResult = True
        )[1]
        if 'traceback' not in str(Error).lower():
            if "is not a directory" in str(Error).lower():
                Error = "请确保模型/配置保存路径中没有中文等特殊字符"
            if "specify the reduction dim" in str(Error).lower():
                Error = "请检查显存是否足够或者 batch size（批处理量）设置是否过高"
        else:
            Error = None 

        self.finished.emit(str(Error))


# Tools: VoiceConverter
def Get_Speakers(Config_Path_Load):
    try:
        with open(Config_Path_Load, 'r', encoding = 'utf-8') as File:
            Params = json.load(File)
        Speakers = Params["speakers"]
        return Speakers
    except:
        return str()

class Execute_Voice_Converting(QObject):
    '''
    Inference model
    '''
    started = Signal()
    finished = Signal(str)

    def __init__(self):
        super().__init__()

    @Slot(tuple)
    def Execute(self, Params: tuple):
        self.started.emit()

        LANGUAGES = {
            "中":       "[ZH]",
            "Chinese":  "[ZH]",
            "英":       "[EN]",
            "English":  "[EN]",
            "日":       "[JA]",
            "Japanese": "[JA]"
        }
        Error = RunCMD(
            Args = [
                f'cd "{ResourceDir}"',
                'python -c "'
                'from EVT_Core.TTS.VITS.Convert import Voice_Converting; '
                f"TTS = Voice_Converting{str(ItemReplacer(LANGUAGES, Params))}; "
                'TTS.Converting()"'
            ],
            PathType = 'Posix',
            ShowProgress = True,
            CommunicateThroughConsole = True,
            DecodeResult = True
        )[1]
        Error = None if 'traceback' not in str(Error).lower() else Error

        self.finished.emit(str(Error))


# ClientFunc: ClientRebooter
def ClientRebooter():
    '''
    Reboot EVT client
    '''
    UpdaterExecuter() #os.execl(sys.executable, 'python', __file__, *sys.argv[1:]) else os.execl(sys.executable, sys.executable, *sys.argv)


# ClientFunc: IntegrityChecker
class Integrity_Checker(QObject):
    '''
    Check File integrity
    '''
    finished = Signal(str)

    def __init__(self):
        super().__init__()

    @Slot(tuple)
    def Execute(self):
        if 'Undetected' not in [
            Config.GetValue('Env', 'FFmpeg'),
            #Config.GetValue('Env', 'GCC'),
            #Config.GetValue('Env', 'CMake'),
            Config.GetValue('Env', 'Python'),
            Config.GetValue('Env', 'PyReqs'),
            Config.GetValue('Env', 'Pytorch')
        ]:
            Error = RunCMD(
                Args = [
                    f'cd "{ResourceDir}"',
                    'python -c "'
                    'from EVT_Core.Process.Process import Audio_Processing; '
                    'from EVT_Core.ASR_VPR.Identify import Voice_Identifying; '
                    'from EVT_Core.STT_Whisper.Transcribe import Voice_Transcribing; '
                    'from EVT_Core.DAT_VITS.Create import Dataset_Creating; '
                    'from EVT_Core.Train_VITS.Train import Voice_Training; '
                    'from EVT_Core.TTS_VITS.Convert import Voice_Converting"'
                ],
                CommunicateThroughConsole = True,
                DecodeResult = True
            )[1]

        else:
            Error = 'Missing evironment dependencies!'

        self.finished.emit(str(Error))


# ClientFunc: TensorboardRunner
class Tensorboard_Runner(QObject):
    '''
    Check File integrity
    '''
    finished = Signal(str)

    def __init__(self):
        super().__init__()
    
    def RunTensorboard(self, LogDir): #async def RunTensorboard(self, LogDir):
        try:
            Error = None
            InitialWaitTime = 0
            MaximumWaitTime = 30
            while GetPath(LogDir, 'events.out.tfevents') == False:
                time.sleep(3) #await asyncio.sleep(3)
                InitialWaitTime += 3
                if InitialWaitTime >= MaximumWaitTime:
                    break
            '''
            Output = RunCMD([['tensorboard', '--logdir', LogDir]], TimeOut = 9.)
            URL = FindURL(Output) #URL = Output[Output.find('http'):Output.find(' (', Output.find('http'))]
            Function_OpenURL(URL)
            '''
            subprocess.Popen(['tensorboard', '--logdir', LogDir], env = os.environ)
            time.sleep(9) #await asyncio.sleep(9)
            Function_OpenURL('http://localhost:6006/')
        except Exception as e:
            Error = e
        finally:
            return Error

    @Slot(tuple)
    def Execute(self, Params: tuple):
        Error = self.RunTensorboard(*Params)

        self.finished.emit(str(Error))

##############################################################################################################################

# Where to store custom signals
class CustomSignals_MainWindow(QObject):
    '''
    Set up signals for MainWindow
    '''
    Signal_MainWindowShown = Signal()

    # Run task
    Signal_ExecuteTask = Signal(tuple)

    # Monitor task
    Signal_TaskStatus = Signal(str, str)


MainWindowSignals = CustomSignals_MainWindow()


# Show GUI
class MainWindow(Window_Customizing):
    '''
    Show the user interface
    '''
    ui = Window_Customizing.ui

    def __init__(self, parent = None):
        super().__init__(parent)

        self.ConsoleInfo = ConsolOutputHandler()
        self.ConsoleInfo.start()

        self.MonitorUsage = MonitorUsage()
        self.MonitorUsage.start()

    def Function_SetMethodExecutor(self,
        ExecuteButton: QPushButton,
        TerminateButton: Optional[QPushButton] = None,
        ProgressBar: Optional[QProgressBar] = None,
        ConsoleFrame: Optional[QFrame] = None,
        Method: object = ...,
        Params: Optional[tuple] = (),
        ParamsFrom: Optional[list] = [],
        EmptyAllowed: Optional[list] = [],
        #StartEventList: Optional[list] = None,
        #StartParamList: Optional[list[tuple]] = None,
        FinishEventList: Optional[list] = None,
        FinishParamList: Optional[list[tuple]] = None
    ):
        '''
        Function to execute outer class methods (through button)
        '''
        QualName = str(Method.__qualname__)
        ClassName =  QualName.split('.')[0]
        MethodName = QualName.split('.')[1]

        ClassInstance = globals()[ClassName]()
        ClassInstance.started.connect(lambda: MainWindowSignals.Signal_TaskStatus.emit(QualName, 'Started')) if hasattr(ClassInstance, 'started') else None
        #ClassInstance.started.connect(lambda: RunEvent(StartEventList, StartParamList)) if hasattr(ClassInstance, 'started') else None
        ClassInstance.finished.connect(lambda Error: MainWindowSignals.Signal_TaskStatus.emit(QualName, 'Finished') if Error == str(None) else None) if hasattr(ClassInstance, 'finished') else None
        ClassInstance.finished.connect(lambda Error: RunEvent(FinishEventList, FinishParamList) if Error == str(None) else None) if hasattr(ClassInstance, 'finished') else None
        ClassInstance.finished.connect(lambda Error: MainWindowSignals.Signal_TaskStatus.emit(QualName, 'Failed') if Error != str(None) else None) if hasattr(ClassInstance, 'finished') else None
        ClassInstance.finished.connect(lambda Error: Function_ShowMessageBox(QMessageBox.Warning, 'Failure', f'发生错误：\n{Error}') if Error != str(None) else None) if hasattr(ClassInstance, 'finished') else None

        if not isinstance(ClassInstance, QThread):
            WorkerThread = QThread()
            ClassInstance.moveToThread(WorkerThread)
            ClassInstance.finished.connect(WorkerThread.quit) if hasattr(ClassInstance, 'finished') else None
        else:
            WorkerThread = ClassInstance

        @Slot()
        def ExecuteMethod():
            '''
            Update the attributes for outer class methods and wait to execute with multithreading
            '''
            Args = Params#if Params != () else None
            if ParamsFrom not in ([], None):
                Args = Function_ParamsChecker(ParamsFrom, EmptyAllowed)
                if Args == "Abort":
                    return print("Aborted.")
                else:
                    pass #print("Continued.\n")

            MainWindowSignals = CustomSignals_MainWindow()
            MainWindowSignals.Signal_ExecuteTask.connect(getattr(ClassInstance, MethodName)) #MainWindowSignals.Signal_ExecuteTask.connect(lambda Args: getattr(ClassInstance, MethodName)(*Args))

            WorkerThread.started.connect(lambda: Function_AnimateFrame(self, ConsoleFrame, MinHeight = 0, MaxHeight = 210, Mode = "Extend")) if ConsoleFrame else None
            WorkerThread.started.connect(lambda: Function_AnimateProgressBar(ProgressBar, IsTaskAlive = True)) if ProgressBar else None
            WorkerThread.started.connect(lambda: Function_AnimateStackedWidget(self, Function_FindParentUI(ExecuteButton, QStackedWidget), TargetIndex = 1)) if TerminateButton else None
            WorkerThread.finished.connect(lambda: Function_AnimateFrame(self, ConsoleFrame, MinHeight = 0, MaxHeight = 210, Mode = "Reduce")) if ConsoleFrame else None
            WorkerThread.finished.connect(lambda: Function_AnimateProgressBar(ProgressBar, IsTaskAlive = False)) if ProgressBar else None
            WorkerThread.finished.connect(lambda: Function_AnimateStackedWidget(self, Function_FindParentUI(ExecuteButton, QStackedWidget), TargetIndex = 0)) if TerminateButton else None
            #WorkerThread.finished.connect(lambda: MainWindowSignals.Signal_ExecuteTask.disconnect(getattr(ClassInstance, MethodName)))

            MainWindowSignals.Signal_ExecuteTask.emit(Args)

            WorkerThread.start()

        ExecuteButton.clicked.connect(ExecuteMethod)#if ExecuteButton else ExecuteMethod()
        ExecuteButton.setText("Execute 执行") if ExecuteButton != None and ExecuteButton.text() == "" else None

        @Slot()
        def TerminateMethod():
            '''
            Terminate the running thread
            '''
            if not WorkerThread.isFinished():
                try:
                    WorkerThread.terminate()
                except:
                    WorkerThread.quit()

            ProcessTerminator(
                Program = 'python.exe',
                SelfIgnored = True,
                SearchKeyword = True
            )

            ProgressBar.setValue(0)

        TerminateButton.clicked.connect(
            lambda: Function_ShowMessageBox(
                MessageType = QMessageBox.Question,
                WindowTitle = "Ask",
                Text = "当前任务仍在执行中，是否确认终止？",
                Buttons = QMessageBox.Yes|QMessageBox.No,
                EventButtons = [QMessageBox.Yes],
                EventLists = [[TerminateMethod]],
                ParamLists = [[()]]
            )
        ) if TerminateButton else None
        TerminateButton.setText("Terminate 终止") if TerminateButton != None and TerminateButton.text() == "" else None

    def Main(self):
        '''
        Main funtion to orgnize all the subfunctions
        '''
        self.setWindowIcon(QIcon(NormPath(Path(ResourceDir).joinpath('Icon.ico'))))

        #############################################################
        ########################## TitleBar #########################
        #############################################################

        # Title
        self.ui.Label_Title.setText("Easy Voice Toolkit - by Spr_Aachen")

        # Window controling buttons
        self.ui.Button_Close_Window.clicked.connect(self.close)
        self.ui.Button_Maximize_Window.clicked.connect(lambda: self.showNormal() if self.isMaximized() else self.showMaximized())
        self.ui.Button_Minimize_Window.clicked.connect(self.showMinimized)

        # Menu toggling button
        self.ui.Button_Toggle_Menu.clicked.connect(
            lambda: Function_AnimateFrame(
                Parent = self,
                Frame = self.ui.Frame_Menu,
                MinWidth = 48,
                MaxWidth = 210
            )
        )
        self.ui.Button_Toggle_Menu.setCheckable(True)
        self.ui.Button_Toggle_Menu.setChecked(False)
        self.ui.Button_Toggle_Menu.setAutoExclusive(False)
        self.ui.Button_Toggle_Menu.setToolTipDuration(-1)
        self.ui.Button_Toggle_Menu.setToolTip(QCA.translate("ToolTip", "点击以展开/折叠菜单"))

        #############################################################
        ############################ Menu ###########################
        #############################################################

        self.ui.Label_Menu_Home_Text.setText(QCA.translate("Label", "主页"))
        self.ui.Button_Menu_Home.clicked.connect(
            lambda: Function_AnimateStackedWidget(
                Parent = self,
                StackedWidget = self.ui.StackedWidget_Pages,
                TargetIndex = 0
            )
        )
        self.ui.Button_Menu_Home.setCheckable(True)
        self.ui.Button_Menu_Home.setChecked(True)
        self.ui.Button_Menu_Home.setAutoExclusive(True)
        self.ui.Button_Menu_Home.setToolTipDuration(-1)
        self.ui.Button_Menu_Home.setToolTip(QCA.translate("ToolTip", "主页"))

        self.ui.Label_Menu_Download_Text.setText(QCA.translate("Label", "下载"))
        self.ui.Button_Menu_Download.clicked.connect(
            lambda: Function_AnimateStackedWidget(
                Parent = self,
                StackedWidget = self.ui.StackedWidget_Pages,
                TargetIndex = 1
            )
        )
        self.ui.Button_Menu_Download.setCheckable(True)
        self.ui.Button_Menu_Download.setChecked(False)
        self.ui.Button_Menu_Download.setAutoExclusive(True)
        self.ui.Button_Menu_Download.setToolTipDuration(-1)
        self.ui.Button_Menu_Download.setToolTip(QCA.translate("ToolTip", "文件下载和安装"))

        self.ui.Label_Menu_Models_Text.setText(QCA.translate("Label", "模型"))
        self.ui.Button_Menu_Models.clicked.connect(
            lambda: Function_AnimateStackedWidget(
                Parent = self,
                StackedWidget = self.ui.StackedWidget_Pages,
                TargetIndex = 2
            )
        )
        self.ui.Button_Menu_Models.setCheckable(True)
        self.ui.Button_Menu_Models.setChecked(False)
        self.ui.Button_Menu_Models.setAutoExclusive(True)
        self.ui.Button_Menu_Models.setToolTipDuration(-1)
        self.ui.Button_Menu_Models.setToolTip(QCA.translate("ToolTip", "模型管理"))

        self.ui.Label_Menu_Process_Text.setText(QCA.translate("Label", "处理"))
        self.ui.Button_Menu_Process.clicked.connect(
            lambda: Function_AnimateStackedWidget(
                Parent = self,
                StackedWidget = self.ui.StackedWidget_Pages,
                TargetIndex = 3
            )
        )
        self.ui.Button_Menu_Process.setCheckable(True)
        self.ui.Button_Menu_Process.setChecked(False)
        self.ui.Button_Menu_Process.setAutoExclusive(True)
        self.ui.Button_Menu_Process.setToolTipDuration(-1)
        self.ui.Button_Menu_Process.setToolTip(QCA.translate("ToolTip", "音频处理"))

        self.ui.Label_Menu_ASR_Text.setText(QCA.translate("Label", "ASR"))
        self.ui.Button_Menu_ASR.clicked.connect(
            lambda: Function_AnimateStackedWidget(
                Parent = self,
                StackedWidget = self.ui.StackedWidget_Pages,
                TargetIndex = 4
            )
        )
        self.ui.Button_Menu_ASR.setCheckable(True)
        self.ui.Button_Menu_ASR.setChecked(False)
        self.ui.Button_Menu_ASR.setAutoExclusive(True)
        self.ui.Button_Menu_ASR.setToolTipDuration(-1)
        self.ui.Button_Menu_ASR.setToolTip(QCA.translate("ToolTip", "语音识别"))

        self.ui.Label_Menu_STT_Text.setText(QCA.translate("Label", "STT"))
        self.ui.Button_Menu_STT.clicked.connect(
            lambda: Function_AnimateStackedWidget(
                Parent = self,
                StackedWidget = self.ui.StackedWidget_Pages,
                TargetIndex = 5
            )
        )
        self.ui.Button_Menu_STT.setCheckable(True)
        self.ui.Button_Menu_STT.setChecked(False)
        self.ui.Button_Menu_STT.setAutoExclusive(True)
        self.ui.Button_Menu_STT.setToolTipDuration(-1)
        self.ui.Button_Menu_STT.setToolTip(QCA.translate("ToolTip", "语音转文字"))

        self.ui.Label_Menu_Dataset_Text.setText(QCA.translate("Label", "DAT"))
        self.ui.Button_Menu_Dataset.clicked.connect(
            lambda: Function_AnimateStackedWidget(
                Parent = self,
                StackedWidget = self.ui.StackedWidget_Pages,
                TargetIndex = 6
            )
        )
        self.ui.Button_Menu_Dataset.setCheckable(True)
        self.ui.Button_Menu_Dataset.setChecked(False)
        self.ui.Button_Menu_Dataset.setAutoExclusive(True)
        self.ui.Button_Menu_Dataset.setToolTipDuration(-1)
        self.ui.Button_Menu_Dataset.setToolTip(QCA.translate("ToolTip", "数据集生成"))

        self.ui.Label_Menu_Train_Text.setText(QCA.translate("Label", "训练"))
        self.ui.Button_Menu_Train.clicked.connect(
            lambda: Function_AnimateStackedWidget(
                Parent = self,
                StackedWidget = self.ui.StackedWidget_Pages,
                TargetIndex = 7
            )
        )
        self.ui.Button_Menu_Train.setCheckable(True)
        self.ui.Button_Menu_Train.setChecked(False)
        self.ui.Button_Menu_Train.setAutoExclusive(True)
        self.ui.Button_Menu_Train.setToolTipDuration(-1)
        self.ui.Button_Menu_Train.setToolTip(QCA.translate("ToolTip", "模型训练"))

        self.ui.Label_Menu_TTS_Text.setText(QCA.translate("Label", "TTS"))
        self.ui.Button_Menu_TTS.clicked.connect(
            lambda: Function_AnimateStackedWidget(
                Parent = self,
                StackedWidget = self.ui.StackedWidget_Pages,
                TargetIndex = 8
            )
        )
        self.ui.Button_Menu_TTS.setCheckable(True)
        self.ui.Button_Menu_TTS.setChecked(False)
        self.ui.Button_Menu_TTS.setAutoExclusive(True)
        self.ui.Button_Menu_TTS.setToolTipDuration(-1)
        self.ui.Button_Menu_TTS.setToolTip(QCA.translate("ToolTip", "文字转语音"))

        self.ui.Label_Menu_Settings_Text.setText(QCA.translate("Label", "设置"))
        self.ui.Button_Menu_Settings.clicked.connect(
            lambda: Function_AnimateStackedWidget(
                Parent = self,
                StackedWidget = self.ui.StackedWidget_Pages,
                TargetIndex = 9
            )
        )
        self.ui.Button_Menu_Settings.setCheckable(True)
        self.ui.Button_Menu_Settings.setChecked(False)
        self.ui.Button_Menu_Settings.setAutoExclusive(True)
        self.ui.Button_Menu_Settings.setToolTipDuration(-1)
        self.ui.Button_Menu_Settings.setToolTip(QCA.translate("ToolTip", "客户端设置"))

        self.ui.Label_Menu_Info_Text.setText(QCA.translate("Label", "关于"))
        self.ui.Button_Menu_Info.clicked.connect(
            lambda: Function_AnimateStackedWidget(
                Parent = self,
                StackedWidget = self.ui.StackedWidget_Pages,
                TargetIndex = 10
            )
        )
        self.ui.Button_Menu_Info.setCheckable(True)
        self.ui.Button_Menu_Info.setChecked(False)
        self.ui.Button_Menu_Info.setAutoExclusive(True)
        self.ui.Button_Menu_Info.setToolTipDuration(-1)
        self.ui.Button_Menu_Info.setToolTip(QCA.translate("ToolTip", "关于本软件"))

        #############################################################
        ####################### Content: Home #######################
        #############################################################

        #self.ui.ToolButton_Home_Title.setText(QCA.translate("Label", "主页"))

        self.ui.TextBrowser_Pic_Home.setStyleSheet(
            self.ui.TextBrowser_Pic_Home.styleSheet() +
            "QTextBrowser {"
            f"    background-image: url({NormPath(Path(ResourceDir).joinpath('Sources/Cover.png'), 'Posix')});"
            "    background-size: cover;"
            "    background-repeat: no-repeat;"
            "    background-position: center 0px;"
            "}"
        )

        Function_SetText(
            Widget = self.ui.TextBrowser_Text_Home,
            Text = SetRichText(
                Title = QCA.translate("TextBrowser", "介绍"),
                TitleAlign = "left",
                TitleSize = 24,
                TitleWeight = 840,
                Body = QCA.translate("TextBrowser",
                    "一个基于Whisper、VITS等项目实现的简易语音工具箱，提供了包括语音模型训练在内的多种自动化音频工具\n"
                    "\n"
                    "工具箱目前包含以下功能：\n"
                    "音频基本处理\n"
                    "语音识别和筛选\n"
                    "语音转文字字幕\n"
                    "语音数据集制作\n"
                    "语音模型训练\n"
                    "语音模型推理\n"
                    "\n"
                    "这些功能彼此之间相互独立，但又能无缝衔接地形成一套完整的工作流\n"
                    "用户可以根据自己的需求有选择性地使用，亦或者依次通过这些工具将未经处理的语音文件逐步变为理想的语音模型\n"
                ),
                BodyAlign = "left",
                BodySize = 12,
                BodyWeight = 420,
                BodyLineHeight = 27
            )
        )

        self.ui.Label_Demo_Text.setText(QCA.translate("Button", "视频演示"))
        Function_SetURL(
            Button = self.ui.Button_Demo,
            URL = "https://www.bilibili.com/video/BV",
            ButtonTooltip = "Click to view demo video"
        )
        self.ui.Label_Server_Text.setText(QCA.translate("Button", "云端版本"))
        Function_SetURL(
            Button = self.ui.Button_Server,
            URL = "https://colab.research.google.com/github/Spr-Aachen/EVT-Resources/blob/main/Easy_Voice_Toolkit_for_Colab.ipynb",
            ButtonTooltip = "Click to run on server"
        )
        self.ui.Label_Repo_Text.setText(QCA.translate("Button", "项目仓库"))
        Function_SetURL(
            Button = self.ui.Button_Repo,
            URL = "https://github.com/Spr-Aachen/Easy-Voice-Toolkit",
            ButtonTooltip = "Click to view github repo"
        )
        self.ui.Label_Donate_Text.setText(QCA.translate("Button", "赞助作者"))
        Function_SetURL(
            Button = self.ui.Button_Donate,
            URL = "https://",
            ButtonTooltip = "Click to buy him a coffee"
        )

        #############################################################
        ##################### Content: Download #####################
        #############################################################

        self.ui.ToolButton_Download_Title.setText(QCA.translate("Label", "环境依赖"))

        self.ui.Label_Download_FFmpeg.setText("FFmpeg")
        self.Function_SetMethodExecutor(
            ExecuteButton = self.ui.Button_Install_FFmpeg,
            ProgressBar = self.ui.ProgressBar_Download_FFmpeg,
            Method = FFmpeg_Installer.Execute,
            Params = ()
        )
        MainWindowSignals.Signal_MainWindowShown.connect(
            self.ui.Button_Install_FFmpeg.click #if Config.GetValue('Env', 'FFmpeg', 'Undetected') == 'Undetected' else EnvConfiguratorSignals.Signal_FFmpegDetected.emit
        )
        self.ui.Button_Install_FFmpeg.setText('')
        self.ui.Button_Install_FFmpeg.setCheckable(True)
        self.ui.Button_Install_FFmpeg.setToolTipDuration(-1)
        self.ui.Button_Install_FFmpeg.setToolTip(QCA.translate("ToolTip", "重新下载"))
        EnvConfiguratorSignals.Signal_FFmpegUndetected.connect(
            lambda: Config.EditConfig('Env', 'FFmpeg', 'Undetected'),
        )
        EnvConfiguratorSignals.Signal_FFmpegUndetected.connect(
            lambda: Function_ShowMessageBox(
                WindowTitle = "Tip",
                Text = "未检测到FFmpeg，已开始下载",
                EventButtons = [QMessageBox.Ok],
                EventLists = [[self.ui.Button_Menu_Download.click]],
                ParamLists = [[()]]
            )
        )
        EnvConfiguratorSignals.Signal_FFmpegInstalled.connect(#self.ui.Button_Install_FFmpeg.click)
            lambda: EnvConfiguratorSignals.Signal_FFmpegDetected.emit()
        )
        EnvConfiguratorSignals.Signal_FFmpegInstallFailed.connect(
            lambda: Function_ShowMessageBox(
                MessageType = QMessageBox.Warning,
                WindowTitle = "Warning",
                Text = "安装FFmpeg出错",
                EventButtons = [QMessageBox.Ok]
            )
        )
        EnvConfiguratorSignals.Signal_FFmpegDetected.connect(
            lambda: Config.EditConfig('Env', 'FFmpeg', 'Detected'),
            type = Qt.QueuedConnection
        )
        EnvConfiguratorSignals.Signal_FFmpegDetected.connect(
            lambda: self.ui.ProgressBar_Download_FFmpeg.setValue(100),
            type = Qt.QueuedConnection
        )
        EnvConfiguratorSignals.Signal_FFmpegStatus.connect(
            lambda Status: self.ui.Label_Download_FFmpeg_Status.setText(Status)
        )

        '''
        self.ui.Label_Download_GCC.setText("GCC")
        self.Function_SetMethodExecutor(
            ExecuteButton = self.ui.Button_Install_GCC,
            ProgressBar = self.ui.ProgressBar_Download_GCC,
            Method = GCC_Installer.Execute,
            Params = ()
        )
        MainWindowSignals.Signal_MainWindowShown.connect(
            self.ui.Button_Install_GCC.click #if Config.GetValue('Env', 'GCC', 'Undetected') == 'Undetected' else EnvConfiguratorSignals.Signal_GCCDetected.emit
        )
        self.ui.Button_Install_GCC.setText('')
        self.ui.Button_Install_GCC.setCheckable(True)
        self.ui.Button_Install_GCC.setToolTipDuration(-1)
        self.ui.Button_Install_GCC.setToolTip(QCA.translate("ToolTip", "重新下载"))
        EnvConfiguratorSignals.Signal_GCCUndetected.connect(
            lambda: Config.EditConfig('Env', 'GCC', 'Undetected'),
        )
        EnvConfiguratorSignals.Signal_GCCUndetected.connect(
            lambda: Function_ShowMessageBox(
                WindowTitle = "Tip",
                Text = "未检测到GCC，已开始下载",
                EventButtons = [QMessageBox.Ok],
                EventLists = [[self.ui.Button_Menu_Download.click]],
                ParamLists = [[()]]
            )
        )
        EnvConfiguratorSignals.Signal_GCCInstalled.connect(#self.ui.Button_Install_GCC.click)
            lambda: EnvConfiguratorSignals.Signal_GCCDetected.emit()
        )
        EnvConfiguratorSignals.Signal_GCCInstallFailed.connect(
            lambda: Function_ShowMessageBox(
                MessageType = QMessageBox.Warning,
                WindowTitle = "Warning",
                Text = "安装GCC出错",
                EventButtons = [QMessageBox.Ok]
            )
        )
        EnvConfiguratorSignals.Signal_GCCDetected.connect(
            lambda: Config.EditConfig('Env', 'GCC', 'Detected'),
            type = Qt.QueuedConnection
        )
        EnvConfiguratorSignals.Signal_GCCDetected.connect(
            lambda: self.ui.ProgressBar_Download_GCC.setValue(100),
            type = Qt.QueuedConnection
        )
        EnvConfiguratorSignals.Signal_GCCStatus.connect(
            lambda Status: self.ui.Label_Download_GCC_Status.setText(Status)
        )

        self.ui.Label_Download_CMake.setText("CMake")
        self.Function_SetMethodExecutor(
            ExecuteButton = self.ui.Button_Install_CMake,
            ProgressBar = self.ui.ProgressBar_Download_CMake,
            Method = CMake_Installer.Execute,
            Params = ()
        )
        EnvConfiguratorSignals.Signal_GCCDetected.connect(
            self.ui.Button_Install_CMake.click #if Config.GetValue('Env', 'CMake', 'Undetected') == 'Undetected' else EnvConfiguratorSignals.Signal_CMakeDetected.emit
        )
        self.ui.Button_Install_CMake.setText('')
        self.ui.Button_Install_CMake.setCheckable(True)
        self.ui.Button_Install_CMake.setToolTipDuration(-1)
        self.ui.Button_Install_CMake.setToolTip(QCA.translate("ToolTip", "重新下载"))
        EnvConfiguratorSignals.Signal_CMakeUndetected.connect(
            lambda: Config.EditConfig('Env', 'CMake', 'Undetected'),
        )
        EnvConfiguratorSignals.Signal_CMakeUndetected.connect(
            lambda: Function_ShowMessageBox(
                WindowTitle = "Tip",
                Text = "未检测到CMake，已开始下载",
                EventButtons = [QMessageBox.Ok],
                EventLists = [[self.ui.Button_Menu_Download.click]],
                ParamLists = [[()]]
            )
        )
        EnvConfiguratorSignals.Signal_CMakeInstalled.connect(#self.ui.Button_Install_CMake.click)
            lambda: EnvConfiguratorSignals.Signal_CMakeDetected.emit()
        )
        EnvConfiguratorSignals.Signal_CMakeInstallFailed.connect(
            lambda: Function_ShowMessageBox(
                MessageType = QMessageBox.Warning,
                WindowTitle = "Warning",
                Text = "安装CMake出错",
                EventButtons = [QMessageBox.Ok]
            )
        )
        EnvConfiguratorSignals.Signal_CMakeDetected.connect(
            lambda: Config.EditConfig('Env', 'CMake', 'Detected'),
            type = Qt.QueuedConnection
        )
        EnvConfiguratorSignals.Signal_CMakeDetected.connect(
            lambda: self.ui.ProgressBar_Download_CMake.setValue(100),
            type = Qt.QueuedConnection
        )
        EnvConfiguratorSignals.Signal_CMakeStatus.connect(
            lambda Status: self.ui.Label_Download_CMake_Status.setText(Status)
        )
        '''

        self.ui.Label_Download_Python.setText("Python")
        self.Function_SetMethodExecutor(
            ExecuteButton = self.ui.Button_Install_Python,
            ProgressBar = self.ui.ProgressBar_Download_Python,
            Method = Python_Installer.Execute,
            Params = ('3.9', )
        )
        MainWindowSignals.Signal_MainWindowShown.connect( #EnvConfiguratorSignals.Signal_CMakeDetected.connect(
            self.ui.Button_Install_Python.click #if Config.GetValue('Env', 'Python', 'Undetected') == 'Undetected' else EnvConfiguratorSignals.Signal_PythonDetected.emit
        )
        self.ui.Button_Install_Python.setText('')
        self.ui.Button_Install_Python.setCheckable(True)
        self.ui.Button_Install_Python.setToolTipDuration(-1)
        self.ui.Button_Install_Python.setToolTip(QCA.translate("ToolTip", "重新下载"))
        EnvConfiguratorSignals.Signal_PythonUndetected.connect(
            lambda: Config.EditConfig('Env', 'Python', 'Undetected'),
        )
        EnvConfiguratorSignals.Signal_PythonUndetected.connect(
            lambda: Function_ShowMessageBox(
                WindowTitle = "Tip",
                Text = "未检测到Python，已开始下载",
                EventButtons = [QMessageBox.Ok],
                EventLists = [[self.ui.Button_Menu_Download.click]],
                ParamLists = [[()]]
            )
        )
        EnvConfiguratorSignals.Signal_PythonInstalled.connect(#self.ui.Button_Install_Python.click)
            lambda: EnvConfiguratorSignals.Signal_PythonDetected.emit()
        )
        EnvConfiguratorSignals.Signal_PythonInstallFailed.connect(
            lambda: Function_ShowMessageBox(
                MessageType = QMessageBox.Warning,
                WindowTitle = "Warning",
                Text = "安装Python出错",
                EventButtons = [QMessageBox.Ok]
            )
        )
        EnvConfiguratorSignals.Signal_PythonDetected.connect(
            lambda: Config.EditConfig('Env', 'Python', 'Detected'),
            type = Qt.QueuedConnection
        )
        EnvConfiguratorSignals.Signal_PythonDetected.connect(
            lambda: self.ui.ProgressBar_Download_Python.setValue(100),
            type = Qt.QueuedConnection
        )
        EnvConfiguratorSignals.Signal_PythonStatus.connect(
            lambda Status: self.ui.Label_Download_Python_Status.setText(Status)
        )

        self.ui.Label_Download_PyReqs.setText("Python Requirements")
        self.Function_SetMethodExecutor(
            ExecuteButton = self.ui.Button_Install_PyReqs,
            ProgressBar = self.ui.ProgressBar_Download_PyReqs,
            Method = PyReqs_Installer.Execute,
            Params = (NormPath(Path(ResourceDir).joinpath('requirements.txt')), )
        )
        EnvConfiguratorSignals.Signal_PythonDetected.connect(
            self.ui.Button_Install_PyReqs.click #if Config.GetValue('Env', 'PyReqs', 'Undetected') == 'Undetected' else EnvConfiguratorSignals.Signal_PyReqsDetected.emit
        )
        self.ui.Button_Install_PyReqs.setText('')
        self.ui.Button_Install_PyReqs.setCheckable(True)
        self.ui.Button_Install_PyReqs.setToolTipDuration(-1)
        self.ui.Button_Install_PyReqs.setToolTip(QCA.translate("ToolTip", "重新下载"))
        EnvConfiguratorSignals.Signal_PyReqsUndetected.connect(
            lambda: Config.EditConfig('Env', 'PyReqs', 'Undetected'),
        )
        EnvConfiguratorSignals.Signal_PyReqsUndetected.connect(
            lambda: Function_ShowMessageBox(
                WindowTitle = "Tip",
                Text = "未检测到Python依赖库，已开始下载",
                EventButtons = [QMessageBox.Ok],
                EventLists = [[self.ui.Button_Menu_Download.click]],
                ParamLists = [[()]]
            )
        )
        EnvConfiguratorSignals.Signal_PyReqsInstalled.connect(#self.ui.Button_Install_PyReqs.click)
            lambda: EnvConfiguratorSignals.Signal_PyReqsDetected.emit()
        )
        EnvConfiguratorSignals.Signal_PythonInstallFailed.connect(
            lambda: Function_ShowMessageBox(
                MessageType = QMessageBox.Warning,
                WindowTitle = "Warning",
                Text = "安装Python依赖库出错",
                EventButtons = [QMessageBox.Ok]
            )
        )
        EnvConfiguratorSignals.Signal_PyReqsDetected.connect(
            lambda: Config.EditConfig('Env', 'PyReqs', 'Detected'),
            type = Qt.QueuedConnection
        )
        EnvConfiguratorSignals.Signal_PyReqsDetected.connect(
            lambda: self.ui.ProgressBar_Download_PyReqs.setValue(100),
            type = Qt.QueuedConnection
        )
        EnvConfiguratorSignals.Signal_PyReqsStatus.connect(
            lambda Status: self.ui.Label_Download_PyReqs_Status.setText(Status)
        )

        self.ui.Label_Download_Pytorch.setText("Pytorch")
        self.Function_SetMethodExecutor(
            ExecuteButton = self.ui.Button_Install_Pytorch,
            ProgressBar = self.ui.ProgressBar_Download_Pytorch,
            Method = Pytorch_Installer.Execute,
            Params = ()
        )
        EnvConfiguratorSignals.Signal_PythonDetected.connect(
            self.ui.Button_Install_Pytorch.click #if Config.GetValue('Env', 'Pytorch', 'Undetected') == 'Undetected' else EnvConfiguratorSignals.Signal_PytorchDetected.emit
        )
        self.ui.Button_Install_Pytorch.setText('')
        self.ui.Button_Install_Pytorch.setCheckable(True)
        self.ui.Button_Install_Pytorch.setToolTipDuration(-1)
        self.ui.Button_Install_Pytorch.setToolTip(QCA.translate("ToolTip", "重新下载"))
        EnvConfiguratorSignals.Signal_PytorchUndetected.connect(
            lambda: Config.EditConfig('Env', 'Pytorch', 'Undetected'),
        )
        EnvConfiguratorSignals.Signal_PytorchUndetected.connect(
            lambda: Function_ShowMessageBox(
                WindowTitle = "Tip",
                Text = "未检测到Pytorch，已开始下载",
                EventButtons = [QMessageBox.Ok],
                EventLists = [[self.ui.Button_Menu_Download.click]],
                ParamLists = [[()]]
            )
        )
        EnvConfiguratorSignals.Signal_PytorchInstalled.connect(#self.ui.Button_Install_Pytorch.click)
            lambda: EnvConfiguratorSignals.Signal_PytorchDetected.emit()
        )
        EnvConfiguratorSignals.Signal_PytorchInstallFailed.connect(
            lambda: Function_ShowMessageBox(
                MessageType = QMessageBox.Warning,
                WindowTitle = "Warning",
                Text = "安装Pytorch出错",
                EventButtons = [QMessageBox.Ok]
            )
        )
        EnvConfiguratorSignals.Signal_PytorchDetected.connect(
            lambda: Config.EditConfig('Env', 'Pytorch', 'Detected'),
            type = Qt.QueuedConnection
        )
        EnvConfiguratorSignals.Signal_PytorchDetected.connect(
            lambda: self.ui.ProgressBar_Download_Pytorch.setValue(100),
            type = Qt.QueuedConnection
        )
        EnvConfiguratorSignals.Signal_PytorchStatus.connect(
            lambda Status: self.ui.Label_Download_Pytorch_Status.setText(Status)
        )

        #############################################################
        ####################### Content: Models #####################
        #############################################################

        self.ui.ToolButton_Models_ASR_Title.setText(QCA.translate("ToolButton", 'ASR'))
        self.ui.ToolButton_Models_ASR_Title.setCheckable(True)
        self.ui.ToolButton_Models_ASR_Title.setChecked(True)
        self.ui.ToolButton_Models_ASR_Title.setAutoExclusive(True)
        self.ui.ToolButton_Models_ASR_Title.clicked.connect(
            lambda: Function_AnimateStackedWidget(
                Parent = self,
                StackedWidget = self.ui.StackedWidget_Pages_Process,
                TargetIndex = 0
            )
        )
        self.ui.ToolButton_Models_ASR_Title.setToolTip(
            "语音识别模型"
        )

        self.ui.ToolButton_Models_STT_Title.setText(QCA.translate("ToolButton", 'STT'))
        self.ui.ToolButton_Models_STT_Title.setCheckable(True)
        self.ui.ToolButton_Models_STT_Title.setChecked(False)
        self.ui.ToolButton_Models_STT_Title.setAutoExclusive(True)
        self.ui.ToolButton_Models_STT_Title.clicked.connect(
            lambda: Function_AnimateStackedWidget(
                Parent = self,
                StackedWidget = self.ui.StackedWidget_Pages_Process,
                TargetIndex = 1
            )
        )
        self.ui.ToolButton_Models_STT_Title.setToolTip(
            "语音转文字模型"
        )

        self.ui.ToolButton_Models_TTS_Title.setText(QCA.translate("ToolButton", 'TTS'))
        self.ui.ToolButton_Models_TTS_Title.setCheckable(True)
        self.ui.ToolButton_Models_TTS_Title.setChecked(False)
        self.ui.ToolButton_Models_TTS_Title.setAutoExclusive(True)
        self.ui.ToolButton_Models_TTS_Title.clicked.connect(
            lambda: Function_AnimateStackedWidget(
                Parent = self,
                StackedWidget = self.ui.StackedWidget_Pages_Process,
                TargetIndex = 0
            )
        )
        self.ui.ToolButton_Models_TTS_Title.setToolTip(
            "文字转语音模型"
        )

        '''
        #############################################################
        ###################### Content: Tools #######################
        #############################################################

        DialogBox = MessageBox_Stacked()
        DialogBox.setWindowTitle('Guidance（该引导仅出现一次）')
        DialogBox.SetContent(
            [
                NormPath(Path(ResourceDir).joinpath('Sources/Guidance0.png')),
                NormPath(Path(ResourceDir).joinpath('Sources/Guidance1.png')),
                NormPath(Path(ResourceDir).joinpath('Sources/Guidance2.png')),
                NormPath(Path(ResourceDir).joinpath('Sources/Guidance3.png')),
                NormPath(Path(ResourceDir).joinpath('Sources/Guidance4.png')),
            ],
            [
                '欢迎来到工具界面！这里集成了EVT目前支持的所有工具，来快速熟悉一下使用方法吧',
                '顶部区域用于切换当前工具',
                '中间区域用于设置当前工具的各项参数，从左至右依次为目录、设置、预览',
                '底部区域用于执行当前工具',
                '工具之间会自动继承可关联的参数选项，如果不希望这样可以到设置页面关闭该功能'
            ]
        )
        #DialogBox.setStandardButtons(QMessageBox.Ok)
        self.ui.Button_Menu_Tools.clicked.connect(
            lambda: DialogBox.exec() if eval(Config.GetValue('Dialog', 'GuidanceShown', 'False')) is False else None,
            type = Qt.QueuedConnection
        )
        self.ui.Button_Menu_Tools.clicked.connect(
            lambda: Config.EditConfig('Dialog', 'GuidanceShown', 'True'),
            type = Qt.QueuedConnection
        )
        '''

        #############################################################
        ###################### Content: Process #####################
        #############################################################
        # 将媒体文件批量转换为音频文件，然后自动切除音频的静音部分

        self.ui.ToolButton_AudioProcessor_Title.setText(QCA.translate("ToolButton", '音频基本处理'))
        self.ui.ToolButton_AudioProcessor_Title.setCheckable(True)
        self.ui.ToolButton_AudioProcessor_Title.setChecked(True)
        self.ui.ToolButton_AudioProcessor_Title.setAutoExclusive(True)
        self.ui.ToolButton_AudioProcessor_Title.clicked.connect(
            lambda: Function_AnimateStackedWidget(
                Parent = self,
                StackedWidget = self.ui.StackedWidget_Pages_Process,
                TargetIndex = 0
            )
        )

        Path_Config_Process = NormPath(Path(CurrentDir).joinpath('Config', 'Config_Process.ini'))
        Config_Process = ManageConfig(
            Config.GetValue(
                'ConfigPath',
                'Path_Config_Process',
                Path_Config_Process
            )
        )

        # Middle
        self.ui.GroupBox_EssentialParams_Process.setTitle(QCA.translate("GroupBox", "必要参数"))

        self.ui.CheckBox_Toggle_BasicSettings_Process.setCheckable(True)
        self.ui.CheckBox_Toggle_BasicSettings_Process.setChecked(
            True #eval(Config_Process.GetValue('AudioProcessor', 'Toggle_BasicSettings', ''))
        )
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_Toggle_BasicSettings_Process,
            CheckedText = "基础设置",
            CheckedEventList = [
                Function_AnimateFrame,
                #Config_Process.EditConfig
            ],
            CheckedArgsList = [
                (
                    self, self.ui.Frame_BasicSettings_Process,
                    None, None,
                    0, self.ui.Frame_BasicSettings_Process.sizeHint().height(),
                    210,
                    'Extend'
                ),
                #('AudioProcessor', 'Toggle_BasicSettings', 'True')
            ],
            UncheckedText = "基础设置",
            UncheckedEventList = [
                Function_AnimateFrame,
                #Config_Process.EditConfig
            ],
            UncheckedArgsList = [
                (
                    self, self.ui.Frame_BasicSettings_Process,
                    None, None,
                    0, self.ui.Frame_BasicSettings_Process.sizeHint().height(),
                    210,
                    'Reduce'
                ),
                #('AudioProcessor', 'Toggle_BasicSettings', 'False')
            ],
            TakeEffect = True
        )

        Function_SetText(
            Widget = self.ui.Label_Process_Media_Dir_Input,
            Text = SetRichText(
                Title = QCA.translate("Label", "媒体输入目录"),
                Body = QCA.translate("Label", "该目录中的媒体文件将会以下列设置输出为音频文件。")
            )
        )
        Function_SetFileDialog(
            Button = self.ui.Button_Process_Media_Dir_Input,
            LineEdit = self.ui.LineEdit_Process_Media_Dir_Input,
            Mode = "SelectDir"
        )
        Function_SetText(
            Widget = self.ui.LineEdit_Process_Media_Dir_Input,
            Text = str(Config_Process.GetValue('AudioProcessor', 'Media_Dir_Input', '')),
            SetPlaceholderText = True
        )
        self.ui.LineEdit_Process_Media_Dir_Input.textChanged.connect(
            lambda Value: Config_Process.EditConfig('AudioProcessor', 'Media_Dir_Input', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_Process_Media_Format_Output,
            Text = SetRichText(
                Title = QCA.translate("Label", "媒体输出格式"),
                Body = QCA.translate("Label", "媒体文件将会以设置的格式输出为音频文件，若维持不变则保持'None'即可。")
            )
        )
        self.ui.ComboBox_Process_Media_Format_Output.addItems(['flac', 'wav', 'mp3', 'aac', 'm4a', 'wma', 'aiff', 'au', 'ogg', 'None'])
        self.ui.ComboBox_Process_Media_Format_Output.setCurrentText(
            str(Config_Process.GetValue('AudioProcessor', 'Media_Format_Output', 'wav'))
        )
        self.ui.ComboBox_Process_Media_Format_Output.currentTextChanged.connect(
            lambda Value: Config_Process.EditConfig('AudioProcessor', 'Media_Format_Output', str(Value))
        )

        '''
        Function_SetText(
            Widget = self.ui.Label_Process_Denoise_Audio,
            Text = SetRichText(
                Title = "启用杂音去除",
                Body = QCA.translate("Label", "音频中的非人声部分将被弱化。")
            )
        )
        self.ui.CheckBox_Process_Denoise_Audio.setCheckable(True)
        self.ui.CheckBox_Process_Denoise_Audio.setChecked(
            eval(Config_Process.GetValue('AudioProcessor', 'Denoise_Audio', 'True'))
        )
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_Process_Denoise_Audio,
            CheckedText = "已启用",
            CheckedEventList = [
                Config_Process.EditConfig
            ],
            CheckedArgsList = [
                ('AudioProcessor', 'Denoise_Audio', 'True')
            ],
            UncheckedText = "未启用",
            UncheckedEventList = [
                Config_Process.EditConfig
            ],
            UncheckedArgsList = [
                ('AudioProcessor', 'Denoise_Audio', 'False')
            ],
            TakeEffect = True
        )
        '''

        Function_SetText(
            Widget = self.ui.Label_Process_Slice_Audio,
            Text = SetRichText(
                Title = "启用静音切除",
                Body = QCA.translate("Label", "音频中的静音部分将被切除。")
            )
        )
        self.ui.CheckBox_Process_Slice_Audio.setCheckable(True)
        self.ui.CheckBox_Process_Slice_Audio.setChecked(
            eval(Config_Process.GetValue('AudioProcessor', 'Slice_Audio', 'True'))
        )
        def TempFunction_HideWidgets(SetVisible):
            for Frame in (self.ui.Frame_Process_RMS_Threshold,self.ui.Frame_Process_Hop_Size,self.ui.Frame_Process_Silent_Interval_Min,self.ui.Frame_Process_Silence_Kept_Max,self.ui.Frame_Process_Audio_Length_Min):
                Frame.setVisible(SetVisible)
            if self.ui.CheckBox_Toggle_AdvanceSettings_Process.isChecked():
                Function_AnimateFrame(
                    Parent = self,
                    Frame = self.ui.Frame_AdvanceSettings_Process,
                    MinHeight = self.ui.Frame_Process_SampleRate.height()+self.ui.Frame_Process_SampleWidth.height()+self.ui.Frame_Process_ToMono.height(),
                    MaxHeight = self.ui.Frame_AdvanceSettings_Process.sizeHint().height() if SetVisible else (self.ui.Frame_Process_SampleRate.height()+self.ui.Frame_Process_SampleWidth.height()+self.ui.Frame_Process_ToMono.height()),
                    Duration = 210,
                    Mode = 'Extend' if SetVisible else 'Reduce'
                )
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_Process_Slice_Audio,
            CheckedText = "已启用",
            CheckedEventList = [
                Config_Process.EditConfig,
                TempFunction_HideWidgets
            ],
            CheckedArgsList = [
                ('AudioProcessor', 'Slice_Audio', 'True'),
                (True)
            ],
            UncheckedText = "未启用",
            UncheckedEventList = [
                Config_Process.EditConfig,
                TempFunction_HideWidgets
            ],
            UncheckedArgsList = [
                ('AudioProcessor', 'Slice_Audio', 'False'),
                (False)
            ],
            TakeEffect = True
        )

        Function_SetText(
            Widget = self.ui.Label_Process_Media_Dir_Output,
            Text = SetRichText(
                Title = QCA.translate("Label", "媒体输出目录"),
                Body = QCA.translate("Label", "最后生成的音频文件将被保存到该目录中。")
            )
        )
        Function_SetFileDialog(
            Button = self.ui.Button_Process_Media_Dir_Output,
            LineEdit = self.ui.LineEdit_Process_Media_Dir_Output,
            Mode = "SelectDir"
        )
        Function_SetText(
            Widget = self.ui.LineEdit_Process_Media_Dir_Output,
            Text = str(Config_Process.GetValue('AudioProcessor', 'Media_Dir_Output', '')),
            SetPlaceholderText = True
        )
        self.ui.LineEdit_Process_Media_Dir_Output.textChanged.connect(
            lambda Value: Config_Process.EditConfig('AudioProcessor', 'Media_Dir_Output', str(Value))
        )
        '''
        self.ui.LineEdit_Process_Media_Dir_Output.textChanged.connect(
            lambda Value: Function_ShowMessageBox(
                MessageType = QMessageBox.Warning,
                WindowTitle = "Warning",
                Text = "输出路径与输入路径相同"
            ) if Value == self.ui.LineEdit_Process_Media_Dir_Input.text() else None
        )
        '''

        self.ui.CheckBox_Toggle_AdvanceSettings_Process.setCheckable(True)
        self.ui.CheckBox_Toggle_AdvanceSettings_Process.setChecked(
            False #eval(Config_Process.GetValue('AudioProcessor', 'Toggle_AdvanceSettings', ''))
        )
        def TempFunction_ExtendVisibleWidgets(Visualize):
            AlteredMaxHeight = self.ui.Frame_Process_SampleRate.height()+self.ui.Frame_Process_SampleWidth.height()+self.ui.Frame_Process_ToMono.height()
            Function_AnimateFrame(
                Parent = self,
                Frame = self.ui.Frame_AdvanceSettings_Process,
                MinHeight = 0,
                MaxHeight = self.ui.Frame_AdvanceSettings_Process.sizeHint().height() if self.ui.CheckBox_Process_Slice_Audio.isChecked() else AlteredMaxHeight,
                Duration = 210,
                Mode = 'Extend' if Visualize else 'Reduce'
            )
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_Toggle_AdvanceSettings_Process,
            CheckedText = "高级设置",
            CheckedEventList = [
                TempFunction_ExtendVisibleWidgets,
                #Config_Process.EditConfig
            ],
            CheckedArgsList = [
                (True),
                #('AudioProcessor', 'Toggle_AdvanceSettings', 'True')
            ],
            UncheckedText = "高级设置",
            UncheckedEventList = [
                TempFunction_ExtendVisibleWidgets,
                #Config_Process.EditConfig
            ],
            UncheckedArgsList = [
                (False),
                #('AudioProcessor', 'Toggle_AdvanceSettings', 'False')
            ],
            TakeEffect = True
        )

        Function_SetText(
            Widget = self.ui.Label_Process_RMS_Threshold,
            Text = SetRichText(
                Title = QCA.translate("Label", "均方根阈值 (db)"),
                Body = QCA.translate("Label", "低于该阈值的片段将被视作静音进行处理，若有降噪需求可以增加该值。")
            )
        )
        self.ui.DoubleSpinBox_Process_RMS_Threshold.setRange(-100, 0)
        #self.ui.DoubleSpinBox_Process_RMS_Threshold.setSingleStep(0.01)
        self.ui.DoubleSpinBox_Process_RMS_Threshold.setValue(
            float(Config_Process.GetValue('AudioProcessor', 'RMS_Threshold', '-40.'))
        )
        self.ui.DoubleSpinBox_Process_RMS_Threshold.valueChanged.connect(
            lambda Value: Config_Process.EditConfig('AudioProcessor', 'RMS_Threshold', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_Process_Hop_Size,
            Text = SetRichText(
                Title = QCA.translate("Label", "跃点大小 (ms)"),
                Body = QCA.translate("Label", "每个RMS帧的长度，增加该值能够提高分割精度但会减慢进程。")
            )
        )
        self.ui.SpinBox_Process_Hop_Size.setRange(0, 100)
        self.ui.SpinBox_Process_Hop_Size.setSingleStep(1)
        self.ui.SpinBox_Process_Hop_Size.setValue(
            int(Config_Process.GetValue('AudioProcessor', 'Hop_Size', '10'))
        )
        self.ui.SpinBox_Process_Hop_Size.valueChanged.connect(
            lambda Value: Config_Process.EditConfig('AudioProcessor', 'Hop_Size', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_Process_Silent_Interval_Min,
            Text = SetRichText(
                Title = QCA.translate("Label", "最小静音间隔 (ms)"),
                Body = QCA.translate("Label", "静音部分被分割成的最小长度，若音频只包含短暂中断可以减小该值。")
            )
        )
        self.ui.SpinBox_Process_Silent_Interval_Min.setRange(0, 3000)
        self.ui.SpinBox_Process_Silent_Interval_Min.setSingleStep(1)
        self.ui.SpinBox_Process_Silent_Interval_Min.setValue(
            int(Config_Process.GetValue('AudioProcessor', 'Silent_Interval_Min', '300'))
        )
        self.ui.SpinBox_Process_Silent_Interval_Min.valueChanged.connect(
            lambda Value: Config_Process.EditConfig('AudioProcessor', 'Silent_Interval_Min', str(Value))
        )
        self.ui.SpinBox_Process_Silent_Interval_Min.setToolTipDuration(-1)
        self.ui.SpinBox_Process_Silent_Interval_Min.setToolTip(QCA.translate("ToolTip", "注意：这个值必须小于最小音频长度，大于跃点大小。"))

        Function_SetText(
            Widget = self.ui.Label_Process_Silence_Kept_Max,
            Text = SetRichText(
                Title = QCA.translate("Label", "最大静音长度 (ms)"),
                Body = QCA.translate("Label", "被分割的音频周围保持静音的最大长度。")
            )
        )
        self.ui.SpinBox_Process_Silence_Kept_Max.setRange(0, 10000)
        self.ui.SpinBox_Process_Silence_Kept_Max.setSingleStep(1)
        self.ui.SpinBox_Process_Silence_Kept_Max.setValue(
            int(Config_Process.GetValue('AudioProcessor', 'Silence_Kept_Max', '1000'))
        )
        self.ui.SpinBox_Process_Silence_Kept_Max.valueChanged.connect(
            lambda Value: Config_Process.EditConfig('AudioProcessor', 'Silence_Kept_Max', str(Value))
        )
        self.ui.SpinBox_Process_Silence_Kept_Max.setToolTipDuration(-1)
        self.ui.SpinBox_Process_Silence_Kept_Max.setToolTip(QCA.translate("ToolTip", "注意：这个值无需完全对应被分割音频中的静音长度。算法将自行检索最佳的分割位置。"))

        Function_SetText(
            Widget = self.ui.Label_Process_Audio_Length_Min,
            Text = SetRichText(
                Title = QCA.translate("Label", "最小音频长度 (ms)"),
                Body = QCA.translate("Label", "每个被分割的音频片段所需的最小长度。")
            )
        )
        self.ui.SpinBox_Process_Audio_Length_Min.setRange(300, 30000)
        self.ui.SpinBox_Process_Audio_Length_Min.setSingleStep(1)
        self.ui.SpinBox_Process_Audio_Length_Min.setValue(
            int(Config_Process.GetValue('AudioProcessor', 'Audio_Length_Min', '3000'))
        )
        self.ui.SpinBox_Process_Audio_Length_Min.valueChanged.connect(
            lambda Value: Config_Process.EditConfig('AudioProcessor', 'Audio_Length_Min', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_Process_ToMono,
            Text = SetRichText(
                Title = "合并声道",
                Body = QCA.translate("Label", "将输出音频的声道合并为单声道。")
            )
        )
        self.ui.CheckBox_Process_ToMono.setCheckable(True)
        self.ui.CheckBox_Process_ToMono.setChecked(
            eval(Config_Process.GetValue('AudioProcessor', 'ToMono', 'False'))
        )
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_Process_ToMono,
            CheckedText = "已启用",
            CheckedEventList = [
                Config_Process.EditConfig
            ],
            CheckedArgsList = [
                ('AudioProcessor', 'ToMono', 'True')
            ],
            UncheckedText = "未启用",
            UncheckedEventList = [
                Config_Process.EditConfig
            ],
            UncheckedArgsList = [
                ('AudioProcessor', 'ToMono', 'False')
            ],
            TakeEffect = True
        )

        Function_SetText(
            Widget = self.ui.Label_Process_SampleRate,
            Text = SetRichText(
                Title = "输出采样率",
                Body = QCA.translate("Label", "输出音频所拥有的采样率，若维持不变则保持'None'即可。")
            )
        )
        self.ui.ComboBox_Process_SampleRate.addItems(['22050', '44100', '48000', '96000', '192000', 'None'])
        self.ui.ComboBox_Process_SampleRate.setCurrentText(
            str(Config_Process.GetValue('AudioProcessor', 'SampleRate', 'None'))
        )
        self.ui.ComboBox_Process_SampleRate.currentTextChanged.connect(
            lambda Value: Config_Process.EditConfig('AudioProcessor', 'SampleRate', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_Process_SampleWidth,
            Text = SetRichText(
                Title = "输出采样位数",
                Body = QCA.translate("Label", "输出音频所拥有的采样位数，若维持不变则保持'None'即可。")
            )
        )
        self.ui.ComboBox_Process_SampleWidth.addItems(['8', '16', '24', '32', '32 (Float)', 'None'])
        self.ui.ComboBox_Process_SampleWidth.setCurrentText(
            str(Config_Process.GetValue('AudioProcessor', 'SampleWidth', 'None'))
        )
        self.ui.ComboBox_Process_SampleWidth.currentTextChanged.connect(
            lambda Value: Config_Process.EditConfig('AudioProcessor', 'SampleWidth', str(Value))
        )

        # Left
        Function_SetTreeWidget(
            TreeWidget = self.ui.TreeWidget_Catalogue_Process,
            RootItemTexts = [self.ui.GroupBox_EssentialParams_Process.title()],
            ChildItemTexts = [(self.ui.CheckBox_Toggle_BasicSettings_Process.text(),self.ui.CheckBox_Toggle_AdvanceSettings_Process.text())],
            AddVertically = True
        )
        Function_ScrollToWidget(
            Trigger = self.ui.TreeWidget_Catalogue_Process.topLevelItem(0),
            TargetWidget = self.ui.GroupBox_EssentialParams_Process,
            ScrollArea = self.ui.ScrollArea_Middle_Process
        )
        Function_ScrollToWidget(
            Trigger = self.ui.TreeWidget_Catalogue_Process.topLevelItem(0).child(0),
            TargetWidget = self.ui.Frame_BasicSettings_Process,
            ScrollArea = self.ui.ScrollArea_Middle_Process
        )
        Function_ScrollToWidget(
            Trigger = self.ui.TreeWidget_Catalogue_Process.topLevelItem(0).child(1),
            TargetWidget = self.ui.Frame_AdvanceSettings_Process,
            ScrollArea = self.ui.ScrollArea_Middle_Process
        )

        # Right
        MonitorFile_Config_AudioProcessor = MonitorFile(
            Config.GetValue('ConfigPath', 'Path_Config_Process')
        )
        MonitorFile_Config_AudioProcessor.start()
        MonitorFile_Config_AudioProcessor.Signal_FileContent.connect(
            lambda FileContent: self.ui.TextBrowser_Params_Process.setText(
                FileContent
            )
        )

        self.ui.Button_CheckOutput_Process.setText(QCA.translate("Button", "打开输出目录"))
        Function_SetURL(
            Button = self.ui.Button_CheckOutput_Process,
            URL = self.ui.LineEdit_Process_Media_Dir_Output,
            ButtonTooltip = "Click to open"
        )

        # Bottom
        self.ui.Button_Process_Execute.setToolTipDuration(-1)
        self.ui.Button_Process_Execute.setToolTip(QCA.translate("ToolTip", "执行音频基本处理"))
        self.ui.Button_Process_Terminate.setToolTipDuration(-1)
        self.ui.Button_Process_Terminate.setToolTip(QCA.translate("ToolTip", "终止音频基本处理"))
        self.Function_SetMethodExecutor(
            ExecuteButton = self.ui.Button_Process_Execute,
            TerminateButton = self.ui.Button_Process_Terminate,
            ProgressBar = self.ui.ProgressBar_Process,
            ConsoleFrame = self.ui.Frame_Console,
            Method = Execute_Audio_Processing.Execute,
            ParamsFrom = [
                self.ui.LineEdit_Process_Media_Dir_Input,
                self.ui.LineEdit_Process_Media_Dir_Output,
                self.ui.ComboBox_Process_Media_Format_Output,
                self.ui.ComboBox_Process_SampleRate,
                self.ui.ComboBox_Process_SampleWidth,
                self.ui.CheckBox_Process_ToMono,
                #self.ui.CheckBox_Process_Denoise_Audio,
                self.ui.CheckBox_Process_Slice_Audio,
                self.ui.DoubleSpinBox_Process_RMS_Threshold,
                self.ui.SpinBox_Process_Audio_Length_Min,
                self.ui.SpinBox_Process_Silent_Interval_Min,
                self.ui.SpinBox_Process_Hop_Size,
                self.ui.SpinBox_Process_Silence_Kept_Max
            ],
            EmptyAllowed = [
                self.ui.ComboBox_Process_Media_Format_Output,
                self.ui.ComboBox_Process_SampleRate,
                self.ui.ComboBox_Process_SampleWidth
            ],
            FinishEventList = [
                Function_ShowMessageBox
            ],
            FinishParamList = [
                (
                    QMessageBox.Question, "Ask",
                    "当前任务已执行结束，是否跳转至下一工具界面？",
                    QMessageBox.Yes|QMessageBox.No, [QMessageBox.Yes],
                    [[self.ui.Button_Menu_ASR.click]], [[()]]
                )
            ]
        )

        #############################################################
        ######################## Content: ASR #######################
        #############################################################
        # 在不同说话人的音频中批量筛选出属于同一说话人的音频。用户需要提供一段包含目标说话人的语音作为期望值

        self.ui.ToolButton_VoiceIdentifier_Title.setText(QCA.translate("ToolButton", "VPR"))
        self.ui.ToolButton_VoiceIdentifier_Title.setCheckable(True)
        self.ui.ToolButton_VoiceIdentifier_Title.setChecked(True)
        self.ui.ToolButton_VoiceIdentifier_Title.setAutoExclusive(True)
        self.ui.ToolButton_VoiceIdentifier_Title.clicked.connect(
            lambda: Function_AnimateStackedWidget(
                Parent = self,
                StackedWidget = self.ui.StackedWidget_Pages_ASR,
                TargetIndex = 0
            )
        )

        Path_Config_ASR_VPR = NormPath(Path(CurrentDir).joinpath('Config', 'Config_ASR_VPR.ini'))
        Config_ASR_VPR = ManageConfig(
            Config.GetValue(
                'ConfigPath',
                'Path_Config_ASR_VPR',
                Path_Config_ASR_VPR
            )
        )

        # Middle
        self.ui.GroupBox_EssentialParams_ASR_VPR.setTitle("必要参数")

        self.ui.CheckBox_Toggle_BasicSettings_ASR_VPR.setCheckable(True)
        self.ui.CheckBox_Toggle_BasicSettings_ASR_VPR.setChecked(
            True #eval(Config_ASR_VPR.GetValue('VoiceIdentifier', 'Toggle_BasicSettings', ''))
        )
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_Toggle_BasicSettings_ASR_VPR,
            CheckedText = "基础设置",
            CheckedEventList = [
                Function_AnimateFrame,
                #Config_ASR_VPR.EditConfig
            ],
            CheckedArgsList = [
                (
                    self, self.ui.Frame_BasicSettings_ASR_VPR,
                    None, None,
                    0, self.ui.Frame_BasicSettings_ASR_VPR.sizeHint().height(),
                    210,
                    'Extend'
                ),
                #('VoiceIdentifier', 'Toggle_BasicSettings', 'True')
            ],
            UncheckedText = "基础设置",
            UncheckedEventList = [
                Function_AnimateFrame,
                #Config_ASR_VPR.EditConfig
            ],
            UncheckedArgsList = [
                (
                    self, self.ui.Frame_BasicSettings_ASR_VPR,
                    None, None,
                    0, self.ui.Frame_BasicSettings_ASR_VPR.sizeHint().height(),
                    210,
                    'Reduce'
                ),
                #('VoiceIdentifier', 'Toggle_BasicSettings', 'False')
            ],
            TakeEffect = True
        )

        Function_SetText(
            Widget = self.ui.Label_ASR_VPR_Audio_Dir_Input,
            Text = SetRichText(
                Title = "音频输入目录",
                Body = QCA.translate("Label", "该目录中的音频文件将会按照以下设置进行识别筛选。")
            )
        )
        Function_SetFileDialog(
            Button = self.ui.Button_ASR_VPR_Audio_Dir_Input,
            LineEdit = self.ui.LineEdit_ASR_VPR_Audio_Dir_Input,
            Mode = "SelectDir"
        )
        Function_SetText(
            Widget = self.ui.LineEdit_ASR_VPR_Audio_Dir_Input,
            Text = str(Config_ASR_VPR.GetValue('VoiceIdentifier', 'Audio_Dir_Input', '')),
            SetPlaceholderText = True
        )
        self.ui.LineEdit_ASR_VPR_Audio_Dir_Input.textChanged.connect(
            lambda Value: Config_ASR_VPR.EditConfig('VoiceIdentifier', 'Audio_Dir_Input', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_ASR_VPR_StdAudioSpeaker,
            Text = SetRichText(
                Title = "目标人物与音频",
                Body = QCA.translate("Label", "目标人物的名字及其语音文件的所在路径，音频中尽量不要混入杂音。")
            )
        )
        self.ui.Table_ASR_VPR_StdAudioSpeaker.SetHorizontalHeaders(['人物姓名', '音频路径', '增删'])
        self.ui.Table_ASR_VPR_StdAudioSpeaker.SetValue(
            eval(Config_ASR_VPR.GetValue('VoiceIdentifier', 'StdAudioSpeaker', '{"": ""}')),
            FileType = "音频类型 (*.mp3 *.aac *.wav *.flac)"
        )
        self.ui.Table_ASR_VPR_StdAudioSpeaker.ValueChanged.connect(
            lambda Value: Config_ASR_VPR.EditConfig('VoiceIdentifier', 'StdAudioSpeaker', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_ASR_VPR_DecisionThreshold,
            Text = SetRichText(
                Title = "判断阈值",
                Body = QCA.translate("Label", "判断是否为同一人的阈值，若参与比对的说话人声音相识度较高可以增加该值。")
            )
        )
        self.ui.DoubleSpinBox_ASR_VPR_DecisionThreshold.setRange(0.5, 1)
        self.ui.DoubleSpinBox_ASR_VPR_DecisionThreshold.setSingleStep(0.01)
        self.ui.DoubleSpinBox_ASR_VPR_DecisionThreshold.setValue(
            float(Config_ASR_VPR.GetValue('VoiceIdentifier', 'DecisionThreshold', '0.75'))
        )
        self.ui.DoubleSpinBox_ASR_VPR_DecisionThreshold.valueChanged.connect(
            lambda Value: Config_ASR_VPR.EditConfig('VoiceIdentifier', 'DecisionThreshold', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_ASR_VPR_Audio_Dir_Output,
            Text = SetRichText(
                Title = "音频输出目录",
                Body = QCA.translate("Label", "最后筛选出的音频文件将被复制到该目录中。")
            )
        )
        Function_SetFileDialog(
            Button = self.ui.Button_ASR_VPR_Audio_Dir_Output,
            LineEdit = self.ui.LineEdit_ASR_VPR_Audio_Dir_Output,
            Mode = "SelectDir"
        )
        Function_SetText(
            Widget = self.ui.LineEdit_ASR_VPR_Audio_Dir_Output,
            Text = str(Config_ASR_VPR.GetValue('VoiceIdentifier', 'Audio_Dir_Output', '')),
            SetPlaceholderText = True
        )
        self.ui.LineEdit_ASR_VPR_Audio_Dir_Output.textChanged.connect(
            lambda Value: Config_ASR_VPR.EditConfig('VoiceIdentifier', 'Audio_Dir_Output', str(Value))
        )

        self.ui.CheckBox_Toggle_AdvanceSettings_ASR_VPR.setCheckable(True)
        self.ui.CheckBox_Toggle_AdvanceSettings_ASR_VPR.setChecked(False)
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_Toggle_AdvanceSettings_ASR_VPR,
            CheckedText = "高级设置",
            CheckedEventList = [
                Function_AnimateFrame
            ],
            CheckedArgsList = [
                (
                    self, self.ui.Frame_AdvanceSettings_ASR_VPR,
                    None, None,
                    0, self.ui.Frame_AdvanceSettings_ASR_VPR.sizeHint().height(),
                    210,
                    'Extend'
                )
            ],
            UncheckedText = "高级设置",
            UncheckedEventList = [
                Function_AnimateFrame
            ],
            UncheckedArgsList = [
                (
                    self, self.ui.Frame_AdvanceSettings_ASR_VPR,
                    None, None,
                    0, self.ui.Frame_AdvanceSettings_ASR_VPR.sizeHint().height(),
                    210,
                    'Reduce'
                )
            ],
            TakeEffect = True
        )

        Function_SetText(
            Widget = self.ui.Label_ASR_VPR_Model_Dir,
            Text = SetRichText(
                Title = "模型存放目录",
                Body = QCA.translate("Label", "该目录将会用于存放下载的声纹识别模型，若模型已存在会直接使用。")
            )
        )
        Function_SetFileDialog(
            Button = self.ui.Button_ASR_VPR_Model_Dir,
            LineEdit = self.ui.LineEdit_ASR_VPR_Model_Dir,
            Mode = "SelectDir"
        )
        self.ui.LineEdit_ASR_VPR_Model_Dir.setText(
            str(Config_ASR_VPR.GetValue('VoiceIdentifier', 'Model_Dir', NormPath(Path(CurrentDir).joinpath('Models', 'ASR', 'VPR'), 'Posix')))
        )
        self.ui.LineEdit_ASR_VPR_Model_Dir.textChanged.connect(
            lambda Value: Config_ASR_VPR.EditConfig('VoiceIdentifier', 'Model_Dir', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_ASR_VPR_Model_Type,
            Text = SetRichText(
                Title = "模型类型",
                Body = QCA.translate("Label", "声纹识别模型的类型。")
            )
        )
        self.ui.ComboBox_ASR_VPR_Model_Type.addItems(['Ecapa-Tdnn'])
        self.ui.ComboBox_ASR_VPR_Model_Type.setCurrentText(
            str(Config_ASR_VPR.GetValue('VoiceIdentifier', 'Model_Type', 'Ecapa-Tdnn'))
        )
        self.ui.ComboBox_ASR_VPR_Model_Type.currentTextChanged.connect(
            lambda Value: Config_ASR_VPR.EditConfig('VoiceIdentifier', 'Model_Type', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_ASR_VPR_Model_Name,
            Text = SetRichText(
                Title = "模型名字",
                Body = QCA.translate("Label", "声纹识别模型的名字，默认代表模型的大小。")
            )
        )
        self.ui.ComboBox_ASR_VPR_Model_Name.addItems(['small'])
        self.ui.ComboBox_ASR_VPR_Model_Name.setCurrentText(
            str(Config_ASR_VPR.GetValue('VoiceIdentifier', 'Model_Name', 'small'))
        )
        self.ui.ComboBox_ASR_VPR_Model_Name.currentTextChanged.connect(
            lambda Value: Config_ASR_VPR.EditConfig('VoiceIdentifier', 'Model_Name', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_ASR_VPR_Feature_Method,
            Text = SetRichText(
                Title = "特征提取方法",
                Body = QCA.translate("Label", "音频特征的提取方法。")
            )
        )
        self.ui.ComboBox_ASR_VPR_Feature_Method.addItems(['spectrogram', 'melspectrogram'])
        self.ui.ComboBox_ASR_VPR_Feature_Method.setCurrentText(
            str(Config_ASR_VPR.GetValue('VoiceIdentifier', 'Feature_Method', 'spectrogram'))
        )
        self.ui.ComboBox_ASR_VPR_Feature_Method.currentTextChanged.connect(
            lambda Value: Config_ASR_VPR.EditConfig('VoiceIdentifier', 'Feature_Method', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_ASR_VPR_Duration_of_Audio,
            Text = SetRichText(
                Title = "音频长度",
                Body = QCA.translate("Label", "用于预测的音频长度。")
            )
        )
        self.ui.DoubleSpinBox_ASR_VPR_Duration_of_Audio.setRange(0, 30)
        #self.ui.DoubleSpinBox_ASR_VPR_Duration_of_Audio.setSingleStep(0.01)
        self.ui.DoubleSpinBox_ASR_VPR_Duration_of_Audio.setValue(
            float(Config_ASR_VPR.GetValue('VoiceIdentifier', 'Duration_of_Audio', '3.00'))
        )
        self.ui.DoubleSpinBox_ASR_VPR_Duration_of_Audio.textChanged.connect(
            lambda Value: Config_ASR_VPR.EditConfig('VoiceIdentifier', 'Duration_of_Audio', str(Value))
        )

        # Left
        Function_SetTreeWidget(
            TreeWidget = self.ui.TreeWidget_Catalogue_ASR_VPR,
            RootItemTexts = [self.ui.GroupBox_EssentialParams_ASR_VPR.title()],
            ChildItemTexts = [(self.ui.CheckBox_Toggle_BasicSettings_ASR_VPR.text(),self.ui.CheckBox_Toggle_AdvanceSettings_ASR_VPR.text())],
            AddVertically = True
        )
        Function_ScrollToWidget(
            Trigger = self.ui.TreeWidget_Catalogue_ASR_VPR.topLevelItem(0),
            TargetWidget = self.ui.GroupBox_EssentialParams_ASR_VPR,
            ScrollArea = self.ui.ScrollArea_Middle_ASR_VPR
        )
        Function_ScrollToWidget(
            Trigger = self.ui.TreeWidget_Catalogue_ASR_VPR.topLevelItem(0).child(0),
            TargetWidget = self.ui.Frame_BasicSettings_ASR_VPR,
            ScrollArea = self.ui.ScrollArea_Middle_ASR_VPR
        )
        Function_ScrollToWidget(
            Trigger = self.ui.TreeWidget_Catalogue_ASR_VPR.topLevelItem(0).child(1),
            TargetWidget = self.ui.Frame_AdvanceSettings_ASR_VPR,
            ScrollArea = self.ui.ScrollArea_Middle_ASR_VPR
        )

        # Right
        MonitorFile_Config_VoiceIdentifier = MonitorFile(
            Config.GetValue('ConfigPath', 'Path_Config_ASR_VPR')
        )
        MonitorFile_Config_VoiceIdentifier.start()
        MonitorFile_Config_VoiceIdentifier.Signal_FileContent.connect(
            lambda FileContent: self.ui.TextBrowser_Params_ASR_VPR.setText(
                FileContent
            )
        )

        self.ui.Button_SyncParams_ASR_VPR.setText(QCA.translate("Button", "关联参数设置"))
        Function_ParamsSynchronizer(
            Trigger = self.ui.Button_SyncParams_ASR_VPR,
            ParamsFrom = [
                self.ui.LineEdit_Process_Media_Dir_Output
            ],
            ParamsTo = [
                self.ui.LineEdit_ASR_VPR_Audio_Dir_Input
            ]
        )

        self.ui.Button_CheckOutput_ASR_VPR.setText(QCA.translate("Button", "打开输出目录"))
        Function_SetURL(
            Button = self.ui.Button_CheckOutput_ASR_VPR,
            URL = self.ui.LineEdit_ASR_VPR_Audio_Dir_Output,
            ButtonTooltip = "Click to open"
        )

        # Bottom
        self.ui.Button_ASR_VPR_Execute.setToolTipDuration(-1)
        self.ui.Button_ASR_VPR_Execute.setToolTip("执行语音识别和筛选")
        self.ui.Button_ASR_VPR_Terminate.setToolTipDuration(-1)
        self.ui.Button_ASR_VPR_Terminate.setToolTip("终止语音识别和筛选")
        self.Function_SetMethodExecutor(
            ExecuteButton = self.ui.Button_ASR_VPR_Execute,
            TerminateButton = self.ui.Button_ASR_VPR_Terminate,
            ProgressBar = self.ui.ProgressBar_ASR_VPR,
            ConsoleFrame = self.ui.Frame_Console,
            Method = Execute_Voice_Identifying.Execute,
            ParamsFrom = [
                self.ui.Table_ASR_VPR_StdAudioSpeaker,
                self.ui.LineEdit_ASR_VPR_Audio_Dir_Input,
                self.ui.LineEdit_ASR_VPR_Audio_Dir_Output,
                self.ui.LineEdit_ASR_VPR_Model_Dir,
                self.ui.ComboBox_ASR_VPR_Model_Type,
                self.ui.ComboBox_ASR_VPR_Model_Name,
                self.ui.ComboBox_ASR_VPR_Feature_Method,
                self.ui.DoubleSpinBox_ASR_VPR_DecisionThreshold,
                self.ui.DoubleSpinBox_ASR_VPR_Duration_of_Audio
            ],
            FinishEventList = [
                Function_ShowMessageBox
            ],
            FinishParamList = [
                (
                    QMessageBox.Question, "Ask",
                    "当前任务已执行结束，是否跳转至下一工具界面？",
                    QMessageBox.Yes|QMessageBox.No, [QMessageBox.Yes],
                    [[self.ui.Button_Menu_STT.click]], [[()]]
                )
            ]
        )

        #############################################################
        ######################## Content: STT #######################
        #############################################################
        # 将语音文件的内容批量转换为带时间戳的文本并以字幕文件的形式保存

        self.ui.ToolButton_VoiceTranscriber_Title.setText(QCA.translate("ToolButton", "Whisper"))
        self.ui.ToolButton_VoiceTranscriber_Title.setCheckable(True)
        self.ui.ToolButton_VoiceTranscriber_Title.setChecked(True)
        self.ui.ToolButton_VoiceTranscriber_Title.setAutoExclusive(True)
        self.ui.ToolButton_VoiceTranscriber_Title.clicked.connect(
            lambda: Function_AnimateStackedWidget(
                Parent = self,
                StackedWidget = self.ui.StackedWidget_Pages_STT,
                TargetIndex = 0
            )
        )

        Path_Config_STT_Whisper = NormPath(Path(CurrentDir).joinpath('Config', 'Config_STT_Whisper.ini'))
        Config_STT_Whisper = ManageConfig(
            Config.GetValue(
                'ConfigPath',
                'Path_Config_STT_Whisper',
                Path_Config_STT_Whisper
            )
        )

        # Middle
        self.ui.GroupBox_EssentialParams_STT_Whisper.setTitle("必要参数")

        self.ui.CheckBox_Toggle_BasicSettings_STT_Whisper.setCheckable(True)
        self.ui.CheckBox_Toggle_BasicSettings_STT_Whisper.setChecked(
            True #eval(Config_STT_Whisper.GetValue('VoiceTranscriber', 'Toggle_BasicSettings', ''))
        )
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_Toggle_BasicSettings_STT_Whisper,
            CheckedText = "基础设置",
            CheckedEventList = [
                Function_AnimateFrame,
                #Config_STT_Whisper.EditConfig
            ],
            CheckedArgsList = [
                (
                    self, self.ui.Frame_BasicSettings_STT_Whisper,
                    None, None,
                    0, self.ui.Frame_BasicSettings_STT_Whisper.sizeHint().height(),
                    210,
                    'Extend'
                ),
                #('VoiceTranscriber', 'Toggle_BasicSettings', 'True')
            ],
            UncheckedText = "基础设置",
            UncheckedEventList = [
                Function_AnimateFrame,
                #Config_STT_Whisper.EditConfig
            ],
            UncheckedArgsList = [
                (
                    self, self.ui.Frame_BasicSettings_STT_Whisper,
                    None, None,
                    0, self.ui.Frame_BasicSettings_STT_Whisper.sizeHint().height(),
                    210,
                    'Reduce'
                ),
                #('VoiceTranscriber', 'Toggle_BasicSettings', 'False')
            ],
            TakeEffect = True
        )

        Function_SetText(
            Widget = self.ui.Label_STT_Whisper_WAV_Dir,
            Text = SetRichText(
                Title = "音频目录",
                Body = QCA.translate("Label", "该目录中的wav文件的语音内容将会按照以下设置转为文字。")
            )
        )
        Function_SetFileDialog(
            Button = self.ui.Button_STT_Whisper_WAV_Dir,
            LineEdit = self.ui.LineEdit_STT_Whisper_WAV_Dir,
            Mode = "SelectDir"
        )
        Function_SetText(
            Widget = self.ui.LineEdit_STT_Whisper_WAV_Dir,
            Text = str(Config_STT_Whisper.GetValue('VoiceTranscriber', 'WAV_Dir', '')),
            SetPlaceholderText = True
        )
        self.ui.LineEdit_STT_Whisper_WAV_Dir.textChanged.connect(
            lambda Value: Config_STT_Whisper.EditConfig('VoiceTranscriber', 'WAV_Dir', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_STT_Whisper_SRT_Dir,
            Text = SetRichText(
                Title = "字幕输出目录",
                Body = QCA.translate("Label", "最后生成的字幕文件将会保存到该目录中。")
            )
        )
        Function_SetFileDialog(
            Button = self.ui.Button_STT_Whisper_SRT_Dir,
            LineEdit = self.ui.LineEdit_STT_Whisper_SRT_Dir,
            Mode = "SelectDir"
        )
        Function_SetText(
            Widget = self.ui.LineEdit_STT_Whisper_SRT_Dir,
            Text = str(Config_STT_Whisper.GetValue('VoiceTranscriber', 'SRT_Dir', '')),
            SetPlaceholderText = True
        )
        self.ui.LineEdit_STT_Whisper_SRT_Dir.textChanged.connect(
            lambda Value: Config_STT_Whisper.EditConfig('VoiceTranscriber', 'SRT_Dir', str(Value))
        )

        self.ui.CheckBox_Toggle_AdvanceSettings_STT_Whisper.setCheckable(True)
        self.ui.CheckBox_Toggle_AdvanceSettings_STT_Whisper.setChecked(False)
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_Toggle_AdvanceSettings_STT_Whisper,
            CheckedText = "高级设置",
            CheckedEventList = [
                Function_AnimateFrame
            ],
            CheckedArgsList = [
                (
                    self, self.ui.Frame_AdvanceSettings_STT_Whisper,
                    None, None,
                    0, self.ui.Frame_AdvanceSettings_STT_Whisper.sizeHint().height(),
                    210,
                    'Extend'
                )
            ],
            UncheckedText = "高级设置",
            UncheckedEventList = [
                Function_AnimateFrame
            ],
            UncheckedArgsList = [
                (
                    self, self.ui.Frame_AdvanceSettings_STT_Whisper,
                    None, None,
                    0, self.ui.Frame_AdvanceSettings_STT_Whisper.sizeHint().height(),
                    210,
                    'Reduce'
                )
            ],
            TakeEffect = True
        )

        Function_SetText(
            Widget = self.ui.Label_STT_Whisper_Model_Dir,
            Text = SetRichText(
                Title = "模型存放目录",
                Body = QCA.translate("Label", "该目录将会用于存放下载的语音识别模型，若模型已存在会直接使用。")
            )
        )
        Function_SetFileDialog(
            Button = self.ui.Button_STT_Whisper_Model_Dir,
            LineEdit = self.ui.LineEdit_STT_Whisper_Model_Dir,
            Mode = "SelectDir"
        )
        self.ui.LineEdit_STT_Whisper_Model_Dir.setText(
            str(Config_STT_Whisper.GetValue('VoiceTranscriber', 'Model_Dir', NormPath(Path(CurrentDir).joinpath('Models', 'STT', 'Whisper'), 'Posix')))
        )
        self.ui.LineEdit_STT_Whisper_Model_Dir.textChanged.connect(
            lambda Value: Config_STT_Whisper.EditConfig('VoiceTranscriber', 'Model_Dir', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_STT_Whisper_Model_Name,
            Text = SetRichText(
                Title = "模型名字",
                Body = QCA.translate("Label", "语音识别 (whisper) 模型的名字，默认代表模型的大小。")
            )
        )
        self.ui.ComboBox_STT_Whisper_Model_Name.addItems(['tiny', 'base', 'small', 'medium', 'large'])
        self.ui.ComboBox_STT_Whisper_Model_Name.setCurrentText(
            str(Config_STT_Whisper.GetValue('VoiceTranscriber', 'Model_Name', 'small'))
        )
        self.ui.ComboBox_STT_Whisper_Model_Name.currentTextChanged.connect(
            lambda Value: Config_STT_Whisper.EditConfig('VoiceTranscriber', 'Model_Name', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_STT_Whisper_Verbose,
            Text = SetRichText(
                Title = "启用输出日志",
                Body = QCA.translate("Label", "输出debug日志。")
            )
        )
        self.ui.CheckBox_STT_Whisper_Verbose.setCheckable(True)
        self.ui.CheckBox_STT_Whisper_Verbose.setChecked(
            eval(Config_STT_Whisper.GetValue('VoiceTranscriber', 'Verbose', 'True'))
        )
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_STT_Whisper_Verbose,
            CheckedText = "已启用",
            CheckedEventList = [
                Config_STT_Whisper.EditConfig
            ],
            CheckedArgsList = [
                ('VoiceTranscriber', 'Verbose', 'True')
            ],
            UncheckedText = "未启用",
            UncheckedEventList = [
                Config_STT_Whisper.EditConfig
            ],
            UncheckedArgsList = [
                ('VoiceTranscriber', 'Verbose', 'False')
            ],
            TakeEffect = True
        )

        Function_SetText(
            Widget = self.ui.Label_STT_Whisper_Condition_on_Previous_Text,
            Text = SetRichText(
                Title = "前后文一致",
                Body = QCA.translate("Label", "将模型之前的输出作为下个窗口的提示，若模型陷入了失败循环则禁用此项。")
            )
        )
        self.ui.CheckBox_STT_Whisper_Condition_on_Previous_Text.setCheckable(True)
        self.ui.CheckBox_STT_Whisper_Condition_on_Previous_Text.setChecked(
            eval(Config_STT_Whisper.GetValue('VoiceTranscriber', 'Condition_on_Previous_Text', 'False'))
        )
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_STT_Whisper_Condition_on_Previous_Text,
            CheckedText = "已启用",
            CheckedEventList = [
                Config_STT_Whisper.EditConfig
            ],
            CheckedArgsList = [
                ('VoiceTranscriber', 'Condition_on_Previous_Text', 'True')
            ],
            UncheckedText = "未启用",
            UncheckedEventList = [
                Config_STT_Whisper.EditConfig
            ],
            UncheckedArgsList = [
                ('VoiceTranscriber', 'Condition_on_Previous_Text', 'False')
            ],
            TakeEffect = True
        )

        Function_SetText(
            Widget = self.ui.Label_STT_Whisper_fp16,
            Text = SetRichText(
                Title = "半精度计算",
                Body = QCA.translate("Label", "主要使用半精度浮点数进行计算，若GPU不可用则忽略或禁用此项。")
            )
        )
        self.ui.CheckBox_STT_Whisper_fp16.setCheckable(True)
        self.ui.CheckBox_STT_Whisper_fp16.setChecked(
            eval(Config_STT_Whisper.GetValue('VoiceTranscriber', 'fp16', 'True'))
        )
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_STT_Whisper_fp16,
            CheckedText = "已启用",
            CheckedEventList = [
                Config_STT_Whisper.EditConfig
            ],
            CheckedArgsList = [
                ('VoiceTranscriber', 'fp16', 'True')
            ],
            UncheckedText = "未启用",
            UncheckedEventList = [
                Config_STT_Whisper.EditConfig
            ],
            UncheckedArgsList = [
                ('VoiceTranscriber', 'fp16', 'False')
            ],
            TakeEffect = True
        )

        self.ui.GroupBox_OptionalParams_STT_Whisper.setTitle("可选参数")

        Function_SetText(
            Widget = self.ui.Label_STT_Whisper_Language,
            Text = SetRichText(
                Title = "所用语言",
                Body = QCA.translate("Label", "音频中说话人所使用的语言，若自动检测则保持'None'即可。")
            )
        )
        self.ui.ComboBox_STT_Whisper_Language.addItems(['中', '英', '日', 'None'])
        self.ui.ComboBox_STT_Whisper_Language.setCurrentText(
            str(Config_STT_Whisper.GetValue('VoiceTranscriber', 'Language', 'None'))
        )
        self.ui.ComboBox_STT_Whisper_Language.currentTextChanged.connect(
            lambda Value: Config_STT_Whisper.EditConfig('VoiceTranscriber', 'Language', str(Value))
        )

        # Left
        Function_SetTreeWidget(
            TreeWidget = self.ui.TreeWidget_Catalogue_STT_Whisper,
            RootItemTexts = [self.ui.GroupBox_EssentialParams_STT_Whisper.title(),self.ui.GroupBox_OptionalParams_STT_Whisper.title()],
            ChildItemTexts = [(self.ui.CheckBox_Toggle_BasicSettings_STT_Whisper.text(),self.ui.CheckBox_Toggle_AdvanceSettings_STT_Whisper.text()),()],
            AddVertically = True
        )
        Function_ScrollToWidget(
            Trigger = self.ui.TreeWidget_Catalogue_STT_Whisper.topLevelItem(0),
            TargetWidget = self.ui.GroupBox_EssentialParams_STT_Whisper,
            ScrollArea = self.ui.ScrollArea_Middle_STT_Whisper
        )
        Function_ScrollToWidget(
            Trigger = self.ui.TreeWidget_Catalogue_STT_Whisper.topLevelItem(0).child(0),
            TargetWidget = self.ui.Frame_BasicSettings_STT_Whisper,
            ScrollArea = self.ui.ScrollArea_Middle_STT_Whisper
        )
        Function_ScrollToWidget(
            Trigger = self.ui.TreeWidget_Catalogue_STT_Whisper.topLevelItem(0).child(1),
            TargetWidget = self.ui.Frame_AdvanceSettings_STT_Whisper,
            ScrollArea = self.ui.ScrollArea_Middle_STT_Whisper
        )
        Function_ScrollToWidget(
            Trigger = self.ui.TreeWidget_Catalogue_STT_Whisper.topLevelItem(1),
            TargetWidget = self.ui.GroupBox_OptionalParams_STT_Whisper,
            ScrollArea = self.ui.ScrollArea_Middle_STT_Whisper
        )

        # Right
        MonitorFile_Config_VoiceTranscriber = MonitorFile(
            Config.GetValue('ConfigPath', 'Path_Config_STT_Whisper')
        )
        MonitorFile_Config_VoiceTranscriber.start()
        MonitorFile_Config_VoiceTranscriber.Signal_FileContent.connect(
            lambda FileContent: self.ui.TextBrowser_Params_STT_Whisper.setText(
                FileContent
            )
        )

        self.ui.Button_SyncParams_STT_Whisper.setText("关联参数设置")
        Function_ParamsSynchronizer(
            Trigger = self.ui.Button_SyncParams_STT_Whisper,
            ParamsFrom = [
                self.ui.LineEdit_ASR_VPR_Audio_Dir_Output
            ],
            ParamsTo = [
                self.ui.LineEdit_STT_Whisper_WAV_Dir
            ]
        )

        self.ui.Button_CheckOutput_STT_Whisper.setText(QCA.translate("Button", "打开输出目录"))
        Function_SetURL(
            Button = self.ui.Button_CheckOutput_STT_Whisper,
            URL = self.ui.LineEdit_STT_Whisper_SRT_Dir,
            ButtonTooltip = "Click to open"
        )

        # Bottom
        self.ui.Button_STT_Whisper_Execute.setToolTipDuration(-1)
        self.ui.Button_STT_Whisper_Execute.setToolTip("执行语音转文字字幕")
        self.ui.Button_STT_Whisper_Terminate.setToolTipDuration(-1)
        self.ui.Button_STT_Whisper_Terminate.setToolTip("终止语音转文字字幕")
        self.Function_SetMethodExecutor(
            ExecuteButton = self.ui.Button_STT_Whisper_Execute,
            TerminateButton = self.ui.Button_STT_Whisper_Terminate,
            ProgressBar = self.ui.ProgressBar_STT_Whisper,
            ConsoleFrame = self.ui.Frame_Console,
            Method = Execute_Voice_Transcribing.Execute,
            ParamsFrom = [
                self.ui.ComboBox_STT_Whisper_Model_Name,
                self.ui.LineEdit_STT_Whisper_Model_Dir,
                self.ui.LineEdit_STT_Whisper_WAV_Dir,
                self.ui.LineEdit_STT_Whisper_SRT_Dir,
                self.ui.CheckBox_STT_Whisper_Verbose,
                'transcribe', #self.ui.ComboBox_STT_Whisper_Task
                self.ui.ComboBox_STT_Whisper_Language,
                self.ui.CheckBox_STT_Whisper_Condition_on_Previous_Text,
                self.ui.CheckBox_STT_Whisper_fp16
            ],
            EmptyAllowed = [
                self.ui.ComboBox_STT_Whisper_Language
            ],
            FinishEventList = [
                Function_ShowMessageBox
            ],
            FinishParamList = [
                (
                    QMessageBox.Question, "Ask",
                    "当前任务已执行结束，是否跳转至下一工具界面？",
                    QMessageBox.Yes|QMessageBox.No, [QMessageBox.Yes],
                    [[self.ui.Button_Menu_Dataset.click]], [[()]]
                )
            ]
        )

        #############################################################
        ###################### Content: Dataset #####################
        #############################################################
        # 生成适用于语音模型训练的数据集。用户需要提供语音文件与对应的字幕文件

        self.ui.ToolButton_DatasetCreator_Title.setText(QCA.translate("ToolButton", "VITS"))
        self.ui.ToolButton_DatasetCreator_Title.setCheckable(True)
        self.ui.ToolButton_DatasetCreator_Title.setChecked(True)
        self.ui.ToolButton_DatasetCreator_Title.setAutoExclusive(True)
        self.ui.ToolButton_DatasetCreator_Title.clicked.connect(
            lambda: Function_AnimateStackedWidget(
                Parent = self,
                StackedWidget = self.ui.StackedWidget_Pages_Dataset,
                TargetIndex = 0
            )
        )

        Path_Config_DAT_VITS = NormPath(Path(CurrentDir).joinpath('Config', 'Config_DAT_VITS.ini'))
        Config_DAT_VITS = ManageConfig(
            Config.GetValue(
                'ConfigPath',
                'Path_Config_DAT_VITS',
                Path_Config_DAT_VITS
            )
        )

        # Middle
        self.ui.GroupBox_EssentialParams_DAT_VITS.setTitle("必要参数")

        self.ui.CheckBox_Toggle_BasicSettings_DAT_VITS.setCheckable(True)
        self.ui.CheckBox_Toggle_BasicSettings_DAT_VITS.setChecked(
            True #eval(Config_DAT_VITS.GetValue('DatasetCreator', 'Toggle_BasicSettings', ''))
        )
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_Toggle_BasicSettings_DAT_VITS,
            CheckedText = "基础设置",
            CheckedEventList = [
                Function_AnimateFrame,
                #Config_DAT_VITS.EditConfig
            ],
            CheckedArgsList = [
                (
                    self, self.ui.Frame_BasicSettings_DAT_VITS,
                    None, None,
                    0, self.ui.Frame_BasicSettings_DAT_VITS.sizeHint().height(),
                    210,
                    'Extend'
                ),
                #('DatasetCreator', 'Toggle_BasicSettings', 'True')
            ],
            UncheckedText = "基础设置",
            UncheckedEventList = [
                Function_AnimateFrame,
                #Config_DAT_VITS.EditConfig
            ],
            UncheckedArgsList = [
                (
                    self, self.ui.Frame_BasicSettings_DAT_VITS,
                    None, None,
                    0, self.ui.Frame_BasicSettings_DAT_VITS.sizeHint().height(),
                    210,
                    'Reduce'
                ),
                #('DatasetCreator', 'Toggle_BasicSettings', 'False')
            ],
            TakeEffect = True
        )

        Function_SetText(
            Widget = self.ui.Label_DAT_VITS_WAV_Dir,
            Text = SetRichText(
                Title = "音频输入目录",
                Body = QCA.translate("Label", "该目录中的wav文件将会按照以下设置重采样并根据字幕时间戳进行分割。")
            )
        )
        Function_SetFileDialog(
            Button = self.ui.Button_DAT_VITS_WAV_Dir,
            LineEdit = self.ui.LineEdit_DAT_VITS_WAV_Dir,
            Mode = "SelectDir"
        )
        Function_SetText(
            Widget = self.ui.LineEdit_DAT_VITS_WAV_Dir,
            Text = str(Config_DAT_VITS.GetValue('DatasetCreator', 'WAV_Dir', '')),
            SetPlaceholderText = True
        )
        self.ui.LineEdit_DAT_VITS_WAV_Dir.textChanged.connect(
            lambda Value: Config_DAT_VITS.EditConfig('DatasetCreator', 'WAV_Dir', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_DAT_VITS_SRT_Dir,
            Text = SetRichText(
                Title = "字幕输入目录",
                Body = QCA.translate("Label", "该目录中的srt文件将会按照以下设置转为适用于模型训练的csv文件。")
            )
        )
        Function_SetFileDialog(
            Button = self.ui.Button_DAT_VITS_SRT_Dir,
            LineEdit = self.ui.LineEdit_DAT_VITS_SRT_Dir,
            Mode = "SelectDir"
        )
        Function_SetText(
            Widget = self.ui.LineEdit_DAT_VITS_SRT_Dir,
            Text = str(Config_DAT_VITS.GetValue('DatasetCreator', 'SRT_Dir', '')),
            SetPlaceholderText = True
        )
        self.ui.LineEdit_DAT_VITS_SRT_Dir.textChanged.connect(
            lambda Value: Config_DAT_VITS.EditConfig('DatasetCreator', 'SRT_Dir', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_DAT_VITS_TrainRatio,
            Text = SetRichText(
                Title = "训练集占比",
                Body = QCA.translate("Label", "划分给训练集的数据在数据集中所占的比例。")
            )
        )
        self.ui.DoubleSpinBox_DAT_VITS_TrainRatio.setRange(0.5, 0.9)
        self.ui.DoubleSpinBox_DAT_VITS_TrainRatio.setSingleStep(0.1)
        self.ui.DoubleSpinBox_DAT_VITS_TrainRatio.setValue(
            float(Config_DAT_VITS.GetValue('DatasetCreator', 'TrainRatio', '0.7'))
        )
        self.ui.DoubleSpinBox_DAT_VITS_TrainRatio.valueChanged.connect(
            lambda Value: Config_DAT_VITS.EditConfig('DatasetCreator', 'TrainRatio', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_DAT_VITS_Add_AuxiliaryData,
            Text = SetRichText(
                Title = "添加辅助数据",
                Body = QCA.translate("Label", "添加用以辅助训练的数据集，若当前语音数据的质量/数量较低则建议启用。")
            )
        )
        self.ui.CheckBox_DAT_VITS_Add_AuxiliaryData.setCheckable(True)
        self.ui.CheckBox_DAT_VITS_Add_AuxiliaryData.setChecked(
            eval(Config_DAT_VITS.GetValue('DatasetCreator', 'Add_AuxiliaryData', 'False'))
        )
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_DAT_VITS_Add_AuxiliaryData,
            CheckedText = "已启用",
            CheckedEventList = [
                Config_DAT_VITS.EditConfig
            ],
            CheckedArgsList = [
                ('DatasetCreator', 'Add_AuxiliaryData', 'True')
            ],
            UncheckedText = "未启用",
            UncheckedEventList = [
                Config_DAT_VITS.EditConfig
            ],
            UncheckedArgsList = [
                ('DatasetCreator', 'Add_AuxiliaryData', 'False')
            ],
            TakeEffect = True
        )

        Function_SetText(
            Widget = self.ui.Label_DAT_VITS_WAV_Dir_Split,
            Text = SetRichText(
                Title = "音频输出目录",
                Body = QCA.translate("Label", "最后处理完成的音频将会保存到该目录中。")
            )
        )
        Function_SetFileDialog(
            Button = self.ui.Button_DAT_VITS_WAV_Dir_Split,
            LineEdit = self.ui.LineEdit_DAT_VITS_WAV_Dir_Split,
            Mode = "SelectDir"
        )
        Function_SetText(
            Widget = self.ui.LineEdit_DAT_VITS_WAV_Dir_Split,
            Text = str(Config_DAT_VITS.GetValue('DatasetCreator', 'WAV_Dir_Split', '')),
            SetPlaceholderText = True
        )
        self.ui.LineEdit_DAT_VITS_WAV_Dir_Split.textChanged.connect(
            lambda Value: Config_DAT_VITS.EditConfig('DatasetCreator', 'WAV_Dir_Split', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_DAT_VITS_FileList_Path_Training,
            Text = SetRichText(
                Title = "训练集文本路径",
                Body = QCA.translate("Label", "最后生成的训练集txt文件将会保存到该路径。")
            )
        )
        Function_SetFileDialog(
            Button = self.ui.Button_DAT_VITS_FileList_Path_Training,
            LineEdit = self.ui.LineEdit_DAT_VITS_FileList_Path_Training,
            Mode = "SaveFile",
            FileType = "txt类型 (*.txt)"
        )
        Function_SetText(
            Widget = self.ui.LineEdit_DAT_VITS_FileList_Path_Training,
            Text = str(Config_DAT_VITS.GetValue('DatasetCreator', 'FileList_Path_Training', '')),
            SetPlaceholderText = True
        )
        self.ui.LineEdit_DAT_VITS_FileList_Path_Training.textChanged.connect(
            lambda Value: Config_DAT_VITS.EditConfig('DatasetCreator', 'FileList_Path_Training', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_DAT_VITS_FileList_Path_Validation,
            Text = SetRichText(
                Title = "验证集文本路径",
                Body = QCA.translate("Label", "最后生成的验证集txt文件将会保存到该路径。")
            )
        )
        Function_SetFileDialog(
            Button = self.ui.Button_DAT_VITS_FileList_Path_Validation,
            LineEdit = self.ui.LineEdit_DAT_VITS_FileList_Path_Validation,
            Mode = "SaveFile",
            FileType = "txt类型 (*.txt)"
        )
        Function_SetText(
            Widget = self.ui.LineEdit_DAT_VITS_FileList_Path_Validation,
            Text = str(Config_DAT_VITS.GetValue('DatasetCreator', 'FileList_Path_Validation', '')),
            SetPlaceholderText = True
        )
        self.ui.LineEdit_DAT_VITS_FileList_Path_Validation.textChanged.connect(
            lambda Value: Config_DAT_VITS.EditConfig('DatasetCreator', 'FileList_Path_Validation', str(Value))
        )

        self.ui.CheckBox_Toggle_AdvanceSettings_DAT_VITS.setCheckable(True)
        self.ui.CheckBox_Toggle_AdvanceSettings_DAT_VITS.setChecked(False)
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_Toggle_AdvanceSettings_DAT_VITS,
            CheckedText = "高级设置",
            CheckedEventList = [
                Function_AnimateFrame
            ],
            CheckedArgsList = [
                (
                    self, self.ui.Frame_AdvanceSettings_DAT_VITS,
                    None, None,
                    0, self.ui.Frame_AdvanceSettings_DAT_VITS.sizeHint().height(),
                    210,
                    'Extend'
                )
            ],
            UncheckedText = "高级设置",
            UncheckedEventList = [
                Function_AnimateFrame
            ],
            UncheckedArgsList = [
                (
                    self, self.ui.Frame_AdvanceSettings_DAT_VITS,
                    None, None,
                    0, self.ui.Frame_AdvanceSettings_DAT_VITS.sizeHint().height(),
                    210,
                    'Reduce'
                )
            ],
            TakeEffect = True
        )

        Function_SetText(
            Widget = self.ui.Label_DAT_VITS_SampleRate,
            Text = SetRichText(
                Title = "采样率 (HZ)",
                Body = QCA.translate("Label", "数据集所要求的音频采样率，若维持不变则保持'None'即可。")
            )
        )
        self.ui.ComboBox_DAT_VITS_SampleRate.addItems(['22050', '44100', '48000', '96000', '192000', 'None'])
        self.ui.ComboBox_DAT_VITS_SampleRate.setCurrentText(
            str(Config_DAT_VITS.GetValue('DatasetCreator', 'SampleRate', '22050'))
        )
        self.ui.ComboBox_DAT_VITS_SampleRate.currentTextChanged.connect(
            lambda Value: Config_DAT_VITS.EditConfig('DatasetCreator', 'SampleRate', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_DAT_VITS_SampleWidth,
            Text = SetRichText(
                Title = "采样位数",
                Body = QCA.translate("Label", "数据集所要求的音频采样位数，若维持不变则保持'None'即可。")
            )
        )
        self.ui.ComboBox_DAT_VITS_SampleWidth.addItems(['8', '16', '24', '32', '32 (Float)', 'None'])
        self.ui.ComboBox_DAT_VITS_SampleWidth.setCurrentText(
            str(Config_DAT_VITS.GetValue('DatasetCreator', 'SampleWidth', '16'))
        )
        self.ui.ComboBox_DAT_VITS_SampleWidth.currentTextChanged.connect(
            lambda Value: Config_DAT_VITS.EditConfig('DatasetCreator', 'SampleWidth', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_DAT_VITS_ToMono,
            Text = SetRichText(
                Title = "合并声道",
                Body = QCA.translate("Label", "将数据集音频的声道合并为单声道。")
            )
        )
        self.ui.CheckBox_DAT_VITS_ToMono.setCheckable(True)
        self.ui.CheckBox_DAT_VITS_ToMono.setChecked(
            eval(Config_DAT_VITS.GetValue('DatasetCreator', 'ToMono', 'True'))
        )
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_DAT_VITS_ToMono,
            CheckedText = "已启用",
            CheckedEventList = [
                Config_DAT_VITS.EditConfig
            ],
            CheckedArgsList = [
                ('DatasetCreator', 'ToMono', 'True')
            ],
            UncheckedText = "未启用",
            UncheckedEventList = [
                Config_DAT_VITS.EditConfig
            ],
            UncheckedArgsList = [
                ('DatasetCreator', 'ToMono', 'False')
            ],
            TakeEffect = True
        )

        Function_SetText(
            Widget = self.ui.Label_DAT_VITS_AuxiliaryData_Path,
            Text = SetRichText(
                Title = "辅助数据文本路径",
                Body = QCA.translate("Label", "辅助数据集的文本的所在路径。")
            )
        )
        Function_SetFileDialog(
            Button = self.ui.Button_DAT_VITS_AuxiliaryData_Path,
            LineEdit = self.ui.LineEdit_DAT_VITS_AuxiliaryData_Path,
            Mode = "SelectFile",
            FileType = "文本类型 (*.csv *.txt)"
        )
        Function_SetText(
            Widget = self.ui.LineEdit_DAT_VITS_AuxiliaryData_Path,
            Text = str(Config_DAT_VITS.GetValue('DatasetCreator', 'AuxiliaryData_Path', NormPath(Path(CurrentDir).joinpath('AuxiliaryData', 'AuxiliaryData.txt')) if Path(CurrentDir).joinpath('AuxiliaryData', 'AuxiliaryData.txt').exists() else '')),
            SetPlaceholderText = True
        )
        self.ui.LineEdit_DAT_VITS_AuxiliaryData_Path.textChanged.connect(
            lambda Value: Config_DAT_VITS.EditConfig('DatasetCreator', 'AuxiliaryData_Path', str(Value))
        )

        # Left
        Function_SetTreeWidget(
            TreeWidget = self.ui.TreeWidget_Catalogue_DAT_VITS,
            RootItemTexts = [self.ui.GroupBox_EssentialParams_DAT_VITS.title()],
            ChildItemTexts = [(self.ui.CheckBox_Toggle_BasicSettings_DAT_VITS.text(),self.ui.CheckBox_Toggle_AdvanceSettings_DAT_VITS.text())],
            AddVertically = True
        )
        Function_ScrollToWidget(
            Trigger = self.ui.TreeWidget_Catalogue_DAT_VITS.topLevelItem(0),
            TargetWidget = self.ui.GroupBox_EssentialParams_DAT_VITS,
            ScrollArea = self.ui.ScrollArea_Middle_DAT_VITS
        )
        Function_ScrollToWidget(
            Trigger = self.ui.TreeWidget_Catalogue_DAT_VITS.topLevelItem(0).child(0),
            TargetWidget = self.ui.Frame_BasicSettings_DAT_VITS,
            ScrollArea = self.ui.ScrollArea_Middle_DAT_VITS
        )
        Function_ScrollToWidget(
            Trigger = self.ui.TreeWidget_Catalogue_DAT_VITS.topLevelItem(0).child(1),
            TargetWidget = self.ui.Frame_AdvanceSettings_DAT_VITS,
            ScrollArea = self.ui.ScrollArea_Middle_DAT_VITS
        )

        # Right
        MonitorFile_Config_DatasetCreator = MonitorFile(
            Config.GetValue('ConfigPath', 'Path_Config_DAT_VITS')
        )
        MonitorFile_Config_DatasetCreator.start()
        MonitorFile_Config_DatasetCreator.Signal_FileContent.connect(
            lambda FileContent: self.ui.TextBrowser_Params_DAT_VITS.setText(
                FileContent
            )
        )

        self.ui.Button_SyncParams_DAT_VITS.setText("关联参数设置")
        Function_ParamsSynchronizer(
            Trigger = self.ui.Button_SyncParams_DAT_VITS,
            ParamsFrom = [
                self.ui.LineEdit_STT_Whisper_WAV_Dir, #self.ui.LineEdit_ASR_VPR_Audio_Dir_Output
                self.ui.LineEdit_STT_Whisper_SRT_Dir
            ],
            ParamsTo = [
                self.ui.LineEdit_DAT_VITS_WAV_Dir,
                self.ui.LineEdit_DAT_VITS_SRT_Dir
            ]
        )

        self.ui.Button_CheckOutput_DAT_VITS.setText(QCA.translate("Button", "打开输出文件"))
        Function_SetURL(
            Button = self.ui.Button_CheckOutput_DAT_VITS,
            URL = [
                self.ui.LineEdit_DAT_VITS_FileList_Path_Training,
                self.ui.LineEdit_DAT_VITS_FileList_Path_Validation
            ],
            ButtonTooltip = "Click to open"
        )

        # Bottom
        self.ui.Button_DAT_VITS_Execute.setToolTipDuration(-1)
        self.ui.Button_DAT_VITS_Execute.setToolTip("执行语音数据集制作")
        self.ui.Button_DAT_VITS_Terminate.setToolTipDuration(-1)
        self.ui.Button_DAT_VITS_Terminate.setToolTip("终止语音数据集制作")
        self.Function_SetMethodExecutor(
            ExecuteButton = self.ui.Button_DAT_VITS_Execute,
            TerminateButton = self.ui.Button_DAT_VITS_Terminate,
            ProgressBar = self.ui.ProgressBar_DAT_VITS,
            ConsoleFrame = self.ui.Frame_Console,
            Method = Execute_Dataset_Creating.Execute,
            ParamsFrom = [
                self.ui.LineEdit_DAT_VITS_SRT_Dir,
                self.ui.LineEdit_DAT_VITS_WAV_Dir,
                self.ui.ComboBox_DAT_VITS_SampleRate,
                self.ui.ComboBox_DAT_VITS_SampleWidth,
                self.ui.CheckBox_DAT_VITS_ToMono,
                self.ui.LineEdit_DAT_VITS_WAV_Dir_Split,
                self.ui.CheckBox_DAT_VITS_Add_AuxiliaryData,
                self.ui.LineEdit_DAT_VITS_AuxiliaryData_Path,
                self.ui.DoubleSpinBox_DAT_VITS_TrainRatio,
                self.ui.LineEdit_DAT_VITS_FileList_Path_Training,
                self.ui.LineEdit_DAT_VITS_FileList_Path_Validation
            ],
            EmptyAllowed = [
                self.ui.ComboBox_DAT_VITS_SampleRate,
                self.ui.ComboBox_DAT_VITS_SampleWidth,
                self.ui.LineEdit_DAT_VITS_AuxiliaryData_Path
            ],
            FinishEventList = [
                Function_ShowMessageBox
            ],
            FinishParamList = [
                (
                    QMessageBox.Question, "Ask",
                    "当前任务已执行结束，是否跳转至下一工具界面？",
                    QMessageBox.Yes|QMessageBox.No, [QMessageBox.Yes],
                    [[self.ui.Button_Menu_Train.click]], [[()]]
                )
            ]
        )

        #############################################################
        ####################### Content: Train ######################
        #############################################################
        # 训练出适用于语音合成的模型文件。用户需要提供语音数据集

        self.ui.ToolButton_VoiceTrainer_Title.setText(QCA.translate("ToolButton", "VITS"))
        self.ui.ToolButton_VoiceTrainer_Title.setCheckable(True)
        self.ui.ToolButton_VoiceTrainer_Title.setChecked(True)
        self.ui.ToolButton_VoiceTrainer_Title.setAutoExclusive(True)
        self.ui.ToolButton_VoiceTrainer_Title.clicked.connect(
            lambda: Function_AnimateStackedWidget(
                Parent = self,
                StackedWidget = self.ui.StackedWidget_Pages_Train,
                TargetIndex = 0
            )
        )

        Path_Config_Train_VITS = NormPath(Path(CurrentDir).joinpath('Config', 'Config_Train_VITS.ini'))
        Config_Train_VITS = ManageConfig(
            Config.GetValue(
                'ConfigPath',
                'Path_Config_Train_VITS',
                Path_Config_Train_VITS
            )
        )

        # Midlle
        self.ui.GroupBox_EssentialParams_Train_VITS.setTitle("必要参数")

        self.ui.CheckBox_Toggle_BasicSettings_Train_VITS.setCheckable(True)
        self.ui.CheckBox_Toggle_BasicSettings_Train_VITS.setChecked(
            True #eval(Config_Train_VITS.GetValue('VoiceTrainer', 'Toggle_BasicSettings', ''))
        )
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_Toggle_BasicSettings_Train_VITS,
            CheckedText = "基础设置",
            CheckedEventList = [
                Function_AnimateFrame,
                #Config_Train_VITS.EditConfig
            ],
            CheckedArgsList = [
                (
                    self, self.ui.Frame_BasicSettings_Train_VITS,
                    None, None,
                    0, self.ui.Frame_BasicSettings_Train_VITS.sizeHint().height(),
                    210,
                    'Extend'
                ),
                #('VoiceTrainer', 'Toggle_BasicSettings', 'True')
            ],
            UncheckedText = "基础设置",
            UncheckedEventList = [
                Function_AnimateFrame,
                #Config_Train_VITS.EditConfig
            ],
            UncheckedArgsList = [
                (
                    self, self.ui.Frame_BasicSettings_Train_VITS,
                    None, None,
                    0, self.ui.Frame_BasicSettings_Train_VITS.sizeHint().height(),
                    210,
                    'Reduce'
                ),
                #('VoiceTrainer', 'Toggle_BasicSettings', 'False')
            ],
            TakeEffect = True
        )
        
        Function_SetText(
            Widget = self.ui.Label_Train_VITS_FileList_Path_Training,
            Text = SetRichText(
                Title = "训练集文本路径",
                Body = QCA.translate("Label", "用于提供训练集音频路径及其语音内容的训练集txt文件的所在路径。")
            )
        )
        Function_SetFileDialog(
            Button = self.ui.Button_Train_VITS_FileList_Path_Training,
            LineEdit = self.ui.LineEdit_Train_VITS_FileList_Path_Training,
            Mode = "SelectFile",
            FileType = "txt类型 (*.txt)"
        )
        Function_SetText(
            Widget = self.ui.LineEdit_Train_VITS_FileList_Path_Training,
            Text = str(Config_Train_VITS.GetValue('VoiceTrainer', 'FileList_Path_Training', '')),
            SetPlaceholderText = True
        )
        self.ui.LineEdit_Train_VITS_FileList_Path_Training.textChanged.connect(
            lambda Value: Config_Train_VITS.EditConfig('VoiceTrainer', 'FileList_Path_Training', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_Train_VITS_FileList_Path_Validation,
            Text = SetRichText(
                Title = "验证集文本路径",
                Body = QCA.translate("Label", "用于提供验证集音频路径及其语音内容的验证集txt文件的所在路径。")
            )
        )
        Function_SetFileDialog(
            Button = self.ui.Button_Train_VITS_FileList_Path_Validation,
            LineEdit = self.ui.LineEdit_Train_VITS_FileList_Path_Validation,
            Mode = "SelectFile",
            FileType = "txt类型 (*.txt)"
        )
        Function_SetText(
            Widget = self.ui.LineEdit_Train_VITS_FileList_Path_Validation,
            Text = str(Config_Train_VITS.GetValue('VoiceTrainer', 'FileList_Path_Validation', '')),
            SetPlaceholderText = True
        )
        self.ui.LineEdit_Train_VITS_FileList_Path_Validation.textChanged.connect(
            lambda Value: Config_Train_VITS.EditConfig('VoiceTrainer', 'FileList_Path_Validation', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_Train_VITS_Epochs,
            Text = SetRichText(
                Title = "迭代轮数",
                Body = QCA.translate("Label", "将全部样本完整迭代一轮的次数。")
            )
        )
        self.ui.SpinBox_Train_VITS_Epochs.setRange(30, 300000)
        self.ui.SpinBox_Train_VITS_Epochs.setSingleStep(1)
        self.ui.SpinBox_Train_VITS_Epochs.setValue(
            int(Config_Train_VITS.GetValue('VoiceTrainer', 'Epochs', '100'))
        )
        self.ui.SpinBox_Train_VITS_Epochs.valueChanged.connect(
            lambda Value: Config_Train_VITS.EditConfig('VoiceTrainer', 'Epochs', str(Value))
        )
        self.ui.SpinBox_Train_VITS_Epochs.setToolTipDuration(-1)
        self.ui.SpinBox_Train_VITS_Epochs.setToolTip("提示：在均没有预训练模型与辅助数据的情况下建议从一万轮次起步")

        Function_SetText(
            Widget = self.ui.Label_Train_VITS_Batch_Size,
            Text = SetRichText(
                Title = "批处理量",
                Body = QCA.translate("Label", "每轮迭代中单位批次的样本数量，需根据GPU的性能调节该值。")
            )
        )
        self.ui.SpinBox_Train_VITS_Batch_Size.setRange(2, 128)
        self.ui.SpinBox_Train_VITS_Batch_Size.setSingleStep(1)
        self.ui.SpinBox_Train_VITS_Batch_Size.setValue(
            int(Config_Train_VITS.GetValue('VoiceTrainer', 'Batch_Size', '4'))
        )
        self.ui.SpinBox_Train_VITS_Batch_Size.valueChanged.connect(
            lambda Value: Config_Train_VITS.EditConfig('VoiceTrainer', 'Batch_Size', str(Value))
        )
        self.ui.SpinBox_Train_VITS_Batch_Size.setToolTipDuration(-1)
        self.ui.SpinBox_Train_VITS_Batch_Size.setToolTip("建议：4~6G: 2; 8~10G: 4; 12~14G: 8; ...")

        Function_SetText(
            Widget = self.ui.Label_Train_VITS_Use_PretrainedModels,
            Text = SetRichText(
                Title = "使用预训练模型",
                Body = QCA.translate("Label", "使用预训练模型（底模），其载入优先级高于检查点。")
            )
        )
        self.ui.CheckBox_Train_VITS_Use_PretrainedModels.setCheckable(True)
        self.ui.CheckBox_Train_VITS_Use_PretrainedModels.setChecked(
            eval(Config_Train_VITS.GetValue('VoiceTrainer', 'Use_PretrainedModels', 'True'))
        )
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_Train_VITS_Use_PretrainedModels,
            CheckedText = "已启用",
            CheckedEventList = [
                Config_Train_VITS.EditConfig
            ],
            CheckedArgsList = [
                ('VoiceTrainer', 'Use_PretrainedModels', 'True')
            ],
            UncheckedText = "未启用",
            UncheckedEventList = [
                Config_Train_VITS.EditConfig
            ],
            UncheckedArgsList = [
                ('VoiceTrainer', 'Use_PretrainedModels', 'False')
            ],
            TakeEffect = True
        )

        Function_SetText(
            Widget = self.ui.Label_Train_VITS_Dir_Output,
            Text = SetRichText(
                Title = "输出目录",
                Body = QCA.translate("Label", "训练所得模型与对应配置文件的存放目录，若目录中已存在模型则会将其视为检查点。")
            )
        )
        Function_SetFileDialog(
            Button = self.ui.Button_Train_VITS_Dir_Output,
            LineEdit = self.ui.LineEdit_Train_VITS_Dir_Output,
            Mode = "SelectDir",
            Directory = NormPath(Path(CurrentDir).joinpath('Models', 'TTS', 'VITS'), 'Posix')
        )
        Function_SetText(
            Widget = self.ui.LineEdit_Train_VITS_Dir_Output,
            Text = str(Config_Train_VITS.GetValue('VoiceTrainer', 'Dir_Output', NormPath(Path(CurrentDir).joinpath('Models', 'TTS', 'VITS', str(datetime.today())), 'Posix'))),
            SetPlaceholderText = True
        )
        self.ui.LineEdit_Train_VITS_Dir_Output.textChanged.connect(
            lambda Value: Config_Train_VITS.EditConfig('VoiceTrainer', 'Dir_Output', str(Value))
        )
        self.ui.Label_Train_VITS_Dir_Output.setToolTipDuration(-1)
        self.ui.Label_Train_VITS_Dir_Output.setToolTip("提示：当目录中存在多个模型时，编号最大的那个会被选为检查点。")

        self.ui.CheckBox_Toggle_AdvanceSettings_Train_VITS.setCheckable(True)
        self.ui.CheckBox_Toggle_AdvanceSettings_Train_VITS.setChecked(False)
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_Toggle_AdvanceSettings_Train_VITS,
            CheckedText = "高级设置",
            CheckedEventList = [
                Function_AnimateFrame
            ],
            CheckedArgsList = [
                (
                    self, self.ui.Frame_AdvanceSettings_Train_VITS,
                    None, None,
                    0, self.ui.Frame_AdvanceSettings_Train_VITS.sizeHint().height(),
                    210,
                    'Extend'
                )
            ],
            UncheckedText = "高级设置",
            UncheckedEventList = [
                Function_AnimateFrame
            ],
            UncheckedArgsList = [
                (
                    self, self.ui.Frame_AdvanceSettings_Train_VITS,
                    None, None,
                    0, self.ui.Frame_AdvanceSettings_Train_VITS.sizeHint().height(),
                    210,
                    'Reduce'
                )
            ],
            TakeEffect = True
        )

        Function_SetText(
            Widget = self.ui.Label_Train_VITS_Eval_Interval,
            Text = SetRichText(
                Title = "评估间隔",
                Body = QCA.translate("Label", "每次保存模型所间隔的步数。PS: 步数 ≈ 迭代轮次 * 训练样本数 / 批处理量")
            )
        )
        self.ui.SpinBox_Train_VITS_Eval_Interval.setRange(300, 3000000)
        self.ui.SpinBox_Train_VITS_Eval_Interval.setSingleStep(1)
        self.ui.SpinBox_Train_VITS_Eval_Interval.setValue(
            int(Config_Train_VITS.GetValue('VoiceTrainer', 'Eval_Interval', '1000'))
        )
        self.ui.SpinBox_Train_VITS_Eval_Interval.valueChanged.connect(
            lambda Value: Config_Train_VITS.EditConfig('VoiceTrainer', 'Eval_Interval', str(Value))
        )
        self.ui.SpinBox_Train_VITS_Eval_Interval.setToolTipDuration(-1)
        self.ui.SpinBox_Train_VITS_Eval_Interval.setToolTip("提示：设置过小可能导致磁盘占用激增哦")

        Function_SetText(
            Widget = self.ui.Label_Train_VITS_Num_Workers,
            Text = SetRichText(
                Title = "进程数量",
                Body = QCA.translate("Label", "进行数据加载时可并行的进程数量，需根据CPU的性能调节该值。")
            )
        )
        self.ui.SpinBox_Train_VITS_Num_Workers.setRange(2, 32)
        self.ui.SpinBox_Train_VITS_Num_Workers.setSingleStep(2)
        self.ui.SpinBox_Train_VITS_Num_Workers.setValue(
            int(Config_Train_VITS.GetValue('VoiceTrainer', 'Num_Workers', '4'))
        )
        self.ui.SpinBox_Train_VITS_Num_Workers.valueChanged.connect(
            lambda Value: Config_Train_VITS.EditConfig('VoiceTrainer', 'Num_Workers', str(Value))
        )
        self.ui.SpinBox_Train_VITS_Num_Workers.setToolTipDuration(-1)
        self.ui.SpinBox_Train_VITS_Num_Workers.setToolTip("提示：如果配置属于低U高显的话不妨试试把数值降到2。")

        Function_SetText(
            Widget = self.ui.Label_Train_VITS_FP16_Run,
            Text = SetRichText(
                Title = "半精度训练",
                Body = QCA.translate("Label", "通过混合了float16精度的训练方式减小显存占用以支持更大的批处理量。")
            )
        )
        self.ui.CheckBox_Train_VITS_FP16_Run.setCheckable(True)
        self.ui.CheckBox_Train_VITS_FP16_Run.setChecked(
            eval(Config_Train_VITS.GetValue('VoiceTrainer', 'FP16_Run', 'True'))
        )
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_Train_VITS_FP16_Run,
            CheckedText = "已启用",
            CheckedEventList = [
                Config_Train_VITS.EditConfig
            ],
            CheckedArgsList = [
                ('VoiceTrainer', 'FP16_Run', 'True')
            ],
            UncheckedText = "未启用",
            UncheckedEventList = [
                Config_Train_VITS.EditConfig
            ],
            UncheckedArgsList = [
                ('VoiceTrainer', 'FP16_Run', 'False')
            ],
            TakeEffect = True
        )

        Function_SetText(
            Widget = self.ui.Label_Train_VITS_Model_Path_Pretrained_G,
            Text = SetRichText(
                Title = "预训练G_*模型路径",
                Body = QCA.translate("Label", "预训练生成器（Generator）模型的所在路径。")
            )
        )
        Function_SetFileDialog(
            Button = self.ui.Button_Train_VITS_Model_Path_Pretrained_G,
            LineEdit = self.ui.LineEdit_Train_VITS_Model_Path_Pretrained_G,
            Mode = "SelectFile",
            FileType = "pth类型 (*.pth)"
        )
        Function_SetText(
            Widget = self.ui.LineEdit_Train_VITS_Model_Path_Pretrained_G,
            Text = str(Config_Train_VITS.GetValue('VoiceTrainer', 'Model_Path_Pretrained_G', NormPath(Path(CurrentDir).joinpath('Models', 'TTS', 'VITS', 'G_Basic.pth'), 'Posix'))),
            SetPlaceholderText = True
        )
        self.ui.LineEdit_Train_VITS_Model_Path_Pretrained_G.textChanged.connect(
            lambda Value: Config_Train_VITS.EditConfig('VoiceTrainer', 'Model_Path_Pretrained_G', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_Train_VITS_Model_Path_Pretrained_D,
            Text = SetRichText(
                Title = "预训练D_*模型路径",
                Body = QCA.translate("Label", "预训练判别器（Discriminator）模型的所在路径。")
            )
        )
        Function_SetFileDialog(
            Button = self.ui.Button_Train_VITS_Model_Path_Pretrained_D,
            LineEdit = self.ui.LineEdit_Train_VITS_Model_Path_Pretrained_D,
            Mode = "SelectFile",
            FileType = "pth类型 (*.pth)"
        )
        Function_SetText(
            Widget = self.ui.LineEdit_Train_VITS_Model_Path_Pretrained_D,
            Text = str(Config_Train_VITS.GetValue('VoiceTrainer', 'Model_Path_Pretrained_D', NormPath(Path(CurrentDir).joinpath('Models', 'TTS', 'VITS', 'D_Basic.pth'), 'Posix'))),
            SetPlaceholderText = True
        )
        self.ui.LineEdit_Train_VITS_Model_Path_Pretrained_D.textChanged.connect(
            lambda Value: Config_Train_VITS.EditConfig('VoiceTrainer', 'Model_Path_Pretrained_D', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_Train_VITS_Keep_Original_Speakers,
            Text = SetRichText(
                Title = "保留原说话人（实验性）",
                Body = QCA.translate("Label", "保留预训练模型中原有的说话人。")
            )
        )
        self.ui.CheckBox_Train_VITS_Keep_Original_Speakers.setCheckable(True)
        self.ui.CheckBox_Train_VITS_Keep_Original_Speakers.setChecked(
            eval(Config_Train_VITS.GetValue('VoiceTrainer', 'Keep_Original_Speakers', 'False'))
        )
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_Train_VITS_Keep_Original_Speakers,
            CheckedText = "已启用",
            CheckedEventList = [
                Config_Train_VITS.EditConfig
            ],
            CheckedArgsList = [
                ('VoiceTrainer', 'Keep_Original_Speakers', 'True')
            ],
            UncheckedText = "未启用",
            UncheckedEventList = [
                Config_Train_VITS.EditConfig
            ],
            UncheckedArgsList = [
                ('VoiceTrainer', 'Keep_Original_Speakers', 'False')
            ],
            TakeEffect = True
        )
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_Train_VITS_Keep_Original_Speakers,
            CheckedEventList = [
                Function_ShowMessageBox
            ],
            CheckedArgsList = [
                (
                    QMessageBox.Warning, "Tip",
                    "开启该实验性功能需要注意以下几点：\n"
                    "1. 为防止老角色的音色在训练过程中被逐渐遗忘，请保证每个原角色至少有一两条音频参与训练。\n"
                    "2. 为防止老角色的顺序被重组（导致音色混乱），请保证在'配置路径'选项中设置的配置文件包含了底模的角色信息。\n"
                    "3. 相对的，需要适当增加迭代轮数以保证训练效果且每轮迭代所的花费时间也会增加。"
                )
            ],
            TakeEffect = False
        )

        self.ui.GroupBox_OptionalParams_Train_VITS.setTitle("可选参数")

        Function_SetText(
            Widget = self.ui.Label_Train_VITS_Speakers,
            Text = SetRichText(
                Title = "人物名字",
                Body = QCA.translate("Label", "若数据集使用的是人物编号而非人物名字，则在此处按编号填写名字并用逗号隔开。")
            )
        )
        self.ui.LineEdit_Train_VITS_Speakers.setReadOnly(False)
        Function_SetText(
            Widget = self.ui.LineEdit_Train_VITS_Speakers,
            Text = str(Config_Train_VITS.GetValue('VoiceTrainer', 'Speakers', '')),
            SetPlaceholderText = True
        )
        self.ui.LineEdit_Train_VITS_Speakers.textChanged.connect(
            lambda Value: Config_Train_VITS.EditConfig('VoiceTrainer', 'Speakers', str(Value))
        )
        self.ui.LineEdit_Train_VITS_Speakers.setToolTipDuration(-1)
        self.ui.LineEdit_Train_VITS_Speakers.setToolTip("注意：逗号后面不需要加空格")

        # Left
        Function_SetTreeWidget(
            TreeWidget = self.ui.TreeWidget_Catalogue_Train_VITS,
            RootItemTexts = [self.ui.GroupBox_EssentialParams_Train_VITS.title(),self.ui.GroupBox_OptionalParams_Train_VITS.title()],
            ChildItemTexts = [(self.ui.CheckBox_Toggle_BasicSettings_Train_VITS.text(),self.ui.CheckBox_Toggle_AdvanceSettings_Train_VITS.text()),()],
            AddVertically = True
        )
        Function_ScrollToWidget(
            Trigger = self.ui.TreeWidget_Catalogue_Train_VITS.topLevelItem(0),
            TargetWidget = self.ui.GroupBox_EssentialParams_Train_VITS,
            ScrollArea = self.ui.ScrollArea_Middle_Train_VITS
        )
        Function_ScrollToWidget(
            Trigger = self.ui.TreeWidget_Catalogue_Train_VITS.topLevelItem(0).child(0),
            TargetWidget = self.ui.Frame_BasicSettings_Train_VITS,
            ScrollArea = self.ui.ScrollArea_Middle_Train_VITS
        )
        Function_ScrollToWidget(
            Trigger = self.ui.TreeWidget_Catalogue_Train_VITS.topLevelItem(0).child(1),
            TargetWidget = self.ui.Frame_AdvanceSettings_Train_VITS,
            ScrollArea = self.ui.ScrollArea_Middle_Train_VITS
        )
        Function_ScrollToWidget(
            Trigger = self.ui.TreeWidget_Catalogue_Train_VITS.topLevelItem(1),
            TargetWidget = self.ui.GroupBox_OptionalParams_Train_VITS,
            ScrollArea = self.ui.ScrollArea_Middle_Train_VITS
        )

        # Right
        MonitorFile_Config_VoiceTrainer = MonitorFile(
            Config.GetValue('ConfigPath', 'Path_Config_Train_VITS')
        )
        MonitorFile_Config_VoiceTrainer.start()
        MonitorFile_Config_VoiceTrainer.Signal_FileContent.connect(
            lambda FileContent: self.ui.TextBrowser_Params_Train_VITS.setText(
                FileContent
            )
        )

        self.ui.Button_RunTensorboard_Train_VITS.setText("启动Tensorboard")
        self.Function_SetMethodExecutor(
            ExecuteButton = self.ui.Button_RunTensorboard_Train_VITS,
            Method = Tensorboard_Runner.Execute,
            ParamsFrom = [
                self.ui.LineEdit_Train_VITS_Dir_Output
            ]
        )

        self.ui.Button_SyncParams_Train_VITS.setText("关联参数设置")
        Function_ParamsSynchronizer(
            Trigger = self.ui.Button_SyncParams_Train_VITS,
            ParamsFrom = [
                self.ui.LineEdit_DAT_VITS_FileList_Path_Training,
                self.ui.LineEdit_DAT_VITS_FileList_Path_Validation
            ],
            ParamsTo = [
                self.ui.LineEdit_Train_VITS_FileList_Path_Training,
                self.ui.LineEdit_Train_VITS_FileList_Path_Validation
            ]
        )

        self.ui.Button_CheckOutput_Train_VITS.setText(QCA.translate("Button", "打开输出目录"))
        Function_SetURL(
            Button = self.ui.Button_CheckOutput_Train_VITS,
            URL = self.ui.LineEdit_Train_VITS_Dir_Output,
            ButtonTooltip = "Click to open"
        )

        # Bottom
        self.ui.Button_Train_VITS_Execute.setToolTipDuration(-1)
        self.ui.Button_Train_VITS_Execute.setToolTip("执行语音模型训练")
        self.ui.Button_Train_VITS_Terminate.setToolTipDuration(-1)
        self.ui.Button_Train_VITS_Terminate.setToolTip("终止语音模型训练")
        self.Function_SetMethodExecutor(
            ExecuteButton = self.ui.Button_Train_VITS_Execute,
            TerminateButton = self.ui.Button_Train_VITS_Terminate,
            ProgressBar = self.ui.ProgressBar_Train_VITS,
            ConsoleFrame = self.ui.Frame_Console,
            Method = Execute_Voice_Training.Execute,
            ParamsFrom = [
                self.ui.LineEdit_Train_VITS_FileList_Path_Training,
                self.ui.LineEdit_Train_VITS_FileList_Path_Validation,
                self.ui.SpinBox_Train_VITS_Eval_Interval,
                self.ui.SpinBox_Train_VITS_Epochs,
                self.ui.SpinBox_Train_VITS_Batch_Size,
                self.ui.CheckBox_Train_VITS_FP16_Run,
                self.ui.LineEdit_Train_VITS_Speakers,
                self.ui.CheckBox_Train_VITS_Keep_Original_Speakers,
                self.ui.SpinBox_Train_VITS_Num_Workers,
                self.ui.CheckBox_Train_VITS_Use_PretrainedModels,
                self.ui.LineEdit_Train_VITS_Model_Path_Pretrained_G,
                self.ui.LineEdit_Train_VITS_Model_Path_Pretrained_D,
                self.ui.LineEdit_Train_VITS_Dir_Output
            ],
            EmptyAllowed = [
                self.ui.LineEdit_Train_VITS_Model_Path_Pretrained_G,
                self.ui.LineEdit_Train_VITS_Model_Path_Pretrained_D,
                self.ui.LineEdit_Train_VITS_Speakers
            ],
            FinishEventList = [
                Function_ShowMessageBox
            ],
            FinishParamList = [
                (
                    QMessageBox.Question, "Ask",
                    "当前任务已执行结束，是否跳转至下一工具界面？",
                    QMessageBox.Yes|QMessageBox.No, [QMessageBox.Yes],
                    [[self.ui.Button_Menu_TTS.click]], [[()]]
                )
            ]
        )
        MainWindowSignals.Signal_TaskStatus.connect(
            lambda Task, Status: Function_ShowMessageBox(
                MessageType = QMessageBox.Question,
                WindowTitle = "Ask",
                Text = "是否稍后启用tensorboard？",
                Buttons = QMessageBox.Yes|QMessageBox.No,
                EventButtons = [QMessageBox.Yes],
                EventLists = [[self.ui.Button_RunTensorboard_Train_VITS.click]],
                ParamLists = [[()]]
            ) if Task == 'Execute_Voice_Training.Execute' and Status == 'Started' else None
        )

        #############################################################
        ######################## Content: TTS #######################
        #############################################################
        # 将文字转为语音并生成音频文件，用户需要提供相应的模型和配置文件

        self.ui.ToolButton_VoiceConverter_Title.setText(QCA.translate("ToolButton", "VITS"))
        self.ui.ToolButton_VoiceConverter_Title.setCheckable(True)
        self.ui.ToolButton_VoiceConverter_Title.setChecked(True)
        self.ui.ToolButton_VoiceConverter_Title.setAutoExclusive(True)
        self.ui.ToolButton_VoiceConverter_Title.clicked.connect(
            lambda: Function_AnimateStackedWidget(
                Parent = self,
                StackedWidget = self.ui.StackedWidget_Pages_TTS,
                TargetIndex = 0
            )
        )

        Path_Config_TTS_VITS = NormPath(Path(CurrentDir).joinpath('Config', 'Config_TTS_VITS.ini'))
        Config_TTS_VITS = ManageConfig(
            Config.GetValue(
                'ConfigPath',
                'Path_Config_TTS_VITS',
                Path_Config_TTS_VITS
            )
        )

        # Middle
        self.ui.GroupBox_EssentialParams_TTS_VITS.setTitle(QCA.translate("GroupBox", "必要参数"))

        self.ui.CheckBox_Toggle_BasicSettings_TTS_VITS.setCheckable(True)
        self.ui.CheckBox_Toggle_BasicSettings_TTS_VITS.setChecked(
            True #eval(Config_TTS_VITS.GetValue('VoiceConverter', 'Toggle_BasicSettings', ''))
        )
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_Toggle_BasicSettings_TTS_VITS,
            CheckedText = "基础设置",
            CheckedEventList = [
                Function_AnimateFrame,
                #Config_TTS_VITS.EditConfig
            ],
            CheckedArgsList = [
                (
                    self, self.ui.Frame_BasicSettings_TTS_VITS,
                    None, None,
                    0, self.ui.Frame_BasicSettings_TTS_VITS.sizeHint().height(),
                    210,
                    'Extend'
                ),
                #('VoiceConverter', 'Toggle_BasicSettings', 'True')
            ],
            UncheckedText = "基础设置",
            UncheckedEventList = [
                Function_AnimateFrame,
                #Config_TTS_VITS.EditConfig
            ],
            UncheckedArgsList = [
                (
                    self, self.ui.Frame_BasicSettings_TTS_VITS,
                    None, None,
                    0, self.ui.Frame_BasicSettings_TTS_VITS.sizeHint().height(),
                    210,
                    'Reduce'
                ),
                #('VoiceConverter', 'Toggle_BasicSettings', 'False')
            ],
            TakeEffect = True
        )

        Function_SetText(
            Widget = self.ui.Label_TTS_VITS_Config_Path_Load,
            Text = SetRichText(
                Title = "配置加载路径",
                Body = QCA.translate("Label", "用于推理的配置文件的所在路径。")
            )
        )
        Function_SetFileDialog(
            Button = self.ui.Button_TTS_VITS_Config_Path_Load,
            LineEdit = self.ui.LineEdit_TTS_VITS_Config_Path_Load,
            Mode = "SelectFile",
            FileType = "json类型 (*.json)"
        )
        Function_SetText(
            Widget = self.ui.LineEdit_TTS_VITS_Config_Path_Load,
            Text = str(Config_TTS_VITS.GetValue('VoiceConverter', 'Config_Path_Load', '')),
            SetPlaceholderText = True
        )
        self.ui.LineEdit_TTS_VITS_Config_Path_Load.textChanged.connect(
            lambda Value: Config_TTS_VITS.EditConfig('VoiceConverter', 'Config_Path_Load', str(Value))
        )
        self.ui.LineEdit_TTS_VITS_Config_Path_Load.textChanged.connect(
            lambda: self.ui.ComboBox_TTS_VITS_Speaker.clear(),
            type = Qt.QueuedConnection
        )
        self.ui.LineEdit_TTS_VITS_Config_Path_Load.textChanged.connect(
            lambda Path: self.ui.ComboBox_TTS_VITS_Speaker.addItems(
                Get_Speakers(Path)
            ),
            type = Qt.QueuedConnection
        )

        Function_SetText(
            Widget = self.ui.Label_TTS_VITS_Model_Path_Load,
            Text = SetRichText(
                Title = "G_*模型加载路径",
                Body = QCA.translate("Label", "用于推理的生成器（Generator）模型的所在路径。")
            )
        )
        Function_SetFileDialog(
            Button = self.ui.Button_TTS_VITS_Model_Path_Load,
            LineEdit = self.ui.LineEdit_TTS_VITS_Model_Path_Load,
            Mode = "SelectFile",
            FileType = "pth类型 (*.pth)"
        )
        Function_SetText(
            Widget = self.ui.LineEdit_TTS_VITS_Model_Path_Load,
            Text = str(Config_TTS_VITS.GetValue('VoiceConverter', 'Model_Path_Load', '')),
            SetPlaceholderText = True
        )
        self.ui.LineEdit_TTS_VITS_Model_Path_Load.textChanged.connect(
            lambda Value: Config_TTS_VITS.EditConfig('VoiceConverter', 'Model_Path_Load', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_TTS_VITS_Text,
            Text = SetRichText(
                Title = "输入文字",
                Body = QCA.translate("Label", "输入的文字会作为说话人的语音内容。")
            )
        )
        Function_SetText(
            Widget = self.ui.PlainTextEdit_TTS_VITS_Text,
            Text = str(Config_TTS_VITS.GetValue('VoiceConverter', 'Text', '')),
            SetPlaceholderText = True,
            PlaceholderText = '请输入语句'
        )
        self.ui.PlainTextEdit_TTS_VITS_Text.textChanged.connect(
            lambda: Config_TTS_VITS.EditConfig('VoiceConverter', 'Text', self.ui.PlainTextEdit_TTS_VITS_Text.toPlainText())
        )

        Function_SetText(
            Widget = self.ui.Label_TTS_VITS_Language,
            Text = SetRichText(
                Title = "所用语言",
                Body = QCA.translate("Label", "说话人/文字所使用的语言。")
            )
        )
        self.ui.ComboBox_TTS_VITS_Language.addItems(['中', '英', '日'])
        self.ui.ComboBox_TTS_VITS_Language.setCurrentText(
            str(Config_TTS_VITS.GetValue('VoiceConverter', 'Language', '中'))
        )
        self.ui.ComboBox_TTS_VITS_Language.currentTextChanged.connect(
            lambda Value: Config_TTS_VITS.EditConfig('VoiceConverter', 'Language', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_TTS_VITS_Speaker,
            Text = SetRichText(
                Title = "人物名字",
                Body = QCA.translate("Label", "说话人物的名字。")
            )
        )
        self.ui.ComboBox_TTS_VITS_Speaker.addItems(
            Get_Speakers(str(Config_TTS_VITS.GetValue('VoiceConverter', 'Config_Path_Load', 'None')))
        )
        self.ui.ComboBox_TTS_VITS_Speaker.setCurrentText(
            str(Config_TTS_VITS.GetValue('VoiceConverter', 'Speaker', '')) if str(Config_TTS_VITS.GetValue('VoiceConverter', 'Speaker', '')) in Get_Speakers(str(Config_TTS_VITS.GetValue('VoiceConverter', 'Config_Path_Load', 'None')))
            else (Get_Speakers(str(Config_TTS_VITS.GetValue('VoiceConverter', 'Config_Path_Load', 'None')))[0] if Get_Speakers(str(Config_TTS_VITS.GetValue('VoiceConverter', 'Config_Path_Load', 'None'))) != '' else '')
        )
        self.ui.ComboBox_TTS_VITS_Speaker.currentTextChanged.connect(
            lambda Value: Config_TTS_VITS.EditConfig('VoiceConverter', 'Speaker', str(Value))
        )

        Function_SetText(
            Widget = self.ui.Label_TTS_VITS_Audio_Dir_Save,
            Text = SetRichText(
                Title = "音频保存目录",
                Body = QCA.translate("Label", "推理得到的音频会保存到该目录。")
            )
        )
        Function_SetFileDialog(
            Button = self.ui.Button_TTS_VITS_Audio_Dir_Save,
            LineEdit = self.ui.LineEdit_TTS_VITS_Audio_Dir_Save,
            Mode = "SelectDir"
        )
        Function_SetText(
            Widget = self.ui.LineEdit_TTS_VITS_Audio_Dir_Save,
            Text = str(Config_TTS_VITS.GetValue('VoiceConverter', 'Audio_Dir_Save', '')),
            SetPlaceholderText = True
        )
        self.ui.LineEdit_TTS_VITS_Audio_Dir_Save.textChanged.connect(
            lambda Value: Config_TTS_VITS.EditConfig('VoiceConverter', 'Audio_Dir_Save', str(Value))
        )

        self.ui.CheckBox_Toggle_AdvanceSettings_TTS_VITS.setCheckable(True)
        self.ui.CheckBox_Toggle_AdvanceSettings_TTS_VITS.setChecked(False)
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_Toggle_AdvanceSettings_TTS_VITS,
            CheckedText = "高级设置",
            CheckedEventList = [
                Function_AnimateFrame
            ],
            CheckedArgsList = [
                (
                    self, self.ui.Frame_AdvanceSettings_TTS_VITS,
                    None, None,
                    0, self.ui.Frame_AdvanceSettings_TTS_VITS.sizeHint().height(),
                    210,
                    'Extend'
                )
            ],
            UncheckedText = "高级设置",
            UncheckedEventList = [
                Function_AnimateFrame
            ],
            UncheckedArgsList = [
                (
                    self, self.ui.Frame_AdvanceSettings_TTS_VITS,
                    None, None,
                    0, self.ui.Frame_AdvanceSettings_TTS_VITS.sizeHint().height(),
                    210,
                    'Reduce'
                )
            ],
            TakeEffect = True
        )

        Function_SetText(
            Widget = self.ui.Label_TTS_VITS_EmotionStrength,
            Text = SetRichText(
                Title = "情感强度",
                Body = QCA.translate("Label", "情感的变化程度。")
            )
        )
        self.ui.HorizontalSlider_TTS_VITS_EmotionStrength.setMinimum(0)
        self.ui.HorizontalSlider_TTS_VITS_EmotionStrength.setMaximum(100)
        self.ui.HorizontalSlider_TTS_VITS_EmotionStrength.setTickInterval(1)
        self.ui.HorizontalSlider_TTS_VITS_EmotionStrength.setValue(
            int(float(Config_TTS_VITS.GetValue('VoiceConverter', 'EmotionStrength', '0.67')) * 100)
        )
        self.ui.HorizontalSlider_TTS_VITS_EmotionStrength.valueChanged.connect(
            lambda Value: Config_TTS_VITS.EditConfig('VoiceConverter', 'EmotionStrength', str(Value * 0.01))
        )
        Function_ParamsSynchronizer(
            Trigger = self.ui.HorizontalSlider_TTS_VITS_EmotionStrength,
            ParamsFrom = [
                self.ui.HorizontalSlider_TTS_VITS_EmotionStrength
            ],
            Times = 0.01,
            ParamsTo = [
                self.ui.DoubleSpinBox_TTS_VITS_EmotionStrength
            ]
        )
        self.ui.DoubleSpinBox_TTS_VITS_EmotionStrength.setRange(0, 1)
        self.ui.DoubleSpinBox_TTS_VITS_EmotionStrength.setSingleStep(0.01)
        self.ui.DoubleSpinBox_TTS_VITS_EmotionStrength.setValue(
            float(Config_TTS_VITS.GetValue('VoiceConverter', 'EmotionStrength', '0.67'))
        )
        self.ui.DoubleSpinBox_TTS_VITS_EmotionStrength.valueChanged.connect(
            lambda Value: Config_TTS_VITS.EditConfig('VoiceConverter', 'EmotionStrength', str(Value))
        )
        Function_ParamsSynchronizer(
            Trigger = self.ui.DoubleSpinBox_TTS_VITS_EmotionStrength,
            ParamsFrom = [
                self.ui.DoubleSpinBox_TTS_VITS_EmotionStrength
            ],
            Times = 100,
            ParamsTo = [
                self.ui.HorizontalSlider_TTS_VITS_EmotionStrength
            ]
        )

        Function_SetText(
            Widget = self.ui.Label_TTS_VITS_PhonemeDuration,
            Text = SetRichText(
                Title = "音素音长",
                Body = QCA.translate("Label", "音素的发音长度。")
            )
        )
        self.ui.HorizontalSlider_TTS_VITS_PhonemeDuration.setMinimum(0)
        self.ui.HorizontalSlider_TTS_VITS_PhonemeDuration.setMaximum(10)
        self.ui.HorizontalSlider_TTS_VITS_PhonemeDuration.setTickInterval(1)
        self.ui.HorizontalSlider_TTS_VITS_PhonemeDuration.setValue(
            int(float(Config_TTS_VITS.GetValue('VoiceConverter', 'PhonemeDuration', '0.8')) * 10)
        )
        self.ui.HorizontalSlider_TTS_VITS_PhonemeDuration.valueChanged.connect(
            lambda Value: Config_TTS_VITS.EditConfig('VoiceConverter', 'PhonemeDuration', str(Value * 0.1))
        )
        Function_ParamsSynchronizer(
            Trigger = self.ui.HorizontalSlider_TTS_VITS_PhonemeDuration,
            ParamsFrom = [
                self.ui.HorizontalSlider_TTS_VITS_PhonemeDuration
            ],
            Times = 0.1,
            ParamsTo = [
                self.ui.DoubleSpinBox_TTS_VITS_PhonemeDuration
            ]
        )
        self.ui.DoubleSpinBox_TTS_VITS_PhonemeDuration.setRange(0, 1)
        self.ui.DoubleSpinBox_TTS_VITS_PhonemeDuration.setSingleStep(0.1)
        self.ui.DoubleSpinBox_TTS_VITS_PhonemeDuration.setValue(
            float(Config_TTS_VITS.GetValue('VoiceConverter', 'PhonemeDuration', '0.8'))
        )
        self.ui.DoubleSpinBox_TTS_VITS_PhonemeDuration.valueChanged.connect(
            lambda Value: Config_TTS_VITS.EditConfig('VoiceConverter', 'PhonemeDuration', str(Value))
        )
        Function_ParamsSynchronizer(
            Trigger = self.ui.DoubleSpinBox_TTS_VITS_PhonemeDuration,
            ParamsFrom = [
                self.ui.DoubleSpinBox_TTS_VITS_PhonemeDuration
            ],
            Times = 10,
            ParamsTo = [
                self.ui.HorizontalSlider_TTS_VITS_PhonemeDuration
            ]
        )

        Function_SetText(
            Widget = self.ui.Label_TTS_VITS_SpeechRate,
            Text = SetRichText(
                Title = "整体语速",
                Body = QCA.translate("Label", "整体的说话速度。")
            )
        )
        self.ui.HorizontalSlider_TTS_VITS_SpeechRate.setMinimum(0)
        self.ui.HorizontalSlider_TTS_VITS_SpeechRate.setMaximum(20)
        self.ui.HorizontalSlider_TTS_VITS_SpeechRate.setTickInterval(1)
        self.ui.HorizontalSlider_TTS_VITS_SpeechRate.setValue(
            int(float(Config_TTS_VITS.GetValue('VoiceConverter', 'SpeechRate', '1.')) * 10)
        )
        self.ui.HorizontalSlider_TTS_VITS_SpeechRate.valueChanged.connect(
            lambda Value: Config_TTS_VITS.EditConfig('VoiceConverter', 'SpeechRate', str(Value * 0.1))
        )
        Function_ParamsSynchronizer(
            Trigger = self.ui.HorizontalSlider_TTS_VITS_SpeechRate,
            ParamsFrom = [
                self.ui.HorizontalSlider_TTS_VITS_SpeechRate
            ],
            Times = 0.1,
            ParamsTo = [
                self.ui.DoubleSpinBox_TTS_VITS_SpeechRate
            ]
        )
        self.ui.DoubleSpinBox_TTS_VITS_SpeechRate.setRange(0, 2)
        self.ui.DoubleSpinBox_TTS_VITS_SpeechRate.setSingleStep(0.1)
        self.ui.DoubleSpinBox_TTS_VITS_SpeechRate.setValue(
            float(Config_TTS_VITS.GetValue('VoiceConverter', 'SpeechRate', '1.'))
        )
        self.ui.DoubleSpinBox_TTS_VITS_SpeechRate.valueChanged.connect(
            lambda Value: Config_TTS_VITS.EditConfig('VoiceConverter', 'SpeechRate', str(Value))
        )
        Function_ParamsSynchronizer(
            Trigger = self.ui.DoubleSpinBox_TTS_VITS_SpeechRate,
            ParamsFrom = [
                self.ui.DoubleSpinBox_TTS_VITS_SpeechRate
            ],
            Times = 10,
            ParamsTo = [
                self.ui.HorizontalSlider_TTS_VITS_SpeechRate
            ]
        )

        # Right
        MonitorFile_Config_VoiceConverter = MonitorFile(
            Config.GetValue('ConfigPath', 'Path_Config_TTS_VITS')
        )
        MonitorFile_Config_VoiceConverter.start()
        MonitorFile_Config_VoiceConverter.Signal_FileContent.connect(
            lambda FileContent: self.ui.TextBrowser_Params_TTS_VITS.setText(
                FileContent
            )
        )

        self.ui.Button_CheckOutput_TTS_VITS.setText(QCA.translate("Button", "打开输出目录"))
        Function_SetURL(
            Button = self.ui.Button_CheckOutput_TTS_VITS,
            URL = self.ui.LineEdit_TTS_VITS_Audio_Dir_Save,
            ButtonTooltip = "Click to open"
        )

        # Left
        Function_SetTreeWidget(
            TreeWidget = self.ui.TreeWidget_Catalogue_TTS_VITS,
            RootItemTexts = [self.ui.GroupBox_EssentialParams_TTS_VITS.title()],
            ChildItemTexts = [(self.ui.CheckBox_Toggle_BasicSettings_TTS_VITS.text(),self.ui.CheckBox_Toggle_AdvanceSettings_TTS_VITS.text())],
            AddVertically = True
        )
        Function_ScrollToWidget(
            Trigger = self.ui.TreeWidget_Catalogue_TTS_VITS.topLevelItem(0),
            TargetWidget = self.ui.GroupBox_EssentialParams_TTS_VITS,
            ScrollArea = self.ui.ScrollArea_Middle_TTS_VITS
        )
        Function_ScrollToWidget(
            Trigger = self.ui.TreeWidget_Catalogue_TTS_VITS.topLevelItem(0).child(0),
            TargetWidget = self.ui.Frame_BasicSettings_TTS_VITS,
            ScrollArea = self.ui.ScrollArea_Middle_TTS_VITS
        )
        Function_ScrollToWidget(
            Trigger = self.ui.TreeWidget_Catalogue_TTS_VITS.topLevelItem(0).child(1),
            TargetWidget = self.ui.Frame_AdvanceSettings_TTS_VITS,
            ScrollArea = self.ui.ScrollArea_Middle_TTS_VITS
        )

        # Bottom
        self.ui.Button_TTS_VITS_Execute.setToolTipDuration(-1)
        self.ui.Button_TTS_VITS_Execute.setToolTip("执行语音模型推理")
        self.ui.Button_TTS_VITS_Terminate.setToolTipDuration(-1)
        self.ui.Button_TTS_VITS_Terminate.setToolTip("终止语音模型推理")
        self.Function_SetMethodExecutor(
            ExecuteButton = self.ui.Button_TTS_VITS_Execute,
            TerminateButton = self.ui.Button_TTS_VITS_Terminate,
            ProgressBar = self.ui.ProgressBar_TTS_VITS,
            ConsoleFrame = self.ui.Frame_Console,
            Method = Execute_Voice_Converting.Execute,
            ParamsFrom = [
                self.ui.LineEdit_TTS_VITS_Config_Path_Load,
                self.ui.LineEdit_TTS_VITS_Model_Path_Load,
                self.ui.PlainTextEdit_TTS_VITS_Text,
                self.ui.ComboBox_TTS_VITS_Language,
                self.ui.ComboBox_TTS_VITS_Speaker,
                self.ui.DoubleSpinBox_TTS_VITS_EmotionStrength,
                self.ui.DoubleSpinBox_TTS_VITS_PhonemeDuration,
                self.ui.DoubleSpinBox_TTS_VITS_SpeechRate,
                self.ui.LineEdit_TTS_VITS_Audio_Dir_Save
            ],
            EmptyAllowed = [
                self.ui.ComboBox_TTS_VITS_Speaker
            ],
            FinishEventList = [
                Function_ShowMessageBox
            ],
            FinishParamList = [
                (
                    QMessageBox.Information, "Tip",
                    "当前任务已执行结束！",
                    QMessageBox.Ok
                )
            ]
        )

        #############################################################
        ##################### Content: Settings #####################
        #############################################################

        self.ui.ToolButton_Settings_Title.setText(QCA.translate("Label", "系统选项"))

        self.ui.Label_Setting_Language.setText(QCA.translate("Label", "语言"))
        self.ui.ComboBox_Setting_Language.addItems(['中文'])
        self.ui.ComboBox_Setting_Language.setCurrentText(
            {
                'Chinese': '中文'
            }.get(Config.GetValue('Settings', 'Language', 'Chinese'))
        )
        self.ui.ComboBox_Setting_Language.currentIndexChanged.connect(
            lambda: Config.EditConfig(
                'Settings',
                'Language',
                {
                    '中文': 'Chinese'
                }.get(self.ui.ComboBox_Setting_Language.currentText())
            )
        )

        self.ui.Button_Setting_ClientRebooter.clicked.connect(ClientRebooter)
        self.ui.Button_Setting_ClientRebooter.setText(QCA.translate("Button", "重启客户端"))
        self.ui.Button_Setting_ClientRebooter.setCheckable(True)
        self.ui.Button_Setting_ClientRebooter.setToolTipDuration(-1)
        self.ui.Button_Setting_ClientRebooter.setToolTip(QCA.translate("ToolTip", "重启EVT客户端"))

        self.Function_SetMethodExecutor(
            ExecuteButton = self.ui.Button_Setting_IntegrityChecker,
            Method = Integrity_Checker.Execute,
            Params = ()
        )
        MainWindowSignals.Signal_TaskStatus.connect(
            lambda Task, Status: self.ui.Button_Setting_IntegrityChecker.setCheckable(
                False if Status == 'Started' else True
            )
        )
        self.ui.Button_Setting_IntegrityChecker.setText(QCA.translate("Button", "检查完整性"))
        self.ui.Button_Setting_IntegrityChecker.setCheckable(True)
        self.ui.Button_Setting_IntegrityChecker.setToolTipDuration(-1)
        self.ui.Button_Setting_IntegrityChecker.setToolTip(QCA.translate("ToolTip", "检查文件完整性"))

        self.ui.Label_Setting_AutoUpdate.setText(QCA.translate("Label", "自动检查版本并更新"))
        self.ui.CheckBox_Setting_AutoUpdate.setCheckable(True)
        self.ui.CheckBox_Setting_AutoUpdate.setChecked(
            {
                'Enabled': True,
                'Disabled': False
            }.get(Config.GetValue('Settings', 'AutoUpdate', 'Enabled'))
        )
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_Setting_AutoUpdate,
            CheckedText = "已启用",
            CheckedEventList = [
                Config.EditConfig,
                #Updater
            ],
            CheckedArgsList = [
                ('Settings', 'AutoUpdate', 'Enabled'),
                #(CurrentVersion, IsFileCompiled, CurrentDir, f'Easy Voice Toolkit {CurrentVersion}', CurrentDir)
            ],
            UncheckedText = "未启用",
            UncheckedEventList = [
                Config.EditConfig
            ],
            UncheckedArgsList = [
                ('Settings', 'AutoUpdate', 'Disabled')
            ],
            TakeEffect = True
        )

        self.ui.Label_Setting_Synchronizer.setText(QCA.translate("Label", "自动关联前后工具的部分参数设置"))
        self.ui.CheckBox_Setting_Synchronizer.setCheckable(True)
        self.ui.CheckBox_Setting_Synchronizer.setChecked(
            {
                'Enabled': True,
                'Disabled': False
            }.get(Config.GetValue('Tools', 'Synchronizer', 'Enabled'))
        )
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_Setting_Synchronizer,
            CheckedText = "已启用",
            CheckedEventList = [
                Config.EditConfig,
                Function_ParamsSynchronizer,
                Function_ParamsSynchronizer,
                Function_ParamsSynchronizer,
                Function_ParamsSynchronizer
            ],
            CheckedArgsList = [
                ('Tools', 'Synchronizer', 'Enabled'),
                (self.ui.LineEdit_Process_Media_Dir_Output,[self.ui.LineEdit_Process_Media_Dir_Output],None,[self.ui.LineEdit_ASR_VPR_Audio_Dir_Input]),
                (self.ui.LineEdit_ASR_VPR_Audio_Dir_Output,[self.ui.LineEdit_ASR_VPR_Audio_Dir_Output],None,[self.ui.LineEdit_STT_Whisper_WAV_Dir]),
                ([self.ui.LineEdit_STT_Whisper_WAV_Dir,self.ui.LineEdit_STT_Whisper_SRT_Dir],[self.ui.LineEdit_STT_Whisper_WAV_Dir,self.ui.LineEdit_STT_Whisper_SRT_Dir],None,[self.ui.LineEdit_DAT_VITS_WAV_Dir,self.ui.LineEdit_DAT_VITS_SRT_Dir]),
                ([self.ui.LineEdit_DAT_VITS_FileList_Path_Training,self.ui.LineEdit_DAT_VITS_FileList_Path_Validation],[self.ui.LineEdit_DAT_VITS_FileList_Path_Training,self.ui.LineEdit_DAT_VITS_FileList_Path_Validation],None,[self.ui.LineEdit_Train_VITS_FileList_Path_Training,self.ui.LineEdit_Train_VITS_FileList_Path_Validation]),
            ],
            UncheckedText = "未启用",
            UncheckedEventList = [
                Config.EditConfig,
                #Function_ParamsSynchronizer,
                #Function_ParamsSynchronizer,
                #Function_ParamsSynchronizer,
                #Function_ParamsSynchronizer
            ],
            UncheckedArgsList = [
                ('Tools', 'Synchronizer', 'Disabled'),
                #(self.ui.LineEdit_Process_Media_Dir_Output,[self.ui.LineEdit_Process_Media_Dir_Output],None,[self.ui.LineEdit_ASR_VPR_Audio_Dir_Input],"Disconnect"),
                #(self.ui.LineEdit_ASR_VPR_Audio_Dir_Output,[self.ui.LineEdit_ASR_VPR_Audio_Dir_Output],None,[self.ui.LineEdit_STT_Whisper_WAV_Dir],"Disconnect"),
                #([self.ui.LineEdit_STT_Whisper_WAV_Dir,self.ui.LineEdit_STT_Whisper_SRT_Dir],[self.ui.LineEdit_STT_Whisper_WAV_Dir,self.ui.LineEdit_STT_Whisper_SRT_Dir],None,[self.ui.LineEdit_DAT_VITS_WAV_Dir,self.ui.LineEdit_DAT_VITS_SRT_Dir],"Disconnect"),
                #([self.ui.LineEdit_DAT_VITS_FileList_Path_Training,self.ui.LineEdit_DAT_VITS_FileList_Path_Validation],[self.ui.LineEdit_DAT_VITS_FileList_Path_Training,self.ui.LineEdit_DAT_VITS_FileList_Path_Validation],None,[self.ui.LineEdit_Train_VITS_FileList_Path_Training,self.ui.LineEdit_Train_VITS_FileList_Path_Validation],"Disconnect")
            ],
            TakeEffect = True
        )
        Function_ConfigureCheckBox(
            CheckBox = self.ui.CheckBox_Setting_Synchronizer,
            UncheckedEventList = [
                Function_ShowMessageBox
            ],
            UncheckedArgsList = [
                (
                    QMessageBox.Information, "Tip",
                    "该设置将于重启之后生效"
                )
            ],
            TakeEffect = False
        )

        #############################################################
        ####################### Content: Info #######################
        #############################################################

        self.ui.ToolButton_Info_Title.setText(QCA.translate("Label", "用户须知"))

        Function_SetText(
            Widget = self.ui.TextBrowser_Text_Info,
            Text = SetRichText(
                Title = QCA.translate("TextBrowser", "声明"),
                TitleAlign = "left",
                TitleSize = 24,
                TitleWeight = 840,
                Body = QCA.translate("TextBrowser",
                    "请自行解决数据集的授权问题。对于使用未经授权的数据集进行训练所导致的任何问题，您将承担全部责任，并且该仓库及其维护者不承担任何后果！\n"
                    "\n"
                    "您还需要服从以下条例：\n"
                    "0. 本项目仅用于学术交流目的，旨在促进沟通和学习。不适用于生产环境。\n"
                    "1. 基于 Easy Voice Toolkit 发布的任何视频必须在描述中明确指出它们用于变声，并指定声音或音频的输入源，例如使用他人发布的视频或音频，并将分离出的人声作为转换的输入源，必须提供清晰的原始视频链接。如果您使用自己的声音或其他商业语音合成软件生成的声音作为转换的输入源，也必须在描述中说明。\n"
                    "2. 您将对输入源引起的任何侵权问题负全部责任。当使用其他商业语音合成软件作为输入源时，请确保遵守该软件的使用条款。请注意，许多语音合成引擎在其使用条款中明确声明不能用于输入源转换。\n"
                    "3. 继续使用本项目被视为同意本仓库 README 中所述的相关条款。本仓库的 README 有义务进行劝导，但不承担可能出现的任何后续问题的责任。\n"
                    "4. 如果您分发此仓库的代码或将由此项目生成的任何结果公开发布（包括但不限于视频分享平台），请注明原始作者和代码来源（即此仓库）。\n"
                    "5. 如果您将此项目用于任何其他计划，请提前与本仓库的作者联系并告知。\n"
                ),
                BodyAlign = "left",
                BodySize = 12,
                BodyWeight = 420,
                BodyLineHeight = 27
            )
        )

        #############################################################
        ######################### StatusBar #########################
        #############################################################

        # Toggle Console
        self.ui.Button_Toggle_Console.setCheckable(True)
        self.ui.Button_Toggle_Console.setChecked(False)
        self.ui.Button_Toggle_Console.setAutoExclusive(False)
        self.ui.Button_Toggle_Console.setToolTipDuration(-1)
        self.ui.Button_Toggle_Console.setToolTip("Click to toggle console")
        self.ui.Button_Toggle_Console.clicked.connect(
            lambda: Function_AnimateFrame(
                Parent = self,
                Frame = self.ui.Frame_Console,
                MinHeight = 0,
                MaxHeight = 210
            )
        )

        # Print ConsoleInfo
        self.ConsoleInfo.Signal_ConsoleInfo.connect(
            lambda Info: self.ui.PlainTextEdit_Console.setPlainText(Info)
        )

        # Display ToolsStatus
        self.ui.Label_ToolsStatus.clear()
        MainWindowSignals.Signal_TaskStatus.connect(
            lambda Task, Status: self.ui.Label_ToolsStatus.setText(
                f"工具状态：{'忙碌' if Status == 'Started' else '空闲'}"
            ) if Task in [
                'Execute_Audio_Processing.Execute',
                'Execute_Voice_Identifying.Execute',
                'Execute_Voice_Transcribing.Execute',
                'Execute_Dataset_Creating.Execute',
                'Execute_Voice_Training.Execute',
                'Execute_Voice_Converting.Execute'
            ] else None
        )

        # Display Usage
        self.MonitorUsage.Signal_UsageInfo.connect(
            lambda Usage_CPU, Usage_GPU: self.ui.Label_Usage_CPU.setText(
                f"CPU: {Usage_CPU}"
            )
        )
        self.MonitorUsage.Signal_UsageInfo.connect(
            lambda Usage_CPU, Usage_GPU: self.ui.Label_Usage_GPU.setText(
                f"GPU: {Usage_GPU}"
            )
        )

        # Display Version
        self.ui.Label_Version.setText(CurrentVersion)

        # Show MainWindow (and emit signal)
        self.show()
        MainWindowSignals.Signal_MainWindowShown.emit()

##############################################################################################################################

if __name__ == "__main__":
    UpdaterExecuter()

    App = QApplication(sys.argv)

    Window = MainWindow()
    Window.Main()
    
    sys.exit(App.exec())

##############################################################################################################################