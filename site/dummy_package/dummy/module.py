"""
Module that contains Parameterized classes and simple functions.
"""

import param


class Base(param.Parameterized):
    """
    Base docs.
    """

    x = param.Number(2, bounds=(1, 100), doc="""
        This is x.""")

    allowed_values = param.List(['a', 'b'], doc="""
        This is allowed_values.""")

    def _private(self):
        """_private"""
        pass

    def public_simple(self):
        """public_simple"""
        pass

    @param.depends('x')
    def public_depends(self):
        """public_depends"""
        pass

    def public_typed(self, a: int, b: str) -> int:
        """public_typed"""
        return 0


    def public_numpy(self, a, b):
        """Return something.

        Parameters
        ----------
        a : int
            Some integer.
        b : str
            Some string.

        Returns
        -------
        int
            The return value.
        """


class Concrete(Base):
    """
    Concrete docs
    """

    foo = param.Callable(doc="This is foo.")

    def public_simple(self):
        pass


def function_typed(a: int, b: str) -> int:
    """function_typed"""
    return 0


def function_numpy(a, b):
    """Return something.

    Parameters
    ----------
    a : int
        Some integer.
    b : str
        Some string.

    Returns
    -------
    int
        The return value.
    """
    return 0
