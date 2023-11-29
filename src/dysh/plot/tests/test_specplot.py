# PyInstallwe won't work if there's pathlib in the environment
# Why? Idk. But removing the dependency and commenting this out doesn't seem to hurt.
# dysh_root = pathlib.Path(dysh.__file__).parent.resolve()


class test_specplot:
    """ """

    def test_default_plotter():
        """
        Just plot a default plot of a spectrum and visually inspect
        """
        return 0

    def test_complicated_plotter():
        """
        Plot a more complicated spectrum and visually inspect
        """
        return 0
