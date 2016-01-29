# File: TestProject.py

import os
import timeit
import sys
import threading
import time
import random

#---------------------- Runtime Configuaration Variables --------------------
kDebugLevel         =   0
kShowXferSpeeds     =   True
kTestThreadCount    =   2
#----------------------------------------------------------------------------

kOneMegabyte        =   1000000
kTotalUniqueChars   =   37    #there are 37 characters in alphabet plus 0-9 plus carrage return

class IOTester:

    """ A single instance of a WRC tester
    Uses up to 10 threads using a randomly generated multiplier which is the number of times to repeat a 37 unique character pattern:
    from one up to a maximum of one million
    """

    def __init__(self, multiple):
        self.charStrMultiple        =   multiple
        self.sourceBuffer           =   bytes(b'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\n' * multiple)
        self.TotalBytes             =   kTotalUniqueChars * multiple
        self.megsXferred            =   self.TotalBytes / kOneMegabyte
        self.destBuffer             =   bytearray(self.TotalBytes)
        return

    def WriteTestPattern(self):
        self.myFileH.write(self.sourceBuffer)
        return

    def CompareWholeFile(self):
        global keyboardinputstr
        xFerBytes    =   self.myFileH.readinto(self.destBuffer)
        if (self.sourceBuffer != self.destBuffer):
            print("File Compare Error. Dumping Memory buffer into file 'MemBufferX' in script directory")

            keyboardinputstr = 'p'  #pause the test
        return

    def startNewTest(self):
        print("\nCreating New Test File...")
        self.testFileName    =   "testfile.bin"
        for j in range(10000):
            if (os.path.isfile(self.testFileName) == False):            #is there no file with this name already?
                break                                               #yep, break out of loop
            else:
                self.testFileName    =   "testfile{0}.bin".format(j+1)   #nope, try next file name
        if (j == 9999):
            print("Sorry, exceeded the number of unique file names (10,000)\nExiting program. Try deleting all the test files in the 'TestFiles' directory")
            keyboardinputstr[0]    =   "q"     # exit the whole program
            exit(0)
        while True:
            if (CheckForNewKeyboardInput() == True):
#                os.remove(os.getcwd() + "/" + self.testFileName)
                os.remove(os.path.realpath(self.testFileName))
                exit(0)
            self.myFileH = open(self.testFileName, "wb", buffering=0)   # this is good enough for SMB on MacOS
            if (sys.platform == "darwin"):                      # Disable write caching on Mac/afp
                myResult    =   fcntl.fcntl(self.myFileH, fcntl.F_NOCACHE, 1)

            t           =   timeit.Timer(self.WriteTestPattern)
            totalTime   =   t.timeit(1)
            if (kShowXferSpeeds):
                print("Write Elapsed Time:", totalTime)
                print("Write Speed", self.megsXferred / totalTime, "MB per second")

            self.myFileH.close()
            if (True == CheckForNewKeyboardInput()):
                os.remove(os.path.realpath(self.testFileName))
                exit(0)
            self.myFileH = open(self.testFileName, "rb", buffering=0)   # this is good enough for SMB on MacOS
            if (sys.platform == "darwin"):                      # Disable read caching on Mac/afp
                myResult2    =   fcntl.fcntl(self.myFileH, fcntl.F_NOCACHE, 1)

            t = timeit.Timer(self.CompareWholeFile)
            totalTime   =   t.timeit(1)
            if (kShowXferSpeeds):
                print("Read Elapsed Time:", totalTime)
                print("Read Speed", self.megsXferred / totalTime, "MB per second")

            self.myFileH.close()

        return

if (sys.platform == "darwin"):
    bMacOS       =   True
    import fcntl


def CheckForNewKeyboardInput():
    global keyboardinputstr
    if (keyboardinputstr == "q"):
        print("\nExiting program")
        return True
    elif (keyboardinputstr == "p"):
        print("\nProgram Paused\nPress 'r' & <Return> to resume or 'q' & <Return> to quit")
        while (keyboardinputstr != "r"):
            if (keyboardinputstr == "q"):   # still allow user to quit from paused state
                print("\nExiting program")
                return True
            time.sleep(1)   # slow down this loop so we don't consume all the CPU
        print("Resuming program...\n")
    return False

def getkeyboardinput_thread():
    while True:
        global keyboardinputstr
        keyboardinputstr             =   input("")  # silently wait for user keyboard input
        if (keyboardinputstr == "q"):   # if the user wants to quit, we need to kill this thread
            break


print("\nPython I/O Tester v. 1.0 by Chris Karr")
if (kDebugLevel > 0):
    print("\nThe current platform is: ", sys.platform)

kTestFilesFolder    =   "TestFiles"

originalDir         =   os.getcwd()
if (sys.platform == "darwin"):
    try:
        os.chdir(r"/Volumes/Public")
    except:
        print("\nPlease make sure that you have only the public share of the test drive (UUT) mounted")
        exit(0)
elif (sys.platform == "win32"):
    try:
        myStr    =   input("Please <enter> the IP address of the currently mounted Public share: ")
        os.chdir("\\\\" + myStr + "\\Public\\")
    except:
        print("\nPlease make sure that you have the public share of the test drive (UUT) mounted and that you have entered the correct IP address")
        exit(0)
else:
    print("Sorry, this script does not yet support any platform other than Mac and Windows")
    exit(0)     # don't support other platforms like Linux yet

if (os.path.exists(kTestFilesFolder) == False):
    os.mkdir(kTestFilesFolder)
os.chdir(kTestFilesFolder)

keyboardinputstr    =   "A"
print("\nTo Start Press:  <s> <Enter>\nTo Pause Press:  <p> <Enter>\nTo Resume Press: <r> <Enter>\nTo Quit Press:   <q> <Enter>p")
kbThread            =  threading.Thread(target=getkeyboardinput_thread)
kbThread.start()

testStrMultiple     =   random.randrange(1,kOneMegabyte, 1)
testStrMultiple     =   1000000
testInstance   =   IOTester(testStrMultiple)
testThread     =   threading.Thread(target=testInstance.startNewTest())

#testInstance[10]    =   {0,0,0,0,0,0,0,0,0,0}
#for i in range(kTestThreadCount):
#    testInstance[i]   =   IOTester(testStrMultiple)
#    testThread[i]     =   threading.Thread(target=testInstance[i].startNewTest())

while keyboardinputstr != "q":
    time.sleep(1)