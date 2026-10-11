"""Use the .NET Framework declared by our installer, before pywebview fallback."""
RUNTIME_FILES=(
    'clr_loader/ffi/dlls/amd64/ClrLoader.dll',
    'pythonnet/runtime/Python.Runtime.dll',
    'webview/lib/Microsoft.Web.WebView2.Core.dll',
    'webview/lib/Microsoft.Web.WebView2.WinForms.dll',
    'webview/lib/WebBrowserInterop.x64.dll',
    'webview/lib/runtimes/win-x64/native/WebView2Loader.dll',
)

class MissingRuntimeFile(FileNotFoundError):
    def __init__(self,resource):
        self.resource=resource
        super().__init__('WINDOWS_RUNTIME_FILE_MISSING')

def verify_packaged_runtime(root):
    for resource in RUNTIME_FILES:
        if not (root/resource).is_file(): raise MissingRuntimeFile(resource)

def initialize_netfx():
    # pywebview 6.2.1 catches ANY failure importing clr, sets PYTHONNET_RUNTIME
    # to coreclr and retries, masking the original .NET Framework failure.
    # A runtime object avoids PYTHONNET_* env overrides and prevents that fallback.
    import clr_loader
    import pythonnet
    pythonnet.load(clr_loader.get_netfx())
