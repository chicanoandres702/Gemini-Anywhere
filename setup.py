# setup.py
import sys
from cx_Freeze import setup, Executable

setup(
    name="GeminiOverlay",
    version="1.0",
    description="Gemini Overlay Application",
    executables=[
        Executable(
            "GeminiOverlay.py",  # Change to the filename of your main script
            base="Win32GUI" if sys.platform == "win32" else None  # Use "Win32GUI" on Windows to suppress console window
        )
    ],
    options={
        "build_exe": {
             "include_files": [],
             "packages": ["customtkinter", "keyboard", "google.generativeai"]
         }
    }
)
