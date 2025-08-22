# Flag default set to True
_is_first = True


# Function to return the is_first flag
def is_first() -> bool:
    return _is_first


# Function to set the is_first flag
def set_first():
    global _is_first
    _is_first = False


# Function to reset the is_first flag
def reset_first():
    global _is_first
    _is_first = True
