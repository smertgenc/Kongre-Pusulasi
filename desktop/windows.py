"""Small Windows API wrapper: per-user lock, job lifetime and native dialogs."""
import ctypes
from ctypes import wintypes

def kernel(): return ctypes.WinDLL('kernel32', use_last_error=True)

class AlreadyRunning(ValueError): pass

def windows_error(operation):
    error=OSError(operation)
    error.winerror=ctypes.get_last_error()
    return error

def message(text, *, error=False, confirm=False):
    api = ctypes.WinDLL('user32', use_last_error=True)
    api.MessageBoxW.argtypes = [wintypes.HWND,wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.UINT]
    api.MessageBoxW.restype = ctypes.c_int
    return api.MessageBoxW(None,text,'AHP Congress Analyzer', (0x10 if error else 0x40)|(0x4 if confirm else 0)) == 6

class InstanceLock:
    def __init__(self):
        self.api = kernel()
        self.api.CreateMutexW.argtypes = [ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR]
        self.api.CreateMutexW.restype = wintypes.HANDLE
        self.api.CloseHandle.argtypes = [wintypes.HANDLE]
        self.handle = self.api.CreateMutexW(None, False, 'Local\\AHP-Congress-Analyzer')
        if not self.handle: raise windows_error('INSTANCE_LOCK_FAILED')
        if ctypes.get_last_error() == 183:
            self.close(); raise AlreadyRunning('Uygulama zaten açık. Önce açık pencereyi kapatın.')
    def close(self):
        if self.handle: self.api.CloseHandle(self.handle); self.handle = None

class ChildJob:
    """Kill all descendants if the desktop host exits unexpectedly."""
    def __init__(self):
        class Basic(ctypes.Structure):
            _fields_ = [('process_time',ctypes.c_int64),('job_time',ctypes.c_int64),
                        ('flags',wintypes.DWORD),('min_working_set',ctypes.c_size_t),
                        ('max_working_set',ctypes.c_size_t),('active',wintypes.DWORD),
                        ('affinity',ctypes.c_size_t),('priority',wintypes.DWORD),('scheduling',wintypes.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(name,ctypes.c_uint64) for name in ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]
        class Extended(ctypes.Structure):
            _fields_ = [('basic',Basic),('io',IO),('process_memory',ctypes.c_size_t),
                        ('job_memory',ctypes.c_size_t),('peak_process',ctypes.c_size_t),('peak_job',ctypes.c_size_t)]
        self.api = kernel()
        self.api.CreateJobObjectW.argtypes = [ctypes.c_void_p,wintypes.LPCWSTR]
        self.api.CreateJobObjectW.restype = wintypes.HANDLE
        self.api.SetInformationJobObject.argtypes = [wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
        self.api.SetInformationJobObject.restype = wintypes.BOOL
        self.api.OpenProcess.argtypes = [wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        self.api.OpenProcess.restype = wintypes.HANDLE
        self.api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE,wintypes.HANDLE]
        self.api.AssignProcessToJobObject.restype = wintypes.BOOL
        self.api.CloseHandle.argtypes = [wintypes.HANDLE]
        self.handle = self.api.CreateJobObjectW(None,None)
        if not self.handle: raise windows_error('JOB_CREATE_FAILED')
        info = Extended(); info.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.api.SetInformationJobObject(self.handle,9,ctypes.byref(info),ctypes.sizeof(info)):
            error=windows_error('JOB_CONFIG_FAILED');self.close();raise error

    def assign(self, pid):
        process = self.api.OpenProcess(0x0100|0x0001,False,pid)
        try:
            if not process or not self.api.AssignProcessToJobObject(self.handle,process):
                raise windows_error('JOB_ASSIGN_FAILED')
        finally:
            if process: self.api.CloseHandle(process)
    def close(self):
        if self.handle: self.api.CloseHandle(self.handle); self.handle = None
