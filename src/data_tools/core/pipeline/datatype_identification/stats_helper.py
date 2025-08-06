# ====================================================================
# mode: To compute the mode for the given data
# Parameters: 
#     axis - Computation based on row or column level axis
#     pre_sorted - sort the data or not
# ====================================================================

def mode(axis, pre_sorted: bool = False):
    if not pre_sorted:
        axis = sorted(axis)

    _count_max = 1
    _count = 0
    _mode = _current = axis[0]

    for v in axis:
        if v == _current:
            _count = _count + 1
        else:
            if _count > _count_max:
                _count_max = _count
                _mode = _current
            _count = 1
            _current = v

    if _count > _count_max:
        return _current
    
    return _mode
