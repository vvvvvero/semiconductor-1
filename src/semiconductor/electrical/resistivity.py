
import numpy as np
import scipy.constants as const
import scipy.optimize as opt

from semiconductor.general_functions.carrierfunctions import get_carriers
from semiconductor.material.intrinsic_carrier_density import IntrinsicCarrierDensity as ni
from semiconductor.electrical.mobility import Mobility as Mob
from semiconductor.electrical.ionisation import Ionisation as Ion
from semiconductor.helper.helper import BaseModelClass


class Conductivity(BaseModelClass):
    '''
    Calculates the conductivity of a semiconductor given the inputs

    inputs
        1. material: (str)
            The elemental name for the material. Defualt (Si)
        2. temp: (float)
            The temperature of the material in Kelvin (300)
        3. mob_author: (str)
            The mobility author  to be used
        4. nieff_author (str)
            The intrinsic carrier density to be used
        5. ionis_author (str)
            The author of a model to be used for dopant ionisation
        6. dopant (str)
            The elemental name for the dopants
        7. nxc: (array like cm^-3)
            The number of excess carriers
        8. Na: (array like cm^-3)
            The number of acceptor dopants
        9. Nd: (array like cm^-3)
            The number of donar dopants
    '''

    _cal_dts = {
        'material': 'Si',
        'temp': 300,
        'mob_author': None,
        'nieff_author': None,
        'ionis_author': None,
        'dopant': 'boron',
        'Na': 1e16,
        'Nd': 0,
        'nxc': 1e10,
        'resistivity': 1.
    }

    def __init__(self, **kwargs):
        self.calculationdetails = kwargs

    def _update_links(self):

        # setting downstream values, this should change from initalisation
        # to just updating through the update function
        self.Mob = Mob(material=self._cal_dts['material'],
                       author=self._cal_dts['mob_author'],
                       temp=self._cal_dts['temp'])
        self.ni = ni(material=self._cal_dts['material'],
                     author=self._cal_dts['nieff_author'],
                     temp=self._cal_dts['temp'])
        self.ion = Ion(material=self._cal_dts['material'],
                       author=self._cal_dts['ionis_author'],
                       ni_author=self._cal_dts['nieff_author'],
                       temp=self._cal_dts['temp'])

    def query_used_authors(self):
        return self.Mob.model, self.ni.model, self.ion.model

    def _conductivity(self, **kwargs):

        self.calculationdetails = kwargs
        self._update_links()

        Nid, Nia = get_carriers(nxc=0,
                                Na=self._cal_dts['Na'],
                                Nd=self._cal_dts['Nd'],
                                temp=self._cal_dts['temp'],
                                ni_author=self._cal_dts['nieff_author']
                                )

        if np.all(Nid > Nia):
            Nid = self.ion.update_dopant_ionisation(
                N_dop=Nid,
                nxc=self._cal_dts['nxc'],
                impurity=self._cal_dts['dopant'])
        elif np.all(Nia > Nid):
            Nia = self.ion.update_dopant_ionisation(
                N_dop=Nia,
                nxc=self._cal_dts['nxc'],
                impurity=self._cal_dts['dopant'])

        ne, nh = get_carriers(
            Na=Nia,
            Nd=Nid,
            nxc=self._cal_dts['nxc'],
            temp=self._cal_dts['temp'],
            ni_author=self._cal_dts['nieff_author']
        )

        mob_e = self.Mob.electron_mobility(nxc=self._cal_dts['nxc'],
                                           Na=self._cal_dts['Na'],
                                           Nd=self._cal_dts['Nd']
                                           )
        mob_h = self.Mob.hole_mobility(nxc=self._cal_dts['nxc'],
                                       Na=self._cal_dts['Na'],
                                       Nd=self._cal_dts['Nd'])

        return const.e * (mob_e * ne + mob_h * nh)

    def calculate(self, **kwargs):
        '''
        calculates the conductivity
        '''

        self._cal_dts['conductivity'] = self._conductivity(**kwargs)

        return self._cal_dts['conductivity']


