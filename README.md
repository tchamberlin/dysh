[![Documentation Status](https://readthedocs.org/projects/dysh/badge/?version=latest)](https://dysh.readthedocs.io/en/latest/?badge=latest)
[![pre-commit.ci Status](https://results.pre-commit.ci/badge/github/GreenBankObservatory/dysh/main.svg)](https://results.pre-commit.ci/latest/github/GreenBankObservatory/dysh/main)
[![CI Workflow Build Status](https://github.com/GreenBankObservatory/dysh/actions/workflows/ci.yml/badge.svg)](https://github.com/GreenBankObservatory/dysh/actions/workflows/ci.yml)

# dysh

*dysh* is a Python spectral line data reduction and analysis program for singledish data with specific emphasis on data from the Green Bank Telescope.  It is currently under development in collaboration between the [Green Bank Observatory](https:/greenbankobservatory.org) and the Laboratory for Millimeter-Wave Astronomy (LMA) at [University of Maryland (UMD)](https://www.astro.umd.edu).  It is intended to be a full replacement for the GBO's current reduction package [GBTIDL](https://www.gb.nrao.edu/GBT/DA/gbtidl/users_guide/).

## Getting Started
### Installation

dysh requires Python 3.9+ and recent versions of [astropy]( https://astropy.org), [numpy](https://numpy.org), [scipy](https://scipy.org), [pandas](https://pandas.pydata.org), [specutils](https://specutils.readthedocs.io/en/stable/),  and [matplotlib](https://matplotlib.org).

#### With pip from PyPi
dysh is most easily installed with *pip*, which will take care of any dependencies.  The packaged code is hosted at the [Python Packaging Index](https://pypi.org/project/dysh).

```bash
    $ pip install dysh
```

#### From GitHub
To install from github without creating a separate virtual environment:

```bash
    $ git clone git@github.com:GreenBankObservatory/dysh.git
    $ cd dysh
    $ pip install -e .
```
If you wish to install using a virtual environment, which we strongly recommend if you plan to contribute to the code, see Development.

### Reporting Issues

If you find a bug or something you think is in error, please report it on
the [github issue tracker](https://github.com/GreenBankObservatory/dysh/issues).
(You must have a [Github account](https://github.com) to submit an issue)

---

## Development

Here are the steps if you want to develop code for dysh. We use [hatch](https://hatch.pypa.io/) to manage the build environment.
The usual caveats apply how you set up your python development environment.

1.  Clone the repo and install hatch.

```bash
    $ git clone git@github.com:GreenBankObservatory/dysh.git
    $ cd dysh
    $ pip install hatch
```

2.  Hatch will default to using the system Python if there's no ``HATCH_PYTHON`` environment variable set. To use a specific version of Python, add the following line to your ``~/.bash_profile``:

```
export HATCH_PYTHON=/path/to/bin/python
```

Then source the new profile to apply the changes.

```bash
$ source ~/.bash_profile
```

3.  Create and activate a virtual environment with hatch and install the packages required for development.
The virtual environment will be created the first time; subsequent invoking ``hatch shell`` will simply load the created environment.cdi

```bash
    $ hatch shell
    (dysh) $ pip install -r requirements.txt
```

4.  Build and install the package

```bash
    (dysh) $ hatch build
    (dysh) $ pip install -e .
```

5.  You can exit this environment (which effectively had started a new shell) just exit:

```bash
    (dysh) $ exit
```

6.  Each time when you come back in this directory without being in this virtual environment, you'll need to load the virtual environment

```bash
    $ hatch shell
```

Notice you can ONLY do that from this directory

## Testing
 We use pytest for unit and integration testing.  From the top-level dysh directory, run:

```bash
    $ pytest
```
