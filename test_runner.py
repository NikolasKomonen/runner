import pytest
import os
import shutil
from runner import CommandOptions, CommandExecutor, DateTimeHandler
import datetime

testRootFolder = '.tempTestLogs'


def setup_module():
    if os.path.exists(testRootFolder):
        shutil.rmtree(testRootFolder)
    os.mkdir(testRootFolder)


def teardown_module():
    if os.path.exists(testRootFolder):
        shutil.rmtree(testRootFolder)


class TestCommandOptions:

    def test_parsed_all_options(self):
        wrappedCommand = ['ping', '-c', '2', '192.168.0.14.14']
        fullCommand = ['runner.py', '-c', '4', '--failed-count', '2',
                       '--sys-trace', '--call-trace', '--log-trace', '--debug']
        fullCommand.extend(wrappedCommand)
        co = CommandOptions(fullCommand)
        assert co.parseSuccessful

        result = co.getParsedCommand()

        expectedActiveOptions = set()
        expectedActiveOptions.update(
            [CommandOptions.SYS_TRACE, CommandOptions.CALL_TRACE,
             CommandOptions.LOG_TRACE, CommandOptions.DEBUG])
        assert result[0] == expectedActiveOptions

        expectedActiveOptionsWithVariables = {
            CommandOptions.COUNT: 4, CommandOptions.FAILED_COUNT: 2}
        assert result[1] == expectedActiveOptionsWithVariables

        assert result[2] == wrappedCommand

    def test_parsed_some_options(self):
        wrappedCommand = ['ping', '-c', '2', '192.168.0.14.14']
        fullCommand = ['runner.py', '-c', '4', '--call-trace', '--log-trace']
        fullCommand.extend(wrappedCommand)
        co = CommandOptions(fullCommand)
        assert co.parseSuccessful

        result = co.getParsedCommand()

        expectedActiveOptions = set()
        expectedActiveOptions.update(
            [CommandOptions.CALL_TRACE, CommandOptions.LOG_TRACE])
        assert result[0] == expectedActiveOptions

        expectedActiveOptionsWithVariables = {CommandOptions.COUNT: 4}
        assert result[1] == expectedActiveOptionsWithVariables

        assert result[2] == wrappedCommand

    def test_parsed_options_missing_variable(self, capsys):
        wrappedCommand = ['ping', '-c', '2', '192.168.0.14.14']
        # --failed-count is missing an int after it
        fullCommand = ['runner.py', '-c', '4', '--failed-count', '--debug']
        fullCommand.extend(wrappedCommand)
        co = CommandOptions(fullCommand)
        assert not co.parseSuccessful

        captured = capsys.readouterr()
        assert captured.err == CommandOptions.MISSING_INT_MSG.format(
            CommandOptions.FAILED_COUNT)

    def test_parsed_options_small_variable(self, capsys):
        wrappedCommand = ['ping', '-c', '2', '192.168.0.14.14']
        # --failed-count value should be > 0
        fullCommand = ['runner.py', '-c', '4',
                       '--failed-count', '0', '--debug']
        fullCommand.extend(wrappedCommand)
        co = CommandOptions(fullCommand)
        assert not co.parseSuccessful

        captured = capsys.readouterr()
        assert captured.err == CommandOptions.LARGER_INT_MSG.format(
            0, CommandOptions.FAILED_COUNT)

    def test_parsed_options_missing_command(self, capsys):
        fullCommand = ['runner.py', '-c', '4',
                       '--failed-count', '2', '--debug']
        # no wrapped command
        co = CommandOptions(fullCommand)
        assert not co.parseSuccessful

        captured = capsys.readouterr()
        assert captured.err == CommandOptions.NO_WRAPPED_COMMAND_MSG

    def test_help_option_activated(self, capsys):
        fullCommand = ['runner.py', '--help']
        co = CommandOptions(fullCommand)
        co.getParsedCommand()
        assert not co.parseSuccessful

        captured = capsys.readouterr()
        expectedMessage = (CommandOptions.HELP_MESSAGE +
                           CommandOptions.HELP_EXAMPLE)
        assert captured.err == expectedMessage

    def test_help_option_activated_with_other_options(self, capsys):
        fullCommand = ['runner.py', '--debug', '--help', '--log-trace']
        co = CommandOptions(fullCommand)
        co.getParsedCommand()
        assert not co.parseSuccessful

        captured = capsys.readouterr()
        expectedMessage = (CommandOptions.HELP_MESSAGE +
                           CommandOptions.HELP_EXAMPLE)
        assert captured.err == expectedMessage

    def test_unrecognized_option(self, capsys):
        wrappedCommand = ['ping', '-c', '2', '192.168.0.14.14']
        fullCommand = ['runner.py', '-c', '4', '--failed-count', '2',
                       '--UNRECOGNIZED-OPTION', '--sys-trace', '--call-trace',
                       '--log-trace', '--debug']
        fullCommand.extend(wrappedCommand)
        co = CommandOptions(fullCommand)
        assert not co.parseSuccessful

        captured = capsys.readouterr()
        expectedMessage = CommandOptions.UNRECOGNIZED_OPTION_MSG.format(
            '--UNRECOGNIZED-OPTION')
        assert captured.err == expectedMessage


