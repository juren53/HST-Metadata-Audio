"""
HAM – HSTL Audio Metadata Framework
"""
import datetime as _dt, time as _time

__version__ = "0.2.2"

_now = _dt.datetime.now()
_tz_full = _time.tzname[_time.localtime().tm_isdst]
_tz = "".join(w[0] for w in _tz_full.split())  # "Central Daylight Time" -> "CDT"
__commit_date__ = _now.strftime("%Y-%m-%d %H%M ") + _tz

__app_name__ = "HSTL Audio Metadata"
__short_name__ = "HAM"
