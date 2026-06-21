import re


_EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")
_PHONE_RE = re.compile(r"^[0-9+\-\s().]{7,20}$")


def normalize_email(email):
    return (email or '').strip().lower()


def normalize_username(username):
    return ' '.join((username or '').strip().split())


def normalize_phone(phone):
    if phone is None:
        return None

    phone = phone.strip()
    if not phone:
        return None

    cleaned = re.sub(r'[^0-9+]', '', phone)
    return cleaned or None


def validate_email(email):
    normalized = normalize_email(email)
    return bool(normalized) and bool(_EMAIL_RE.match(normalized))


def validate_phone(phone):
    if phone is None:
        return True

    phone = phone.strip()
    if not phone:
        return True

    return bool(_PHONE_RE.match(phone))


def validate_password_strength(password):
    password = password or ''
    errors = []

    if len(password) < 8:
        errors.append('at least 8 characters')
    if not re.search(r'[A-Z]', password):
        errors.append('one uppercase letter')
    if not re.search(r'[a-z]', password):
        errors.append('one lowercase letter')
    if not re.search(r'\d', password):
        errors.append('one number')
    if not re.search(r'[^\w\s]', password):
        errors.append('one special character')

    if errors:
        if len(errors) == 1:
            suffix = errors[0]
        else:
            suffix = ', '.join(errors[:-1]) + ' and ' + errors[-1]
        return False, 'Password must contain ' + suffix + '.'

    return True, ''
