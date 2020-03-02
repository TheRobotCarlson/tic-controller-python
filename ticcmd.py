import subprocess

import yaml

import logging

logger = logging.getLogger('ticcmd')
 
def ticcmd(*args, debug=True):
    logger.debug("ticcmd " + (" ".join(list(args))))
        
    if not debug:
        return subprocess.check_output(['ticcmd'] + list(args))
    else:
        return None

# step sizes
class StepSizes:
    FULL, ONEHALF, ONEQUARTER, ONEEIGHTH, ONESIXTEENTH, ONETHIRTYSECOND, ONESIXTYFOURTH, ONEHUNDREDTWENTYEIGHTH, ONETWOFIFTYSIXTH = range(9)
    MAX = 8
    MIN = 0


class _TicController:
    def __init__(self):
        pass
        
    def energize(self):
        """
        This command is a request for the Tic to energize the stepper motor coils by enabling its stepper motor driver. 
        The Tic will clear the “intentionally de-energized” error bit. If there are no other errors, this allows the system to start up.
        """
        return ticcmd("--energize")
        
    def deenergize(self):
        """
        This command causes the Tic to de-energize the stepper motor coils by disabling its stepper motor driver. 
        The motor will stop moving and consuming power. This command sets the “position uncertain” flag 
        (because the Tic is no longer in control of the motor’s position); 
        the Tic will also set the “intentionally de-energized” error bit, turn on its red LED, and drive its ERR line high.

        The “energize” command will undo the effect of this command (except it will leave the “position uncertain” flag set) 
        and could make the system start up again.
        """
        return ticcmd("--deenergize")
        
    def exit_safe_start(self):
        """
        This command causes the “safe start violation” error to be cleared for 200 ms. 
        If there are no other errors, this allows the system to start up.

        In the Tic Control Center, the green “Resume” button in the lower left will additionally exit safe 
        start if the control mode is Serial / I²C / USB.
        """
        return ticcmd("--exit-safe-start")
    
    def enter_safe_start(self):
        """
        If safe start is enabled, this command causes the Tic to stop the motor (using the configured soft error response behavior) 
        and set its “safe start violation” error bit. If safe start is disabled, or if the Tic is not in one of the listed modes, 
        this command will cause a brief interruption in motor control (during which the soft error response behavior will be triggered) 
        but otherwise have no effect.

        In Serial mode, an “exit safe start” command is required before the Tic will move the motor again. 
        In the speed control modes, the input must be moved to a neutral position before the Tic will exit safe start and move the motor again. 
        """
        return ticcmd("--enter-safe-start")
    
    def _set_target_position(self, position):
        """
        This command sets the target position of the Tic, in microsteps.

        In the Tic Control Center, the controls in the “Set target” box can be used to set a target position. 
        These controls are on the “Status” tab.
        """
        return ticcmd("--position", str(position))
    
    def _set_target_velocity(self, velocity):
        """
        This command sets the target velocity of the Tic, in microsteps per 10,000 seconds.

        In the Tic Control Center, the controls in the “Set target” box can be used to set a target velocity. 
        These controls are on the “Status” tab.
        """
        return ticcmd("--velocity", str(velocity))
    
    def _halt_and_set_position(self, position):
        """
        This command stops the motor abruptly without respecting the deceleration limit 
        and sets the “Current position” variable, which represents what position the Tic currently thinks the motor is in. 
        Besides stopping the motor and setting the current position, this command also clears the “position uncertain” flag, 
        sets the input state to “halt”, and clears the “input after scaling” variable.

        In the Tic Control Center, the “Set current position” button can be used to halt the motor 
        and set the Tic’s current position to the specified value. This button is on the “Status” tab.
        """
        return ticcmd("--halt-and-set-position", str(position))
    
    def _halt_and_hold(self):
        """
        This command stops the motor abruptly without respecting the deceleration limit. 
        Besides stopping the motor, this command also sets the “position uncertain” flag (because the abrupt stop might cause steps to be missed), 
        sets the input state to “halt”, and clears the “input after scaling” variable.

        In the Tic Control Center, the “Halt motor” button can be used to halt the motor. This button is on the “Status” tab.
        """
        return ticcmd("--halt-and-hold")
    
    def home(self, direction=1):
        home_dir = "fwd" if direction == 1 else "rev"
        return ticcmd("--home", home_dir)
    
    def reset_command_timeout(self):
        """
        If the command timeout is enabled, this command resets it and prevents the “command timeout” error from happening for some time.

        The Tic Control Center constantly sends this command while it is connected to a Tic.
        """
        return ticcmd("--reset-command-timeout")  

    def _reset(self):
        """
        This command makes the Tic forget most parts of its current state. Specifically, it does the following:

        - Reloads all settings from the Tic’s non-volatile memory and discards any temporary changes to the settings previously 
            made with serial commands (this applies to the step mode, current limit, decay mode, max speed, starting speed, 
            max acceleration, and max deceleration settings)
        - Abruptly halts the motor
        - Resets the motor driver
        - Sets the Tic’s operation state to “reset”
        - Clears the last movement command and the current position
        - Clears the encoder position
        - Clears the serial and “command timeout” errors and the “errors occurred” bits
        - Enters safe start if configured to do so
        - The Tic’s serial and I²C interfaces will be unreliable for a brief period after the Tic receives the Reset command, 
        so we recommend waiting at least 10 ms after sending a Reset command before sending additional I²C or serial commands.

        This command does not modify the “intentionally de-energized” error bit. 
        Since this command does not trigger a full microcontroller reset, it does not affect the “up time” variable 
        (which indicates the time elapsed since the Tic’s last full microcontroller reset) or the “device reset” variable 
        (which indicates the cause of the Tic’s last full microcontroller reset).
        """
        return ticcmd("--reset")

    def _set_max_velocity(self, velocity):
        """
        Velocity:
        Range: 0 to 500,000,000
        Units: microsteps per 10,000s

        This command temporarily sets the Tic’s maximum allowed motor speed in units of steps per 10,000 seconds. 
        The provided value will override the corresponding setting from the Tic’s non-volatile memory until the next Reset 
        (or Reinitialize) command or full microcontroller reset.
        """
        return ticcmd("--max-speed", str(velocity))

    def _set_starting_velocity(self, velocity):
        """
        Velocity:
        Range: 0 to 500,000,000
        Units: microsteps per 10,000s

        This command temporarily sets the Tic’s starting speed in units of steps per 10,000 seconds. 
        This is the maximum speed at which instant acceleration and deceleration are allowed;
        The provided value will override the corresponding setting from the Tic’s non-volatile memory until the next Reset 
        (or Reinitialize) command or full microcontroller reset.        
        """
        return ticcmd("--starting-speed", str(velocity))

    def _set_max_acceleration(self, accel):
        """
        accel: 100 to 2,147,483,647

        This command temporarily sets the Tic’s maximum allowed motor acceleration in units of steps per second per 100 seconds.
        The provided value will override the corresponding setting from the Tic’s non-volatile memory until the next Reset 
        (or Reinitialize) command or full microcontroller reset.

        If the provided value is between 0 and 99, it is treated as 100.

        This command does not affect the max deceleration, even if the “Use max acceleration limit for deceleration” 
        checkbox in the Tic Control Center is checked.
        """
        return ticcmd("--max-accel", str(accel))

    def _set_max_deceleration(self, accel):
        """
        accel: 100 to 2,147,483,647

        This command temporarily sets the Tic’s maximum allowed motor deceleration in units of steps per second per 100 seconds. 
        The provided value will override the corresponding setting from the Tic’s non-volatile memory until the next Reset 
        (or Reinitialize) command or full microcontroller reset.

        If the provided value is 0, then the max deceleration will be set equal to the current max acceleration value. 
        If the provided value is between 1 and 99, it is treated as 100.
        """
        return ticcmd("--max-accel", str(accel))

    def _set_step_mode(self, step_size):
        """
        This command temporarily sets the step mode (also known as microstepping mode) of the driver on the Tic, 
        which defines how many microsteps correspond to one full step. 
        The provided value will override the corresponding setting from the Tic’s non-volatile memory until the next Reset 
        (or Reinitialize) command or full microcontroller reset.
        """
        return ticcmd("--step-mode", str(step_size))

    def _get_data(self):
        """
        This command reads a block of data from the Tic’s variables; 
        the block starts from the specified offset and can have a variable length.
        """
        return ticcmd("--status", "--full")


