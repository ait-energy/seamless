from datetime import datetime, timedelta

def h2min(h):
    return h*60


a_monday = datetime.strptime("2017-07-03", "%Y-%m-%d")


def to_date(m):
    d = a_monday + timedelta(minutes=m)
    return d.strftime("%a %H:%M:%S")
