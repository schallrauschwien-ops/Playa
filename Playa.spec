# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('assets', 'assets')]
binaries = []
hiddenimports = []
tmp_ret = collect_all('sounddevice')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('soundfile')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('soxr')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('keyboard')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('imageio_ffmpeg')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


# ---------------------------------------------------------------------
# ASIO aussortieren
#
# sounddevice liefert die PortAudio-DLL in zwei Fassungen mit: einmal
# ohne und einmal mit ASIO. Die ASIO-Fassung enthaelt Code aus Steinbergs
# ASIO-SDK. Dessen Lizenz untersagt die Weitergabe des SDK oder von
# Teilen davon, und das vertraegt sich nicht mit der GPLv3, unter der
# Playa steht. Audacity hat dasselbe Problem und liefert ASIO aus
# genau diesem Grund nicht mit.
#
# Also: die -asio.dll geht nicht ins Paket. Playa laeuft dann ueber
# WASAPI und die uebrigen Windows-Wege. Wer ASIO braucht, legt sich die
# passende DLL selbst nach
#     Playa/_internal/_sounddevice_data/portaudio-binaries/
# run.py merkt das und schaltet ASIO von allein ein.
#
# Der Filter laeuft zweimal: einmal ueber die oben gesammelten Listen
# und nach der Analyse noch einmal ueber a.binaries und a.datas. Der
# zweite Durchgang ist der wichtige, denn PyInstaller hat fuer
# sounddevice einen eigenen Hook, der die DLLs sonst wieder hereinholt.
# ---------------------------------------------------------------------

def ohne_asio(eintraege):
    rest = []
    for eintrag in eintraege:
        text = ' '.join(str(t) for t in eintrag if isinstance(t, str)).lower()
        if '-asio.dll' in text:
            print('Playa.spec: ASIO-DLL bleibt draussen ->', eintrag[0])
            continue
        rest.append(eintrag)
    return rest


binaries = ohne_asio(binaries)
datas    = ohne_asio(datas)


a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# Nach der Analyse noch einmal, damit auch das, was der sounddevice-Hook
# von PyInstaller selbst eingesammelt hat, wieder herausfaellt.
a.binaries = ohne_asio(a.binaries)
a.datas    = ohne_asio(a.datas)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Playa',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/playa.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Playa',
)
