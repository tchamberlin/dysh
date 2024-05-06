"""Load generic SDFITS files
- Not typically used directly.  Sub-class for specific telescope SDFITS flavors.
"""

import astropy.units as u
import numpy as np
import pandas as pd
from astropy.io import fits

from ..spectra.spectrum import Spectrum
from ..util import uniq


class SDFITSLoad(object):
    """
    Generic Container for a bintable(s) from selected HDU(s) for a single SDFITS file.
    For multiple SDFITS files, see :class:`~gbtfitsload.GBTFITSLoad`.

    Parameters
    ----------
    filename : str
        input file name
    source  : str
        target source to select from input file. Default: all sources
    hdu : int or list
        Header Data Unit to select from input file. Default: all HDUs

    """

    def __init__(self, filename, source=None, hdu=None, **kwargs):
        kwargs_opts = {
            "fix": False,  # fix non-standard header elements
            "verbose": False,
        }
        kwargs_opts.update(kwargs)
        if kwargs_opts["verbose"]:
            print("==SDFITSLoad %s" % filename)
        # We cannot use this to get mmHg as it will disable all default astropy units!
        # https://docs.astropy.org/en/stable/api/astropy.units.cds.enable.html#astropy.units.cds.enable
        # u.cds.enable()  # to get mmHg
        self._filename = filename
        self._bintable = []
        self._index = None
        self._binheader = []
        self._hdu = fits.open(filename)
        self._header = self._hdu[0].header
        self.load(hdu, **kwargs_opts)
        doindex = kwargs_opts.get("index", True)
        if doindex:
            self.create_index()

    def __del__(self):
        # We need to ensure that any open HDUs are properly
        # closed in order to avoid the ResourceWarning about
        # unclosed file(s)
        try:
            self._hdu.close()
        except Exception:
            pass

    def info(self):
        """Return the `~astropy.HDUList` info()"""
        return self._hdu.info()

    @property
    def bintable(self):
        """The list of bintables"""
        return self._bintable

    def binheader(self):
        """The list of bintable headers"""
        return self._binheader

    @property
    def filename(self):
        """The input SDFITS filename"""
        return self._filename

    def index(self, hdu=None, bintable=None):
        """
        Return The index table.

        Parameters
        ----------
        hdu : int or list
            Header Data Unit to select from the index. Default: all HDUs
        bintable :  int
            The index of the `bintable` attribute, None means all bintables

        Returns
        -------
        index : ~pandas.DataFrame
            The index of this SDFITS file

        """
        df = self._index
        if hdu is None and bintable is None:
            return df
        if hdu is not None:
            df = df[df["HDU"] == hdu]
        if bintable is not None:
            df = df[df["BINTABLE"] == bintable]
        return df

    def create_index(self, hdu=None):
        """
        Create the index of the SDFITS file.

        Parameters
        ----------
            hdu : int or list
                Header Data Unit to select from input file. Default: all HDUs

        """
        if hdu is not None:
            ldu = list([hdu])
        else:
            ldu = range(1, len(self._hdu))
        self._index = None
        for i in ldu:
            # Create a DataFrame without the data column.
            df = pd.DataFrame(np.lib.recfunctions.drop_fields(self._hdu[i].data, "DATA"))
            # Select columns that are strings, decode them and remove white spaces.
            df_obj = df.select_dtypes(["object"])
            df[df_obj.columns] = df_obj.apply(lambda x: x.str.decode("utf-8").str.strip())
            ones = np.ones(len(df.index), dtype=int)
            # create columns to track HDU and BINTABLE numbers and original row index
            df["HDU"] = i * ones
            df["BINTABLE"] = (i - 1) * ones
            df["ROW"] = np.arange(len(df))
            if self._index is None:
                self._index = df
            else:
                self._index = pd.concat([self._index, df], axis=0)
        self.add_primary_hdu()

    def add_primary_hdu(self):
        pass

    def load(self, hdu=None, **kwargs):
        """
        Load the bintable for given hdu.
        Note mmHg and UTC are unrecognized units.  mmHg is in astropy.units.cds but UTC is just wrong.

        Parameters
        ----------
            hdu : int or list
                Header Data Unit to select from input file. Default: all HDUs

        """
        self._bintable = []
        self._binheader = []
        self._nrows = []
        # fix = kwargs.get("fix")

        if hdu is not None:
            ldu = list([hdu])
        else:
            ldu = range(1, len(self._hdu))
        for i in ldu:
            j = i - 1
            self._bintable.append(self._hdu[i])
            self._binheader.append(self._hdu[i].header)
            self._nrows.append(self._binheader[j]["NAXIS2"])

    def fix_meta(self, meta):
        """
        Do any repair to the meta/header for peculariaties in definitions
        from a particular observatory
        The passed-in dictionary will be repaired in place.
        At minimum this method must populate meta['VELDEF'] and meta['VELFRAME']

        Parameters
        ----------
            meta : dict
                The header of the `~Spectrum` to be fixed, corresponding to the `meta` attribute of the Spectrum.

        """
        pass

    def velocity_convention(self, veldef, velframe):
        """
        Compute the velocity convention string use for velocity conversions,
        given the VELDEF and VELFRAME values.
        Return value must be a recognized string of `~specutils.Spectrum1D`, one of
        {"doppler_relativistic", "doppler_optical", "doppler_radio"}
        Sub-classes should implement, because different observatories use VELDEF and
        VELFRAME inconsistently. This base class method hard-coded to return "doppler_radio."

        Parameters
        ----------
            veldef : str
                The velocity definition string (`VELDEF` FITS keyword)
            velframe : str
                The velocity frame string (`VELFRAME` FITS keyword)

        """
        return "doppler_radio"

    def udata(self, key, bintable=None):
        """
        The unique list of values of a given header keyword

        Parameters
        ----------
            key : str
                The keyword to retrieve
            bintable :  int
                The index of the `bintable` attribute, None means all bintables

        Returns
        -------
            udata : list
                The unique set of values for the input keyword.

        """
        if bintable is not None:
            df = self._index[self._index["BINTABLE"] == bintable]
        else:
            df = self._index
        return uniq(df[key])

    def ushow(self, key, bintable=None):
        """
        Print the unique list of values of a given header keyword

        Parameters
        ----------
            key : str
                The keyword to retrieve
            bintable :  int
                The index of the `bintable` attribute, None means all bintables

        """
        print(f"{bintable} {key}: {self.udata(bintable,key)}")

    def naxis(self, naxis, bintable):
        """
        The NAXISn value of the input bintable.

        Parameters
        ----------
            naxis : int
                The NAXIS whose length is requested
            bintable :  int
                The index of the `bintable` attribute

        Returns
        -------
            naxis : the length of the NAXIS

        """
        nax = f"NAXIS{naxis}"
        return self._binheader[bintable][nax]

    def nintegrations(self, bintable, source=None):
        """
        The number of integrations on a given source divided by the number of polarizations

        Parameters
        ----------
            bintable :  int
                The index of the `bintable` attribute
            source: str
                The source name (OBJECT keyword) or None for all sources. Default: None

        Returns
        -------
            nintegrations : the number of integrations

        """

        if source is not None:
            df = self.select("OBJECT", source, self._index[bintable])
            # nfeed = df["FEED"].nunique()
            numsources = len(df)
            # nint = numsources//(self.npol(bintable)*nfeed)
            nint = numsources // self.npol(bintable)
        else:
            nint = self.nrows(bintable) // self.npol(bintable)
        return nint

    def _find_bintable_and_row(self, row):
        """Given a row number from a multi-bintable spanning index, return
            the bintable and original row number

        Parameters
        ----------
            row :  int
                The record (row) index to retrieve

        Returns:
            tuple of ints (bintable, row)
        """
        return (self._index.iloc[row]["BINTABLE"], self._index.iloc[row]["ROW"])

    def rawspectra(self, bintable):
        """
        Get the raw (unprocessed) spectra from the input bintable.

        Parameters
        ----------
            bintable :  int
                The index of the `bintable` attribute

        Returns
        -------
            rawspectra : ~numpy.ndarray
                The DATA column of the input bintable

        """
        return self._bintable[bintable].data[:]["DATA"]

    def rawspectrum(self, i, bintable=0):
        """
        Get a single raw (unprocessed) spectrum from the input bintable.

        Parameters
        ----------
            i :  int
                The row index to retrieve.
            bintable :  int or None
                The index of the `bintable` attribute. If None, the underlying bintable is computed from i

        Returns
        -------
            rawspectrum : ~numpy.ndarray
                The i-th row of DATA column of the input bintable

        """
        if bintable is None:
            (bt, row) = self._find_bintable_and_row(i)
            return self._bintable[bt].data[:]["DATA"][row]
        else:
            return self._bintable[bintable].data[:]["DATA"][i]

    def getrow(self, i, bintable=0):
        """
        Get a FITS_record from the input bintable

        Parameters
        ----------
            i :  int
                The record (row) index to retrieve
            bintable :  int
                The index of the `bintable` attribute

        Returns
        -------
            row : :class:`~astropy.io.fits.fitsrec.FITS_record`
                The i-th record  of the input bintable

        """
        return self._bintable[bintable].data[i]

    def getspec(self, i, bintable=0, observer_location=None):
        """
        Get a row (record) as a Spectrum

        Parameters
        ----------
        i : int
            The record (row) index to retrieve
        bintable : int, optional
             The index of the `bintable` attribute. default is 0.
        observer_location : `~astropy.coordinates.EarthLocation`
            Location of the observatory. See `~dysh.coordinates.Observatory`.
            This will be transformed to `~astropy.coordinates.ITRS` using the time of observation DATE-OBS or MJD-OBS in
            the SDFITS header.  The default is None.

        Returns
        -------
        s : `~dysh.spectra.spectrum.Spectrum`
            The Spectrum object representing the data row.

        """
        df = self.index(bintable=bintable)
        meta = df.iloc[i].dropna().to_dict()
        data = self.rawspectrum(i, bintable)
        meta["NAXIS1"] = len(data)
        if "CUNIT1" not in meta:
            meta["CUNIT1"] = "Hz"  # @todo this is in gbtfits.hdu[0].header['TUNIT11'] but is it always TUNIT11?
        meta["CUNIT2"] = "deg"  # is this always true?
        meta["CUNIT3"] = "deg"  # is this always true?
        restfrq = meta["RESTFREQ"]
        rfq = restfrq * u.Unit(meta["CUNIT1"])
        restfreq = rfq.to("Hz").value
        meta["RESTFRQ"] = restfreq  # WCS wants no E

        s = Spectrum.make_spectrum(data * u.ct, meta, observer_location=observer_location)
        return s

    def nrows(self, bintable):
        """
        The number of rows of the input bintable

        Parameters
        ----------
            bintable :  int
                The index of the `bintable` attribute

        Returns
        -------
            nrows : int
                Number of rows, i.e., the length of the input bintable

        """
        return self._nrows[bintable]

    def nchan(self, bintable):
        """
        The number of channels per row of the input bintable. Assumes all rows have same length.

        Parameters
        ----------
            bintable :  int
                The index of the `bintable` attribute

        Returns
        -------
            nchan : int
                Number channels in the first spectrum of the input bintbale

        """
        return np.shape(self.rawspectrum(1, bintable))[0]

    def npol(self, bintable):
        """
        The number of polarizations present in the input bintable.

        Parameters
        ----------
            bintable :  int
                The index of the `bintable` attribute

        Returns
        -------
            npol: int
                Number of polarizations as given by `CRVAL4` FITS header keyword.

        """
        return len(self.udata(key="CRVAL4", bintable=bintable))

    def sources(self, bintable):
        """
        The number of sources present in the input bintable.

        Parameters
        ----------
            bintable :  int
                The index of the `bintable` attribute

        Returns
        -------
            sources: int
                Number of sources as given by `OBJECT` FITS header keyword.

        """
        return self.udata(bintable=bintable, key="OBJECT")

    def scans(self, bintable):
        """
        The number of scans resent in the input bintable.
        TODO: move this to GBTFISLoad?

        Parameters
        ----------
            bintable :  int
                The index of the `bintable` attribute

        Returns
        -------
            scans: int
                Number of scans as given by `SCAN` FITS header keyword.
        """
        return self.udata(key="SCAN", bintable=bintable)

    def _summary(self, bintable):
        j = bintable
        nrows = self.naxis(bintable=j, naxis=2)
        nflds = self._binheader[j]["TFIELDS"]
        restfreq = np.unique(self._index[j]["RESTFREQ"]) / 1.0e9
        #
        print("HDU       %d" % (j + 1))
        print("BINTABLE: %d rows x %d cols with %d chans" % (self._nrows[j], nflds, self.nchan(j)))
        print("Selected  %d/%d rows" % (self._nrows[j], nrows))
        print("Sources: ", self.sources(j))
        print("RESTFREQ:", restfreq, "GHz")
        print("Scans:   ", self.scans(j))
        print("Npol:    ", self.npol(j))
        print("Nint:    ", self.nintegrations(j))

    def summary(self):
        """Print a summary of each record of the data"""
        print("File:     %s" % self._filename)
        for i in range(len(self._bintable)):
            print("i=", i)
            self._summary(i)

    def __len__(self):
        return self.nrows

    def __repr__(self):
        return self._filename

    def _bintable_from_rows(self, rows=None, bintable=None):
        """
        Extract a bintable from an existing
        bintable in this SDFITSLoad object

        Parameters
        ----------

            rows: int or list-like
                Range of rows in the bintable(s) to write out. e.g. 0, [14,25,32].
            bintable :  int
                The index of the `bintable` attribute

        Returns
        -------
            outbintable : ~astropy.iofits.BinTableHDU
                The binary table HDU created containing the selected rows

        """
        # ensure it is a list if int was given
        if type(rows) == int:
            rows = [rows]
        outbintable = self._bintable[bintable].copy()
        # print(f"bintable copy data length {len(outbintable.data)}")
        outbintable.data = outbintable.data[rows]
        # print(f"bintable rows data length {len(outbintable.data)}")
        outbintable.update()
        return outbintable

    def write(self, fileobj, rows=None, bintable=None, output_verify="exception", overwrite=False, checksum=False):
        """
        Write the `SDFITSLoad` to a new file, potentially sub-selecting rows or bintables.

        Parameters
        ----------
            fileobj : str, file-like or `pathlib.Path`
                File to write to.  If a file object, must be opened in a
                writeable mode.

            rows: int or list-like
                Range of rows in the bintable(s) to write out. e.g. 0, [14,25,32]. Default: None, meaning all rows
                Note: Currently `rows`, if given, must be contained in a single bintable and bintable must be given

            bintable :  int
                The index of the `bintable` attribute or None for all bintables. Default: None

            output_verify : str
                Output verification option.  Must be one of ``"fix"``,
                ``"silentfix"``, ``"ignore"``, ``"warn"``, or
                ``"exception"``.  May also be any combination of ``"fix"`` or
                ``"silentfix"`` with ``"+ignore"``, ``+warn``, or ``+exception"
                (e.g. ``"fix+warn"``).  See https://docs.astropy.org/en/latest/io/fits/api/verification.html for more info

            overwrite : bool, optional
                If ``True``, overwrite the output file if it exists. Raises an
                ``OSError`` if ``False`` and the output file exists. Default is
                ``False``.

            checksum : bool
                When `True` adds both ``DATASUM`` and ``CHECKSUM`` cards
                to the headers of all HDU's written to the file.

        """
        if bintable is None:
            if rows is None:
                # write out everything
                self._hdu.writeto(fileobj, output_verify=output_verify, overwrite=overwrite, checksum=checksum)
            else:
                raise ValueError("You must specify bintable if you specify rows")
        else:
            if rows is None:
                # bin table index counts from 0 and starts at the 2nd HDU (hdu index 1), so add 2
                self._hdu[0 : bintable + 2]._hdu.writeto(
                    fileobj, output_verify=output_verify, overwrite=overwrite, checksum=checksum
                )
            else:
                hdu0 = self._hdu[0].copy()
                # need to get imports correct first
                # hdu0.header["DYSHVER"] = ('dysh '+version(), "This file was created by dysh")
                outhdu = fits.HDUList(hdu0)
                outbintable = self._bintable_from_rows(rows, bintable)
                outhdu.append(outbintable)
                outhdu.writeto(fileobj, output_verify=output_verify, overwrite=overwrite, checksum=checksum)
