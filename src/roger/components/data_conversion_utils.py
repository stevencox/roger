from typing import Any


class TypeConversionUtil:

    type_map = {
        list.__name__: {
            'priority': 0,
            'constructor': lambda x: list([x])
        },
        str.__name__: {
            'priority': 1,
            'constructor': lambda x: str(x)
        },
        bool.__name__: {
            'priority': 2,
            'constructor': lambda x: True if x else False
        },
        float.__name__: {
            'priority': 2,
            'constructor': lambda x: float(x),
        },
        int.__name__: {
            'priority': 2,
            'constructor': lambda x: int(x)
        },
        type(None).__name__: {
            'priority': 3,
            'constructor': lambda x: '',
        }
    }

    @staticmethod
    def cast(value: Any, to_type: str):
        """
        Parses a value to dest type.
        :param value: value to parse
        :param to_type: destination type
        :return: parsed value
        """
        if to_type not in TypeConversionUtil.type_map:
            raise TypeError(f'Type {to_type} not found in conversion map. Available types are {TypeConversionUtil.type_map.keys()}')
        dest_type_constructor = TypeConversionUtil.type_map[to_type]['constructor']
        return dest_type_constructor(value)

    @staticmethod
    def compare_types(data_type: str, data_type_2: str):
        """
        Of two python types selects the one we would like to upcast to.
        :param data_type:
        :param data_type_2:
        :return:
        """
        assert data_type in TypeConversionUtil.type_map, f"Unrecognised type {data_type} From types:" \
                                                         f"{list(TypeConversionUtil.type_map.keys())}"

        assert data_type_2 in TypeConversionUtil.type_map, f"Unrecognised type {data_type} From types: " \
                                                           f"{list(TypeConversionUtil.type_map.keys())}"

        d1_val = TypeConversionUtil.type_map[data_type]['priority']
        d2_val = TypeConversionUtil.type_map[data_type_2]['priority']

        if data_type != data_type_2 and d1_val == d2_val:
            # For float int and bool have same priority
            # treat them as strings.
            d1_val = (d1_val - 1)
            data_type = str.__name__

        return data_type if d1_val < d2_val else data_type_2
