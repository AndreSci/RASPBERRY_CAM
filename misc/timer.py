import datetime


def timer_function(function):
    """ Декоратор для подсчета времени выполнения функции """

    def wrapped(*args):
        start_time = datetime.datetime.now()
        res = function(*args)

        end_time = datetime.datetime.now()
        delta_time = (end_time - start_time).total_seconds()
        print(f"Скорость работы функции {function.__name__}: {delta_time} секунд.")
        return res

    return wrapped
