from pydantic import BaseModel, ConfigDict


def to_camel_case(value: str) -> str:
    words = value.split("_")
    return words[0] + "".join(word.capitalize() for word in words[1:])


class ApiSchema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)


class ApiReadSchema(ApiSchema):
    model_config = ConfigDict(
        alias_generator=to_camel_case,
        populate_by_name=True,
        from_attributes=True,
    )
