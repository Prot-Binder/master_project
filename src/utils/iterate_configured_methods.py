from dataclasses import fields
def _configured_method_names(cfg) -> list[str]:
    method_names = []
    for method_field in fields(cfg.methods):
        method_cfg = getattr(cfg.methods, method_field.name)
        if method_cfg is not None:
            method_names.append(method_field.name)
    return method_names