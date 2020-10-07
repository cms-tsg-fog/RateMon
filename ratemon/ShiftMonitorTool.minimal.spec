# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['ShiftMonitorTool.py'],
             pathex=['/mnt/ratemon/venv/lib/python3.6/site-packages', '/mnt/ratemon/venv/lib64/python3.6/site-packages', '/usr/lib64/python3.6/site-packages', '/usr/lib64/root', '/mnt/ratemon'],
             binaries=[
               ('/usr/lib64/python3.6/site-packages/libcppyy_backend3_6.so', '.'),
               ('/usr/lib64/python3.6/site-packages/libcppyy3_6.cpython-36m-x86_64-linux-gnu.so', '.'),
               ('/usr/lib64/python3.6/site-packages/libROOTPythonizations3_6.cpython-36m-x86_64-linux-gnu.so', '.'),
               ('/usr/lib64/root/libcppyy3_6.so.6.22.02', '.'),
               ('/usr/lib64/root/libcppyy_backend3_6.so', '.'),
               ('/usr/lib64/root/libcppyy3_6.so.6.22', '.'),
               ('/usr/lib64/root/libcppyy_backend3_6.so.6.22', '.'),
               ('/usr/lib64/root/libcppyy_backend3_6.so.6.22.02', '.'),
               ('/usr/lib64/root/libcppyy3_6.so', '.'),
             ],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='ShiftMonitorTool',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='ShiftMonitorTool')
