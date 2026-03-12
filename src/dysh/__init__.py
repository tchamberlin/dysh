"""Top-level package for dysh."""

import warnings

# Astropy Angle.to_string() triggers numpy vectorize floating-point warning (astropy#18989)
warnings.filterwarnings("ignore", message="invalid value encountered in do_format")
# ipympl multiple-inheritance MRO issue with traitlets (ipympl#488)
warnings.filterwarnings("ignore", message="Passing unrecognized arguments to super")

# Deferred IERS-B initialization.  Loading the table at import time costs
# ~200-400ms and is only needed when EarthLocation.get_itrs() is actually
# called (coordinate transforms).  Call _ensure_iers() at the three call
# sites instead.
_iers_initialized = False


def _ensure_iers():
    """Load the IERS-B table into astropy's cache on first use."""
    global _iers_initialized
    if not _iers_initialized:
        from astropy.utils.iers import IERS_B
        from astropy.utils.iers import conf as iers_conf

        iers_conf.auto_download = False
        IERS_B.open()
        _iers_initialized = True


__version__ = "0.14.0"

all = ["version"]


def version():
    """Version of the dysh code

    Returns
    -------
    version : str
        dysh version.
    """
    return __version__
