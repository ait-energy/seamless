import demographic_stats_AUT_VIE as ds
from i_utils import to_date

from itertools import count

from enum import Enum
import logging
from numpy.random import choice, normal
from numpy import ceil
from operator import attrgetter


class ActivityType(Enum):
    work = "Work"
    home = "Home"
    meeting = "Meeting"
    private = "Private"


class Timeperiod(object):
    def __init__(self, begin, end, loc, activity):
        self.begin = begin
        self.end = end
        self.loc = loc
        self.activity = activity

    def during(self, ts, grace_minutes=0):
        return ts >= self.begin-grace_minutes and ts <= self.end+grace_minutes

    def minutes(self):
        return self.end - self.begin

    def to_dict(self):
        return vars(self).copy()

    def __str__(self):
        return "{:}-{:} {:} loc {:}".format(to_date(self.begin), to_date(self.end), self.activity.name, self.loc)


class Schedule(object):
    def __init__(self):
        self.items = []

    def add(self, act):
        temp = self.items.copy()
        temp.append(act)
        self.items = sorted(temp, key=attrgetter("begin"))

    def remove(self, act):
        self.items.remove(act)

    def get_all(self, type):
        return [x for x in self.items if x.activity is type]

    def get(self):
        return self.items.copy()


class Fleet(object):
    def __init__(self, number_employees, car_types, ecar_types):
        while True:
            self.n_bikes = int(choice(list(range(0, int(number_employees * 0.15)))))

            for i in range(car_types):
                key = "car_{:}".format(i)
                val = int(choice(list(range(0, max(1, int(number_employees * 0.15))))))
                self.__dict__[key] = val

            for i in range(ecar_types):
                key = "ecar_{:}".format(i)
                val = int(choice(list(range(0, max(1, int(number_employees * 0.15))))))
                self.__dict__[key] = val

            self.sum_cars = self._sum("car_")
            self.sum_ecars = self._sum("ecar_")

            if self.sum_cars + self.sum_ecars > number_employees:
                False
            else:
                break

    def _sum(self, prefix):
        sum = 0
        for x in vars(self):
            if x.startswith(prefix):
                sum += vars(self)[x]
        return sum

    def to_dict(self):
        return vars(self).copy()


class Company(object):
    def __init__(self, nmbemp, offices, fleet, boss_perc=0.01, middle_manag=0.1):
        self.offices = offices
        self.fleet = fleet

        self.employees = list()
        self.create_employees(nmbemp, boss_perc, middle_manag)

    def create_employees(self, number_employees, boss_perc, middle_manag):
        bosses = max(int(number_employees*boss_perc), 1)  # at least one boss
        middle = int(number_employees*middle_manag)
        workers = number_employees-bosses-middle

        logging.info("creating {:} worker(s), {:} middle management and {:} boss(es)".format(workers, middle, bosses))

        unique_id = count(start=1)

        self._create(bosses, ds.EmployeeType.boss, unique_id)
        self._create(middle, ds.EmployeeType.middle_management, unique_id)
        self._create(workers, ds.EmployeeType.worker, unique_id)

        self._create_external_meetings()

    def _create_external_meetings(self):
        """
        Bosses, middle management and some workers "generate" external meetings.
        The remaining workers join those meetings.

        Some meetings occur at another business site, if available.

        Private activities before and after work are drawn from a normaldist

        """
        mc = MeetingCoordinator()# TODO: The remaining workers join those meetings.

        for e in self.employees:
            logging.info("CREATE {:} {:}: {:} weekly hours, {:} meeting hours".format(e.type.name, e.id, e.weekly_minutes / 60,  e.meeting_minutes / 60))
            create_private_activity_for_employee(e)
            mc.create_meetings_for(e)
            logging.info("FINISH {:} {:}: {:} weekly hours, {:} meeting hours".format(e.type.name, e.id, e.weekly_minutes/60, e.meeting_minutes/60))
        logging.info("{:} external meetings created".format(len(mc.meetings)))

    def _create(self, c, type, unique_id):
        for i in range(c):
            office = int(choice(self.offices))
            self.employees.append(create_employee(next(unique_id), office, type))

    def sum_cars(self):
        return self.fleet.sum_cars

    def sum_ecars(self):
        return self.fleet.sum_ecars

    def to_dict(self):
        d = dict()
        for k, v, in self.fleet.to_dict().items():
            d[k] = str(v)
        d["office"] = str(self.offices)
        d["nmbemp"] = str(len(self.employees))
        return d


