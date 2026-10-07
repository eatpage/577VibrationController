@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PYW=C:\Users\guaiy\.workbuddy\binaries\python\envs\default\Scripts\pythonw.exe"
if not exist "%PYW%" set "PYW=pythonw"

start "" "%PYW%" main.py
