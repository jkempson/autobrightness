import time
import math
import os
from threading import Thread, Lock


def find(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)


def clamp(n, minn, maxn):
    return max(min(maxn, n), minn)


def read_line(filename):
    with open(filename) as f:
        return int(f.readline().strip())


def set_brightness(value):
    f = open(file_cur_bright, 'wt')
    n = f.write(str(value))
    f.close()


def set_ambient_light_max(value):
    f = open(file_ambient_max, 'wt')
    n = f.write(str(value))
    f.close()


def critically_damped_spring(target, current, velocity, timestep):
    current_to_target = target - current
    spring_force = current_to_target * spring_constant
    damping_force = -velocity * 2 * math.sqrt(spring_constant)
    force = spring_force + damping_force
    velocity += force * timestep
    displacement = velocity * timestep
    return velocity, current + displacement


def ambient_poller(delay=1):
    global ambient_light
    while True:
        lock.acquire()
        ambient_light = read_line(file_illum)
        lock.release()
        time.sleep(delay)


def brightness_adjust():
    global ambient_light

    max_brightness = read_line(file_max_bright) - 1
    brightness = read_line(file_cur_bright)

    if os.path.isfile(file_ambient_max):
        ambient_max_level = read_line(file_ambient_max)
    else:
        ambient_max_level = brightness

    velocity = 0

    while True:
        lock.acquire()
        tmp_al = ambient_light
        lock.release()
        current_brightness = read_line(file_cur_bright)
        brightness_perc = brightness / max_brightness
        ambient_perc = clamp(tmp_al / ambient_max_level, 0, 1)

        if int(brightness) != current_brightness:
            if ambient_perc > 0.005:
                ambient_max_level = int(tmp_al * (1 / (current_brightness / max_brightness))) + 1
                print("Sensor max level changed to:", ambient_max_level)
                set_ambient_light_max(ambient_max_level)
            brightness = current_brightness
            target = current_brightness
            velocity = 0
            sleep_time = 1
        else:
            target = (max_brightness * ambient_perc)

            if abs(ambient_perc - brightness_perc) <= target_reached_allowance and abs(velocity) < 100:
                sleep_time = 1
                velocity = 0
            else:
                sleep_time = 0.01
                velocity, brightness = critically_damped_spring(target, brightness, velocity, sleep_time)

            print("Current %:", round(brightness_perc * 100, 1),
                  "\t Target %:", round(ambient_perc * 100, 1), "\t Raw brightness:", int(brightness), "\t Raw target:", int(target), "\tRaw ambient:", ambient_light, "\t Sensor max level:", ambient_max_level, "\t Velocity:", int(velocity))

            brightness = clamp(brightness, 1, max_brightness)
            set_brightness(int(brightness))

        time.sleep(sleep_time)


file_max_bright = '/sys/class/backlight/intel_backlight/max_brightness'
file_cur_bright = '/sys/class/backlight/intel_backlight/brightness'
file_ambient_max = 'ambient_max'
file_illum = find('in_illuminance_raw', '/sys/devices/')

ambient_light = 0
spring_constant = 0.5
target_reached_allowance = 0.03
lock = Lock()

for func in (ambient_poller, brightness_adjust):
    t = Thread(target=func)
    t.setDaemon(True)
    t.start()

while True:
    time.sleep(600)
