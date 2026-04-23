import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

if sys.platform == "darwin":
    icon_file = "assets/icon.icns"
elif sys.platform == "win32":
    icon_file = "assets/icon.ico"
else:
    icon_file = "assets/icon.png"

datas = [
    ("app/templates",  "app/templates"),
    ("app/static",     "app/static"),
    ("assets",         "assets"),
    ("QUIZ_FORMAT.md", "."),
]
datas += collect_data_files("customtkinter")

hiddenimports = (
    collect_submodules("customtkinter") + [
        "run_quiz_server",
        "darkdetect",
        "flask", "werkzeug", "werkzeug.serving", "werkzeug.routing",
        "jinja2", "click", "itsdangerous", "markupsafe",
    ]
)

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if sys.platform == "darwin":
    exe = EXE(
        pyz, a.scripts, [],
        exclude_binaries=True,
        name="QuizLauncher",
        debug=False,
        strip=False,
        upx=False,
        console=False,
        argv_emulation=True,
        icon=icon_file,
    )
    coll = COLLECT(
        exe, a.binaries, a.datas,
        strip=False,
        upx=False,
        name="QuizLauncher",
    )
    app = BUNDLE(
        coll,
        name="QuizLauncher.app",
        icon=icon_file,
        bundle_identifier="com.quizui.launcher",
        info_plist={"NSHighResolutionCapable": True},
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name="QuizLauncher",
        debug=False,
        strip=False,
        upx=True,
        console=False,
        icon=icon_file,
    )