class MockDateTimeHandler(DateTimeHandler):

    def getNow(self):
        return self.now

    def getNowFormattedString(self):
        return self.getNow().strftime(DateTimeHandler.dateTimeFormat)

    def setNow(self, now: datetime.datetime):
        self.now = now


class TestCommandExecutor:

    def teardown_method(self):
        items = os.listdir(testRootFolder)
        for i in items:
            itemPath = os.path.join(testRootFolder, i)
            if os.path.isfile(itemPath):
                os.unlink(itemPath)
            if os.path.isdir(itemPath):
                shutil.rmtree(itemPath)
        if os.path.exists('failpass.txt'):
            os.unlink('failpass.txt')

    def verifyFoldersExist(self, currentRunFolderPath,
                           currentRunFolder: bool = True,
                           call: bool = True, sys: bool = True,
                           log: bool = True):
        exists = os.path.exists(currentRunFolderPath)
        assert exists == currentRunFolder
        if exists:
            assert os.path.exists(os.path.join(
                                  currentRunFolderPath,
                                  CommandExecutor.CALL_TRACE_FILENAME)) == call
            assert os.path.exists(os.path.join(
                                  currentRunFolderPath,
                                  CommandExecutor.SYS_TRACE_FILENAME)) == sys
            assert os.path.exists(os.path.join(
                                  currentRunFolderPath,
                                  CommandExecutor.LOG_TRACE_FILENAME)) == log

    def buildCommandOptions(self, wrappedCommand: str, count: int = 1,
                            failedCount: int = None, sys: bool = True,
                            call: bool = True, log: bool = True,
                            debug: bool = True, help: bool = False):
        args = ['runner.py']
        args.extend([CommandOptions.COUNT, str(count)])
        if failedCount is not None:
            args.extend([CommandOptions.FAILED_COUNT, str(failedCount)])
        if sys:
            args.append(CommandOptions.SYS_TRACE)
        if call:
            args.append(CommandOptions.CALL_TRACE)
        if log:
            args.append(CommandOptions.LOG_TRACE)
        if debug:
            args.append(CommandOptions.DEBUG)
        if help:
            args.append(CommandOptions.HELP)
        args.append(wrappedCommand)
        return CommandOptions(args)

    def getCommandExecutor(self, co: CommandOptions,
                           dtHandler: DateTimeHandler,
                           rootLogFolder: str = testRootFolder,
                           pollInterval: float = 0.1):
        return CommandExecutor(co, dtHandler=dtHandler,
                               rootLogFolder=rootLogFolder,
                               pollInterval=pollInterval)

    def run_fail_pass_script(self, dt: datetime.datetime):
        wrappedCommand = 'testScripts/failpass.sh ' + testRootFolder
        mockDTH = MockDateTimeHandler()
        mockDTH.setNow(dt)
        runCount = 5
        cb = self.getCommandExecutor(self.buildCommandOptions(
            wrappedCommand, count=runCount), dtHandler=mockDTH)
        assert cb.runCommand() == 1

        for i in range(0, runCount):
            currentRunFolderPath = os.path.join(testRootFolder, dt.strftime(
                DateTimeHandler.dateTimeFormat), str(i + 1))
            if i % 2 == 0:
                # every even run fails, so all folders will exist
                self.verifyFoldersExist(currentRunFolderPath)
            else:
                self.verifyFoldersExist(
                    currentRunFolderPath, currentRunFolder=False)

        # Defined in failpass.sh
        fpFile = 'failpass.txt'
        fpFile = os.path.join(testRootFolder, fpFile)
        if os.path.exists(fpFile):
            os.unlink(fpFile)

    def test_all_options_active_and_some_fail(self):
        self.run_fail_pass_script(datetime.datetime(2020, 1, 1, 1, 1, 1))

    def test_all_options_active_run_twice_and_some_fail(self):
        self.run_fail_pass_script(datetime.datetime(2020, 1, 1, 1, 1, 1))
        self.run_fail_pass_script(datetime.datetime(2020, 1, 1, 1, 2, 1))

    def test_all_options_all_pass(self):
        exitCode = 0
        wrappedCommand = 'testScripts/exitwith.sh ' + str(exitCode)
        mockDTH = MockDateTimeHandler()
        dt = datetime.datetime(2020, 5, 1, 1, 2, 1)
        mockDTH.setNow(dt)
        runCount = 3
        cb = self.getCommandExecutor(self.buildCommandOptions(
            wrappedCommand, count=runCount), dtHandler=mockDTH)
        assert cb.runCommand() == exitCode

        for i in range(0, runCount):
            currentRunFolderPath = os.path.join(testRootFolder, dt.strftime(
                DateTimeHandler.dateTimeFormat), str(i + 1))
            self.verifyFoldersExist(
                currentRunFolderPath, currentRunFolder=False)

    def test_all_options_all_fail(self):
        exitCode = 2
        wrappedCommand = 'testScripts/exitwith.sh ' + str(exitCode)
        mockDTH = MockDateTimeHandler()
        dt = datetime.datetime(2020, 5, 1, 1, 2, 1)
        mockDTH.setNow(dt)
        runCount = 3
        cb = self.getCommandExecutor(self.buildCommandOptions(
            wrappedCommand, count=runCount), dtHandler=mockDTH)
        assert cb.runCommand() == exitCode

        for i in range(0, runCount):
            currentRunFolderPath = os.path.join(testRootFolder, dt.strftime(
                DateTimeHandler.dateTimeFormat), str(i + 1))
            self.verifyFoldersExist(currentRunFolderPath)

    def test_hit_failed_count(self, capsys):
        exitCode = 2
        wrappedCommand = 'testScripts/exitwith.sh ' + str(exitCode)
        mockDTH = MockDateTimeHandler()
        dt = datetime.datetime(2026, 5, 1, 1, 2, 1)
        mockDTH.setNow(dt)
        runCount = 4
        failedCount = 3
        cb = self.getCommandExecutor(self.buildCommandOptions(
            wrappedCommand, count=runCount, failedCount=failedCount),
            dtHandler=mockDTH)
        assert cb.runCommand() == exitCode

        captured = capsys.readouterr()
        assert CommandExecutor.FAILED_COUNT_MSG in captured.out

    def test_some_options_active_all_fail(self):
        exitCode = 3
        wrappedCommand = 'testScripts/exitwith.sh ' + str(exitCode)
        mockDTH = MockDateTimeHandler()
        dt = datetime.datetime(2021, 6, 1, 1, 2, 1)
        mockDTH.setNow(dt)
        runCount = 3
        cb = self.getCommandExecutor(self.buildCommandOptions(
            wrappedCommand, count=runCount, sys=False), dtHandler=mockDTH)
        assert cb.runCommand() == exitCode

        for i in range(0, runCount):
            currentRunFolderPath = os.path.join(testRootFolder, dt.strftime(
                DateTimeHandler.dateTimeFormat), str(i + 1))
            self.verifyFoldersExist(currentRunFolderPath, sys=False)

    def test_no_options_active_all_fail(self):
        exitCode = 3
        wrappedCommand = 'testScripts/exitwith.sh ' + str(exitCode)
        mockDTH = MockDateTimeHandler()
        dt = datetime.datetime(2021, 3, 2, 1, 2, 1)
        mockDTH.setNow(dt)
        runCount = 3
        cb = self.getCommandExecutor(self.buildCommandOptions(
            wrappedCommand, count=runCount, sys=False, call=False, log=False),
            dtHandler=mockDTH)
        assert cb.runCommand() == exitCode

        for i in range(0, runCount):
            currentRunFolderPath = os.path.join(testRootFolder, dt.strftime(
                DateTimeHandler.dateTimeFormat), str(i + 1))
            self.verifyFoldersExist(
                currentRunFolderPath, currentRunFolder=False)

    def test_debug_on(self, capsys):
        exitCode = 0
        wrappedCommand = 'testScripts/exitwith.sh ' + str(exitCode)
        mockDTH = MockDateTimeHandler()
        dt = datetime.datetime(2020, 5, 1, 1, 2, 1)
        mockDTH.setNow(dt)
        runCount = 1
        cb = self.getCommandExecutor(self.buildCommandOptions(
            wrappedCommand, count=runCount, log=False, sys=False),
            dtHandler=mockDTH)
        assert cb.runCommand() == exitCode
        outPath = os.path.join(testRootFolder, dt.strftime(
            DateTimeHandler.dateTimeFormat), str(1),
            CommandExecutor.CALL_TRACE_FILENAME)
        expectedCommand = 'strace -o ' + outPath + ' ' + wrappedCommand
        captured = capsys.readouterr()
        assert expectedCommand in captured.out

    def test_debug_off(self, capsys):
        exitCode = 0
        wrappedCommand = 'testScripts/exitwith.sh ' + str(exitCode)
        mockDTH = MockDateTimeHandler()
        dt = datetime.datetime(2020, 5, 1, 1, 2, 1)
        mockDTH.setNow(dt)
        runCount = 1
        cb = self.getCommandExecutor(self.buildCommandOptions(
            wrappedCommand, count=runCount, log=False, sys=False),
            dtHandler=mockDTH)
        assert cb.runCommand() == exitCode
        expectedString = '[DEBUG_TRACE]'
        captured = capsys.readouterr()
        assert expectedString not in captured.out