class Resistivity(Conductivity):
    '''
    Calculates the resistivity of a semiconductor given the inputs

    inputs
        1. material: (str)
            The elemental name for the material. Defualt (Si)
        2. temp: (float)
            The temperature of the material in Kelvin (300)
        3. mob_author: (str)
            The mobility author  to be used
        4. nieff_author (str)
            The intrinsic carrier density to be used
        5. ionis_author (str)
            The author of a model to be used for dopant ionisation
        6. dopant (str)
            The elemental name for the dopants
        7. nxc: (array like cm^-3)
            The number of excess carriers
        8. Na: (array like cm^-3)
            The number of acceptor dopants
        9. Nd: (array like cm^-3)
            The number of donar dopants
    '''

    def calculate(self, **kwargs):
        '''
        calculates the resistivity
        '''

        self._cal_dts['resistivity'] = 1. / self._conductivity(**kwargs)

        return self._cal_dts['resistivity']


class DarkConductivity(BaseModelClass):
    '''
    A class for the special case for a sample where the number of excess
    carriers is zero. It allows calculation of conductance from doping, and
    doping from conductance.

    Calculates the conductivity of a semiconductor given the inputs

    inputs
        1. material: (str)
            The elemental name for the material. Defualt (Si)
        2. temp: (float)
            The temperature of the material in Kelvin (300)
        3. mob_author: (str)
            The mobility author  to be used
        4. nieff_author (str)
            The intrinsic carrier density to be used
        5. ionis_author (str)
            The author of a model to be used for dopant ionisation
        6. dopant_type (str)
            The type of typnt n or p  
    '''

    _cal_dts = {
        'material': 'Si',
        'temp': 300,
        'mob_author': None,
        'nieff_author': None,
        'ionis_author': None,
        'dopant_type': 'p',
        'nxc': 1,
        'dark_resistivity': 1.
    }

    def __init__(self, **kwargs):
        self.calculationdetails = kwargs
        self._update_links()

    def _update_links(self):

        # setting downstream values, this should change from initalisation
        # to just updating through the update function
        self.Mob = Mob(material=self._cal_dts['material'],
                       author=self._cal_dts['mob_author'],
                       temp=self._cal_dts['temp'])

    def query_used_authors(self):
        return self.Mob.model, self.ni.model, self.ion.model

    def dark_resistivity2doping(self, dark_resistivity, **kwargs):
        '''
        cacluate the number of ionised dopoants
        given the resistivity of the sample in the dark
        '''

        return self.dark_conductivity2doping(1. / dark_resistivity, **kwargs)

    def dark_conductivity2doping(self, dark_conductivity, **kwargs):
        '''
        cacluate the number of ionised dopoants
        given the conductivity of the sample in the dark

        Inputs:
            dark_conductivity: (float)
                The conductivty of the sample in the dark
            **kwargs: (optional)
                Any of the values found in cal_dts

        Ouput:
            doping: (float)
                The substitutional doping density.
        '''

        if bool(kwargs):
            self.calculationdetails = kwargs
            self._update_links()

        mob_e = self.Mob.electron_mobility(nxc=1,
                                           Na=0,
                                           Nd=0,
                                           temp=self._cal_dts['temp']
                                           )
        # # get an inital guess
        Na = dark_conductivity / const.e / mob_e

        cond = Conductivity(**self._cal_dts)

        def cal_dop(N, dopant_type, dark_conductivity):
            if dopant_type == 'p':
                Na = N
                Nd = 0
            elif dopant_type == 'n':
                Na = 0
                Nd = N
            condv = (cond.calculate(Na=Na, Nd=Nd))
            return condv - dark_conductivity

        dop = (opt.newton(cal_dop,
                          x0=Na,
                          tol=0.001,
                          args=(self._cal_dts['dopant_type'], dark_conductivity),))

        return dop
