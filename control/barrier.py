

class BarrierClass:

    def __init__(self):
        self.open = 'Open Barrier'
        self.close = 'Close Barrier'

    def open(self):
        # TODO тут должна быть релюшка
        print(self.open)

    def close(self):
        print(self.close)

    def get_status(self):
        print("GET_STATUS")
