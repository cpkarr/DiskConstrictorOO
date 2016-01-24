# File: TestProject.py

import os
import timeit
import sys
import threading
import time
import random

if (sys.platform == "darwin"):
    bMacOS       =   True
    import fcntl

#---------------------- Runtime Configuaration Variables --------------------
kDebugLevel         =   0
kShowXferSpeeds     =   True

#----------------------------------------------------------------------------

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

def WriteTestPattern():
    myFileH.write(sourceBuffer)

def CompareWholeFile():
    global keyboardinputstr
    for i in range(kIterations):
        bytesXFerred    =   myFileH.readinto(destBuffer)
#        if (i == 4):        # inject data corruption
#            destBuffer[50000] = 1
        if (bytesXFerred != kIterationBytes):
            print("i/o Error")
            keyboardinputstr = 'p'  #pause the test
            break
        elif (sourceBuffer != destBuffer):
            print("File Compare Error Between Bytes ", ((i-1) * bytesXFerred), " and ", i * bytesXFerred)
            keyboardinputstr = 'p'  #pause the test
            break

print("\nPython I/O Tester v. 1.0 by Chris Karr")
if (kDebugLevel > 0):
    print("\nThe current platform is: ", sys.platform)

kTotalUniqueChars   =   37    #there are 37 characters in alphabet plus 0-9 plus carrage return
kIterations         =   10
kOneMegabyte        =   1000000
kMegsTransferred    =   kTotalUniqueChars * kIterations
kTotalBytes         =   kMegsTransferred * kOneMegabyte
kIterationBytes     =   kTotalUniqueChars * kOneMegabyte
kTestFilesFolder    =   "TestFiles"
destBuffer          =   bytearray(kIterationBytes)
originalDir         =   os.getcwd()
sourceBuffer        =   bytes(b'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\n' * kOneMegabyte)
if (sys.platform == "darwin"):
    try:
        os.chdir(r"/Volumes/Public")
    except:
        print("\nPlease make sure that you have only the public share of the test drive (UUT) mounted")
        exit(0)
elif (sys.platform == "win32"):
#    os.chdir("\\\\ChrisEX2100\\Public")
    try:
        myStr    =   input("Please <enter> the IP address of the currently mounted Public share: ")
        myStr2   =   "\\\\" + myStr + "\\Public"
        os.chdir(myStr2)
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
kbThread       =  threading.Thread(target=getkeyboardinput_thread)
kbThread.start()

while True:
    if (CheckForNewKeyboardInput() == True):
        exit(0)
    print("\nCreating New Test File...")
    myFileH = open('testfile.bin', "wb", buffering=0)   # this is good enough for SMB on MacOS
    if (sys.platform == "darwin"):                      # Disable write caching on Mac/afp
        myResult    =   fcntl.fcntl(myFileH, fcntl.F_NOCACHE, 1)

    t           =   timeit.Timer(WriteTestPattern)
    totalTime   =   t.timeit(kIterations)
    if (kShowXferSpeeds):
        print("Write Elapsed Time:", totalTime)
        print("Write Speed", kMegsTransferred / totalTime, "MB per second")

    myFileH.close()
    if (True == CheckForNewKeyboardInput()):
        exit(0)
    myFileH = open('testfile.bin', "rb", buffering=0)   # this is good enough for SMB on MacOS
    if (sys.platform == "darwin"):                      # Disable read caching on Mac/afp
        myResult2    =   fcntl.fcntl(myFileH, fcntl.F_NOCACHE, 1)

    t = timeit.Timer(CompareWholeFile)
    totalTime   =   t.timeit(1)
    if (kShowXferSpeeds):
        print("Read Elapsed Time:", totalTime)
        print("Read Speed", kMegsTransferred / totalTime, "MB per second")

    myFileH.close()

