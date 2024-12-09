"""Utils for consuming the API"""
from typing import Dict, Any, Callable, Optional

def try_get_from_dict(data: Dict[str, Any], key: str, fallback: Any, conversion: Optional[Callable[[Any], Any]] = None) -> Any:
    """Try to get value from dict, otherwise return fallback value"""
    if not key in data:
        return fallback
    
    value = data[key]
    if value is None:
        return fallback
    if conversion is None:
        return value
    return conversion(value)
