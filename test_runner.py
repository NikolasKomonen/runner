import pytest
import os
import shutil
from runner import CommandOptions
import datetime
import pdb

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
