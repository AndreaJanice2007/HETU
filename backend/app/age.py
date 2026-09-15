from datetime import date


def age_from_dob(dob: date, today: date | None = None) -> int:
    today = today or date.today()
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years


def is_minor(dob: date, today: date | None = None) -> bool:
    return age_from_dob(dob, today) < 18
