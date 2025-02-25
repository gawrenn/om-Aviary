import unittest

from openmdao.utils.testing_utils import use_tempdirs
from openmdao.utils.assert_utils import assert_near_equal

import aviary.api as av
from aviary.subsystems.energy.battery_builder import BatteryBuilder


@use_tempdirs
class TestSubsystemsMission(unittest.TestCase):
    """
    Test the setup and run optimization model with a bettery subsystem.
    """

    def setUp(self):
        self.phase_info = {
            'pre_mission': {
                'include_takeoff': False,
                'external_subsystems': [BatteryBuilder()],
                'optimize_mass': True,
            },
            'cruise': {
                "subsystem_options": {"core_aerodynamics": {"method": "computed"}},
                'external_subsystems': [BatteryBuilder()],
                "user_options": {
                    "optimize_mach": False,
                    "optimize_altitude": False,
                    "polynomial_control_order": 1,
                    "num_segments": 5,
                    "order": 3,
                    "solve_for_distance": False,
                    "initial_mach": (0.72, "unitless"),
                    "final_mach": (0.72, "unitless"),
                    "mach_bounds": ((0.7, 0.74), "unitless"),
                    "initial_altitude": (35000.0, "ft"),
                    "final_altitude": (35000.0, "ft"),
                    "altitude_bounds": ((23000.0, 38000.0), "ft"),
                    "throttle_enforcement": "boundary_constraint",
                    "fix_initial": True,
                    "constrain_final": False,
                    "fix_duration": False,
                    "initial_bounds": ((0.0, 0.0), "min"),
                    "duration_bounds": ((10.0, 30.0), "min"),
                },
            },
            'post_mission': {
                'include_landing': False,
                'external_subsystems': [],
            },
        }

    def test_subsystems_in_a_mission(self):
        phase_info = self.phase_info.copy()

        prob = av.AviaryProblem()

        prob.load_inputs(
            "models/test_aircraft/aircraft_for_bench_FwFm_with_electric.csv", phase_info)

        # Preprocess inputs
        prob.check_and_preprocess_inputs()

        prob.add_pre_mission_systems()

        prob.add_phases()

        prob.add_post_mission_systems()

        # Link phases and variables
        prob.link_phases()

        prob.add_driver('SLSQP')

        prob.add_design_variables()

        prob.add_objective('fuel_burned')

        prob.setup()

        prob.set_initial_guesses()

        prob.set_val(av.Aircraft.Battery.PACK_ENERGY_DENSITY, 550, units='kJ/kg')
        prob.set_val(av.Aircraft.Battery.PACK_MASS, 1000, units='lbm')
        prob.set_val(av.Aircraft.Battery.ADDITIONAL_MASS, 115, units='lbm')

        prob.run_aviary_problem()

        electric_energy_used = prob.get_val(
            'traj.cruise.timeseries.'
            f'{av.Dynamic.Vehicle.CUMULATIVE_ELECTRIC_ENERGY_USED}',
            units='kW*h',
        )
        soc = prob.get_val(
            'traj.cruise.timeseries.'
            f'{av.Dynamic.Vehicle.BATTERY_STATE_OF_CHARGE}',
        )
        fuel_burned = prob.get_val(av.Mission.Summary.FUEL_BURNED, units='lbm')

        # Check outputs
        # indirectly check mission trajectory by checking total fuel/electric split
        assert_near_equal(electric_energy_used[-1], 38.60747069, 1.e-7)
        assert_near_equal(fuel_burned, 676.93670291, 1.e-7)
        # check battery state-of-charge over mission

        assert_near_equal(
            soc.ravel(),
            [0.9999957806265609,
             0.975511918724275,
             0.9417326925421843,
             0.931042529806735,
             0.931042529806735,
             0.8810540781831623,
             0.8120948314123136,
             0.7902729948636958,
             0.7902729948636958,
             0.7308724676601358,
             0.6489324990486358,
             0.6230037623262401,
             0.6230037623262401,
             0.5730701397031007,
             0.5041865153698425,
             0.4823886057245942,
             0.4823886057245942,
             0.4579498542268948,
             0.4242328589510152,
             0.4135623891269744],
            1e-7,
        )


if __name__ == "__main__":
    # unittest.main()
    test = TestSubsystemsMission()
    test.setUp()
    test.test_subsystems_in_a_mission()