class Employee(object):
    def __init__(self, id, age, gender, type, weekly_min, begin, working_days, meeting_minutes, home, office, mot_prefs):
        self.id = id
        self.age = int(age)
        self.gender = gender
        self.type = type
        self.weekly_minutes = int(weekly_min)
        self.begin = int(begin)
        self.working_days = int(working_days)
        self.meeting_minutes = meeting_minutes
        self.home = home
        self.office = office
        self.mot_preferences = mot_prefs
        self.daily_minutes = round((self.weekly_minutes / self.working_days), 2)

        self.schedule = Schedule()
        for i in range(self.working_days):
            work_begin = self.begin + i * 1440
            work_end = work_begin + self.daily_minutes
            arrival_home = work_end + ds.TT_BUFFER_MIN
            next_day_work_begin = self.begin + (i + 1) * 1440 - ds.TT_BUFFER_MIN

            self.schedule.add(Timeperiod(work_begin, work_end, self.office, ActivityType.work))
            self.schedule.add(Timeperiod(arrival_home, next_day_work_begin, self.home, ActivityType.home))

    def replace_in_schedule(self, workperiod, meeting):
        leave_for_meeting = meeting.begin - ds.TT_BUFFER_MIN
        next_start = meeting.end + ds.TT_BUFFER_MIN

        self.schedule.remove(workperiod)
        self.schedule.add(Timeperiod(workperiod.begin, leave_for_meeting, workperiod.loc, workperiod.activity))
        self.schedule.add(meeting)
        if meeting.end < workperiod.end:
            self.schedule.add(Timeperiod(next_start, workperiod.end, workperiod.loc, workperiod.activity))

    def _update_meeting_minutes(self):
        self.meeting_minutes = sum([w.minutes() for w in self.schedule.get_all(ActivityType.meeting)])
        assert self.meeting_minutes >= 0

    def to_dict(self):
        d = vars(self).copy()
        d["type"] = self.type.name
        d["gender"] = self.gender.name
        d.update(self.mot_preferences.to_types_dict())

        d.pop("schedule")
        d.pop("mot_preferences")
        return d

    def __str__(self):
        return str(self.to_dict())


