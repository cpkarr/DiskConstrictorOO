# File: TestProject.py
""" This script will allow an unlimited number of write/read/compare threads to a network volume.
The file size will vary from 37 bytes to 111 million bytes. If you only run one thread, you will always
get the largest possible size (111 million). If you only run two threads, you will always get the largest
and smallest possible sizes (37 bytes). More than three threads will generate a random file size between
37 and 111 million, exclusive.
You can also use this script as a crude benchmark program by testing only a single thread and setting
the "gShowXferSpeeds" to True
"""
import os
import timeit
import sys
import threading
import time
import random
import io
if sys.platform == "darwin":
    import fcntl

#---------------------- Runtime Configuration Variables --------------------
gDebugLevel         =   0
gShowXferSpeeds     =   False
gMaxFiles           =   10000
#----------------------------------------------------------------------------

gOneMegabyte        =   1000000
gMaxXFerSize        =   gOneMegabyte * 3    # max out at a 111 MB
gTotalUniqueChars   =   37    #there are 37q characters in alphabet + 0-9 + carriage return


# noinspection PyPep8Naming,PyPep8Naming
class IOTester:
    """ A single instance of a WRC tester
    Uses a randomly generated multiplier which is the number of times to repeat a 37 unique character pattern
    """
    def __init__(self, instanceNumber):
        global gOneMegabyte
        global gDebugLevel
        global gMaxXFerSize

        if instanceNumber == 0:
            self.charStrMultiple    =   gMaxXFerSize
        elif instanceNumber == 1:
            self.charStrMultiple    =   1
        else:
            self.charStrMultiple    =   random.randrange(2,gMaxXFerSize, 1) # pick a number between 1 and max size only
        self.sourceBuffer           =   bytes(b'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\n' * self.charStrMultiple)
        self.TotalBytes             =   gTotalUniqueChars * self.charStrMultiple
        self.megsXferred            =   self.TotalBytes / gOneMegabyte
        self.destBuffer             =   bytearray(self.TotalBytes)
        self.instanceNo             =   instanceNumber
        self.testFileName           =   "testfile1.txt" # always start with this file name
        self.myThread               =   threading.Thread(target=self.testThread)

        if gDebugLevel > 0:
            print("Successfully initialized thread {0}".format(instanceNumber + 1))
        return

    def WriteTestPattern(self):
        self.myFileH.write(self.sourceBuffer)
        return

    def CompareWholeFile(self):
        global gkeyboardinputstr
        global gOriginalDir
        xFerBytes    =   self.myFileH.readinto(self.destBuffer)
        if xFerBytes != self.TotalBytes:
            gkeyboardinputstr = 'p'  #pause all tests
            print("Instance ", self.instanceNo, "did not get the expected number of bytes. Pausing all tests.\n")
            print(self.TotalBytes, "bytes expected ", xFerBytes, "bytes received")
        elif self.sourceBuffer != self.destBuffer:
            gkeyboardinputstr = 'p'  #pause all tests
            print("File Compare Error. Dumping Memory buffer into file 'MemBufferX' in script directory.\nPausing all tests")
            try:
                dumpFilePath    =   gOriginalDir + "MemBufferFor_" + self.testFileName
                print("Dumping memory to:", dumpFilePath)
                dumpFile    =   open(dumpFilePath, "wb", buffering=0)
                dumpFile.write(self.destBuffer)
                dumpFile.close()
                gkeyboardinputstr = "p"
            except:
                print("Unexpected error trying to save memory buffer:", sys.exc_info()[0])
        return

    def startNewTest(self):
        global gDebugLevel
        global gMaxFiles
        global gkeyboardinputstr
        
        if gDebugLevel > 0:
            print("\nCreating New Test File...\n")
        for j in range(gMaxFiles):
            if not os.path.isfile(self.testFileName):            #is there no file with this name already?
                break                                               #yep, break out of loop
            else:
                self.testFileName    =   "testfile{0}.txt".format(j+2)   #nope, try next file name
        # noinspection PyUnboundLocalVariable
        if j == gMaxFiles - 1:
            print("Sorry, exceeded the number of unique file names (10,000)\nExiting program. Try deleting all the test files in the 'TestFiles' directory")
            gkeyboardinputstr    =   "q"     # exit the whole program
        else:       # we have a valid name
            if gDebugLevel > 0:
                print("Found a test file name for Instance:", self.instanceNo, "The name is: ", self.testFileName)
                print("Thread from instance", self.instanceNo, "starting a new test cycle")
            self.myFileH = open(self.testFileName, "wb+", buffering=0)   # this is good enough for SMB on MacOS
            if sys.platform == "darwin":                      # Disable caching on Mac/afp
                # noinspection PyUnusedLocal
                ignoreResult    =   fcntl.fcntl(self.myFileH, fcntl.F_NOCACHE, 1)
            self.myThread.start()

    def testThread(self):
        global gOKToStartThreads
        global gDebugLevel
        global gShowXferSpeeds

        while not gOKToStartThreads:   #wait to start testing thread until all test class instances have been initialized
            time.sleep(.5)
            if gDebugLevel > 0:
                print("Entering thread loop for instance:", self.instanceNo)
        while True:
            if CheckForNewKeyboardInput():
                break

            if gShowXferSpeeds:
                t           =   timeit.Timer(self.WriteTestPattern)
                totalTime   =   t.timeit(1)
                print("Write Speed", self.megsXferred / totalTime, "MB per second")
            else:
                if gDebugLevel > 0:
                    print("sourceBuffer from instance ", self.instanceNo, " is: ", len(self.sourceBuffer), " bytes in size")
                self.myFileH.write(self.sourceBuffer)

            if CheckForNewKeyboardInput():
                break

            self.myFileH.seek(0, io.SEEK_SET)

            if gShowXferSpeeds:
                t = timeit.Timer(self.CompareWholeFile)
                totalTime   =   t.timeit(1)
                print("Read Speed", self.megsXferred / totalTime, "MB per second")
            else:
                self.CompareWholeFile()

            self.myFileH.seek(0, io.SEEK_SET)

        self.myFileH.close()
        os.remove(os.path.realpath(self.testFileName))
        return


