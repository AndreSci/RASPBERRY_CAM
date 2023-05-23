import time


class BarrierClass:

    def __init__(self):
        self._open = 'Open Barrier'
        self._close = 'Close Barrier'

    def open(self):
        # TODO тут должна быть релюшка
        # time.sleep(5)
        pass

    def close(self):
        print(self._close)

    def get_status(self):
        print("GET_STATUS")