class PowerUpSafeStart():
    def __init__(self, controller, energize=True, safe_start=True):
        self.controller = controller
        self.energize = energize
        self.safe_start = safe_start

    def __enter__(self):
        if self.energize:
            self.controller.energize()

        if self.safe_start:
            self.controller.exit_safe_start()

        return self

    def __exit__(self, type, value, traceback):
        if self.safe_start:
            self.controller.enter_safe_start()
        
        if self.energize:
            self.controller.deenergize()


class TicController(_TicController):
    """
    Convenience wrapper for using Pololu Tic Motor Controllers through the ticcmd command line tool.
    """

    def __init__(self, min_position=-2000, max_position=2000, velocity=10000, move_size=200, step_size=StepSizes.ONEHALF, power_up_down=True, safe_start=True):
        super(TicController, self).__init__()
        self.min_position = min_position
        self.max_position = max_position
        self.power_up_down = power_up_down
        self.velocity = velocity
        self.step_size = step_size
        self.position = 0
        self.move_size = 200
        self.safe_start = safe_start

    def move_up(self):
        """
        Moves up the step size specified in move_size
        """
        new_position = self.position + self.move_size

        self.move(new_position=new_position)

    def move_down(self):
        """
        Moves down the step size specified in move_size
        """
        new_position = self.position - self.move_size

        self.move(new_position=new_position)

    def move(self, new_position):
        if self.min_position < new_position < self.max_position:
            self.position = new_position

            with PowerUpSafeStart(self, energize=self.power_up_down, safe_start=self.safe_start): 
                return self._set_target_position(new_position)

    def move_up_continuous(self):
        """
        Starts the motor moving forward at the default velocity
        """
        self.move_continuous(self.velocity)

    def move_down_continuous(self):
        """
        Starts the motor moving backwards at the default velocity
        """
        return self.move_continuous(-1*self.velocity)

    def move_continuous(self, velocity):

        # TODO: add velocity checks
        with PowerUpSafeStart(self, energize=self.power_up_down, safe_start=self.safe_start): 
            return self._set_target_velocity(velocity)

    def increase_step_size(self):
        """
        Increases the step size
        """
        step_size = self.step_size + 1

        self.set_step_size(step_size)
    
    def decrease_step_size(self):
        """
        Decreases the step size
        """
        step_size = self.step_size - 1

        self.set_step_size(step_size)
    
    def set_step_size(self, size):
        if StepSizes.MIN < size < StepSizes.MAX:
            self.step_size = size
            return self._set_step_mode(size)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    controller = TicController()

    controller.move_up()

    print(controller.position)
    controller.move_down()

    print(controller.position)
    controller.move_up_continuous()
