"""Load SDFITS files produced by the Green Bank Telescope"""
import sys
import copy
from astropy.wcs import WCS
from astropy.units import cds
from astropy.io import fits
from astropy.modeling import models, fitting
import astropy.units as u
from astropy.table import Table
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from ..spectra.spectrum import Spectrum
from ..spectra.scan import GBTPSScan,GBTTPScan
from ..spectra.obsblock import Obsblock
from ..spectra import dcmeantsys
from .sdfitsload import SDFITSLoad
from ..util import uniq

# from GBT IDL users guide Table 6.7
_PROCEDURES = ["Track", "OnOff", "OffOn", "OffOnSameHA", "Nod", "SubBeamNod"] 

class GBTFITSLoad(SDFITSLoad):
    """GBT-specific container for bintables from selected HDU(s)"""
    def __init__(self, filename, source=None,hdu=None,**kwargs):
        SDFITSLoad.__init__(self,filename,source,hdu)#,fix=False)

        self._compute_proc()
        if kwargs.get("verbose",None):
            print("==GBTLoad %s" % filename)
            self.ushow(0,'OBJECT')
            self.ushow(0,'SCAN')
            self.ushow(0,'SAMPLER')
            self.ushow('PLNUM')
            self.ushow('IFNUM')
            self.ushow(0,'SIG')
            self.ushow(0,'CAL')
            self.ushow(0,'PROCSEQN')
            self.ushow(0,'PROCSIZE')
            self.ushow(0,'OBSMODE')  
            self.ushow(0,'SIDEBAND')

    def _compute_proc(self):
        """Compute the procedure string from obsmode and add to index"""
        for i in range(len(self._ptable)):
            df = self._ptable[i]["OBSMODE"].str.split(':',expand=True)
            self._ptable[i]["PROC"] = df[0]
            # Assign these to something that might be usefule later, since we have them
            self._ptable[i]["_OBSTYPE"] = df[1]
            self._ptable[i]["_SUBOBSMODE"] = df[2]

    def summary(self, scans=None, verbose=False, bintable=0):
