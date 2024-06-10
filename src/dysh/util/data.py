from urllib.parse import urljoin

from astropy.utils.data import download_file as astropy_download_file

# TODO: Replace with a value from config file
DYSH_URL = "https://www.gb.nrao.edu/dysh/example_data/"


def download_file(*args, **kwargs):
    kwargs.setdefault("pkgname", "dysh")
    kwargs.setdefault("cache", True)
    return astropy_download_file(*args, **kwargs)


def get_example_data(example: str | None = None, **kwargs):
    """Retrieve example data

    If `example` is None, all example data will be downloaded. Otherwise, specifying it
    will allow you to download a specific example dataset

    All `kwargs` are passed through to astropy.utils.data.download_file"""

    examples = {
        "positionswitch": [
            "positionswitch/data/AGBT05B_047_01/AGBT05B_047_01.raw.acs/AGBT05B_047_01.raw.acs.fits",
        ],
        "frequencyswitch": [
            "frequencyswitch/data/TREG_050627/TREG_050627.raw.acs/TREG_050627.raw.acs.fits",
        ],
        "subbeamnod": [
            "subbeamnod/data/AGBT13A_124_06/AGBT13A_124_06.raw.acs/AGBT13A_124_06.raw.acs.fits",
        ],
        "multiplefiles": [
            "multifits/TRCO_230413_Ka.raw.vegas/TRCO_230413_Ka.raw.vegas.A.fits",
            "multifits/TRCO_230413_Ka.raw.vegas/TRCO_230413_Ka.raw.vegas.B.fits",
            "multifits/TRCO_230413_Ka.raw.vegas/TRCO_230413_Ka.raw.vegas.C.fits",
            "multifits/TRCO_230413_Ka.raw.vegas/TRCO_230413_Ka.raw.vegas.D.fits",
        ],
    }

    examples_to_download = [example] if example else examples.keys()
    try:
        return {
            e: [download_file(urljoin(DYSH_URL, url), **kwargs) for url in examples[e]] for e in examples_to_download
        }
    except KeyError as error:
        raise KeyError(f"{example} is not available. The following are: {', '.join(examples.keys())}") from error
