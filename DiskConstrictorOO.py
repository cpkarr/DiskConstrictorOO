# File: TestProject.py
""" This script will allow an unlimited number of write/read/compare threads to a network volume.
The file size will vary from 37 bytes to 111 million bytes. If you only run one thread, you will always
get the largest possible size (111 MB). If you only run two threads, you will always get the largest
and smallest possible sizes (111 MB & 37 bytes). More than three threads will generate a random file size that
is a multiple of 37 and is between 37 and 111 million, exclusive.
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
gMaxFiles           =   10000
gOriginalDir        =   " "
gInjectError        =   False
gOKToStartThreads   =   False

#---------------------- These are basically just constants -----------------
gOneMegabyte        =   1000000 #there are one million bytes in a true megabyte
gTotalUniqueChars   =   37    #there are 26 characters in alphabet + 0-9 + carriage return = 37
g37MegMultiplier    =   3
gMaxXFerBytes       =   gOneMegabyte * gTotalUniqueChars * g37MegMultiplier    # max out at about 111 MB (Python 3.5 breaks after 128 MB)

gWindowsVersion     =   0

# noinspection PyPep8Naming,PyPep8Naming
class IOTester:
    """ A single instance of a WRC tester. The first two instances use max and min values, respectively.
    Third and later instances use a randomly generated multiplier which is the number of times to repeat
    a 37 byte, unique-character pattern that is readable in a text editor for easy error identification
    """
    def __init__(self, instanceNumber):
        global gDebugLevel

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
            if (os.path.isfile(self.testFileName)) or (os.path.isfile("Temp" + self.testFileName)):            #is there file or tempfile with this name already?
                self.testFileName    =   "testfile{0}.txt".format(j+2)   #yes, try next file name
            else:
                break                                               #no, break out of loop
        # noinspection PyUnboundLocalVariable
        if j == gMaxFiles - 1:
            print("Sorry, exceeded the number of unique file names (10,000)\nExiting program. Try deleting all the test files in the 'ConstrictorTestFiles' directory")
            gkeyboardinputstr    =   "q"     # exit the whole program
        else:       # we have a valid name
            if gDebugLevel > 0:
                print("Found a test file name for Instance:", self.instanceNo, "The name is: ", self.testFileName)
                print("Thread from instance", self.instanceNo, "starting a new test cycle")

            self.myFileH = open(self.testFileName, mode="wb+", buffering=0)   # create the file so another thread doesn't take our name
            self.myFileH.close()                                                #close it to defeat client side caching

            self.myThread.start()

    def CompareWholeFile(self):
        global gDebugLevel
        global gkeyboardinputstr
        global gOriginalDir
        global gInjectError

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
        global gkeyboardinputstr
        global g37MegMultiplier
        global gOneMegabyte
        global gTotalUniqueChars

        while not gOKToStartThreads:   # Wait to start testing thread until all test class instances have been initialized
            time.sleep(.5)

        while True:
            if CheckForNewKeyboardInput():
                break
            charStrMultiple     = random.randrange(1, g37MegMultiplier * gOneMegabyte + 1, 1)  # pick a number between 1 and max size, inclusive of both
            self.TotalBytes     = gTotalUniqueChars * charStrMultiple
            self.sourceBuffer   = bytes(b'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\n' * charStrMultiple)
            self.destBuffer     = bytearray(self.TotalBytes)  # make a buffer large enough to hold largest possible transfer

            self.myFileH    =   open(self.testFileName, mode="wb", buffering=0) #close and open fresh for every i/o cycle
            if sys.platform == "darwin":  # Disable caching on Mac/afp
                ignoreResult = fcntl.fcntl(self.myFileH, fcntl.F_NOCACHE, 1)
            self.myFileH.write(self.sourceBuffer)

            self.myFileH.close()
            if CheckForNewKeyboardInput():
                break

            os.rename(self.testFileName, "Temp" + self.myFileH.name)
            os.rename("Temp" + self.testFileName, self.testFileName)
            self.myFileH = open(self.testFileName, mode="rb", buffering=0)
            self.myFileH.seek(0, io.SEEK_SET)
            self.CompareWholeFile()
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

def setTestWorkingDirectory(localShareName):  #need to return actual error in future version
    if sys.platform == "darwin":
        try:
            os.chdir("/Volumes/" + localShareName)
        except:
            print("\nPlease make sure that you mounted the correct share of the test drive (UUT). You can mount it using whatever protocol you wish")
            return 1
    elif sys.platform == "win32":
        try:
            myStr    =   input("Please <enter> the IP address of the test drive (UUT): ")
            os.chdir("\\\\" + myStr + "\\" + localShareName)
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
    global gWindowsVersion

    print("\nPython I/O Tester v. 0.9.2 by Chris Karr")
    if gDebugLevel > 0:
        print("\nThe current platform is: ", sys.platform)
        if sys.platform == "win32":
            gWindowsVersion =   sys.getwindowsversion().major
            print("The current Windows version is: " + gWindowsVersion)

    if sys.platform == "darwin":
        gOriginalDir   =   os.getcwd() + "/"
    elif sys.platform == "win32":
        gOriginalDir   =   os.getcwd() + "\\"
    elif sys.platform == "linux":
        gOriginalDir   =   os.getcwd() + "/"

    if gDebugLevel > 0:
        print("Original Dir:", gOriginalDir)

    if sys.platform != "linux":
        ShareName   =   input("\nPlease enter the name of the share you wish to test: (Press <Return> for the Public share)")
        if ShareName == "":
            ShareName = "Public"
    workingDirError      =   setTestWorkingDirectory(ShareName)
    if workingDirError:
        print("\nFatal Error: Unable to change to target test file directory.")
        exit(workingDirError)

    if not os.path.exists("ConstrictorTestFiles"):
        os.mkdir("ConstrictorTestFiles")
    os.chdir("ConstrictorTestFiles")

    TempDir =   str(random.randint(1,999999999))
    if not os.path.exists(TempDir):
        os.mkdir(TempDir)
    os.chdir(TempDir)

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

    workingDirError      =   setTestWorkingDirectory(ShareName)
    os.chdir("ConstrictorTestFiles")
    os.rmdir(TempDir)

main()
