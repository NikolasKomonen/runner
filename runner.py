import sys
import subprocess
import psutil
import os
import time
import logging
from datetime import datetime
import shutil
import pwd
import signal
from typing import Dict, List, IO


class CommandOptions:
    """Handles console commands for CommandExecutor

    Will mainly parse the input and indicate if there were
    any errors.
    """

    COUNT = '-c'
    FAILED_COUNT = '--failed-count'
    SYS_TRACE = '--sys-trace'
    CALL_TRACE = '--call-trace'
    LOG_TRACE = '--log-trace'
    DEBUG = '--debug'
    HELP = '--help'

    allOptions = set()
    allOptions.update([
        COUNT,
        FAILED_COUNT,
        SYS_TRACE,
        CALL_TRACE,
        LOG_TRACE,
        DEBUG,
        HELP
    ])

    optionsWithVariables = set()
    optionsWithVariables.update([
        COUNT,
        FAILED_COUNT
    ])

    HELP_MESSAGE = 'Usage: python runner.py [-c number]' \
        ' [--failed-count number] [--sys-trace]' \
        ' [--call-trace] [--log-trace] [--debug]' \
        ' [--help] wrapped\n'
    HELP_EXAMPLE = 'Example: python runner.py -c 3 --failed-count 2' \
        ' --sys-trace --call-trace --log-trace --debug' \
        ' ping -c 4 192.168.0.2\n'
    MISSING_INT_MSG = 'Missing integer for option: {}\n'
    LARGER_INT_MSG = 'The value, {}, for "{}" must be greater than 0.\n'
    NO_WRAPPED_COMMAND_MSG = 'No command to be wrapped was provided.\n'
    UNRECOGNIZED_OPTION_MSG = 'Did not recognize option: {}\n'

    def __init__(self, args: List[str]):
        """
            Parameters:
                args List[str]: Command arguments
        """

        self.args = args
        self.argsLength = len(args)
        self.activeOptions = set()
        self.activeOptionsWithVariables = {}
        self.wrappedCommand = None
        self.parseSuccessful: bool = self.__parseArgs()

    def getParsedCommand(self):
        """
        Returns a list of objects containing information
        about the options set.

            Returns:

                List[activeOptions, activeOptionsWithVariables, wrappedCommand]

            Explained:

                activeOptions (set):
                            subset of options from CommandOptions.allOptions
                            excluding CommandOptions.optionsWithVariables

                activeOptionsWithVariables (Dict[str, int]):
                            subset of options from
                            CommandOptions.optionsWithVariables
                            as the key and integers as the values

                wrappedCommand (List[str]):
                            The command being wrapped as a list of args
        """

        if not self.parseSuccessful:
            return None
        return [self.activeOptions,
                self.activeOptionsWithVariables,
                self.wrappedCommand]

    def __checkIfHelp(self) -> bool:
        """
        Provides information on how to use the utility

            Returns:
                True if user flagged '--help'
        """

        if self.HELP in self.args:
            sys.stderr.write(self.HELP_MESSAGE)
            sys.stderr.write(self.HELP_EXAMPLE)
            return True
        return False

    def __parseArgs(self) -> int:
        """
        Parses the arguments provided to the the script

            Returns:
                True if successful
        """
        if self.__checkIfHelp():
            return False

        argsLength = len(self.args)

        if argsLength <= 1:
            return True

        # skip file name
        i = 1

        while i < argsLength:
            arg = self.args[i]
            if arg in self.allOptions:
                if arg in self.optionsWithVariables:
                    variable = self.__getOptionVariable(i)
                    if variable is None:
                        return False
                    self.activeOptionsWithVariables[arg] = variable
                    # skip the variable, was handled successfully
                    i += 1
                else:
                    self.activeOptions.add(arg)
            else:
                if arg.startswith('-'):
                    sys.stderr.write(self.UNRECOGNIZED_OPTION_MSG.format(arg))
                    return False
                self.wrappedCommand = self.args[i:]
                return True
            i += 1

        if self.wrappedCommand is None:
            sys.stderr.write(self.NO_WRAPPED_COMMAND_MSG)
            return False

        return True

    def __getOptionVariable(self, index) -> int:
        """
        Trys to get the defined variable after the given option

            Parameters:
                index: index of the option in self.args

            Returns:
                The variable value if exists, else None
        """
        arg = self.args[index]

        if arg in ['-c', '--failed-count']:
            return self.__getNumberFromArgs(index + 1)

        return None

    def __getNumberFromArgs(self, index) -> int:
        """
        Trys to get an int variable

            Parameters:
                index: index of the expected int in self.args

            Returns:
                The int if exists, else None
        """
        if index >= self.argsLength:
            sys.stderr.write(self.MISSING_INT_MSG.format(self.args[index - 1]))
            return None

        value = self.args[index]

        if not value.isnumeric():
            sys.stderr.write(self.MISSING_INT_MSG.format(self.args[index - 1]))
            return None

        number = int(value)

        if number < 1:
            sys.stderr.write(self.LARGER_INT_MSG.format(
                value, self.args[index - 1]))
            return None
        return number



