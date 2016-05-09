# File: TestProject.py
""" This script will allow an unlimited number of write/read/compare threads to a network volume.
The file size will vary from 37 bytes to 111 million bytes. If you only run one thread, you will always
get the largest possible size (111 MB). If you only run two threads, you will always get the largest
and smallest possible sizes (111 MB & 37 bytes). More than three threads will generate a random file size that
is a multiple of 37 and is between 37 and 111 million, exclusive.
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
gDebugLevel         =   0   # Allow for multiple debug levels
gShowXferSpeeds     =   False
gMaxFiles           =   10000
gOriginalDir        =   " "
gInjectError        =   False
gOKToStartThreads   =   False

#---------------------- These are basically just constants -----------------
gOneMegabyte        =   1000000
gMaxXFerSize        =   gOneMegabyte * 3    # max out at a 111 MB
gTotalUniqueChars   =   37    #there are 26 characters in alphabet + 0-9 + carriage return = 37

# noinspection PyPep8Naming,PyPep8Naming
class IOTester:
    """ A single instance of a WRC tester. The first two instances use max and min values, respectively.
    Third and later instances use a randomly generated multiplier which is the number of times to repeat
    a 37 byte, unique-character pattern that is readable in a text editor for easy error identification
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
            self.charStrMultiple    =   random.randrange(2, gMaxXFerSize, 1) # pick a number between 1 and max size only
        self.sourceBuffer           =   bytes(b'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\n' * self.charStrMultiple)
        self.TotalBytes             =   gTotalUniqueChars * self.charStrMultiple
        self.megsXferred            =   self.TotalBytes / gOneMegabyte
        self.destBuffer             =   bytearray(self.TotalBytes)
        self.instanceNo             =   instanceNumber
        self.testFileName           =   "testfile1.txt" # always start with this file name
        self.myThread               =   threading.Thread(target=self.testThread)
        self.threadTerminated       =   False

        if gDebugLevel > 0:
            print("Successfully initialized thread {0}".format(instanceNumber + 1))
        return

    def startNewTest(self):
        global gDebugLevel
        global gMaxFiles
        global gkeyboardinputstr
        
        if gDebugLevel > 0:
            print("\nCreating New Test File...\n")
        for j in range(gMaxFiles):                          #First, get a unique file name
            if os.path.isfile(self.testFileName):            #is there file with this name already?
                self.testFileName    =   "testfile{0}.txt".format(j+2)   #yes, try next file name
            else:
                break                                               #no, break out of loop
        # noinspection PyUnboundLocalVariable
        if j == gMaxFiles - 1:
            print("Sorry, exceeded the number of unique file names (10,000)\nExiting program. Try deleting all the test files in the 'TestFiles' directory")
            gkeyboardinputstr    =   "q"     # exit the whole program
        else:       # we have a valid name
            if gDebugLevel > 0:
                print("Found a test file name for Instance:", self.instanceNo, "The name is: ", self.testFileName)
                print("Thread from instance", self.instanceNo, "starting a new test cycle")

            self.myFileH = open(self.testFileName, mode="wb+", buffering=0)   # create the file so another thread doesn't take our name
            if sys.platform == "linux":
                self.myFileH.close()                                                #close it for linux to defeat client side caching in NFS
            elif sys.platform == "darwin":                      # Disable caching on Mac/afp
                ignoreResult    =   fcntl.fcntl(self.myFileH, fcntl.F_NOCACHE, 1)

            self.myThread.start()

    def WriteTestPattern(self):
        self.myFileH.write(self.sourceBuffer)
        return

    def CompareWholeFile(self):
        global gDebugLevel
        global gkeyboardinputstr
        global gOriginalDir
        global gInjectError

        if sys.platform == "win32": #hack for windows read crashing the thread. Not working yet
            self.myFileH.close()
            localFile = open(self.testFileName, mode="r")
            self.destBuffer = localFile.read()
            localFile.close()
            self.myFileH = open(self.testFileName, mode="wb+", buffering=0)   # open it back up again
            if self.sourceBuffer != bytearray(self.destBuffer, encoding='UTF-8"'):
                gkeyboardinputstr = 'p'  # pause all tests
                print("File Compare Error. Dumping Memory buffer into file 'MemBufferX' in script directory.\nPausing all tests")
                try:
                    dumpFilePath = gOriginalDir + "MemBufferFor_" + self.testFileName
                    print("Dumping memory to:", dumpFilePath)
                    dumpFile = open(dumpFilePath, "wb", buffering=0)
                    dumpFile.write(self.destBuffer)
                    dumpFile.close()
                    gkeyboardinputstr = "p"
                except:
                    print("Unexpected error trying to save memory buffer:", sys.exc_info()[0])
            return
        else:
            xFerBytes    =   self.myFileH.readinto(self.destBuffer)
        if gInjectError:
            self.destBuffer[15]   =   65 # Put an "A" where the "P" should be in the first line to force a mis-compare error
        if xFerBytes != self.TotalBytes:
            gkeyboardinputstr = 'p'  # Pause all tests
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

    def testThread(self):
        global gOKToStartThreads
        global gDebugLevel
        global gShowXferSpeeds
        global gkeyboardinputstr

        while not gOKToStartThreads:   # Wait to start testing thread until all test class instances have been initialized
            time.sleep(.5)
        while True:

            if sys.platform == "linux": #if linux we create/open, close and delete for every i/o cycle
                self.myFileH    =   open(self.testFileName, mode="wb", buffering=0)

            if gShowXferSpeeds:
                t           =   timeit.Timer(self.WriteTestPattern)
                totalTime   =   t.timeit(number=1)
                print("Thread", self.instanceNo + 1, " Write Speed: {0:0.6f}".format(self.megsXferred / totalTime), "MB per second")
            else:
# Ugly hack: Not sure why, but Windows needs this to be inside a timer function or the threads will eventually crash.
# Maybe i/o is not thread safe in Windows? Root cause should be investigated and a better solution found.
#                if sys.platform == "win32":
                if False:   #disable hack for now
                    t           =   timeit.Timer(self.WriteTestPattern)
                    totalTime   =   t.timeit(number=1)
                else:
                    try:
                        self.myFileH.write(self.sourceBuffer)
                    except: #try twice for Windows
                        try:
                            print("Write Error: ", sys.exc_info()[0], " Will retry")
                            self.myFileH.write(self.sourceBuffer)
                        except:
                            print("Pausing Tests. Write Error: ", sys.exc_info()[0])
                            gkeyboardinputstr = "p"

            if CheckForNewKeyboardInput():
                break

            if sys.platform == "linux": #rename the file twice to defeat the NFS cache
                self.myFileH.close()
                os.rename(self.myFileH.name, "Temp" + self.myFileH.name)
                os.rename("Temp" + self.myFileH.name, self.testFileName)
                self.myFileH = open(self.testFileName, mode="rb", buffering=0)

            self.myFileH.seek(0, io.SEEK_SET)
            if gShowXferSpeeds:
                t = timeit.Timer(self.CompareWholeFile)
                totalTime   =   t.timeit(number=1)
                print("Thread", self.instanceNo + 1, " Read  Speed: {0:0.6f}".format(self.megsXferred / totalTime), "MB per second")
            else:
                self.CompareWholeFile()

            if sys.platform == "linux":
                self.myFileH.close()
                os.remove(os.path.realpath(self.testFileName))
            else:
                self.myFileH.seek(0, io.SEEK_SET)   #move file marker back to BOF
                if CheckForNewKeyboardInput():  #if true, user wants to quit. If pause, call will block until user quits or presses 'r'
                   break                          #Don't let the user pause after the file is deleted on linux systems
                                                  #This could cause naming collisions with other clients running this script

        if self.myFileH.closed == False:
            self.myFileH.close()
        if os.path.exists(os.path.realpath(self.testFileName)):
            os.remove(os.path.realpath(self.testFileName))
        self.threadTerminated   =   True
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
            print("\nAll tests paused. Press 'r' to resume or 'q' to quit\n")
        elif gkeyboardinputstr == "r":
            print("\nResuming tests")
    return

