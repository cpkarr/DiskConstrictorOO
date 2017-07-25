# File: TestProject.py
""" This script will allow an unlimited number of write/read/compare threads to a network volume.
The file size will vary from 37 bytes to 111 million bytes. For each WRC cycle, it generates a random file size that
is a multiple of 37 and is between 37 and 111 million bytes in size, inclusive.
"""
import os
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
gkeyboardinputstr   =   "a"

#---------------------- These are basically just constants -----------------
gOneMegabyte        =   1000000 #there are one million bytes in a true megabyte
gTotalUniqueChars   =   37    #there are 26 characters in alphabet + 0-9 + carriage return = 37
g37MegMultiplier    =   3
gMaxXFerBytes       =   gOneMegabyte * gTotalUniqueChars * g37MegMultiplier    # max out at about 111 MB (Python 3.5 breaks after 128 MB)


# noinspection PyAttributeOutsideInit
class IOTester:
    """ A single instance of a WRC tester. It uses a randomly generated multiplier which is the number of times to repeat
    a 37 byte, unique-character pattern that is readable in a text editor for easy error location detection
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
            if os.path.isfile(self.testFileName):            #is there file with this name already?
                self.testFileName    =   "testfile{0}.txt".format(j+2)   #yes, try next file name
            else:
                break                                               #no, break out of loop
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

        while not gOKToStartThreads:   # Wait to start testing thread until all tester class instances have been initialized
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
                fcntl.fcntl(self.myFileH, fcntl.F_NOCACHE, 1)
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
    if sys.platform == "darwin":        # is it MacOS?
        try:
            os.chdir("/Volumes/" + localShareName)
        except:
            print("\nPlease make sure that you mounted the correct share of the test drive (UUT). You can mount it using whatever protocol you wish")
            return 1
    elif sys.platform == "win32":       # is it Windows?
        try:
            myStr    =   input("Please <enter> the IP address of the test drive (UUT): ")
            os.chdir("\\\\" + myStr + "\\" + localShareName)
        except:
            print("\nPlease make sure that you have entered the correct IP address")
            return 1
    elif sys.platform == "linux":
        localMountPoint =   "/mnt/Constrictor"
        if os.path.exists(localMountPoint):
            os.chdir(localMountPoint)
        else:
            print("Unable to find directory '/mnt/Constrictor'.\nPlease make sure the directory exists.")
            print("\nNote: Before you start the tests, you must create a local mountpoint at '/mnt/Constrictor' ")
            print("e.g. 'sudo mkdir /mnt/Constrictor' ")
            print("\nNext, you must mount the test share to the local mountpoint as yourself using the desired protocol "
                  "and disable attribute caching for NFS Volumes")
            print("For NFS use something like: 'sudo mount -o noac 192.168.1.101:/nfs/Public /mnt/Constrictor' ")
            print("\nFor SMB use something like: sudo mount -t cifs -o username=chris,passord=mypassword,"
                    "uid=$USER,gid=$USER //192.168.1.101/Public /mnt/Constrictor")
            print("\nNext, you must give permission for a user process to write to the Constrictor directory")
            print("This should work: 'sudo chmod 777 /mnt/Constrictor' ")
            return 1
    else:
        print("Current reported platform is:", sys.platform)
        print("Sorry, this script only runs on Mac, Linux and Windows")
        print("The current platform is:", sys.platform)
        return 1  # don't support other platforms yet
    return 0

def main():
    global gOKToStartThreads
    global gkeyboardinputstr
    global gDebugLevel
    global gOriginalDir

    print('\nPython Network I/O Integrity Tester v. 0.9.3 by Chris Karr')
    print("\nThe current platform is: ", sys.platform)
    if sys.platform == "win32": # if Windows, make sure it's version 8.1 or later
        gWindowsVersion =   sys.getwindowsversion().major
        if gWindowsVersion < 7:
            gWindowsVersion = sys.getwindowsversion().minor
            if gWindowsVersion < 3:
                print("Sorry, you must be running Windows 8.1 or later to run this script")
                print("Reported Windows Minor Version:", gWindowsVersion)
                time.sleep(5)
                return 0
    if sys.platform == "darwin":
        gOriginalDir   =   os.getcwd() + "/"
    elif sys.platform == "win32":
        gOriginalDir   =   os.getcwd() + "\\"
    elif sys.platform == "linux":
        gOriginalDir   =   os.getcwd() + "/"
    else:
        print("Sorry, this platform is not currently supported")
        time.sleep(5)
        return 0

    if sys.platform == "linux":
        ShareName   =   "Public"      # just stub this out so the static code analyzer doesn't complain
    else:
        ShareName   =   input("\nPlease enter the name of the share you wish to test: (Press <Return> for the Public share)")
        if ShareName == "":
            ShareName = "Public"
    workingDirError      =   setTestWorkingDirectory(ShareName)
    if workingDirError:
        print("\nFatal Error: Unable to change to target test file directory.")
        exit(workingDirError)

    testFilesFolderName = "ConstrictorTestFiles"
    if not os.path.exists(testFilesFolderName):
        os.mkdir(testFilesFolderName, 0o777)    # setting of permissions doesn't actually work under Ubuntu
        os.chmod(testFilesFolderName, 0o777)    # so do it manually

    os.chdir(testFilesFolderName)

    TempDir =   str(random.randint(1,999999999)) #this should avoid accidental directory name collisions, but a 100% deterministic solution would be better
    if not os.path.exists(TempDir):
        os.mkdir(TempDir, 0o777)    # setting of permissions doesn't actually work under Ubuntu
        os.chmod(TempDir, 0o777)    # so do it manually
    os.chdir(TempDir)

    gkeyboardinputstr   =   "A"
    print("\nTo Pause Press:  <p> <Enter>\nTo Resume Press: <r> <Enter>\nTo Quit Press:   <q> <Enter>\n")
    testThreadCount     =   eval(input("\nFor best performance, you need an average of about of 111 MB of free memory per thread\nPlease enter the number of test threads you want to use:"))
    print("There will be", testThreadCount, "test thread(s) created")
    kbThread            =   threading.Thread(target=getkeyboardinput_thread)
    kbThread.start()

    newTester   =   []
    for i in range(testThreadCount):           # create the tester instances. The instances will spawn their own test threads
        newTester.append(IOTester(i))
        newTester[i].startNewTest()
    gOKToStartThreads   =   True

    print("\nRunning Test(s).\nStart time:", time.asctime( time.localtime(time.time()) ))

    while gkeyboardinputstr != "q":
        # this would be a good place to put an animation in the terminal window so
        # that people can see that the program is still alive
        time.sleep(1)       # Don't consume CPU in main thread

    print("Quitting program. Waiting for threads to finish...\n")
    for i in range(testThreadCount):    #wait for all the threads to terminate before printing time and exiting
        while not newTester[i].threadTerminated:
            time.sleep(.1)
    print("\nEnd time:", time.asctime( time.localtime(time.time()) ))

    if sys.platform != "linux":
        setTestWorkingDirectory(ShareName)
        os.chdir(testFilesFolderName)
    else:
        os.chdir("..")
    os.rmdir(TempDir)

main()
