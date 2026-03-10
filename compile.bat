@echo off
setlocal enabledelayedexpansion

REM ------------------------------------------------------------
REM Build a SINGLE-FILE Windows executable with PyInstaller.
REM Output:   .\output\dicom_anon.exe
REM Cleanup:  removes all intermediate build artifacts
REM ------------------------------------------------------------

set "APP_NAME=dicom_anon"
set "ENTRY=anon.py"
set "OUTDIR=output"
set "BUILDDIR=.build"
set "VENV=.venv_build"

REM ------------------------------------------------------------
REM Tk/Tcl bundling (needed for tkinter to work in one-file builds)
REM Default points at the user's Miniconda installation, but you can
REM override TK_ROOT before running compile.bat:
REM   set TK_ROOT=C:\path\to\python\Library
REM ------------------------------------------------------------
if not defined TK_ROOT set "TK_ROOT=%USERPROFILE%\miniconda3\Library"
set "TK_BIN=%TK_ROOT%\bin"
set "TK_LIB=%TK_ROOT%\lib"

set "TCL_DLL=%TK_BIN%\tcl86t.dll"
set "TK_DLL=%TK_BIN%\tk86t.dll"
set "TCL_DIR=%TK_LIB%\tcl8.6"
set "TK_DIR=%TK_LIB%\tk8.6"
set "RTHOOK=%BUILDDIR%\rthook_tk.py"

REM ------------------------------------------------------------
REM ctypes/libffi bundling
REM Some Python distributions (notably Conda) ship libffi as DLLs
REM outside the standard DLLs folder (e.g. %base_prefix%\Library\bin).
REM If these are not bundled into the one-file exe, importing ctypes
REM (or packages that rely on it) can fail at runtime.
REM ------------------------------------------------------------
set "CTYPES_PYD="
set "PY_BASE_PREFIX="
set "FFI_DLL="

if not exist "%ENTRY%" (
  echo [ERROR] Entry file not found: %ENTRY%
  exit /b 1
)

echo [1/4] Preparing build environment...

REM Create build venv (isolates PyInstaller + deps from your global Python)
if not exist "%VENV%\Scripts\python.exe" (
  echo Creating venv: %VENV%
  python -m venv "%VENV%" || exit /b 1
)

set "PY=%VENV%\Scripts\python.exe"

REM Detect locations for _ctypes.pyd and libffi/ffi DLLs from the build interpreter

"%PY%" -c "import _ctypes; print(_ctypes.__file__)" > "ctypes.txt"
set /p CTYPES_PYD=<"ctypes.txt"
del "ctypes.txt"

"%PY%" -c "import sys; print(sys.base_prefix)" > "baseprefix.txt"
set /p PY_BASE_PREFIX=<"baseprefix.txt"
del "baseprefix.txt"

echo CTYPES_PYD=%CTYPES_PYD%
echo PY_BASE_PREFIX=%PY_BASE_PREFIX%

if defined PY_BASE_PREFIX (
  for %%f in ("%PY_BASE_PREFIX%\DLLs\*ffi*.dll") do set "FFI_DLL=%%f"
  for %%f in ("%PY_BASE_PREFIX%\Library\bin\*ffi*.dll") do set "FFI_DLL=%%f"
)

echo FFI_DLL=%FFI_DLL%


REM Install deps for runtime + build (PyInstaller)
echo Installing build dependencies...
"%PY%" -m pip install --upgrade pip setuptools wheel || exit /b 1
"%PY%" -m pip install -r requirements-build.txt || exit /b 1

REM Clean output + previous build artifacts
if exist "%OUTDIR%" rmdir /s /q "%OUTDIR%"
mkdir "%OUTDIR%" || exit /b 1

if exist "%BUILDDIR%" rmdir /s /q "%BUILDDIR%"
mkdir "%BUILDDIR%" || exit /b 1

REM Validate Tk/Tcl runtime files exist
if not exist "%TCL_DLL%" (
  echo [ERROR] Missing Tcl DLL: "%TCL_DLL%"
  echo         Set TK_ROOT to a valid Python\Library folder.
  exit /b 1
)
if not exist "%TK_DLL%" (
  echo [ERROR] Missing Tk DLL: "%TK_DLL%"
  echo         Set TK_ROOT to a valid Python\Library folder.
  exit /b 1
)
if not exist "%TCL_DIR%\init.tcl" (
  echo [ERROR] Missing Tcl scripts folder: "%TCL_DIR%"
  echo         Set TK_ROOT to a valid Python\Library folder.
  exit /b 1
)
if not exist "%TK_DIR%\tk.tcl" (
  echo [ERROR] Missing Tk scripts folder: "%TK_DIR%"
  echo         Set TK_ROOT to a valid Python\Library folder.
  exit /b 1
)

REM Create a small runtime hook that points tkinter at the bundled scripts
(
  echo import os, sys
  echo base = getattr^(sys, "_MEIPASS", os.path.dirname^(sys.executable^)^)
  echo # Ensure bundled DLLs are discoverable
  echo try:
  echo     os.add_dll_directory^(base^)
  echo except Exception:
  echo     os.environ["PATH"] = base + os.pathsep + os.environ.get^("PATH", ""^)
  echo tcl = os.path.join^(base, "tcl", "tcl8.6"^)
  echo tk  = os.path.join^(base, "tcl", "tk8.6"^)
  echo os.environ.setdefault^("TCL_LIBRARY", tcl^)
  echo os.environ.setdefault^("TK_LIBRARY", tk^)
) > "%RTHOOK%"

echo [2/4] Building one-file exe...

"%PY%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --noconsole ^
  --windowed ^
  --add-binary "%CTYPES_PYD%;." ^
  --add-binary "%FFI_DLL%;." ^
  --add-binary "%TCL_DLL%;." ^
  --add-binary "%TK_DLL%;." ^
  --add-data "%TCL_DIR%;tcl\\tcl8.6" ^
  --add-data "%TK_DIR%;tcl\\tk8.6" ^
  --runtime-hook "%RTHOOK%" ^
  --name "%APP_NAME%" ^
  --distpath "%OUTDIR%" ^
  --workpath "%BUILDDIR%\work" ^
  --specpath "%BUILDDIR%\spec" ^
  "%ENTRY%" || exit /b 1

echo [3/4] Cleaning intermediate files...
if exist "%BUILDDIR%" rmdir /s /q "%BUILDDIR%"

REM Optional: remove local __pycache__ created during build
if exist "__pycache__" rmdir /s /q "__pycache__"

echo [4/4] Done.
if exist "%OUTDIR%\%APP_NAME%.exe" (
  echo Built: %OUTDIR%\%APP_NAME%.exe
  exit /b 0
) else (
  echo [ERROR] Build finished but exe not found.
  exit /b 2
)
