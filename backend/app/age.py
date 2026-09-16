from datetime import date


def age_from_dob(dob: date, today: date | None = None) -> int:
    today = today or date.today()
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years


def is_minor(dob: date | None, today: date | None = None) -> bool:
    if dob is None:
        return False
    return age_from_dob(dob, today) < 18


def dob_from_age(age: int, today: date | None = None) -> date:
    today = today or date.today()
    years = int(age)
    if years < 1 or years > 120:
        raise ValueError("Age must be between 1 and 120.")
    try:
        return date(today.year - years, today.month, today.day)
    except ValueError:
        return date(today.year - years, 2, 28)
