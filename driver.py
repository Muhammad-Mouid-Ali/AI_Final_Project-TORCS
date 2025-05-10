import msgParser
import carState
import carControl
import csv
import os

class Driver(object):
    '''
    A driver object for the SCRC
    '''

    # Open the log file only once for telemetry logging
    # log_file_path = "telemetry_gspeedway_corolla.csv"
    # log_file_path = "telemetry_etrack3_peugeot.csv"
    log_file_path = "telemetry_dirt2_mitsubishilancer.csv"
    log_file = open(log_file_path, mode='w', newline='')
    csv_writer = csv.writer(log_file)
    csv_writer.writerow([
        'speedX', 'trackPos', 'angle', 'rpm', 'gear',
        *['track_' + str(i) for i in range(19)],
        *['opponent_' + str(i) for i in range(36)],
        'accel', 'brake', 'steer', 'gear_out'
    ])

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

        # Log telemetry data
        try:
            speedX = self.state.getSpeedX()
            trackPos = self.state.getTrackPos()
            angle = self.state.getAngle()
            rpm = self.state.getRpm()
            gear = self.state.getGear()
            track = self.state.getTrack() or [0.0] * 19
            opponents = self.state.getOpponents() or [200.0] * 36

            accel = self.control.getAccel()
            brake = self.control.getBrake()
            steer = self.control.getSteer()
            gear_out = self.control.getGear()

            if None not in (speedX, trackPos, angle, rpm, gear) and len(track) == 19 and len(opponents) == 36:
                Driver.csv_writer.writerow([
                    speedX, trackPos, angle, rpm, gear,
                    *track,
                    *opponents,
                    accel, brake, steer, gear_out
                ])
        except Exception as e:
            print(f"[WARNING] Telemetry log error: {e}")

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
        if Driver.log_file:
            Driver.log_file.close()
            print("[INFO] Telemetry log saved to telemetry_log.csv")

    def onRestart(self):
        pass
