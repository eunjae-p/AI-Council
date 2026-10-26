@echo off
rem First run: install Python/Node/CLIs, sign in, create the desktop shortcut
rem Runs Setup.cmd in this folder. (Keep this file ASCII-only: cmd.exe reads it in the system code page.)
call "%~dp0Setup.cmd" %*
