import wiringpi
import time
from enum import Enum


BARRIER_PIN = 1
HIGH = 1
LOW = 0

OUTPUT = 1
INPUT = 0

SUCCESS = 1
WARN = 2


class WiringNotInit(Exception):
    "wiringPi isnt initialized"
    pass


class WiringCantInit(Exception):
    "wiringPi cant initialized"
    pass


class UnknownException(Exception):
    "Unknown exception in gpio"
    pass


class GPIO:
    """Класс для работы с GPIO"""

    def __init__(self):
        try:
            wiringpi.wiringPiSetup()
            self.is_init = True
            # set pin barrier to output
            self.set_pin_mode(BARRIER_PIN, OUTPUT)
            self.set_pin_output(BARRIER_PIN, LOW)
        except Exception as e:
            print(e)
            self.is_init = False
            raise WiringCantInit

    def open_barrier(self, pin=BARRIER_PIN):
        """Функция открытия шлагбаума возвращает SUCCESS, если шлагбаум принял команду,
            возвращает ERROR, если произошла ошибка выполения и возвращает 
            WARN, если идет отправка на открытие, а реле уже дала эту команду

        """
        ret = WARN
        if self.is_init:
            try:
                if self.read_pin(pin) == LOW:
                    self.set_pin_output(pin, HIGH)
                    time.sleep(5)
                    self.set_pin_output(pin, LOW)
                    ret = SUCCESS
                return ret
            except Exception as e:
                print(e)
                raise UnknownException
        else:
            raise WiringNotInit

    def read_pin(self, pin):
        """Функция чтения GPIO-пина возвращает либо HIGH либо LOW"""
        if self.is_init:
            try:
                return wiringpi.digitalRead(pin) 
            except Exception as e:
                print(e)
                raise UnknownException
        else:
            raise WiringNotInit

    def set_pin_mode(self, pin, mode):
        """Func to set mode to pin 1 - Output 0 - Input"""
        if self.is_init:
            try:
                wiringpi.pinMode(pin, mode)
            except Exception as e:
                print(e)
                raise UnknownException
        else:
            raise WiringNotInit

    def set_pin_output(self, pin, output):
        """Func to set pin output High (1) and Low to Low (0)"""
        if self.is_init:
            try:
                wiringpi.digitalWrite(pin, output)
            except Exception as e:
                print(e)
                raise UnknownException
        else:
            raise WiringNotInit