class MeetingCoordinator(object):
    def __init__(self, p_joins_meeting=0.3):
        self.joins_meeting = [True, False]
        self.p_joins_meeting = [p_joins_meeting, 1-p_joins_meeting]
        self.meetings = []
        self.joined_meetings = []

    def create_meeting(self, begin, end, location):
        m = Timeperiod(begin, end, location, ActivityType.meeting)
        self.meetings.append(m)
        return m

    def try_to_join_existing_meetings(self, employee):
        max_join = choice(list(range(0, 7)))
        i = 0

        for m in self.meetings:
            for wp in employee.schedule.get_all(ActivityType.work):
                wbm = 15
                meeting_duration = m.minutes()

                if i < max_join and employee.meeting_minutes > 0 \
                        and m.end == wp.end \
                        and (wp.begin+wbm+ds.TT_BUFFER_MIN) <= m.begin:
                    if bool(choice(self.joins_meeting, p=self.p_joins_meeting)):
                        logging.info("joined {:}".format(m))

                        employee.replace_in_schedule(wp, m)
                        i += 1
                        employee.meeting_minutes -= meeting_duration

    def update_worker_schedule(self, e, workperiod, meeting_dur, work_before_meet):
        meeting_loc = ds.office_location(exclude=[workperiod.loc])

        leave_for_meeting = workperiod.begin + work_before_meet
        meeting_start = leave_for_meeting + ds.TT_BUFFER_MIN
        meeting_end = meeting_start + meeting_dur
        next_start = meeting_end + ds.TT_BUFFER_MIN

        if next_start >= workperiod.end:  # if meeting at the end of workperiod, return to work is not possible
            meeting_end = workperiod.end  # so meeting will last until end of workperiod

        meeting = self.create_meeting(meeting_start, meeting_end, meeting_loc)

        e.replace_in_schedule(workperiod, meeting)
        e.meeting_minutes -= meeting.minutes()

    def create_meetings_for(self, e):

        self.try_to_join_existing_meetings(e)

        retries = 30
        while retries > 0:
            workperiod = choice(e.schedule.get_all(ActivityType.work))  # pick random work period
            meeting_dur = min(ds.pick_meeting_duration(), e.meeting_minutes)
            retries -= 1

            before_meeting = int(choice([30, 60, 90]))
            if e.meeting_minutes > 0 and ds.fits_inside(workperiod.minutes(), before_meeting, meeting_dur):
                self.update_worker_schedule(e, workperiod, meeting_dur, work_before_meet=before_meeting)

        e._update_meeting_minutes()  # because this value might change during creation to adher to time restrictions


def create_company(number_employees, car_types=3, ecar_types=3, offices=1):
    fleet = Fleet(number_employees, car_types=car_types, ecar_types=ecar_types)

    office_location = []
    for _ in range(offices):
        office_location.append(ds.office_location())

    return Company(number_employees, office_location, fleet, boss_perc=0.01, middle_manag=0.1)


def create_employee(id, office, emp_type):
    gender = ds.pick_gender()
    age = ds.pick_age(gender)
    weekly_minutes, work_days = ds.weekly_minutes_and_days_per_week(gender, emp_type)

    begin = ds.work_begin()
    home = ds.home_location()
    mp = ds.create_mot_preferences_vienna(gender)

    mu = emp_type.value
    sigma = mu/6
    perc = pick_from_normal(mu, sigma)
    meeting_minutes = max(0, round_to_minutes(weekly_minutes*perc, minutes=30))  # np.ceil(weekly_minutes*perc)//30*30

    return Employee(id, age, gender, emp_type, weekly_minutes, begin, work_days, meeting_minutes, home, office, mp)


def create_private_activity_for_employee(e):
    for w in e.schedule.get_all(ActivityType.home):
        if ds.private_meeting_morning():
            create_activity_morning(w, e.schedule, exclude_locs=[e.home, e.office])

    for w in e.schedule.get_all(ActivityType.home):
        if ds.private_meeting_evening():
            create_activity_evening(w, e.schedule, exclude_locs=[e.home, e.office])


def create_activity_morning(w, schedule, exclude_locs, duration=60):
    loc = ds.home_location(exclude=exclude_locs)
    dur = duration
    priv_start = w.end - dur
    w_end = priv_start - ds.TT_BUFFER_MIN

    schedule.remove(w)
    schedule.add(Timeperiod(w.begin, w_end, w.loc, ActivityType.home))
    schedule.add(Timeperiod(priv_start, w.end, loc, ActivityType.private))


def create_activity_evening(w, schedule, exclude_locs, duration=120):
    loc = ds.home_location(exclude=exclude_locs)
    dur = duration
    priv_end = w.begin + dur
    w_start = priv_end + ds.TT_BUFFER_MIN

    schedule.remove(w)
    schedule.add(Timeperiod(w.begin, priv_end, loc, ActivityType.private))
    schedule.add(Timeperiod(w_start, w.end, w.loc, ActivityType.home))


def round_to_minutes(x, minutes):
    return ceil(x) // minutes * minutes


def pick_from_normal(mu, sigma):
    return (normal(mu, sigma, 1)[0]) / 100