def setTestWorkingDirectory():  #need to return actual error in future version
    if sys.platform != "linux":
        ShareName   =   input("\nPlease enter the name of the share you wish to test: ")
    if ShareName == "":
        ShareName = "Public"
    if sys.platform == "darwin":
        try:
            os.chdir("/Volumes/" + ShareName)
        except:
            print("\nPlease make sure that you mounted the correct share of the test drive (UUT). You can mount it using whatever protocol you wish")
            return 1
    elif sys.platform == "win32":
        print("\nPlease make sure you have turned OpLocks off on the UUT!!!!!!!!!!!!!!!")
        try:
            myStr    =   input("Please <enter> the IP address of the test drive (UUT): ")
            os.chdir("\\\\" + myStr + "\\" + ShareName + "\\")
        except:
            print("\nPlease make sure that you have entered the correct IP address")
            return 1
    elif sys.platform == "linux":
        print("\nBefore you start the tests, you must create a local mountpoint at '/mnt/Constrictor' ")
        print("e.g. 'sudo mkdir /mnt/Constrictor' ")
        print("\nNext, you must mount the test share to the local mountpoint using the desired protocol and disable attribute caching for NFS Volumes")
        print("For NFS use something like: 'sudo mount -o noac 192.168.1.137:/nfs/Public /mnt/Constrictor' ")
        print("For SMB use something like: 'sudo mount //192.168.1 137/Public /mnt/Constrictor' ")
        print("\nNext, you must give permission for a user process to write to the Constrictor directory")
        print("Try something like: 'sudo chmod 777 /mnt/Constrictor' ")
        try:
            os.chdir("/mnt/Constrictor")
        except:
            print("Unable to change active directory to /mnt/Constrictor.\nPlease make sure the directory exists.")
            return 1
    else:
        print("Current reported platform is:", sys.platform)
        print("Sorry, this script does not yet support any platform other than Mac, Linux and Windows")
        print("The current platform is:", sys.platform)
        return 1  # don't support other platforms like Linux yet
    return 0

def main():
    global gOKToStartThreads
    global gkeyboardinputstr
    global gDebugLevel
    global gOriginalDir

    print("\nPython I/O Tester v. 0.9.1 by Chris Karr")
    if gDebugLevel > 0:
        print("\nThe current platform is: ", sys.platform)

    if sys.platform == "darwin":
        gOriginalDir   =   os.getcwd() + "/"
    elif sys.platform == "win32":
        gOriginalDir   =   os.getcwd() + "\\"
    elif sys.platform == "linux":
        gOriginalDir   =   os.getcwd() + "/"

    if gDebugLevel > 0:
        print("Original Dir:", gOriginalDir)
    workingDirError      =   setTestWorkingDirectory()
    if workingDirError:
        print("\nFatal Error: Unable to change to target test file directory.")
        exit(workingDirError)

    if not os.path.exists("TestFiles"):
        os.mkdir("TestFiles")
    os.chdir("TestFiles")

    gkeyboardinputstr    =   "A"
    print("\nTo Pause Press:  <p> <Enter>\nTo Resume Press: <r> <Enter>\nTo Quit Press:   <q> <Enter>\n")
    testThreadCount     =   eval(input("\nFor best performance, you need an average of about of 111 MB of free memory per thread\nPlease enter the number of test threads you want to use:"))
    print("There will be", testThreadCount, "test thread(s) created")
    kbThread            =  threading.Thread(target=getkeyboardinput_thread)
    kbThread.start()

    newTester   =   []
    for i in range(testThreadCount):           # create the tester instances. The instances will spawn their own test threads
        newTester.append(IOTester(i))
        newTester[i].startNewTest()
    # noinspection PyRedeclaration,PyRedeclaration
    gOKToStartThreads   =   True

    print("\nRunning Test(s).\nStart time:", time.asctime( time.localtime(time.time()) ))

# this would be a good place to put an animation in the terminal window so
# that people can see that the program is still alive
    while gkeyboardinputstr != "q":
        time.sleep(1)       # Don't consume CPU for main event loop

    print("Quitting program. Waiting for threads to finish...\n")
    for i in range(testThreadCount):    #wait for all the threads to terminate before printing time and exiting
        while newTester[i].threadTerminated == False:
            time.sleep(.1)
    print("\nEnd time:", time.asctime( time.localtime(time.time()) ))

main()
