"""
HAM – HSTL Audio Metadata Framework
"""
import datetime as _dt, time as _time

__version__ = "0.1.3"

_now = _dt.datetime.now()
_tz = _time.tzname[_time.localtime().tm_isdst]
__commit_date__ = _now.strftime("%Y-%m-%d %H%M ") + _tz

__app_name__ = "HSTL Audio Metadata"
__short_name__ = "HAM"
