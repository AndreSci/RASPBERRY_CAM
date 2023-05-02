
import datetime


def timer_function(function):

    def wrapped(*args):
        start_time = datetime.datetime.now()
        res = function(*args)

        end_time = datetime.datetime.now()
        delta_time = end_time - start_time
        print(f"Скорость работы функции {function.__name__}: {delta_time.total_seconds()} секунд.")
        return res

    return wrapped