def CheckForNewKeyboardInput():
    global gkeyboardinputstr
    if gkeyboardinputstr == "q":
        return True     # Exit out of this thread so program can terminate properly
    elif gkeyboardinputstr == "p":
        while gkeyboardinputstr != "r":
            if gkeyboardinputstr == "q":   # still allow user to quit from paused state
                return True     # Exit out of this thread so program can terminate properly
            time.sleep(1)   # slow down this loop so we don't consume all the CPU
    return False

def getkeyboardinput_thread():
    while True:
        global gkeyboardinputstr
        gkeyboardinputstr             =   input("")  # silently wait for user keyboard input
        if gkeyboardinputstr == "q":   # if the user wants to quit, we need to kill this thread
            break
        elif gkeyboardinputstr == "p":
            print("\nAll tests paused. Press 'r' to resume or 'q' to quit")
        elif gkeyboardinputstr == "r":
            print("\nResuming tests")
    return

def setTestWorkingDirectory():
    if sys.platform == "darwin":
        try:
            os.chdir(r"/Volumes/Public")
        except:
            print("\nPlease make sure that you have only the public share of the test drive (UUT) mounted")
            return 1
    elif sys.platform == "win32":
        try:
            myStr    =   input("Please <enter> the IP address of the currently mounted Public share: ")
            os.chdir("\\\\" + myStr + "\\Public\\")
        except:
            print("\nPlease make sure that you have the public share of the test drive (UUT) mounted and that you have entered the correct IP address")
            return 1
    elif sys.platform == "Linux":
        try:
            myStr    =   input("Please <enter> the IP address of the currently mounted Public share: ")
            os.chdir("\\\\" + myStr + "\\Public\\")
        except:
            print("\nPlease make sure that you have the public share of the test drive (UUT) mounted and that you have entered the correct IP address")
            return 1
    else:
        print("Sorry, this script does not yet support any platform other than Mac, Linux and Windows")
        print("The current platform is:", sys.platform)
        return 1  # don't support other platforms like Linux yet
    return 0

print("\nPython I/O Tester v. 0.9 by Chris Karr")
if gDebugLevel > 0:
    print("\nThe current platform is: ", sys.platform)

gOriginalDir         =   os.getcwd() + "/"
print("Original Dir:", gOriginalDir)
workingDirError      =   setTestWorkingDirectory()
if workingDirError:
    print("\nFatal Error: Unable to change to target test file directory.")
    exit(1)

if not os.path.exists("TestFiles"):
    os.mkdir("TestFiles")
os.chdir("TestFiles")

gkeyboardinputstr    =   "A"
print("\nTo Start Press:  <s> <Enter>\nTo Pause Press:  <p> <Enter>\nTo Resume Press: <r> <Enter>\nTo Quit Press:   <q> <Enter>p\n")
testThreadCount     =   eval(input("\nFor best performance, you need about of 65 MB of free memory per thread\nPlease enter the number of test threads you want to use:"))
print("There will be", testThreadCount, "test thread(s) created")
kbThread            =  threading.Thread(target=getkeyboardinput_thread)
kbThread.start()

newTester   =   []
gOKToStartThreads   =   False
for i in range(testThreadCount):           # create the tester instances. The instances will spawn their own test threads
    newTester.append(IOTester(i))
    newTester[i].startNewTest()
# noinspection PyRedeclaration,PyRedeclaration
gOKToStartThreads   =   True

print("\nRunning Test(s). Start time:", time.asctime( time.localtime(time.time()) ))

while gkeyboardinputstr != "q":
    time.sleep(1)       # Don't consume CPU for main event loop

print("\nEnd time:", time.asctime( time.localtime(time.time()) ))