# From GBTIDL:
# Intended to work with un-calibrated GBT data and is
# likely to give confusing results for other data.  For other data,
# list is usually more useful.
#
# @TODO perhaps return as a astropy.Table then we can have units
        """Create a summary list of the input dataset.   
            If `verbose=False` (default), some numeric data 
            (e.g., RESTFREQ, AZIMUTH, ELEVATIO) are 
            averaged over the records with the same scan number.

        Parameters
        ----------
            scans : int or 2-tuple
                The scan(s) to use. A 2-tuple represents (beginning, ending) scans. Default: show all scans

            verbose: bool
                If True, list every record, otherwise return a compact summary

        Returns
        -------
            summary - `~pandas.DataFrame`
                Summary of the data as a DataFrame.
            
        """
        #@todo allow user to change show list
        #@todo set individual format options on output by
        # changing these to dicts(?)
        show = ["SCAN", "OBJECT", "VELOCITY", "PROC", "PROCSEQN", 
                "RESTFREQ", "DOPFREQ", "IFNUM","FEED", "AZIMUTH", "ELEVATIO", 
                "FDNUM", "PLNUM", "SIG", "CAL"] 
        comp_colnames = [
                "SCAN", "OBJECT", "VELOCITY", "PROC", "PROCSEQN", 
                "RESTFREQ", "DOPFREQ", "# IF","# POL", "# INT", "# FEED", 
                "AZIMUTH", "ELEVATIO"]
        uncompressed_df = None
        if self._ptable is None:
            self._create_index()
        for df in self._ptable:
            # make a copy here because we can't guarantee if this is a 
            # view or a copy without it. See https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#returning-a-view-versus-a-copy
            _df = df[show].copy()
            _df.loc[:,"VELOCITY"] /= 1E3   # convert to km/s
            _df["RESTFREQ"] = _df["RESTFREQ"]/1.0E9 # convert to GHz
            _df["DOPFREQ"] = _df["DOPFREQ"]/1.0E9 # convert to GHz
            if scans is not None:
                if type(scans) == int:
                    scans = [scans]
                if len(scans) == 1:
                    scans = [scans[0],scans[0]]
                _df = self.select_scans(scans,_df).filter(show)
                if uncompressed_df is None:
                    uncompressed_df = _df
                else:
                    uncompressed_df =pd.concat([uncompressed_df,_df])
            else:
                if uncompressed_df is None:
                    uncompressed_df = _df.filter(show)
                else:
                    uncompressed_df = pd.concat([uncompressed_df,_df.filter(show)])
        
        if verbose:
            return uncompressed_df
        # do the work to compress the info 
        # in the dataframe on a scan basis
        compressed_df = pd.DataFrame(columns = comp_colnames)
        scanset = set(uncompressed_df["SCAN"])
        avg_cols = ["SCAN", "VELOCITY", "PROCSEQN", 
                    "RESTFREQ", "DOPFREQ",
                    "AZIMUTH", "ELEVATIO"]
        for s in scanset:
            uf = self.select("SCAN",s,uncompressed_df)
            # for some columns we will display 
            # the mean value
            ser = uf.filter(avg_cols).mean(numeric_only=True)
            ser.rename("filtered ser")
            # for others we will count how many there are
            nIF = uf["IFNUM"].nunique()
            nPol = uf["PLNUM"].nunique()
            nfeed = uf["FEED"].nunique()
            # divide by two to account for sig and ref
            nint  = len(uf)//(nPol*nIF*nfeed*2) 
            obj = list(set(uf["OBJECT"]))[0] # We assume they are all the same!
            proc = list(set(uf["PROC"]))[0] # We assume they are all the same!
            #print(f"Uniq data for scan {s}: {nint} {nIF} {nPol} {nfeed} {obj} {proc}")
            s2 = pd.Series([obj,proc,nIF,nPol,nint,nfeed],
                    name = "uniqued data",
                    index=["OBJECT","PROC",
                           "# IF","# POL", "# INT","# FEED"])
            ser=pd.concat([ser,s2]).reindex(comp_colnames)
            ser.rename("appended ser")
            #print("append series data",ser)
            #print("append series index ",ser.index)
            #print("df cols",compressed_df.columns)
            #print("SAME? ",all(ser.index == compressed_df.columns))
            compressed_df = pd.concat(
                    [compressed_df,ser.to_frame().T],
                    ignore_index=True)
        return compressed_df

    def velocity_convention(self,veldef,velframe):
        # GBT uses VELDEF and VELFRAME incorrectly. 
        return "doppler_radio"

    def select_scans(self,scans,df):
        return df[(df["SCAN"]>=scans[0]) & ( df["SCAN"] <= scans[1])]

    def select_onoff(self,df):
        return df[(df["PROC"]=="OnOff") | ( df["PROC"] == "OffOn")]

    def select(self,key,value,df):
        return df[(df[key]==value)]

    def _create_index_if_needed(self):
        if self._ptable is None:
            self._create_index()

    def getps(self,scans=None,bintable=0,**kwargs):
        '''Get the rows that contain position-switched data.  These include ONs and OFFs.

            kwargs: plnum, feed, ifnum, integration, calibrate=T/F, average=T/F, tsys, weights
            [sampler], ap_eff [if requested units are Jy]
            
        Parameters
        ----------
            scans : int or 2-tuple
                Single scan number or list of scan numbers to use. Default: all scans.
                Scan numbers can be Ons or Offs
        TODO: figure how to allow [startscan, endscan]
        Returns 
        -------
            psscan : ~scan.GBTPSScan
                A `GBTPScan` object containing the data which can be calibrated.
        '''
        # all ON/OFF scans
        kwargs_opts = {
            'ifnum': 0,
            'plnum' : 0, # I prefer "pol"
            'fdnum' : 0,
            'calibrate': True,
            'average': False,
            'tsys': None,
            'weights': None,
        }
        kwargs_opts.update(kwargs)

        ifnum = kwargs_opts['ifnum']
        plnum = kwargs_opts['plnum']
        scanlist = self.onoff_scan_list(scans,ifnum=ifnum,plnum=plnum,bintable=bintable)
        # add ifnum,plnum
        rows = self.onoff_rows(scans,ifnum=ifnum,plnum=plnum,bintable=bintable)
        # do not pass scan list here. We need all the cal rows. They will 
        # be intersected with scan rows in GBTPSScan
        # add ifnum,plnum
        calrows = self.calonoff_rows(scans=None,bintable=bintable)
        g = GBTPSScan(self,scanlist,rows,calrows,bintable)
        return g

    def gettp(self,scan,sig,cal,bintable=0,**kwargs):
        kwargs_opts = {
                'ifnum': 0,
                'plnum' : 0, 
                'fdnum' : 0,
                'subref': None, # subreflector position
                'timeaverage' : True,
                'polaverage': True,
                'weights' : 'equal', # or 'tsys' or ndarray
                'calibrate': False
        }   
        kwargs_opts.update(kwargs)
        TF = {True : 'T', False:'F'}
        sigstate = {True : 'SIG', False:'REF'}
        calstate = {True : 'ON', False:'OFF'}
        ifnum = kwargs_opts['ifnum']
        plnum = kwargs_opts['plnum']
        fdnum =kwargs_opts['fdnum']
        subref = kwargs_opts['subref']
        # do you have to give sig or cal?
        df = self._ptable[0]
        df = df[(df["SCAN"] == scan)]
        if sig is not None:
            sigch = TF[sig]
            df = df[(df['SIG']==sigch)]
            print('S ',len(df))
        if cal is not None:
            calch = TF[cal]
            df = df[df['CAL']==calch]
            print('C ',len(df))
        if ifnum is not None:
            df = df[df['IFNUM']==ifnum]
            print('I ',len(df))
        if plnum is not None:
            df = df[df['PLNUM']==plnum]
            print('P ',len(df))
        if fdnum is not None:
            df = df[df['FDNUM']==fdnum]
            print('F ',len(df))
        if subref is not None:
            df = df[df['SUBREF_STATE']==subref]
            print('SR ',len(df))
        #TBD: if ifnum is none then we will have to sort these by ifnum, plnum and store separate arrays or something. 
        tprows = list(df.index)
        #data = self.rawspectra(bintable)[tprows]
        calrows = self.calonoff_rows(scans=scan,bintable=bintable,**kwargs_opts)
        print(len(calrows['ON']))
        g = GBTTPScan(self,scan,sigstate[sig],calstate[cal],tprows,calrows,bintable,kwargs_opts['calibrate'])
        return g

    # special nod for KA data.
    # See /users/dfrayer/gbtidlpro/snodka

    def getnod_ka(self,scan,bintable=0,**kwargs):
        kwargs_opts = {
                'ifnum': 0,
                'fdnum' : 0,
                'timeaverage' : True,
                'polaverage': True,
                'weights' : 'equal' # or 'tsys' or ndarray
        } 
        kwargs_opts.update(kwargs)
        ifnum = kwargs_opts['ifnum']
        fdnum = kwargs_opts['fdnum']
        if fdnum == 1:
            plnum = 0
            tpon  = self.gettp(scan,sig=True,cal=False,bintable=bintable,fdnum=fdnum,plnum=plnum,ifnum=ifnum,subref=-1)
            tpoff = self.gettp(scan,sig=True,cal=False,bintable=bintable,fdnum=fdnum,plnum=plnum,ifnum=ifnum,subref=1)
        elif fdnum == 0:
            plnum = 1
            tpoff = self.gettp(scan,sig=True,cal=False,bintable=bintable,fdnum=fdnum,plnum=plnum,ifnum=ifnum,subref=-1)
            tpon  = self.gettp(scan,sig=True,cal=False,bintable=bintable,fdnum=fdnum,plnum=plnum,ifnum=ifnum,subref=1)
        else:
            raise ValueError(f"Feed number {fdnum} must be 0 or 1.")
        on  =  tpon.timeaverage(weights=kwargs_opts['weights']) 
        off = tpoff.timeaverage(weights=kwargs_opts['weights'])
        meanTsys = 0.5*(off.meta['TSYS']+on.meta['TSYS'])
        print(f"Tsys(ON) = {on.meta['TSYS']}, Tsys(OFF) = {off.meta['TSYS']}, meanTsys = {meanTsys}")
        data = meanTsys*(on - off)/off
        data.meta['TSYS'] = meanTsys
        return data

    def onoff_scan_list(self,scans=None,ifnum=0,plnum=0,bintable=0):
        self._create_index_if_needed()
        #print(f"onoff_scan_list(scans={scans},if={ifnum},pl={plnum})")
        s = {"ON": [], "OFF" :[]}
        if type(scans) == int:
            scans = [scans]
        if False: # this does all bintables.
            for df in self._ptable:
                #OnOff lowest scan number is on
                #dfonoff = self.select(df,"PROC","OnOff"))
                #OffOn lowest scan number is off
                #dfoffon = self.select(df,"PROC","OffOn"))
                dfon  = self.select("_OBSTYPE","PSWITCHON",df)
                dfoff = self.select("_OBSTYPE","PSWITCHOFF",df)
                onscans = uniq(list(dfon["SCAN"]))
                #print("ON: ",onscans)
                s["ON"].extend(onscans)
                offscans = uniq(list(dfoff["SCAN"]))
                #print("OFF: ",offscans)
                s["OFF"].extend(offscans)

        df    = self._ptable[bintable]
        df = df[(df["PLNUM"] == plnum) & (df["IFNUM"] == ifnum)]
        dfon  = self.select("_OBSTYPE","PSWITCHON",df)
        dfoff = self.select("_OBSTYPE","PSWITCHOFF",df)
        onscans = uniq(list(dfon["SCAN"])) # wouldn't set() do this too?
        offscans = uniq(list(dfoff["SCAN"]))
        if scans is not None:
        # The companion scan will always be +/- 1 depending if procseqn is 1(ON) or 2(OFF)
        # First check the requested scan number(s) are even in the ONs or OFFs of this bintable
            seton = set(onscans)
            setoff = set(offscans)
            onrequested = seton.intersection(scans)
            #print("ON REQUESTED ",onrequested)
            offrequested = setoff.intersection(scans)
            #print("OFF REQUESTED ",offrequested)
            if len(onrequested) == 0 and len(offrequested) == 0:
                raise ValueError(f"Scans {scans} not found in ONs or OFFs of bintable {bintable}")
        # Then check that for each requested ON/OFF there is a matching OFF/ON
        # and build the final matched list of ONs and OFfs.
            sons = list(onrequested.copy())
            soffs = list(offrequested.copy())
            missingoff = []
            missingon = []
            for i in onrequested:
                expectedoff = i+1
                #print(f"DOING ONQUESTED {i}, looking for off {expectedoff}")
                if len(setoff.intersection([expectedoff])) == 0:
                    missingoff.append(expectedoff)
                else:
                    soffs.append(expectedoff)
            for i in offrequested:
                expectedon = i-1
                #print(f"DOING OFFEQUESTED {i}, looking for on {expectedon}")
                if len(seton.intersection([expectedon])) == 0:
                    missingon.append(expectedon)
                else:
                    sons.append(expectedon)
            if len(missingoff) > 0:
                raise ValueError(f"For the requested ON scans {onrequested}, the OFF scans {missingoff} were not present in bintable {bintable}")
            if len(missingon) > 0:
                raise ValueError(f"For the requested OFF scans {offrequested}, the ON scans {missingon} were not present in bintable {bintable}")
            #print("ON",sorted(sons))
            #print("OFF",sorted(soffs))
            s["ON"] = sorted(set(sons))
            s["OFF"] = sorted(set(soffs))
        else:
            s["ON"] = uniq(list(dfon["SCAN"]))
            s["OFF"] = uniq(list(dfoff["SCAN"]))

        return s

    def calonoff_rows(self,scans=None,bintable=0,**kwargs):
        self._create_index_if_needed()
        s = {"ON": [], "OFF" :[]}
        ifnum  = kwargs.get('ifnum',None)
        plnum  = kwargs.get('plnum',None)
        fdnum  = kwargs.get('fdnum',None)
        subref = kwargs.get('subref',None)
        if type(scans) == int:
            scans = [scans]
        df    = self._ptable[bintable]
        if scans is not None:
            df = df[df["SCAN"].isin(scans)]
        dfon  = self.select("CAL","T",df)
        dfoff = self.select("CAL","F",df)
        if ifnum is not None:
            dfon  = self.select("IFNUM",ifnum,dfon)
            dfoff  = self.select("IFNUM",ifnum,dfoff)
        if plnum is not None:
            dfon  = self.select("PLNUM",plnum,dfon)
            dfoff  = self.select("PLNUM",plnum,dfoff)
        if fdnum is not None:
            dfon  = self.select("FDNUM",fdnum,dfon)
            dfoff  = self.select("FDNUM",fdnum,dfoff)
        if subref is not None:
            dfon  = self.select("SUBREF_STATE",subref,dfon)
            dfoff  = self.select("SUBREF_STATE",subref,dfoff)
        s["ON"]  = list(dfon.index)
        s["OFF"] = list(dfoff.index)
        return s

    def onoff_rows(self,scans=None,ifnum=0,plnum=0,bintable=0): 
    #@TODO deal with mulitple bintables
    #@TODO rename this sigref_rows?
    # keep the bintable keyword and allow iteration over bintables if requested (bintable=None) 
        #print(f"onoff_rows(scans={scans},if={ifnum},pl={plnum})")
        self._create_index_if_needed()
        rows = {"ON": [], "OFF" :[]}
        if type(scans) is int:
            scans = [scans]
        scans = self.onoff_scan_list(scans,ifnum,plnum,bintable)
        #scans is now a dict of "ON" "OFF
        for key in scans: 
            rows[key] = self.scan_rows(scans[key],ifnum,plnum,bintable)
        return rows
        
    def scan_rows(self,scans,ifnum=0,plnum=0,bintable=0):
        #scans is a list
        #print(f"scan_rows(scans={scans},if={ifnum},pl={plnum})")
        self._create_index_if_needed()
        if scans is None:
            raise ValueError("Parameter 'scans' cannot be None. It must be int or list of int")
        df = self._ptable[bintable]
        df = df[df["SCAN"].isin(scans) & (df["IFNUM"] == ifnum) & (df["PLNUM"] == plnum)]
        rows = list(df.index)
        if len(rows) == 0:
            raise Exception(f"Scans {scans} not found in bintable {bintable}")
        return rows

    def _scan_rows_all(self,scans):
        """get scan rows regardless of ifnum,plnum, bintable.
        
        Parameters
        ----------
            scans : int or list-like
                The scan numbers to find the rows of

        Returns
        -------
            rows : list
                Lists of the rows in each bintable that contain the scans. Index of `rows` is the bintable index number
        """
        if scans is None:
            raise ValueError("Parameter 'scans' cannot be None. It must be int or list of int")
        df_out = []
        rows = []
        for pt in self._ptable:
            df_out.append(pt[pt["SCAN"].isin(scans)])
        for df in df_out:
            rows.append(list(df.index))
        return rows

    def write_scans(self,fileobj,scans,output_verify="exception",overwrite=False,checksum=False):
        """
        Write specific scans of the `GBTFITSLoad` to a new file.

        Parameters
        ----------
        fileobj : str, file-like or `pathlib.Path`
            File to write to.  If a file object, must be opened in a
            writeable mode.

        scans: int or list-like
            Range of scans to write out. e.g. 0, [14,25,32]. 

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
        # get the rows that contain the scans in all bintables
        rows = self._scan_rows_all(scans)
        #print("Using rows",rows)
        hdu0 = self._hdu[0].copy()
        outhdu = fits.HDUList(hdu0)
        # get the bintables rows as new bintables.
        for i in range(len(rows)):
            ob = self._bintable_from_rows(rows[i],i)
            #print(f"bintable {i} #rows {len(rows[i])} data length {len(ob.data)}")
            if len(ob.data) > 0:
                outhdu.append(ob)
        #print(outhdu.info())
        # write it out!
        outhdu.update_extend() # possibly unneeded
        outhdu.writeto(fileobj,
            output_verify=output_verify,
            overwrite=overwrite, checksum=checksum)
