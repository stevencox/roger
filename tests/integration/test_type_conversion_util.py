from roger.components.data_conversion_utils import TypeConversionUtil


def test_type_comparision():
    datatype_1 = list.__name__
    datatype_2 = str.__name__
    datatype_3 = bool.__name__
    datatype_4 = float.__name__
    datatype_5 = int.__name__
    # list should always come first
    assert datatype_1 == TypeConversionUtil.compare_types(datatype_1, datatype_2)
    assert datatype_1 == TypeConversionUtil.compare_types(datatype_1, datatype_3)
    assert datatype_1 == TypeConversionUtil.compare_types(datatype_1, datatype_4)
    assert datatype_1 == TypeConversionUtil.compare_types(datatype_1, datatype_5)

    # then string
    assert datatype_2 == TypeConversionUtil.compare_types(datatype_2, datatype_3)
    assert datatype_2 == TypeConversionUtil.compare_types(datatype_2, datatype_4)
    assert datatype_2 == TypeConversionUtil.compare_types(datatype_2, datatype_5)

    # the rest should always be casted up to string
    assert datatype_2 == TypeConversionUtil.compare_types(datatype_3, datatype_4)
    assert datatype_2 == TypeConversionUtil.compare_types(datatype_4, datatype_5)
    assert datatype_2 == TypeConversionUtil.compare_types(datatype_5, datatype_3)

    # should raise error when sent 'Unknown' data types
    bogus_dt = "bogus"
    try:
        TypeConversionUtil.compare_types(bogus_dt, datatype_1)
    except AssertionError as error:
        exception_raised = True
    assert exception_raised
    try:
        TypeConversionUtil.compare_types(datatype_1, bogus_dt)
    except AssertionError as error:
        exception_raised = True
    assert exception_raised


def test_casting_values():
    castable = [
        ["True", bool.__name__, True],
        [1 , bool.__name__, True],
        [1.0, bool.__name__, True],
        [[], bool.__name__, False]
    ]
    for items in castable:
        assert items[-1] == TypeConversionUtil.cast(*items[:-1])  # cast (value, type)

