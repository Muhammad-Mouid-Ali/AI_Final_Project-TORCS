import msgParser
import carState
import carControl

class Driver(object):
    '''
    A driver object for the SCRC
    '''

    def __init__(self, stage):
        '''Constructor'''
        self.WARM_UP = 0
        self.QUALIFYING = 1
        self.RACE = 2
        self.UNKNOWN = 3
        self.stage = stage

        self.parser = msgParser.MsgParser()
        self.state = carState.CarState()
        self.control = carControl.CarControl()

        self.steer_lock = 0.785398
        self.max_speed = 100
        self.prev_rpm = None

    def init(self):
        '''Return init string with rangefinder angles'''
        self.angles = [0 for _ in range(19)]

        for i in range(5):
            self.angles[i] = -90 + i * 15
            self.angles[18 - i] = 90 - i * 15

        for i in range(5, 9):
            self.angles[i] = -20 + (i - 5) * 5
            self.angles[18 - i] = 20 - (i - 5) * 5

        return self.parser.stringify({'init': self.angles})

    def drive(self, msg):
        self.state.setFromMsg(msg)
        self.steer()
        self.gear()
        self.speed()
        return self.control.toMsg()

    def steer(self):
        angle = self.state.angle
        dist = self.state.trackPos

        if angle is not None and dist is not None:
            self.control.setSteer((angle - dist * 0.5) / self.steer_lock)
        else:
            self.control.setSteer(0.0)

    def gear(self):
        rpm = self.state.getRpm()
        gear = self.state.getGear()

        if rpm is None or gear is None:
            self.control.setGear(1)
            return

        if self.prev_rpm is None:
            up = True
        else:
            up = (self.prev_rpm - rpm) < 0

        if up and rpm > 7000:
            gear += 1
        if not up and rpm < 3000:
            gear -= 1

        gear = max(1, gear)  # Avoid non-positive gear
        self.control.setGear(gear)
        self.prev_rpm = rpm

    def speed(self):
        speed = self.state.getSpeedX()
        accel = self.control.getAccel()

        if speed is None:
            self.control.setAccel(0.0)
            return

        if speed < self.max_speed:
            accel = min(accel + 0.1, 1.0)
        else:
            accel = max(accel - 0.1, 0.0)

        self.control.setAccel(accel)

    def onShutDown(self):
        pass

    def onRestart(self):
        pass
