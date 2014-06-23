


@contextmanager
def retries(numrestries=3):
    for i in range(0, numretries-1):
        try:
            yield 1
            break
        except:
            pass


