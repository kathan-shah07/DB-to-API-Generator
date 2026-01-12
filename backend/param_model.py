from pydantic import create_model, Field, constr


def build_params_model(model_name: str, params_json: list):
    """Return a Pydantic model class built from params_json description.

    Supports simple constraints in params_json:
      - for strings: min_length, max_length, strip (bool)
      - for numbers: min (>=), max (<=)

    Always injects optional pagination fields `limit` and `offset` when not present.
    params_json: [{name,in,type,required?,default?, min?, max?, min_length?, max_length?, strip?}, ...]
    """
    fields = {}

    for p in params_json or []:
        fname = p.get("name")
        if not fname:
            continue
        ptype = (p.get("type") or "string").lower()
        required = p.get("required", True)
        default_val = p.get("default", ... if required else None)

        if ptype == "string":
            min_len = p.get("min_length")
            max_len = p.get("max_length")
            strip = p.get("strip", True)
            if min_len is not None or max_len is not None or strip:
                # use constrained string to apply trimming and length
                str_type = constr(strip_whitespace=bool(strip), min_length=min_len or None, max_length=max_len or None)
                fields[fname] = (str_type, default_val)
            else:
                fields[fname] = (str, default_val)

        elif ptype == "integer":
            ge = p.get("min")
            le = p.get("max")
            fld = Field(default_val if default_val is not ... else ..., ge=ge, le=le)
            fields[fname] = (int, fld)

        elif ptype == "number":
            ge = p.get("min")
            le = p.get("max")
            fld = Field(default_val if default_val is not ... else ..., ge=ge, le=le)
            fields[fname] = (float, fld)

        elif ptype == "boolean":
            fields[fname] = (bool, default_val)

        else:
            # fallback to string
            fields[fname] = (str, default_val)

    # Inject pagination params if not present
    if "limit" not in fields:
        fields["limit"] = (int, Field(100, ge=0))
    if "offset" not in fields:
        fields["offset"] = (int, Field(0, ge=0))

    return create_model(model_name, **fields)