class CommandExecutor:
    """Sets up a command to be run and executed.

    Will run the command and setup all necessary logging.
    """

    SYS_TRACE_FILENAME = "systemTrace.txt"
    CALL_TRACE_FILENAME = "callTrace.txt"
    LOG_TRACE_FILENAME = "logTrace.txt"

    DEBUG_MSG = '\n[SCRIPT-DEBUG]: Running command: "{}"\n'


    def __init__(self, co: CommandOptions,
                 rootLogFolder: str = 'runnerLogs',
                 pollInterval: int = 1):
        """
            Parameters:
                rootLogFolder (str): The root folder to hold all the logs

                pollInterval (int): The interval to poll the wrapped command
        """
        parsedCommand = co.getParsedCommand()

        if parsedCommand is None:
            return

        self.activeOptions = parsedCommand[0]
        self.activeOptionsWithVariables = parsedCommand[1]
        self.wrappedCommand = parsedCommand[2]
        self.__pollInterval = pollInterval

        # Defaults
        self.__totalRunCount = 1
        self.__failedCount = None
        self.__sysTrace = False
        self.__callTrace = False
        self.__logTrace = False
        self.__debugMode = False
        self.__help = False
        self.__setupLogging = False
        self.rootLogFolder = rootLogFolder

        self.__setOptions()

    def __setOptions(self):
        """Sets all the flags based on the provided options"""

        if CommandOptions.COUNT in self.activeOptionsWithVariables:
            self.__totalRunCount = self.activeOptionsWithVariables[
                CommandOptions.COUNT]

        if CommandOptions.FAILED_COUNT in self.activeOptionsWithVariables:
            self.__failedCount = self.activeOptionsWithVariables[
                CommandOptions.FAILED_COUNT]

        if CommandOptions.SYS_TRACE in self.activeOptions:
            self.__sysTrace = True

        if CommandOptions.CALL_TRACE in self.activeOptions:
            self.__callTrace = True

        if CommandOptions.LOG_TRACE in self.activeOptions:
            self.__logTrace = True

        if CommandOptions.DEBUG in self.activeOptions:
            self.__debugMode = True

        if CommandOptions.HELP in self.activeOptions:
            self.__help = True

        if self.__sysTrace or self.__callTrace or self.__logTrace:
            self.__setupLogging = True

    def __gatherSystemStats(self, pid: int, f: IO):
        """Logs system stats of the given pid to the given file
        
            Parameters:
                pid (int):

                f (IO): an opened, writable IO
        """

        p = psutil.Process(pid)
        memory = p.memory_percent()
        cpuPercent = p.cpu_percent()
        threads = p.num_threads()
        network = psutil.net_io_counters()
        diskIO = p.io_counters()

        f.write(str(diskIO))
        f.write('\n')
        f.write(str(round(memory, 3))+"%")
        f.write('\n')
        f.write(str(cpuPercent)+"/"+str(threads))
        f.write('\n')
        f.write(str(network))
        f.write('\n-----------\n')

    def __runSubprocessCommand(self, command: str) -> subprocess.Popen:
        """Runs the given command in a subprocess.

            Parameters:
                
                command (str):
                    The command is the same that you would enter into a terminal.

            Returns: 
                subprocess.Popen
        """

        if self.__debugMode:
            print(self.DEBUG_MSG.format(command))
        return subprocess.Popen(command, shell=True)

    def __runCommandOnce(self, logPath: str) -> int:
        """
        Sets up the logs and runs the wrapped command

            Parameters:
                logPath (str): The path to output all logs for this run.
                    The path must already exist in the filesystem.

            Returns:
                (int) The exit code
        """

        command = []

        if self.__sysTrace:
            statsFile = open(os.path.join(
                logPath, self.SYS_TRACE_FILENAME), 'w')
            statsFile.write("Disk IO\n")
            statsFile.write("Memory\n")
            statsFile.write("Processes/Threads\n")
            statsFile.write("Network\n")
            statsFile.write('-----------\n')

        if self.__callTrace:
            command.extend(
                ['strace',
                 '-o',
                 os.path.join(logPath, self.CALL_TRACE_FILENAME)])

        command.extend(self.wrappedCommand)

        if self.__logTrace:
            command.extend(
                ['2>&1',
                 '|',
                 'tee',
                 os.path.join(logPath, self.LOG_TRACE_FILENAME)])
            command.extend([';(exit ${PIPESTATUS})'])

        p = self.__runSubprocessCommand(' '.join(command))

        while not self.__signalHandler.receivedSignal:
            exitCode = p.poll()

            if exitCode is not None:
                p.kill()
                break

            if self.__sysTrace:
                self.__gatherSystemStats(p.pid, statsFile)

            time.sleep(self.__pollInterval)

        if self.__sysTrace:
            statsFile.close()

        return exitCode


def main():
    co = CommandOptions(sys.argv)
    if not co.parseSuccessful:
        return None

    ce = CommandExecutor(co)
    return ce.__runCommandOnce()


if __name__ == "__main__":
    main()
