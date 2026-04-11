from dataclasses import fields
def get_configured_method_names(cfg) -> list[str]:
    method_names = []
    for method_field in fields(cfg.methods):
        method_cfg = getattr(cfg.methods, method_field.name)
        if method_cfg is not None:
            method_names.append(method_field.name)
    _sorted_method_names = _sort_methods_by_order(method_names)
    return _sorted_method_names

# this function ensures that eq is invoked before pull and pull before all other methods, as the remaining methods depend on it.
def _sort_methods_by_order(method_names) -> list[str]:
    sorted_methods = []
    priority_methods = ["eq", "pull"]
    if "eq" in method_names:
        sorted_methods.append("eq")
    if "pull" in method_names:
        sorted_methods.append("pull")
    for method_name in method_names:
        if method_name not in priority_methods:
            sorted_methods.append(method_name)
    return sorted_methods