import time

def executiontimer(method):
    def wrapper(instance):
        start = time.perf_counter()

        method(instance)

        end = time.perf_counter()

        elapsed = end - start

        print(f"Execution time: {elapsed:.6f} seconds")

    return wrapper





class test:
    @executiontimer
    def test2(self):
        for i in range(10000):
            pass
        print("finished")




t = test()
t.test2()