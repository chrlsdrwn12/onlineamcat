import datetime

def now():
    x = datetime.datetime.today()
    return datetime.datetime.strftime(x, '%Y-%m-%d-%H-%M-%S')

def validate_date(date_text):
    try:
        d = datetime.datetime.strptime(date_text, '%Y-%m-%d')
    except ValueError:
        d = None
    return d

def date_add_days(date_str, days, weekends=True):
    if days == 0:
        return date_str
    if weekends:
        start_date_obj = str_to_dateobj(date_str)
        enddate = start_date_obj + datetime.timedelta(days=int(days))
    else:
        count = 0
        enddate = str_to_dateobj(date_str)
        inc = 1
        if days < 0:
            inc = -1
        while count != days:
            enddate = enddate + datetime.timedelta(days=inc)
            #print (enddate, enddate.isoweekday())
            if enddate.isoweekday() in [1,2,3,4,5]:
                count += inc
    return '{}'.format(enddate)

def str_to_dateobj(day): # Convert the string 'yyyy-mm-dd' to datetime.date
    return datetime.date(int(day[0:4]), int(day[5:7]),int(day[8:10]))
    #return datetime.datetime.strptime(day, '%Y-%m-%d')

def days_between_dates(start, end, weekends=False):
    #print ('Days between', start, end)
    days = 0
    if start < end:
        temp = str_to_dateobj(start)
        target = str_to_dateobj(end)
        while temp < target:
            if temp.isoweekday() in [1,2,3,4,5]:
                days += 1
            temp = temp + datetime.timedelta(days=1)
    return days

def get_month():
    # Get current month
    month = datetime.datetime.now().strftime("%m")
    print (month)
    return month

if __name__ == '__main__':
    # Test add dayd, ignore weekends
    day = '2016-09-18'
    add = 3
    print (date_add_days(day,add))
    print (date_add_days(day,add, weekends=False))
