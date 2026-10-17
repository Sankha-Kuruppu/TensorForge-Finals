"""JobShield LK: fake overseas-job post detection with drift monitoring."""
# On Windows, torch's DLLs fail to initialise (WinError 1114) if pyarrow's are
# loaded first, and pandas loads pyarrow. Import torch before anything else.
import torch  # noqa: F401
